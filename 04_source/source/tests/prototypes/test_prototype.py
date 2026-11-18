"""T005 — four-column linked interaction prototype tests.

Run from PACKAGE_ROOT, inside the venv:

    python -m pytest tests/prototypes -q

Checks (PROJECT_BOOK §9, TASK-005 hard assertions):
  * the three prototype files exist; the JS parses (node --check);
  * four columns render PDF truth / extraction / chunk+index / final
    citation, with a comparison table showing wrong page, first-fault
    stage and correct source location together;
  * the embedded demo data matches the frozen T004 evidence exactly
    (no re-implemented verdict logic): 4 fault cases, one per fault
    class, plus one PASS control entry;
  * the honest truth column is corrected from upstream stage-diff values
    while the extraction column keeps the observed (faulty) records;
  * status mapping follows §9.3: PASS green, FAIL red, AMBIGUOUS /
    UNLOCATABLE / UNKNOWN amber, SKIPPED grey — and no ambiguous or
    unlocatable verdict ever maps to the PASS class;
  * no CDN or network requests: no external URLs, fetches or XHR.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PACKAGE_ROOT.parents[1]
PROTOTYPES = REPO_ROOT / "prototypes"
HTML = PROTOTYPES / "report-prototype.html"
CSS = PROTOTYPES / "report-prototype.css"
JS = PROTOTYPES / "report-prototype.js"

T004 = REPO_ROOT / "07_evidence" / "runtime_logs" / "t004-stage-diffs.json"

EXPECTED_FAULT_TYPES = {
    "PAGE_OFFSET",
    "PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def embedded_cases() -> list[dict]:
    text = read(JS)
    match = re.search(
        r"/\* BEGIN GENERATED DATA.*?const PROTOTYPE_CASES = (\[.*?\]);\s*/\* END GENERATED DATA \*/",
        text,
        re.DOTALL,
    )
    assert match, "generated data block markers missing in report-prototype.js"
    return json.loads(match.group(1))


def status_meta() -> dict:
    text = read(JS)
    match = re.search(r"const STATUS_META = (\{.*?\n\});", text, re.DOTALL)
    assert match, "STATUS_META block missing in report-prototype.js"
    return json.loads(match.group(1))


def test_prototype_files_exist():
    assert HTML.is_file(), "prototypes/report-prototype.html missing"
    assert CSS.is_file(), "prototypes/report-prototype.css missing"
    assert JS.is_file(), "prototypes/report-prototype.js missing"


def test_js_syntax_valid():
    node = shutil.which("node")
    assert node, "node not available for --check"
    result = subprocess.run(
        [node, "--check", str(JS)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr


def test_four_columns_and_comparison_table():
    html = read(HTML)
    for column_id, heading in [
        ("col-truth", "PDF 真值"),
        ("col-extraction", "抽取"),
        ("col-chunk-index", "分片与索引"),
        ("col-citation", "最终引用"),
    ]:
        assert f'id="{column_id}"' in html, f"column {column_id} missing"
        assert heading in html, f"column heading {heading} missing"
    for header in ("错误页码", "首错阶段", "正确来源位置"):
        assert header in html, f"comparison table header {header} missing"
    for control in ("filter-fault", "filter-stage", "filter-status",
                    "download-json", "copy-json", "citation-list",
                    "comparison-body", "stage-diff-list", "raw-json"):
        assert f'id="{control}"' in html, f"element #{control} missing"


def test_no_network_requests():
    for path in (HTML, CSS, JS):
        text = read(path)
        assert "https://" not in text, f"{path.name} contains an https URL"
        assert "http://" not in text, f"{path.name} contains an http URL"
        assert "fetch(" not in text, f"{path.name} uses fetch()"
        assert "XMLHttpRequest" not in text, f"{path.name} uses XHR"
        assert "@import" not in text, f"{path.name} uses @import"
        assert re.search(r"(cdn\.|unpkg|jsdelivr)", text.lower()) is None, (
            f"{path.name} references a CDN host"
        )
    html = read(HTML)
    assert 'src="http' not in html and "href=\"http" not in html
    assert re.search(r'<script[^>]+src="[^"]+"', html) is None or all(
        src.startswith("report-prototype") for src in
        re.findall(r'<script[^>]+src="([^"]+)"', html)
    ), "external script source present"
    assert re.search(r'<link[^>]+href="[^"]+"', html) is None or all(
        href.startswith("report-prototype") for href in
        re.findall(r'<link[^>]+href="([^"]+)"', html)
    ), "external stylesheet present"


def test_demo_cases_cover_four_fault_classes():
    cases = embedded_cases()
    fault_cases = [c for c in cases if c["fault_type"] is not None]
    assert len(fault_cases) == 4, f"expected 4 fault cases, got {len(fault_cases)}"
    assert {c["fault_type"] for c in fault_cases} == EXPECTED_FAULT_TYPES
    assert len({c["case_id"] for c in cases}) == len(cases), "duplicate case_id"
    controls = [c for c in cases if c["verdict"] == "PASS"]
    assert len(controls) == 1, "expected exactly one PASS control entry"


def test_embedded_data_matches_t004_evidence():
    t004 = json.loads(T004.read_text(encoding="utf-8"))
    by_id = {c["case_id"]: c for c in t004["cases"]}
    cases = embedded_cases()
    for entry in cases:
        if entry["fault_type"] is None:
            source = by_id[entry["case_id"].removesuffix("-control")]["control_verdict"]
        else:
            source = by_id[entry["case_id"]]["fault_verdict"]
        assert entry["verdict"] == source["verdict"]
        assert entry["first_fault_stage"] == source["first_fault_stage"]
        assert entry["observed_page_value"] == source["observed_page_value"]
        assert entry["correct_pdf_page_number1"] == source["correct_pdf_page_number1"]
        assert entry["candidate_source_pages0"] == source["candidate_source_pages0"]
        assert entry["citation_page_basis"] == source["citation_page_basis"]
        if entry["fault_type"] is not None:
            assert entry["stage_diffs"] == by_id[entry["case_id"]]["stage_diffs"]
        else:
            assert entry["stage_diffs"] == []


def test_truth_column_is_honest_and_extraction_keeps_observed():
    cases = {c["case_id"]: c for c in embedded_cases()}
    # mm-ext-01: extraction observed text_state ERROR on page 2, honest is TEXT.
    mm = cases["mm-ext-01"]
    truth_page2 = next(p for p in mm["truth_pages"] if p["pdf_page_index0"] == 2)
    obs_page2 = next(p for p in mm["extraction"] if p["pdf_page_index0"] == 2)
    assert truth_page2["text_state"] == "TEXT"
    assert obs_page2["text_state"] == "ERROR"
    # po-ext-01: extraction hashes for pages 2/3 are swapped vs honest truth.
    po = cases["po-ext-01"]
    for index0 in (2, 3):
        truth_hash = next(p for p in po["truth_pages"]
                          if p["pdf_page_index0"] == index0)["text_sha256"]
        obs_hash = next(p for p in po["extraction"]
                        if p["pdf_page_index0"] == index0)["text_sha256"]
        assert truth_hash != obs_hash, f"po-ext-01 page {index0} hashes must differ"
    # un-ext-01: no correct source page may be invented.
    un = cases["un-ext-01"]
    assert un["correct_pdf_page_number1"] is None
    assert un["candidate_source_pages0"] == []
    # du-chk-01: all candidate pages are preserved in truth, chunking reduced them.
    du = cases["du-chk-01"]
    assert du["candidate_source_pages0"] == [2, 4]
    assert du["correct_pdf_page_number1"] == [3, 5]


def test_status_mapping_follows_section_9_3():
    meta = status_meta()
    assert meta["PASS"]["cls"] == "status-pass"
    assert meta["FAIL_PAGE_OFFSET"]["cls"] == "status-fail"
    assert meta["FAIL_METADATA_MISSING"]["cls"] == "status-fail"
    assert meta["FAIL_AMBIGUOUS"]["cls"] == "status-amber"
    assert meta["FAIL_UNLOCATABLE"]["cls"] == "status-amber"
    assert meta["UNKNOWN"]["cls"] == "status-amber"
    assert meta["SKIPPED"]["cls"] == "status-skipped"
    # No ambiguous / unlocatable / unknown verdict may ever render as PASS.
    for verdict, entry in meta.items():
        if verdict in ("FAIL_AMBIGUOUS", "FAIL_UNLOCATABLE", "UNKNOWN"):
            assert entry["cls"] != "status-pass", verdict
            assert "PASS" not in entry["label"] or verdict == "PASS", verdict
    for entry in embedded_cases():
        assert status_meta()[entry["verdict"]]["cls"] != "status-pass" \
            or entry["verdict"] == "PASS"


def test_css_has_section_9_3_status_styles():
    css = read(CSS)
    for cls in ("status-pass", "status-fail", "status-amber", "status-skipped"):
        assert f".{cls}" in css, f"CSS class .{cls} missing"
    # Status is text as well as colour: badges carry a label in the JS.
    js = read(JS)
    assert "statusBadge" in js and "label" in js
    # §9.3 palette anchors present (green / red / amber / grey).
    assert "#2e7d32" in css and "#c62828" in css
    assert "#b26a00" in css and "#616161" in css


def test_js_links_four_columns_on_selection():
    js = read(JS)
    for fn in ("renderTruthColumn", "renderExtractionColumn",
               "renderChunkIndexColumn", "renderCitationColumn",
               "renderComparison", "selectCase", "renderAll"):
        assert f"function {fn}" in js, f"{fn} missing from prototype JS"
    assert "row-correct" in js and "row-candidate" in js
    assert "#case=" in js, "deep-link selection (#case=) missing"
