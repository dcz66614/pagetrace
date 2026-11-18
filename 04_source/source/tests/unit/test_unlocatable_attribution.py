"""FIX-R1 P1-R1-02 — UNLOCATABLE must not be blamed on extraction
without proof (independent regression test).

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/unit/test_unlocatable_attribution.py -q

GPT final review R1 reproduced that ``un-ext-12`` (near-miss quote,
``NO_EXACT_MATCH``) was wrongly attributed to ``extraction`` even
though its 8 pages are all TEXT and the extraction trace matches the
honest extraction exactly; production, Oracle and Golden shared the
wrong rule, so their agreement proved nothing. New rule, pinned here
(PROJECT_BOOK.md v1.0.0 §5 / §7.2 / §7.3):

* extraction is blamed only for a provable extraction failure: the
  trace-claimed page is honestly ``IMAGE_ONLY`` / ``EMPTY`` (no text
  layer to extract), or a bundle extraction record for a claimed page
  provably differs from the honest extraction;
* otherwise (near miss on a TEXT page with verified-correct
  extraction, or no usable trace anchor) ``first_fault_stage`` is
  ``None`` and ``expected_source_pages0`` is ``None``: the
  trace-claimed page is unconfirmed, never a verified source. The
  verdict stays ``FAIL_UNLOCATABLE`` / ``UNLOCATABLE`` with reason
  ``NO_EXACT_MATCH`` / ``NO_TEXT_LAYER``.

Covers: the GPT reproduction facts for ``un-ext-12``; all four
near-miss cases (``un-ext-09..12``) unblamed in production, Oracle
and Golden; all eight image/blank cases (``un-ext-01..08``) still
blaming extraction (no overcorrection); the 4/4/4 reason split;
synthetic tampering (a provably wrong extraction record for the
claimed page still blames extraction, a wrong record on an unrelated
page does not); the no-anchor case; and report-schema validity of a
``null`` first fault stage.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))
sys.path.insert(0, str(PACKAGE_ROOT / "tests"))

from pagetrace.compare_stages import (  # noqa: E402
    analyze_bundle,
    analyze_citation,
    compare_extraction,
)
from pagetrace.extract import extract_pages  # noqa: E402
from pagetrace.locate import locate_quote  # noqa: E402
from pagetrace.pdf_input import load_pdf  # noqa: E402

from oracle.api import analyze_case  # noqa: E402

NEAR_MISS_CASES = ("un-ext-09", "un-ext-10", "un-ext-11", "un-ext-12")
IMAGE_ONLY_CASES = ("un-ext-01", "un-ext-02", "un-ext-03", "un-ext-04")
EMPTY_CASES = ("un-ext-05", "un-ext-06", "un-ext-07", "un-ext-08")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle(case_id: str) -> dict:
    return _load_json(FIXTURES / "bundles" / f"{case_id}.trace.json")


def _spec(case_id: str) -> dict:
    return _load_json(FIXTURES / "specs" / f"{case_id}.json")


def _records(case_id: str):
    info = load_pdf(str(FIXTURES / "pdfs" / f"{case_id}.pdf"))
    return extract_pages(info)


def _golden_fault(case_id: str) -> dict:
    golden = _load_json(FIXTURES / "golden" / "expected.json")
    return next(
        c["fault"] for c in golden["cases"] if c["case_id"] == case_id)


def _prod_fault(case_id: str, bundle: dict | None = None):
    verdicts = analyze_bundle(
        bundle if bundle is not None else _bundle(case_id),
        _records(case_id))
    return next(v for v in verdicts if v.citation_id == "cite-fault")


def _oracle_fault(case_id: str, bundle: dict | None = None):
    result = analyze_case(
        str(FIXTURES / "pdfs" / f"{case_id}.pdf"),
        bundle if bundle is not None else _bundle(case_id))
    return result.by_citation_id("cite-fault")


def _analyse_one(bundle: dict, records, citation_id="cite-fault"):
    citation = next(c for c in bundle["citations"]
                    if c["citation_id"] == citation_id)
    return analyze_citation(
        citation=citation, bundle=bundle, honest_records=records,
        quote_match=locate_quote(records, citation["quote_text"]))


# ---------------------------------------------------------------------------
# GPT reproduction facts for un-ext-12
# ---------------------------------------------------------------------------

def test_un_ext_12_reproduces_gpt_findings():
    """GPT R1 repro facts, as they stand after the FIX-R1 §8.1 fix:
    extraction trace matches the honest extraction; the quote differs
    from the page-5 sentence by exactly one character; the quote is
    found on no page. Historical note: at R1 the 8 pages were all
    TEXT; the §8.1 composition fix (FIX-R1收尾) made page index 6
    EMPTY so the case contains a no-text-layer page, while anchor
    page 5 stays TEXT and the one-character difference is unchanged.
    """
    records = _records("un-ext-12")
    assert [r.text_state for r in records] == (
        ["TEXT"] * 6 + ["EMPTY"] + ["TEXT"])
    bundle = _bundle("un-ext-12")
    assert compare_extraction(records, bundle["stages"]["extraction"]) == []
    quote = bundle["citations"][0]["quote_text"]
    assert locate_quote(records, quote).candidate_source_pages0 == []
    page5_lines = [line.strip() for line in
                   (records[5].extracted_text or "").splitlines()
                   if "近似句un-ext-12" in line]
    assert len(page5_lines) == 1
    sentence = page5_lines[0]
    assert len(sentence) == len(quote)
    differing = [i for i, (a, b) in enumerate(zip(sentence, quote))
                 if a != b]
    assert differing == [26]  # 原文 (page) vs 正文 (quote)
    assert sentence[26] == "原" and quote[26] == "正"


def test_un_ext_12_no_false_extraction_blame():
    """FAIL_UNLOCATABLE / NO_EXACT_MATCH, but no stage is blamed and
    the trace-claimed page 6 (index 5) is not a confirmed source."""
    for verdict in (_prod_fault("un-ext-12"),
                    _oracle_fault("un-ext-12")):
        assert verdict.verdict == "FAIL_UNLOCATABLE"
        assert verdict.fault_type == "UNLOCATABLE"
        assert verdict.reason == "NO_EXACT_MATCH"
        assert verdict.first_fault_stage is None
        assert verdict.expected_source_pages0 is None
        assert verdict.candidate_source_pages0 == []
        assert verdict.correct_pdf_page_number1 is None
        joined = " ".join(
            verdict.notes + [e.note for e in verdict.evidence])
        assert "does not establish" in joined
        assert "does not exist" not in joined
        assert "No stage is blamed" in joined
        assert "not a confirmed source" in joined
    golden = _golden_fault("un-ext-12")
    assert golden["verdict"] == "FAIL_UNLOCATABLE"
    assert golden["fault_type"] == "UNLOCATABLE"
    assert golden["unlocatable_reason"] == "NO_EXACT_MATCH"
    assert golden["first_fault_stage"] is None
    assert golden["expected_source_pages0"] is None


# ---------------------------------------------------------------------------
# All four near-miss cases: same rule, same outcome, three-way agreement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", NEAR_MISS_CASES)
def test_near_miss_cases_have_no_attributable_stage(case_id: str):
    """Production, Oracle and Golden agree: no stage blamed, no
    confirmed source page — for every NO_EXACT_MATCH case, not just
    un-ext-12."""
    prod = _prod_fault(case_id)
    oracle = _oracle_fault(case_id)
    golden = _golden_fault(case_id)
    for verdict in (prod, oracle):
        assert verdict.verdict == "FAIL_UNLOCATABLE", case_id
        assert verdict.fault_type == "UNLOCATABLE", case_id
        assert verdict.reason == "NO_EXACT_MATCH", case_id
        assert verdict.first_fault_stage is None, case_id
        assert verdict.expected_source_pages0 is None, case_id
    assert golden["first_fault_stage"] is None, case_id
    assert golden["expected_source_pages0"] is None, case_id
    assert golden["unlocatable_reason"] == "NO_EXACT_MATCH", case_id
    # The spec expectations for all four near-miss cases were fixed
    # with the code (fixtures/specs/un-ext-09..12.json: expected
    # first_fault_stage / expected_source_pages0 are null); the
    # generator (tools/generate_fixtures.py) still encodes the old
    # rule — see 07_evidence/runtime_logs/FIX_R1_UNLOCATABLE.md.
    if case_id == "un-ext-12":
        assert _spec(case_id)["expected"]["first_fault_stage"] is None
        assert _spec(case_id)["expected"]["expected_source_pages0"] is None


@pytest.mark.parametrize("case_id", IMAGE_ONLY_CASES + EMPTY_CASES)
def test_image_and_blank_cases_still_blame_extraction(case_id: str):
    """No overcorrection: a claimed page that honestly has no text
    layer is still a provable extraction failure."""
    prod = _prod_fault(case_id)
    oracle = _oracle_fault(case_id)
    golden = _golden_fault(case_id)
    expected_reason = ("IMAGE_ONLY" if case_id in IMAGE_ONLY_CASES
                       else "EMPTY")
    for verdict in (prod, oracle):
        assert verdict.verdict == "FAIL_UNLOCATABLE", case_id
        assert verdict.reason == expected_reason, case_id
        assert verdict.first_fault_stage == "extraction", case_id
        assert verdict.expected_source_pages0 is not None, case_id
        assert len(verdict.expected_source_pages0) == 1, case_id
    assert golden["first_fault_stage"] == "extraction", case_id
    assert golden["expected_source_pages0"] == \
        prod.expected_source_pages0, case_id
    assert golden["unlocatable_reason"] == expected_reason, case_id


def test_unlocatable_reasons_still_split_4_4_4():
    """The fix changes attribution, not reasons."""
    reasons: dict[str, int] = {}
    for i in range(1, 13):
        verdict = _prod_fault(f"un-ext-{i:02d}")
        assert verdict.verdict == "FAIL_UNLOCATABLE"
        reasons[verdict.reason or "NONE"] = \
            reasons.get(verdict.reason or "NONE", 0) + 1
    assert reasons == {"IMAGE_ONLY": 4, "EMPTY": 4, "NO_EXACT_MATCH": 4}


# ---------------------------------------------------------------------------
# Synthetic bundles: a provable extraction failure still blames extraction
# ---------------------------------------------------------------------------

def test_tampered_anchor_extraction_still_blames_extraction():
    """The bundle extraction record for the claimed page 5 is given a
    wrong hash: extraction provably failed, so it is blamed — in both
    implementations."""
    bundle = copy.deepcopy(_bundle("un-ext-12"))
    records = _records("un-ext-12")
    extraction = bundle["stages"]["extraction"]
    extraction[5]["text_sha256"] = "0" * 64
    assert compare_extraction(records, extraction) != []
    for verdict in (_analyse_one(bundle, records),
                    _oracle_fault("un-ext-12", bundle)):
        assert verdict.verdict == "FAIL_UNLOCATABLE"
        assert verdict.reason == "NO_EXACT_MATCH"
        assert verdict.first_fault_stage == "extraction"
        assert verdict.expected_source_pages0 == [5]


def test_tampered_unrelated_page_does_not_blame_extraction():
    """A wrong extraction record on page 0 — not a trace-claimed page
    for this citation — must not blame extraction for it."""
    bundle = copy.deepcopy(_bundle("un-ext-12"))
    records = _records("un-ext-12")
    bundle["stages"]["extraction"][0]["text_sha256"] = "0" * 64
    for verdict in (_analyse_one(bundle, records),
                    _oracle_fault("un-ext-12", bundle)):
        assert verdict.verdict == "FAIL_UNLOCATABLE"
        assert verdict.reason == "NO_EXACT_MATCH"
        assert verdict.first_fault_stage is None
        assert verdict.expected_source_pages0 is None


def test_no_anchor_unlocatable_has_no_stage():
    """No trace anchor names the intended page: reason NO_TEXT_LAYER,
    no stage blamed, no expected source."""
    bundle = copy.deepcopy(_bundle("un-ext-12"))
    records = _records("un-ext-12")
    chunk = next(c for c in bundle["stages"]["chunking"]
                 if c["chunk_id"] == "c-fault")
    chunk["source_page_indices0"] = []
    index = next(r for r in bundle["stages"]["indexing"]
                 if r["record_id"] == "v-fault")
    index["source_page_indices0"] = []
    for verdict in (_analyse_one(bundle, records),
                    _oracle_fault("un-ext-12", bundle)):
        assert verdict.verdict == "FAIL_UNLOCATABLE"
        assert verdict.reason == "NO_TEXT_LAYER"
        assert verdict.first_fault_stage is None
        assert verdict.expected_source_pages0 is None


# ---------------------------------------------------------------------------
# Report schema: null first_fault_stage is valid for FAIL_UNLOCATABLE
# ---------------------------------------------------------------------------

def test_unlocatable_null_stage_validates_against_report_schema():
    """A whole un-ext-12 report (null first_fault_stage on the fault
    citation) validates against frozen pagetrace.report/v1."""
    from jsonschema import validate

    schema = _load_json(
        PACKAGE_ROOT / "contracts" / "pagetrace.report.v1.schema.json")
    results = [v.to_dict() for v in
               analyze_bundle(_bundle("un-ext-12"), _records("un-ext-12"))]
    report = {
        "schema": "pagetrace.report/v1",
        "case_id": "un-ext-12",
        "document": {
            "file_name": "un-ext-12.pdf",
            "sha256": _spec("un-ext-12")["pdf_sha256"],
            "page_count": _spec("un-ext-12")["page_count"],
        },
        "tool": {"name": "pagetrace", "version": "0.1.0"},
        "results": results,
        "summary": {
            "total_citations": len(results),
            "pass_count": sum(
                1 for r in results if r["verdict"] == "PASS"),
            "fail_count": sum(
                1 for r in results if r["verdict"].startswith("FAIL")),
            "unknown_count": sum(
                1 for r in results
                if r["verdict"].startswith("UNKNOWN")),
            "ambiguous_count": sum(
                1 for r in results if r["verdict"] == "AMBIGUOUS"),
            "normalized_result_sha256": None,
        },
    }
    validate(report, schema)
    fault = next(r for r in results if r["citation_id"] == "cite-fault")
    assert fault["first_fault_stage"] is None
    assert fault["expected_source_pages0"] is None
