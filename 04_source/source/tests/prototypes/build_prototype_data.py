"""T005 — regenerate the embedded demo data in prototypes/report-prototype.js.

Reads only frozen T002/T003/T004 evidence (no re-implementation of verdict
logic) and rewrites the block between the BEGIN/END GENERATED DATA markers
in ``prototypes/report-prototype.js``.

Demo entries: one fault case per fault class (PAGE_OFFSET,
PAGE_METADATA_MISSING, DUPLICATE_TEXT_AMBIGUITY, UNLOCATABLE) plus one PASS
control entry, so the prototype shows PASS in neutral green and never shows
AMBIGUOUS / UNLOCATABLE / UNKNOWN as PASS.

Usage (from the repository root):

    python3 04_source/source/tests/prototypes/build_prototype_data.py

The ``truth_pages`` column is the honest extraction: bundle extraction
records corrected with the upstream values of extraction-stage diffs from
``t004-stage-diffs.json`` (e.g. mm-ext-01 page 2 text_state ERROR -> TEXT,
po-ext-01 pages 2/3 text_sha256 swapped back). The ``extraction`` column
keeps the bundle records exactly as observed, so the drift is visible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PACKAGE_ROOT = REPO_ROOT / "04_source" / "source"
JS_PATH = REPO_ROOT / "prototypes" / "report-prototype.js"
T004_PATH = REPO_ROOT / "07_evidence" / "runtime_logs" / "t004-stage-diffs.json"
T003_PATH = REPO_ROOT / "07_evidence" / "runtime_logs" / "t003-locate.json"
BUNDLES = PACKAGE_ROOT / "fixtures" / "bundles"

DEMO_CASE_IDS = ("po-ext-01", "mm-ext-01", "du-chk-01", "un-ext-01")

BEGIN_MARKER = "/* BEGIN GENERATED DATA (build_prototype_data.py) */"
END_MARKER = "/* END GENERATED DATA */"


def short_hash(value: str | None) -> str | None:
    return value[:12] if value else None


def honest_truth_pages(bundle: dict, stage_diffs: list[dict]) -> list[dict]:
    """Bundle extraction records corrected to the honest (upstream) values."""
    pages = [dict(rec) for rec in bundle["stages"]["extraction"]]
    by_index = {rec["pdf_page_index0"]: rec for rec in pages}
    for diff in stage_diffs:
        if diff["stage"] != "extraction" or diff.get("pdf_page_index0") is None:
            continue
        rec = by_index.get(diff["pdf_page_index0"])
        if rec is not None and diff["field"] in rec:
            rec[diff["field"]] = diff["upstream_value"]
    return pages


def build_fault_entry(case: dict, bundle: dict, locate: dict) -> dict:
    fv = case["fault_verdict"]
    fault_cite = next(
        c for c in bundle["citations"] if c["citation_id"] == fv["citation_id"]
    )
    display = next(
        d for d in bundle["stages"]["display"] if d["citation_id"] == fv["citation_id"]
    )
    return {
        "case_id": case["case_id"],
        "fault_type": case["fault_type"],
        "variant": case["variant"],
        "citation_id": fv["citation_id"],
        "quote_text": fault_cite["quote_text"],
        "quote_sha256": fv["quote_sha256"],
        "verdict": fv["verdict"],
        "first_fault_stage": fv["first_fault_stage"],
        "observed_page_value": fv["observed_page_value"],
        "citation_page_basis": fv["citation_page_basis"],
        "correct_pdf_page_number1": fv["correct_pdf_page_number1"],
        "correct_viewer_page1": fv["correct_viewer_page1"],
        "candidate_source_pages0": fv["candidate_source_pages0"],
        "expected_source_pages0": fv["expected_source_pages0"],
        "document": bundle["document"],
        "truth_pages": honest_truth_pages(bundle, case["stage_diffs"]),
        "extraction": bundle["stages"]["extraction"],
        "chunks": bundle["stages"]["chunking"],
        "index_records": bundle["stages"]["indexing"],
        "display": display,
        "stage_diffs": case["stage_diffs"],
        "locate_fault_quote": locate["fault_quote"],
    }


def build_control_entry(case: dict, bundle: dict, locate: dict) -> dict:
    cv = case["control_verdict"]
    control_cite = next(
        c for c in bundle["citations"] if c["citation_id"] == cv["citation_id"]
    )
    display = next(
        d for d in bundle["stages"]["display"] if d["citation_id"] == cv["citation_id"]
    )
    chunk = next(
        c for c in bundle["stages"]["chunking"]
        if c["chunk_id"] == control_cite["chunk_id"]
    )
    index_rec = next(
        r for r in bundle["stages"]["indexing"]
        if r["record_id"] == control_cite["index_record_id"]
    )
    return {
        "case_id": case["case_id"] + "-control",
        "fault_type": None,
        "variant": "control",
        "citation_id": cv["citation_id"],
        "quote_text": control_cite["quote_text"],
        "quote_sha256": cv["quote_sha256"],
        "verdict": "PASS",
        "first_fault_stage": None,
        "observed_page_value": cv["observed_page_value"],
        "citation_page_basis": cv["citation_page_basis"],
        "correct_pdf_page_number1": cv["correct_pdf_page_number1"],
        "correct_viewer_page1": cv["correct_viewer_page1"],
        "candidate_source_pages0": cv["candidate_source_pages0"],
        "expected_source_pages0": cv["expected_source_pages0"],
        "document": bundle["document"],
        "truth_pages": [dict(rec) for rec in bundle["stages"]["extraction"]],
        "extraction": bundle["stages"]["extraction"],
        "chunks": [chunk],
        "index_records": [index_rec],
        "display": display,
        "stage_diffs": [],
        "locate_fault_quote": locate["control_quote"],
    }


def main() -> None:
    t004 = json.loads(T004_PATH.read_text(encoding="utf-8"))
    t003 = json.loads(T003_PATH.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in t004["cases"]}
    locates = {c["case_id"]: c for c in t003["cases"]}

    entries: list[dict] = []
    for case_id in DEMO_CASE_IDS:
        bundle = json.loads((BUNDLES / f"{case_id}.trace.json").read_text(encoding="utf-8"))
        entries.append(build_fault_entry(cases[case_id], bundle, locates[case_id]))
    # One PASS control entry (from po-ext-01) for contrast.
    bundle = json.loads((BUNDLES / "po-ext-01.trace.json").read_text(encoding="utf-8"))
    entries.append(build_control_entry(cases["po-ext-01"], bundle, locates["po-ext-01"]))

    data_json = json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True)
    block = (
        f"{BEGIN_MARKER}\n"
        f"const PROTOTYPE_CASES = {data_json};\n"
        f"{END_MARKER}"
    )
    text = JS_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    if not pattern.search(text):
        raise SystemExit(f"markers not found in {JS_PATH}")
    JS_PATH.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")
    print(f"wrote {len(entries)} demo entries into {JS_PATH}")


if __name__ == "__main__":
    main()
