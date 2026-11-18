"""T008 — four-column linked HTML report tests.

Run from PACKAGE_ROOT, inside the venv:
    TMPDIR=$PWD/.tmp python -m pytest tests/integration/test_html_report.py -q

Checks (PROJECT_BOOK §9, TASK-008 hard assertions):

* the three production files exist; the JS parses (node --check);
* the report renders real pipeline output, not mock data: entries are
  built by running the production implementation (extract_pdf +
  analyze_bundle) over all 48 frozen fixtures — 96 citations, 12/12
  per fault class detected, 48/48 first-fault stages, 48/48 controls
  PASS — and the embedded JSON in the rendered HTML matches those
  pipeline results exactly;
* the demo subset covers one fault case per fault class plus a PASS
  control; the truth column is the honest extraction while the
  extraction column keeps the observed (faulty) records;
* four columns render PDF truth / extraction / chunk+index / final
  citation, with a comparison table showing wrong page, first-fault
  stage and correct source location together;
* status mapping follows §9.3: PASS green, FAIL red, AMBIGUOUS /
  UNLOCATABLE / UNKNOWN amber, SKIPPED grey — and no ambiguous or
  unlocatable verdict ever maps to the PASS tone;
* no CDN or network requests: no external URLs, fetches or XHR in
  the HTML, CSS, JS or rendered page;
* rendering is deterministic (identical SHA-256 across writes) and
  quote text is escaped so it can never break out of the embedded
  JSON block;
* a real headless browser renders the four columns from file://
  (skipped when no cached headless shell is available).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"
SRC = PACKAGE_ROOT / "src" / "pagetrace"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace import report_html  # noqa: E402
from pagetrace.report_html import (  # noqa: E402
    build_report_document,
    build_view_entry,
    render_html,
    status_tone,
    write_report,
)

HTML_MODULE = SRC / "report_html.py"
CSS = SRC / "assets" / "report.css"
JS = SRC / "assets" / "report.js"

EXPECTED_FAULT_TYPES = {
    "PAGE_OFFSET",
    "PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE",
}

DEMO_FAULT_CASES = ("po-ext-01", "mm-ext-01", "du-chk-01", "un-ext-01")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def embedded_document(html_text: str) -> dict:
    match = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>',
        html_text, re.DOTALL)
    assert match, "embedded #report-data block missing"
    return json.loads(match.group(1))


def headless_shell() -> Path | None:
    candidates = sorted(Path.home().glob(
        ".cache/ms-playwright/chromium_headless_shell-*/"
        "chrome-headless-shell-linux64/chrome-headless-shell"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


@pytest.fixture(scope="module")
def pipeline_entries():
    """All 96 real entries + counts from the production pipeline."""
    entries, counts = report_html.build_entries_from_fixtures(FIXTURES)
    return entries, counts


@pytest.fixture(scope="module")
def demo_entries(pipeline_entries):
    """One fault entry per fault class + one PASS control entry."""
    entries, _ = pipeline_entries
    by_case = {}
    for entry in entries:
        by_case.setdefault(entry["case_id"], {})[entry["citation_id"]] = entry
    demo = [by_case[case_id]["cite-fault"] for case_id in DEMO_FAULT_CASES]
    demo.append(by_case["po-ext-01"]["cite-control"])
    return demo


def test_deliverable_files_exist():
    assert HTML_MODULE.is_file(), "src/pagetrace/report_html.py missing"
    assert CSS.is_file(), "src/pagetrace/assets/report.css missing"
    assert JS.is_file(), "src/pagetrace/assets/report.js missing"


def test_js_syntax_valid():
    node = shutil.which("node")
    assert node, "node not available for --check"
    result = subprocess.run(
        [node, "--check", str(JS)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_no_network_requests(demo_entries):
    for path in (CSS, JS):
        text = read(path)
        assert "https://" not in text, f"{path.name} contains an https URL"
        assert "http://" not in text, f"{path.name} contains an http URL"
        assert "fetch(" not in text, f"{path.name} uses fetch()"
        assert "XMLHttpRequest" not in text, f"{path.name} uses XHR"
        assert "@import" not in text, f"{path.name} uses @import"
        assert re.search(r"(cdn\.|unpkg|jsdelivr)", text.lower()) is None, (
            f"{path.name} references a CDN host")
    html_text = render_html(demo_entries)
    assert "https://" not in html_text, "rendered HTML contains https URL"
    assert "http://" not in html_text, "rendered HTML contains http URL"
    assert "fetch(" not in html_text, "rendered HTML uses fetch()"
    assert re.search(r'<script[^>]+src="[^"]+"', html_text) is None or all(
        src.startswith("assets/report") for src in
        re.findall(r'<script[^>]+src="([^"]+)"', html_text)
    ), "external script source present"
    assert re.search(r'<link[^>]+href="[^"]+"', html_text) is None or all(
        href.startswith("assets/report") for href in
        re.findall(r'<link[^>]+href="([^"]+)"', html_text)
    ), "external stylesheet present"


def test_real_pipeline_counts(pipeline_entries):
    entries, counts = pipeline_entries
    assert len(entries) == 96, f"expected 96 citations, got {len(entries)}"
    assert counts["cases"] == 48
    assert counts["detected_by_fault_type"] == {
        fault: 12 for fault in EXPECTED_FAULT_TYPES}, counts
    assert counts["first_fault_stage_correct"] == 48, counts
    assert counts["control_pass"] == 48, counts


def test_demo_subset_covers_four_fault_classes_plus_control(demo_entries):
    assert len(demo_entries) == 5
    fault_entries = [e for e in demo_entries if e["fault_type"] is not None]
    assert len(fault_entries) == 4
    assert {e["fault_type"] for e in fault_entries} == EXPECTED_FAULT_TYPES
    assert len({e["entry_id"] for e in demo_entries}) == 5
    controls = [e for e in demo_entries if e["verdict"] == "PASS"]
    assert len(controls) == 1
    assert controls[0]["entry_id"] == "po-ext-01/cite-control"


def test_embedded_data_matches_pipeline(demo_entries, pipeline_entries):
    entries, _ = pipeline_entries
    golden = json.loads(
        (FIXTURES / "golden" / "expected.json").read_text(encoding="utf-8"))
    golden_by_id = {c["case_id"]: c for c in golden["cases"]}
    html_text = render_html(demo_entries)
    document = embedded_document(html_text)
    assert document["schema"] == "pagetrace.report/v1"
    assert document["bundle_schema"] == "pagetrace.bundle/v1"
    assert len(document["entries"]) == 5
    by_id = {e["entry_id"]: e for e in document["entries"]}
    for entry in demo_entries:
        assert by_id[entry["entry_id"]] == entry, entry["entry_id"]
    # Spot-check against Golden: every demo fault verdict is the
    # frozen expectation, and the control is PASS.
    for entry in demo_entries:
        gold = golden_by_id[entry["case_id"]]
        if entry["citation_id"] == "cite-fault":
            assert entry["verdict"] == gold["fault"]["verdict"]
            assert entry["fault_type"] == gold["fault"]["fault_type"]
            assert entry["first_fault_stage"] == \
                gold["fault"]["first_fault_stage"]
            assert entry["candidate_source_pages0"] == \
                gold["fault"]["candidate_source_pages0"]
            assert entry["correct_pdf_page_number1"] == \
                gold["fault"]["correct_pdf_page_number1"]
        else:
            assert entry["verdict"] == "PASS"
    # No embedded payload can close the script element.
    raw = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>',
        html_text, re.DOTALL).group(1)
    assert "</script" not in raw.replace("\\u003c/script", ""), (
        "embedded JSON contains a literal </script>")


def test_truth_column_is_honest_and_extraction_keeps_observed(demo_entries):
    by_id = {e["entry_id"]: e for e in demo_entries}
    # mm-ext-01: extraction observed text_state ERROR on page 2, honest TEXT.
    mm = by_id["mm-ext-01/cite-fault"]
    truth_page2 = next(p for p in mm["truth_pages"]
                       if p["pdf_page_index0"] == 2)
    obs_page2 = next(p for p in mm["extraction"]
                     if p["pdf_page_index0"] == 2)
    assert truth_page2["text_state"] == "TEXT"
    assert obs_page2["text_state"] == "ERROR"
    assert mm["extraction_diffs"], "mm-ext-01 must carry extraction diffs"
    # po-ext-01: extraction hashes for pages 2/3 are swapped vs honest truth.
    po = by_id["po-ext-01/cite-fault"]
    for index0 in (2, 3):
        truth_hash = next(p for p in po["truth_pages"]
                          if p["pdf_page_index0"] == index0)["text_sha256"]
        obs_hash = next(p for p in po["extraction"]
                        if p["pdf_page_index0"] == index0)["text_sha256"]
        assert truth_hash != obs_hash, f"po-ext-01 page {index0} must differ"
    # un-ext-01: no correct source page may be invented.
    un = by_id["un-ext-01/cite-fault"]
    assert un["correct_pdf_page_number1"] is None
    assert un["candidate_source_pages0"] == []
    # du-chk-01: all candidate pages preserved in truth; chunk reduced them.
    du = by_id["du-chk-01/cite-fault"]
    assert du["candidate_source_pages0"] == [2, 4]
    assert du["correct_pdf_page_number1"] == [3, 5]
    assert du["chunk"]["source_page_indices0"] == [2]
    assert du["index_record"]["source_page_indices0"] == [2]


def test_four_columns_and_comparison_table(demo_entries):
    html_text = render_html(demo_entries)
    for column_id, heading in [
        ("col-truth", "PDF 真值"),
        ("col-extraction", "抽取"),
        ("col-chunk-index", "分片与索引"),
        ("col-citation", "最终引用"),
    ]:
        assert f'id="{column_id}"' in html_text, f"column {column_id} missing"
        assert heading in html_text, f"column heading {heading} missing"
    for header in ("错误页码", "首错阶段", "正确来源位置"):
        assert header in html_text, f"comparison header {header} missing"
    for control in ("filter-fault", "filter-stage", "filter-status",
                    "download-json", "copy-json", "citation-list",
                    "comparison-body", "stage-diff-list", "raw-json",
                    "report-data", "report-summary"):
        assert f'id="{control}"' in html_text, f"element #{control} missing"
    assert 'href="assets/report.css"' in html_text
    assert 'src="assets/report.js"' in html_text


def test_status_mapping_follows_section_9_3():
    assert status_tone("PASS") == "pass"
    assert status_tone("FAIL_PAGE_OFFSET") == "fail"
    assert status_tone("FAIL_METADATA_MISSING") == "fail"
    assert status_tone("FAIL_AMBIGUOUS") == "amber"
    assert status_tone("FAIL_UNLOCATABLE") == "amber"
    for verdict in ("UNKNOWN_TRACE_MISSING", "UNKNOWN_PAGE_BASIS",
                    "AMBIGUOUS", "NEEDS_MANUAL_REVIEW", "BOGUS"):
        assert status_tone(verdict) == "amber", verdict
    js = read(JS)
    match = re.search(r"const STATUS_META = (\{.*?\n\});", js, re.DOTALL)
    assert match, "STATUS_META block missing in report.js"
    meta = json.loads(match.group(1))
    assert meta["PASS"]["tone"] == "pass"
    assert meta["FAIL_PAGE_OFFSET"]["tone"] == "fail"
    assert meta["FAIL_METADATA_MISSING"]["tone"] == "fail"
    for verdict in ("FAIL_AMBIGUOUS", "FAIL_UNLOCATABLE",
                    "UNKNOWN_TRACE_MISSING", "UNKNOWN_PAGE_BASIS",
                    "AMBIGUOUS", "NEEDS_MANUAL_REVIEW"):
        assert meta[verdict]["tone"] == "amber", verdict
        assert meta[verdict]["cls"] != "status-pass", verdict
        assert "PASS" not in meta[verdict]["label"] or verdict == "PASS"
    css = read(CSS)
    for cls in ("status-pass", "status-fail", "status-amber", "status-skipped"):
        assert f".{cls}" in css, f"CSS class .{cls} missing"
    assert "#2e7d32" in css and "#c62828" in css
    assert "#b26a00" in css and "#616161" in css
    for fn in ("paintTruth", "paintExtraction", "paintChunkIndex",
               "paintCitation", "paintComparison", "selectEntry", "paintAll"):
        assert fn in js, f"JS function {fn} missing"


def test_summary_counts(pipeline_entries):
    entries, _ = pipeline_entries
    document = build_report_document(entries)
    summary = document["summary"]
    assert summary["total_citations"] == 96
    assert summary["pass_count"] == 48
    assert summary["fail_count"] == 48
    assert summary["unknown_count"] == 0
    assert summary["ambiguous_count"] == 0
    assert summary["by_fault_type"] == {
        fault: 12 for fault in EXPECTED_FAULT_TYPES}


def test_html_escaping_of_quote_text():
    result = {
        "citation_id": "cite-fault",
        "quote_sha256": "0" * 64,
        "citation_page_value": 3,
        "citation_page_basis": "PDF_NUMBER_1",
        "candidate_source_pages0": [2],
        "expected_source_pages0": [2],
        "observed_page_value": 3,
        "correct_pdf_page_number1": [3],
        "correct_viewer_page1": [3],
        "verdict": "PASS",
        "fault_type": None,
        "first_fault_stage": None,
        "evidence": [],
        "notes": [],
    }
    bundle = {
        "document": {"file_name": "x.pdf", "page_count": 5, "sha256": "a" * 64},
        "citations": [{
            "citation_id": "cite-fault",
            "quote_text": 'evil </script><script>alert(1)</script> & "quoted"',
            "chunk_id": "c1", "index_record_id": "v1",
        }],
        "stages": {"extraction": [], "chunking": [], "indexing": [],
                   "display": []},
    }
    entry = build_view_entry(
        case_id="esc-01", result=result, bundle=bundle, honest_records=[])
    html_text = render_html([entry])
    assert "<script>alert(1)" not in html_text
    assert "\\u003cscript\\u003ealert(1)" in html_text
    assert embedded_document(html_text)["entries"][0]["quote_text"] == \
        'evil </script><script>alert(1)</script> & "quoted"'


def test_unknown_verdict_rejected():
    result = {
        "citation_id": "cite-fault",
        "quote_sha256": "0" * 64,
        "citation_page_value": 3,
        "citation_page_basis": "PDF_NUMBER_1",
        "candidate_source_pages0": [2],
        "expected_source_pages0": [2],
        "observed_page_value": 3,
        "correct_pdf_page_number1": [3],
        "correct_viewer_page1": [3],
        "verdict": "BOGUS",
        "fault_type": None,
        "first_fault_stage": None,
        "evidence": [],
        "notes": [],
    }
    bundle = {
        "document": {"file_name": "x.pdf", "page_count": 1, "sha256": "a" * 64},
        "citations": [{"citation_id": "cite-fault", "quote_text": "q",
                       "chunk_id": "c1", "index_record_id": "v1"}],
        "stages": {},
    }
    with pytest.raises(ValueError, match="unknown verdict"):
        build_view_entry(
            case_id="bad-01", result=result, bundle=bundle, honest_records=[])


def test_write_report_deterministic(tmp_path, demo_entries):
    first = write_report(tmp_path / "a", demo_entries,
                         pdf_dir="../../04_source/source/fixtures/pdfs")
    second = write_report(tmp_path / "b", demo_entries,
                          pdf_dir="../../04_source/source/fixtures/pdfs")
    assert first["report_html_sha256"] == second["report_html_sha256"]
    assert {k: v["sha256"] for k, v in first["assets"].items()} == \
        {k: v["sha256"] for k, v in second["assets"].items()}
    assert first["entries"] == 5
    html_path = Path(first["report_html"])
    assert html_path.is_file() and html_path.stat().st_size > 0
    assert (Path(first["report_html"]).parent / "assets" / "report.css").is_file()
    assert (Path(first["report_html"]).parent / "assets" / "report.js").is_file()
    assert first["report_html_sha256"] == hashlib.sha256(
        html_path.read_bytes()).hexdigest()


def test_browser_renders_four_columns(tmp_path, demo_entries):
    binary = headless_shell()
    if binary is None:
        pytest.skip("no cached headless shell available")
    out = write_report(tmp_path / "report", demo_entries,
                       pdf_dir="../../04_source/source/fixtures/pdfs")
    url = Path(out["report_html"]).as_uri()
    result = subprocess.run(
        [str(binary), "--headless", "--disable-gpu", "--no-sandbox",
         "--virtual-time-budget=5000", "--dump-dom", url],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[:2000]
    dom = result.stdout
    for fragment in ("① PDF 真值", "② 抽取", "③ 分片与索引", "④ 最终引用",
                     "po-ext-01/cite-fault", "FAIL — 页码偏移",
                     "错误页码", "正确来源位置"):
        assert fragment in dom, f"rendered DOM missing {fragment!r}"
    assert "http://" not in dom and "https://" not in dom, (
        "rendered DOM contains an external URL")
