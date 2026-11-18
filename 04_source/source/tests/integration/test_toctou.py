"""Regression tests for P026 P1-R1-01 (PDF TOCTOU) and the P2 image-enum
finding (R1 §4: image enumeration failure misreported as EMPTY).

Run from PACKAGE_ROOT, inside the venv::

    python -m pytest tests/integration/test_toctou.py -q

TOCTOU threat (GPT R1, reproduced before the fix): two synthetic PDFs
with the same byte size and the same physical page count but different
content. ``load_pdf`` verified PDF1's SHA-256; the file was then swapped
for PDF2; ``extract_pages`` re-opened the path and checked only the
page count, so the report bound PDF1's SHA to PDF2's extraction.

Fixed behaviour under test:

* ``extract_pages`` parses the exact bytes validated by ``load_pdf``
  (carried in ``PdfDocumentInfo.pdf_bytes``) — a swap after validation
  cannot change what is extracted, so the report SHA always matches
  the extracted bytes;
* any path re-read (info without carried bytes, or ``extract_pdf``
  given verified bytes + an expected hash) re-checks SHA-256 and
  rejects a swapped file with ``PdfInputError`` (``SHA_MISMATCH``)
  instead of analysing it — the CLI ``analyze`` path rejects it
  (exit 2, no report written);
* image enumeration failure is ``ERROR``, never ``EMPTY``.

The synthetic PDFs are built with pypdf only (a runtime dependency):
one Helvetica text line per page, same-length markers, so both files
come out byte-identical in size with different SHA-256.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import (  # noqa: E402
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

import pagetrace.cli as cli_module  # noqa: E402
from pagetrace.extract import (  # noqa: E402
    _extract_one_page,
    _page_has_images,
    extract_pages,
    extract_pdf,
)
from pagetrace.normalize import quote_sha256  # noqa: E402
from pagetrace.pdf_input import PdfInputError, load_pdf  # noqa: E402

QUOTE = "TOCTOU marker AAAAAAAA alpha"


# ---------------------------------------------------------------------------
# Synthetic PDFs: same size, same page count, different content
# ---------------------------------------------------------------------------

def _build_pdf(path: Path, marker: str) -> bytes:
    """Write a 2-page PDF whose pages carry *marker*; return its bytes.

    The two markers must be the same length, so the two PDFs come out
    the same size (pypdf writes no timestamps / random ids here).
    """
    writer = PdfWriter()
    for tag in ("alpha", "beta"):
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        })
        resources = DictionaryObject({
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}),
        })
        text = f"TOCTOU marker {marker} {tag}"
        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = writer._add_object(stream)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path.read_bytes()


@pytest.fixture()
def swapped_pair(tmp_path: Path):
    """(pdf_path, pdf1_bytes, pdf2_bytes): same size/pages, diff content."""
    pdf_path = tmp_path / "doc.pdf"
    pdf1 = _build_pdf(pdf_path, "AAAAAAAA")
    pdf2 = _build_pdf(tmp_path / "other.pdf", "BBBBBBBB")
    assert len(pdf1) == len(pdf2), "test PDFs must be the same size"
    assert hashlib.sha256(pdf1).hexdigest() != hashlib.sha256(pdf2).hexdigest()
    info = load_pdf(str(pdf_path))
    assert info.page_count == 2
    assert info.sha256 == hashlib.sha256(pdf1).hexdigest()
    return pdf_path, pdf1, pdf2


def _build_bundle(pdf_path: Path, pdf_bytes: bytes, tmp_path: Path) -> Path:
    """A minimal 1-citation PASS bundle for *pdf_bytes* (honest extraction)."""
    info, records = extract_pdf(str(pdf_path))
    assert info.sha256 == hashlib.sha256(pdf_bytes).hexdigest()
    bundle = {
        "schema": "pagetrace.bundle/v1",
        "case_id": "toctou-01",
        "document": {
            "file_name": pdf_path.name,
            "page_count": info.page_count,
            "sha256": info.sha256,
        },
        "page_semantics": {
            "canonical_field": "pdf_page_index0",
            "index_base": 0,
            "viewer_base": 1,
        },
        "citations": [
            {
                "citation_id": "cite-1",
                "chunk_id": "c-1",
                "index_record_id": "v-1",
                "quote_text": QUOTE,
            }
        ],
        "stages": {
            "extraction": [
                {
                    "pdf_page_index0": r.pdf_page_index0,
                    "pdf_page_label": r.pdf_page_label,
                    "text_sha256": r.text_sha256,
                    "text_state": r.text_state,
                }
                for r in records
            ],
            "chunking": [
                {
                    "chunk_id": "c-1",
                    "source_page_indices0": [0],
                    "text_sha256": quote_sha256(QUOTE),
                }
            ],
            "indexing": [
                {
                    "record_id": "v-1",
                    "pdf_page_label": records[0].pdf_page_label,
                    "source_page_indices0": [0],
                }
            ],
            "display": [
                {
                    "citation_id": "cite-1",
                    "citation_page_basis": "PDF_INDEX_0",
                    "citation_page_value": 0,
                    "viewer_page1": 1,
                }
            ],
            "missing_stages": [],
        },
    }
    out = tmp_path / "toctou-01.trace.json"
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# P1-R1-01: TOCTOU
# ---------------------------------------------------------------------------

def test_extract_pages_uses_verified_bytes_after_swap(swapped_pair):
    """Swap after validation: extraction still returns the VERIFIED bytes.

    The report SHA must match the bytes actually extracted — PDF2's
    content must never appear while the identity claims PDF1's SHA.
    """
    pdf_path, pdf1, pdf2 = swapped_pair
    sha1 = hashlib.sha256(pdf1).hexdigest()
    info = load_pdf(str(pdf_path))
    assert info.sha256 == sha1
    pdf_path.write_bytes(pdf2)  # swap AFTER verification
    records = extract_pages(info)
    assert info.sha256 == sha1
    assert any("AAAAAAAA" in (r.extracted_text or "") for r in records)
    assert not any("BBBBBBBB" in (r.extracted_text or "") for r in records)


def test_extract_pages_without_carried_bytes_rejects_swapped_file(
        swapped_pair):
    """No verified bytes carried: a path re-read must re-check the SHA.

    An info value built without ``pdf_bytes`` (older caller) still
    fails closed instead of extracting the swapped file.
    """
    pdf_path, pdf1, pdf2 = swapped_pair
    sha1 = hashlib.sha256(pdf1).hexdigest()
    info = load_pdf(str(pdf_path))
    stripped = dataclasses.replace(info, pdf_bytes=None)
    pdf_path.write_bytes(pdf2)  # swap AFTER validation
    with pytest.raises(PdfInputError) as excinfo:
        extract_pages(stripped)
    assert excinfo.value.reason == "SHA_MISMATCH"
    assert sha1 in str(excinfo.value)


def test_extract_pdf_rejects_swapped_file_with_expected_sha(swapped_pair):
    """Verified bytes + expected hash: a swap on disk is rejected."""
    pdf_path, pdf1, pdf2 = swapped_pair
    sha1 = hashlib.sha256(pdf1).hexdigest()
    pdf_path.write_bytes(pdf2)  # swap BEFORE extraction
    with pytest.raises(PdfInputError) as excinfo:
        extract_pdf(str(pdf_path), pdf_bytes=pdf1, expected_sha256=sha1)
    assert excinfo.value.reason == "SHA_MISMATCH"


def test_extract_pdf_with_verified_bytes_ignores_swapped_file(swapped_pair):
    """Verified bytes with no expected hash: extraction uses those bytes."""
    pdf_path, pdf1, pdf2 = swapped_pair
    pdf_path.write_bytes(pdf2)  # swap BEFORE extraction
    info, records = extract_pdf(str(pdf_path), pdf_bytes=pdf1)
    assert info.sha256 == hashlib.sha256(pdf1).hexdigest()
    assert any("AAAAAAAA" in (r.extracted_text or "") for r in records)
    assert not any("BBBBBBBB" in (r.extracted_text or "") for r in records)


def test_cli_report_sha_matches_extracted_bytes(tmp_path, swapped_pair,
                                                capsys):
    """No swap: ``analyze`` passes and the report SHA is the extracted PDF's."""
    pdf_path, pdf1, _pdf2 = swapped_pair
    sha1 = hashlib.sha256(pdf1).hexdigest()
    bundle = _build_bundle(pdf_path, pdf1, tmp_path)
    out = tmp_path / "out"
    rc = cli_module.main(["analyze", "--pdf", str(pdf_path),
                          "--trace", str(bundle), "--out", str(out)])
    assert rc == 0, capsys.readouterr().out
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["document"]["sha256"] == sha1
    assert report["results"][0]["verdict"] == "PASS"


def test_cli_rejects_swapped_pdf_same_size_same_pages(
        tmp_path, swapped_pair, monkeypatch, capsys):
    """Swap between hash verification and extraction: CLI rejects (exit 2).

    The swap is injected deterministically where the TOCTOU window was:
    ``cli.extract_pdf`` is wrapped so the file is replaced with the
    same-size, same-page-count PDF2 before the real extraction runs.
    No report may be written for the swapped file.
    """
    pdf_path, pdf1, pdf2 = swapped_pair
    bundle = _build_bundle(pdf_path, pdf1, tmp_path)
    out = tmp_path / "out"
    real_extract_pdf = cli_module.extract_pdf

    def _swap_then_extract(*args, **kwargs):
        pdf_path.write_bytes(pdf2)
        return real_extract_pdf(*args, **kwargs)

    monkeypatch.setattr(cli_module, "extract_pdf", _swap_then_extract)
    rc = cli_module.main(["analyze", "--pdf", str(pdf_path),
                          "--trace", str(bundle), "--out", str(out)])
    assert rc == 2, capsys.readouterr().out
    assert not (out / "report.json").exists()


# ---------------------------------------------------------------------------
# P2: image enumeration failure must be ERROR, never EMPTY
# ---------------------------------------------------------------------------

class _FakePage:
    """A page whose text / image enumeration the test controls exactly."""

    def __init__(self, text: str, images: object):
        self._text = text
        self._images = images

    def extract_text(self) -> str:
        return self._text

    @property
    def images(self):
        if self._images is _RAISE:
            raise RuntimeError("image enumeration failed")
        return self._images


_RAISE = object()


def test_image_enum_failure_is_error_not_empty():
    """A blank-text page whose images cannot be enumerated is ERROR."""
    assert _page_has_images(_FakePage("", _RAISE)) is None
    record = _extract_one_page(_FakePage("", _RAISE), 0, None)
    assert record.text_state == "ERROR"
    assert record.extracted_text is None
    assert record.text_sha256 is None


def test_image_enum_failure_does_not_mask_real_text():
    """Text present + image enum failing: still TEXT (enum not consulted)."""
    record = _extract_one_page(_FakePage("some text", _RAISE), 0, None)
    assert record.text_state == "TEXT"
    assert record.extracted_text == "some text"
    assert record.text_sha256 is not None


def test_image_enum_controls_still_classify():
    """No failure: images -> IMAGE_ONLY, none -> EMPTY (unchanged)."""
    assert _page_has_images(_FakePage("", [object()])) is True
    assert _extract_one_page(_FakePage("", [object()]), 0, None).text_state \
        == "IMAGE_ONLY"
    assert _page_has_images(_FakePage("", [])) is False
    assert _extract_one_page(_FakePage("", []), 0, None).text_state == "EMPTY"
