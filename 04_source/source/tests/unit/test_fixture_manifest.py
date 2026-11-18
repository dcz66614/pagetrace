"""T002 acceptance: fixture manifest agrees with the real PDFs/bundles.

Checks (PROJECT_BOOK §8.1 hard assertions):
  * 48 cases, 12 per fault type; >= 1 control citation per PDF (48 total)
  * manifest PDF page counts / SHA-256 match the real files
  * spec labels match the labels stored in the PDF
  * control quotes are really on their claimed pages; fault quotes are
    really on their true pages (except UNLOCATABLE, where the quote must
    be absent from every extractable page)
  * every bundle validates against pagetrace.bundle/v1
  * structural coverage: Chinese text, blank pages, image pages,
    cross-page splits, duplicate sentences
  * regeneration is byte-deterministic (two runs, identical hashes)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import pytest
from pypdf import PdfReader

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"
TOOLS = PACKAGE_ROOT / "tools"

sys.path.insert(0, str(TOOLS))

FAULT_TYPES = (
    "PAGE_OFFSET",
    "PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE",
)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", text).strip()


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_spec(case_id: str) -> dict:
    return json.loads((FIXTURES / "specs" / f"{case_id}.json").read_text(encoding="utf-8"))


def load_bundle(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "bundles" / f"{case_id}.trace.json").read_text(encoding="utf-8"))


def extracted_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [norm(page.extract_text() or "") for page in reader.pages]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_manifest()


def test_manifest_counts(manifest):
    assert manifest["case_count"] == 48
    assert manifest["counts_by_fault_type"] == {ft: 12 for ft in FAULT_TYPES}
    assert len(manifest["cases"]) == 48
    assert manifest["coverage"]["control_citations_total"] == 48


def test_coverage(manifest):
    cov = manifest["coverage"]
    assert cov["pdfs_with_chinese_text"] == 48
    assert cov["pdfs_with_blank_page"] >= 12
    assert cov["pdfs_with_image_page"] >= 12
    assert cov["pdfs_with_cross_page_split"] >= 12
    assert cov["pdfs_with_duplicate_sentence"] >= 12
    assert set(cov["label_schemes_used"]) >= {
        "decimal", "roman", "roman-decimal", "alpha-prefix"}


def test_pdfs_match_manifest(manifest):
    sha_lines = dict(
        line.split(None, 1)[::-1]
        for line in (FIXTURES / "sha256sums.txt").read_text(
            encoding="utf-8").splitlines() if line.strip())
    for entry in manifest["cases"]:
        pdf_path = FIXTURES / "pdfs" / entry["pdf_file_name"]
        assert pdf_path.is_file(), pdf_path
        data = pdf_path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["pdf_sha256"]
        assert sha_lines[entry["pdf_file_name"]] == entry["pdf_sha256"]
        reader = PdfReader(str(pdf_path))
        assert len(reader.pages) == entry["page_count"]
        assert list(reader.page_labels) == entry["page_labels"]


def test_specs_match_manifest(manifest):
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        assert spec["pdf_sha256"] == entry["pdf_sha256"]
        assert spec["page_count"] == entry["page_count"]
        assert spec["fault_type"] == entry["fault_type"]
        assert spec["first_fault_stage"] == entry["first_fault_stage"]
        assert spec["fault_citation"]["quote_text"] == entry["fault_quote_text"]
        assert spec["control_citation"]["quote_text"] == entry["control_quote_text"]


def test_quotes_located_as_specified(manifest):
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        pages = extracted_pages(FIXTURES / "pdfs" / entry["pdf_file_name"])
        ctrl = spec["control_citation"]
        ctrl_pages = ctrl["true_source_pages0"]
        if len(ctrl_pages) == 1:
            assert norm(ctrl["quote_text"]) in pages[ctrl_pages[0]], entry["case_id"]
        else:
            # Cross-page control (R-10): each half on its own page.
            assert len(ctrl_pages) == 2, entry["case_id"]
            halves = _split_control_halves(spec)
            assert norm(halves[0]) in pages[ctrl_pages[0]], entry["case_id"]
            assert norm(halves[1]) in pages[ctrl_pages[1]], entry["case_id"]
        fault = spec["fault_citation"]
        fq = norm(fault["quote_text"])
        if spec["fault_type"] == "UNLOCATABLE":
            assert all(fq not in p for p in pages), entry["case_id"]
        elif spec["fault_type"] == "DUPLICATE_TEXT_AMBIGUITY":
            for p0 in fault["true_source_pages0"]:
                assert fq in pages[p0], (entry["case_id"], p0)
        else:
            for p0 in fault["true_source_pages0"]:
                assert fq in pages[p0], (entry["case_id"], p0)


def _split_control_halves(spec: dict) -> tuple[str, str]:
    pages = spec["pages"]
    idx = spec["split_pages0"]
    assert len(idx) == 2
    # The split halves are the only lines that differ between the two
    # pages' authored content and the shared sentence pools: recover
    # them from the spec lines by matching the control quote halves.
    quote = spec["control_citation"]["quote_text"]
    first_lines = pages[idx[0]]["lines"]
    second_lines = pages[idx[1]]["lines"]
    first = next(line for line in first_lines if quote.startswith(norm(line)))
    second = next(line for line in second_lines if quote.endswith(norm(line)))
    return first, second


def test_bundles_validate_against_schema(manifest):
    import jsonschema

    schema = json.loads(
        (PACKAGE_ROOT / "contracts" / "pagetrace.bundle.v1.schema.json")
        .read_text(encoding="utf-8"))
    for entry in manifest["cases"]:
        bundle = load_bundle(entry["case_id"])
        jsonschema.validate(bundle, schema)
        assert bundle["case_id"] == entry["case_id"]
        assert bundle["document"]["sha256"] == entry["pdf_sha256"]
        assert bundle["document"]["page_count"] == entry["page_count"]
        assert bundle["document"]["file_name"] == entry["pdf_file_name"]
        # No bare 'page' key anywhere in the bundle (substring matches
        # inside pdf_page_index0 / page_count do not count).
        def _keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield k
                    yield from _keys(v)
            elif isinstance(obj, list):
                for item in obj:
                    yield from _keys(item)

        assert "page" not in set(_keys(bundle))


def test_regeneration_is_byte_deterministic(manifest):
    import generate_fixtures

    with tempfile.TemporaryDirectory(dir=PACKAGE_ROOT) as tmp:
        out = Path(tmp) / "regen"
        generate_fixtures.generate(out, PACKAGE_ROOT, log=lambda *a: None)
        regen = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert [c["pdf_sha256"] for c in regen["cases"]] == [
            c["pdf_sha256"] for c in manifest["cases"]]
        assert regen["counts_by_fault_type"] == manifest["counts_by_fault_type"]
