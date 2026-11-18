"""T003 — PDF input validation and per-page extraction tests.

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/unit/test_extract.py -q

Covers:
  * all 48 T002 fixtures: page count / SHA-256 / labels match the
    manifest and specs; one record per physical page, indices 0..n-1;
    TEXT pages contain every authored line (after §4.2 normalisation);
    blank pages are EMPTY, image pages are IMAGE_ONLY, both with no
    extracted text; ``text_sha256`` matches the extraction records in
    the fixture bundles;
  * §4.2 normalisation (NFC, CRLF/CR -> LF, whitespace collapse) and
    what it must NOT do (case / punctuation / full-half-width kept);
  * controlled errors: missing file, corrupt bytes, empty file,
    encrypted PDF, oversize input, too many pages.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

# Production package lives in src/ (T013 P2-08: the top-level stub is gone);
# src/ must be first on sys.path when running from a checkout.
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pypdf import PdfReader, PdfWriter  # noqa: E402

from pagetrace.extract import PageTextRecord, extract_pages, extract_pdf  # noqa: E402
from pagetrace.normalize import normalize_text, quote_sha256  # noqa: E402
from pagetrace.pdf_input import (  # noqa: E402
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_PAGES,
    PdfInputError,
    load_pdf,
)


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_spec(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "specs" / f"{case_id}.json").read_text(encoding="utf-8"))


def load_bundle(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "bundles" / f"{case_id}.trace.json").read_text(
            encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_manifest()


def _norm(text: str) -> str:
    return normalize_text(text)


# ---------------------------------------------------------------------------
# Fixture-driven extraction: all 48 PDFs
# ---------------------------------------------------------------------------

def test_all_48_fixture_pdfs_extract(manifest):
    """Every fixture PDF loads, and page count / hash match the manifest."""
    assert len(manifest["cases"]) == 48
    for entry in manifest["cases"]:
        pdf_path = FIXTURES / "pdfs" / entry["pdf_file_name"]
        info, records = extract_pdf(str(pdf_path))
        assert info.page_count == entry["page_count"], entry["case_id"]
        assert info.sha256 == entry["pdf_sha256"], entry["case_id"]
        assert info.file_name == entry["pdf_file_name"]
        assert info.file_size_bytes == pdf_path.stat().st_size
        assert info.is_encrypted is False
        assert len(records) == info.page_count, entry["case_id"]
        # Physical indices are continuous from 0; no silent skip.
        assert [r.pdf_page_index0 for r in records] == list(
            range(info.page_count)), entry["case_id"]


def test_fixture_labels_match_specs(manifest):
    """Per-page labels from the PDF equal the spec labels."""
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        info, records = extract_pdf(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        assert list(info.page_labels) == [
            p["pdf_page_label"] for p in spec["pages"]], entry["case_id"]
        assert [r.pdf_page_label for r in records] == [
            p["pdf_page_label"] for p in spec["pages"]], entry["case_id"]


def test_fixture_text_pages_contain_authored_lines(manifest):
    """Every authored line of every TEXT page survives pypdf extraction
    (after §4.2 normalisation); blank/image pages extract nothing."""
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        _, records = extract_pdf(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        by_index = {r.pdf_page_index0: r for r in records}
        for page in spec["pages"]:
            rec = by_index[page["pdf_page_index0"]]
            if page["kind"] == "text":
                assert rec.text_state == "TEXT", (
                    entry["case_id"], page["pdf_page_index0"])
                assert rec.extracted_text is not None
                assert rec.text_sha256 is not None
                normed = _norm(rec.extracted_text)
                for line in page["lines"]:
                    assert _norm(line) in normed, (
                        entry["case_id"], page["pdf_page_index0"], line)
            elif page["kind"] == "blank":
                assert rec.text_state == "EMPTY", (
                    entry["case_id"], page["pdf_page_index0"])
                assert rec.extracted_text == ""
                assert rec.text_sha256 is None
            elif page["kind"] == "image":
                assert rec.text_state == "IMAGE_ONLY", (
                    entry["case_id"], page["pdf_page_index0"])
                assert rec.extracted_text == ""
                assert rec.text_sha256 is None
            else:  # pragma: no cover - generator only emits these kinds
                raise AssertionError(f"unknown kind {page['kind']!r}")


def test_fixture_text_sha256_is_hash_of_normalized_extraction(manifest):
    """``text_sha256`` is the SHA-256 of the §4.2-normalised text
    extracted independently with raw pypdf — the honest per-page
    ground truth, recomputed here rather than trusted from any
    bundle (the bundles carry the *implanted* fault in the trace)."""
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        _, records = extract_pdf(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        reader = PdfReader(str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        for page_spec, record, pdf_page in zip(
                spec["pages"], records, reader.pages):
            assert page_spec["pdf_page_index0"] == record.pdf_page_index0
            if record.text_state == "TEXT":
                raw = pdf_page.extract_text() or ""
                assert record.text_sha256 == hashlib.sha256(
                    _norm(raw).encode("utf-8")).hexdigest(), (
                    entry["case_id"], record.pdf_page_index0)
            else:
                assert record.text_sha256 is None


def test_bundle_extraction_records_agree_except_faulted_stage(manifest):
    """Bundle extraction records equal the honest extraction — except
    in the 6 cases whose fault was implanted *in the extraction stage*
    itself (po-ext-01..03 hash swap; mm-ext-01..03 ERROR / missing
    hash / missing record). There the bundle must differ from the PDF
    truth: that difference is exactly what T004's stage comparator
    will attribute to extraction. The PDF itself is never the fault."""
    faulted_extraction = set()
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        bundle = load_bundle(entry["case_id"])
        _, records = extract_pdf(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        mine = {r.pdf_page_index0: r for r in records}
        bundle_by_index = {
            r["pdf_page_index0"]: r for r in bundle["stages"]["extraction"]}
        differs = False
        for index, rec in mine.items():
            bundle_rec = bundle_by_index.get(index)
            if bundle_rec is None:
                differs = True
                continue
            if (bundle_rec.get("text_state") != rec.text_state
                    or bundle_rec.get("text_sha256") != rec.text_sha256
                    or bundle_rec.get("pdf_page_label")
                    != rec.pdf_page_label):
                differs = True
        if len(bundle_by_index) != len(mine):
            differs = True
        # Only PAGE_OFFSET / PAGE_METADATA_MISSING faults implanted in
        # the extraction stage alter the extraction records. UNLOCATABLE
        # cases are also attributed to extraction, but their records
        # are honest — the quote is simply absent from the text layer.
        record_faulted = (
            spec["first_fault_stage"] == "extraction"
            and spec["fault_type"]
            in ("PAGE_OFFSET", "PAGE_METADATA_MISSING"))
        if record_faulted:
            faulted_extraction.add(entry["case_id"])
            assert differs, (
                f"{entry['case_id']}: extraction-stage fault case must "
                f"differ from honest extraction")
        else:
            assert not differs, (
                f"{entry['case_id']}: bundle extraction must equal "
                f"honest extraction when the fault is downstream")
    assert faulted_extraction == {
        "po-ext-01", "po-ext-02", "po-ext-03",
        "mm-ext-01", "mm-ext-02", "mm-ext-03",
    }, faulted_extraction


def test_fixture_page_states_cover_fixture_kinds(manifest):
    """Structural coverage actually seen by the extractor: Chinese text
    pages, blank pages and image pages all occur across the 48 PDFs,
    and no page is ever reported ERROR."""
    states: set[str] = set()
    for entry in manifest["cases"]:
        _, records = extract_pdf(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]))
        states.update(r.text_state for r in records)
    assert "TEXT" in states
    assert "EMPTY" in states
    assert "IMAGE_ONLY" in states
    assert "ERROR" not in states


def test_pdf_reader_page_count_agrees(manifest):
    """Page count from load_pdf agrees with an independent PdfReader."""
    for entry in manifest["cases"]:
        pdf_path = FIXTURES / "pdfs" / entry["pdf_file_name"]
        reader = PdfReader(str(pdf_path))
        info = load_pdf(str(pdf_path))
        assert info.page_count == len(reader.pages), entry["case_id"]
        assert list(info.page_labels) == list(reader.page_labels)


# ---------------------------------------------------------------------------
# Normalisation (§4.2)
# ---------------------------------------------------------------------------

def test_normalize_nfc_crlf_whitespace():
    # Decomposed e + combining acute (U+0301) -> composed é (NFC).
    assert normalize_text("e\u0301xample") == "\u00e9xample"
    assert normalize_text("a\r\nb\rc\nd") == "a b c d"
    assert normalize_text("a \t\n  b") == "a b"
    assert normalize_text("  padded  ") == "padded"
    assert normalize_text("") == ""


def test_normalize_keeps_case_punctuation_full_half_width():
    # §4.2: no case folding, no punctuation changes, no full-width /
    # half-width conversion.
    assert normalize_text("ABC abc ＡＢＣ ａｂｃ") == "ABC abc ＡＢＣ ａｂｃ"
    assert normalize_text("你好，世界！Hello, World.") == "你好，世界！Hello, World."
    assert normalize_text("ＡＢＣ") != normalize_text("ABC")
    assert normalize_text("Hello.") != normalize_text("Hello")
    assert normalize_text("Hello") != normalize_text("hello")


def test_quote_sha256_is_normalized_hash():
    quote = "  关键引文：页码漂移\r\n误导定位。 "
    assert quote_sha256(quote) == hashlib.sha256(
        normalize_text(quote).encode("utf-8")).hexdigest()
    # Same normalised text -> same hash, regardless of raw whitespace.
    assert quote_sha256("a  b") == quote_sha256("a b")
    assert quote_sha256("a b") != quote_sha256("a  c")


# ---------------------------------------------------------------------------
# Controlled input errors
# ---------------------------------------------------------------------------

def test_missing_file_is_controlled_error(tmp_path):
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(tmp_path / "does-not-exist.pdf"))
    assert excinfo.value.reason == "FILE_NOT_FOUND"


def test_directory_is_controlled_error(tmp_path):
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(tmp_path))
    assert excinfo.value.reason == "NOT_A_FILE"


def test_corrupt_bytes_are_controlled_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"this is not a pdf at all")
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(bad))
    assert excinfo.value.reason == "CORRUPT"


def test_empty_file_is_controlled_error(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(empty))
    assert excinfo.value.reason == "CORRUPT"


def test_truncated_pdf_is_controlled_error(tmp_path):
    src = FIXTURES / "pdfs" / "po-ext-01.pdf"
    truncated = tmp_path / "truncated.pdf"
    truncated.write_bytes(src.read_bytes()[:200])
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(truncated))
    assert excinfo.value.reason == "CORRUPT"


def test_encrypted_pdf_is_controlled_error(tmp_path):
    src = FIXTURES / "pdfs" / "po-ext-01.pdf"
    encrypted = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    for page in PdfReader(str(src)).pages:
        writer.add_page(page)
    writer.encrypt("secret-user-password")
    with open(encrypted, "wb") as fh:
        writer.write(fh)
    assert PdfReader(str(encrypted)).is_encrypted
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(encrypted))
    assert excinfo.value.reason == "ENCRYPTED"


def test_oversize_input_rejected_by_size_limit(tmp_path):
    # A file just over the 50 MiB default is rejected on size alone,
    # without parsing; a lowered limit rejects a small real PDF too.
    big = tmp_path / "big.pdf"
    with open(big, "wb") as fh:
        fh.write(b"\x00" * (DEFAULT_MAX_FILE_SIZE_BYTES + 1))
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(big))
    assert excinfo.value.reason == "TOO_LARGE"
    real = FIXTURES / "pdfs" / "po-ext-01.pdf"
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(real), max_file_size_bytes=100)
    assert excinfo.value.reason == "TOO_LARGE"


def test_too_many_pages_rejected_by_page_limit():
    real = FIXTURES / "pdfs" / "po-ext-01.pdf"
    info = load_pdf(str(real))
    assert info.page_count > 1
    with pytest.raises(PdfInputError) as excinfo:
        load_pdf(str(real), max_pages=info.page_count - 1)
    assert excinfo.value.reason == "TOO_MANY_PAGES"
    # The default limit itself is 500.
    assert DEFAULT_MAX_PAGES == 500
    assert DEFAULT_MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024


def test_extract_pdf_convenience_and_record_shape():
    info, records = extract_pdf(str(FIXTURES / "pdfs" / "po-ext-01.pdf"))
    assert info.page_count == len(records)
    for record in records:
        assert isinstance(record, PageTextRecord)
        assert record.text_state in ("TEXT", "EMPTY", "IMAGE_ONLY", "ERROR")
        if record.text_state == "TEXT":
            assert record.extracted_text
            assert record.text_sha256 is not None
            assert len(record.text_sha256) == 64
        else:
            assert record.text_sha256 is None
