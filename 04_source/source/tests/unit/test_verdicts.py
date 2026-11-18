"""T004 — four fault classes and first-fault stage attribution.

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/unit/test_verdicts.py -q

Covers (PROJECT_BOOK.md v1.0.0 §5, §7.3; PAGE_SEMANTICS.md §4):

  * all 48 T002 fixtures: the fault citation's verdict / fault_type /
    first_fault_stage equals the spec's ``expected`` exactly, and the
    control citation in every bundle is PASS (0 false positives);
  * the extraction comparison: exactly the 6 coordinator-confirmed
    bundles differ from the honest extraction (po-ext-01..03 hash
    swaps, mm-ext-01 ERROR, mm-ext-02 omitted hash, mm-ext-03
    omitted record); the other 42 are identical;
  * the three mm-display variants (record absent / value+viewer null /
    viewer null only) are all PAGE_METADATA_MISSING at display;
  * the 12 UNLOCATABLE fault quotes: FAIL_UNLOCATABLE at extraction,
    with reason IMAGE_ONLY (4 image pages) / EMPTY (4 blank pages) /
    NO_EXACT_MATCH (4 near misses) — never "the quote does not exist";
  * duplicate quotes: the full candidate set is kept, the first
    reducing stage is blamed (chunking / indexing / display, 4 each),
    and no single page is ever forced;
  * synthetic bundles: missing stage -> UNKNOWN_TRACE_MISSING (never
    PASS, never a guessed stage); UNKNOWN basis -> UNKNOWN_PAGE_BASIS;
    duplicate with no forced pick -> AMBIGUOUS; >2-page span ->
    NEEDS_MANUAL_REVIEW; stage order is fixed (two wrong stages ->
    the earlier one wins); label-7 display misread -> PAGE_OFFSET.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

# Production package lives in src/ (T013 P2-08: the top-level stub is
# gone); src/ must be first on sys.path when running from a checkout.
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.compare_stages import (  # noqa: E402
    analyze_bundle,
    analyze_citation,
    compare_extraction,
    resolve_display_to_index0,
    stage_diffs_for_bundle,
)
from pagetrace.extract import extract_pages  # noqa: E402
from pagetrace.locate import locate_quote  # noqa: E402
from pagetrace.pdf_input import load_pdf  # noqa: E402
from pagetrace.verdicts import (  # noqa: E402
    CitationVerdict,
    EvidenceItem,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_ids() -> list[str]:
    return sorted(p.stem for p in (FIXTURES / "specs").glob("*.json"))


def _records(case_id: str):
    info = load_pdf(str(FIXTURES / "pdfs" / f"{case_id}.pdf"))
    return extract_pages(info)


def _bundle(case_id: str) -> dict:
    return _load_json(FIXTURES / "bundles" / f"{case_id}.trace.json")


def _spec(case_id: str) -> dict:
    return _load_json(FIXTURES / "specs" / f"{case_id}.json")


def _verdicts(case_id: str):
    return analyze_bundle(_bundle(case_id), _records(case_id))


def _by_id(verdicts, citation_id: str) -> CitationVerdict:
    return next(v for v in verdicts if v.citation_id == citation_id)


# ---------------------------------------------------------------------------
# Fixture-driven: all 48 fault citations + all 48 control citations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", _case_ids())
def test_fault_citation_matches_spec(case_id: str):
    """Fault verdict / fault_type / first_fault_stage == spec expected."""
    spec = _spec(case_id)
    expected = spec["expected"]
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    assert verdict.verdict == expected["verdict"], case_id
    assert verdict.fault_type == expected["fault_type"], case_id
    assert verdict.first_fault_stage == expected["first_fault_stage"], case_id
    assert verdict.candidate_source_pages0 == \
        expected["candidate_source_pages0"], case_id
    assert verdict.expected_source_pages0 == \
        expected["expected_source_pages0"], case_id


@pytest.mark.parametrize("case_id", _case_ids())
def test_control_citation_is_pass(case_id: str):
    """Every bundle's normal control citation is PASS (0 false alarms)."""
    verdict = _by_id(_verdicts(case_id), "cite-control")
    assert verdict.verdict == "PASS", case_id
    assert verdict.fault_type is None, case_id
    assert verdict.first_fault_stage is None, case_id
    assert verdict.correct_pdf_page_number1 == \
        verdict.correct_viewer_page1, case_id
    assert verdict.correct_pdf_page_number1 is not None, case_id


def test_fault_counts_by_class():
    """12/12 per fault class, 48/48 in total."""
    counts: dict[str, int] = {}
    for case_id in _case_ids():
        verdict = _by_id(_verdicts(case_id), "cite-fault")
        counts[verdict.fault_type or "NONE"] = \
            counts.get(verdict.fault_type or "NONE", 0) + 1
    assert counts == {
        "PAGE_OFFSET": 12,
        "PAGE_METADATA_MISSING": 12,
        "DUPLICATE_TEXT_AMBIGUITY": 12,
        "UNLOCATABLE": 12,
    }


# ---------------------------------------------------------------------------
# Extraction comparison: exactly the 6 coordinator-confirmed bundles differ
# ---------------------------------------------------------------------------

def test_extraction_differs_in_exactly_six_bundles():
    """po-ext-01..03 hash swaps; mm-ext-01 ERROR; mm-ext-02 hash
    omitted; mm-ext-03 record omitted. The other 42 bundles match
    the honest extraction exactly."""
    differing = {}
    for case_id in _case_ids():
        diffs = compare_extraction(
            _records(case_id), _bundle(case_id)["stages"]["extraction"])
        if diffs:
            differing[case_id] = [
                (d.pdf_page_index0, d.kind) for d in diffs]
    assert set(differing) == {
        "po-ext-01", "po-ext-02", "po-ext-03",
        "mm-ext-01", "mm-ext-02", "mm-ext-03",
    }, differing
    assert differing["po-ext-01"] == [
        (2, "hash_mismatch"), (3, "hash_mismatch")]
    assert differing["po-ext-02"] == [
        (0, "hash_mismatch"), (1, "hash_mismatch")]
    assert differing["po-ext-03"] == [
        (3, "hash_mismatch"), (6, "hash_mismatch")]
    assert differing["mm-ext-01"] == [(2, "missing")]  # TEXT -> ERROR
    assert differing["mm-ext-02"] == [(1, "missing")]  # hash key omitted
    assert differing["mm-ext-03"] == [(4, "missing")]  # record omitted


def test_extraction_diffs_are_json_serialisable():
    diffs = stage_diffs_for_bundle(_bundle("po-ext-01"),
                                   _records("po-ext-01"))
    text = json.dumps([d.to_dict() for d in diffs], sort_keys=True)
    assert "hash_mismatch" in text
    assert "extraction" in text


# ---------------------------------------------------------------------------
# PAGE_METADATA_MISSING: the three display variants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", ["mm-dsp-10", "mm-dsp-11", "mm-dsp-12"])
def test_mm_display_variants_all_metadata_missing_at_display(case_id: str):
    """Display record absent / value+viewer null / viewer null only:
    all three are PAGE_METADATA_MISSING at display."""
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    assert verdict.verdict == "FAIL_METADATA_MISSING", case_id
    assert verdict.fault_type == "PAGE_METADATA_MISSING", case_id
    assert verdict.first_fault_stage == "display", case_id


@pytest.mark.parametrize("case_id", ["mm-ext-01", "mm-ext-02", "mm-ext-03"])
def test_mm_extraction_variants_at_extraction(case_id: str):
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    assert verdict.verdict == "FAIL_METADATA_MISSING", case_id
    assert verdict.first_fault_stage == "extraction", case_id


# ---------------------------------------------------------------------------
# UNLOCATABLE: image / blank / near-miss — never "does not exist"
# ---------------------------------------------------------------------------

def test_unlocatable_reasons_split_four_four_four():
    """4 IMAGE_ONLY, 4 EMPTY, 4 NO_EXACT_MATCH across the 12 cases.

    FIX-R1 P1-R1-02: attribution is 8 x extraction (the IMAGE_ONLY /
    EMPTY cases, provable extraction failure) + 4 x null (the
    near-miss NO_EXACT_MATCH cases, no stage can be blamed); the
    reason split 4/4/4 is unchanged.
    """
    reasons: dict[str, int] = {}
    for case_id in [f"un-ext-{i:02d}" for i in range(1, 13)]:
        verdict = _by_id(_verdicts(case_id), "cite-fault")
        assert verdict.verdict == "FAIL_UNLOCATABLE", case_id
        assert verdict.fault_type == "UNLOCATABLE", case_id
        if case_id in ("un-ext-09", "un-ext-10", "un-ext-11", "un-ext-12"):
            assert verdict.first_fault_stage is None, case_id
            assert verdict.expected_source_pages0 is None, case_id
        else:
            assert verdict.first_fault_stage == "extraction", case_id
            assert verdict.expected_source_pages0 is not None, case_id
        assert verdict.candidate_source_pages0 == [], case_id
        assert verdict.correct_pdf_page_number1 is None, case_id
        reasons[verdict.reason or "NONE"] = \
            reasons.get(verdict.reason or "NONE", 0) + 1
    assert reasons == {
        "IMAGE_ONLY": 4, "EMPTY": 4, "NO_EXACT_MATCH": 4,
    }, reasons


@pytest.mark.parametrize("case_id", [f"un-ext-{i:02d}" for i in range(1, 13)])
def test_unlocatable_never_claims_quote_does_not_exist(case_id: str):
    """The notes must say the text layer cannot confirm it — never
    that the quoted text does not exist."""
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    joined = " ".join(verdict.notes + [e.note for e in verdict.evidence])
    assert "does not establish" in joined
    assert "does not exist" not in joined


def test_scanned_page_without_text_is_not_a_missing_quote():
    """A quote whose only occurrence is raster text locates 0 pages
    in the text layer, yet the verdict is UNLOCATABLE (image-only),
    not a claim that the document lacks the text."""
    verdict = _by_id(_verdicts("un-ext-01"), "cite-fault")
    assert verdict.reason == "IMAGE_ONLY"
    assert verdict.expected_source_pages0 == [2]  # trace-claimed page


# ---------------------------------------------------------------------------
# DUPLICATE_TEXT_AMBIGUITY: full set kept, first reducing stage blamed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id,stage", [
    ("du-chk-01", "chunking"), ("du-chk-02", "chunking"),
    ("du-chk-03", "chunking"), ("du-chk-04", "chunking"),
    ("du-idx-05", "indexing"), ("du-idx-06", "indexing"),
    ("du-idx-07", "indexing"), ("du-idx-08", "indexing"),
    ("du-dsp-09", "display"), ("du-dsp-10", "display"),
    ("du-dsp-11", "display"), ("du-dsp-12", "display"),
])
def test_duplicate_first_reducing_stage(case_id: str, stage: str):
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    assert verdict.verdict == "FAIL_AMBIGUOUS", case_id
    assert verdict.fault_type == "DUPLICATE_TEXT_AMBIGUITY", case_id
    assert verdict.first_fault_stage == stage, case_id
    # The full candidate set is kept; no single page is forced.
    assert len(verdict.candidate_source_pages0) >= 2, case_id
    assert verdict.candidate_source_pages0 == \
        verdict.expected_source_pages0, case_id
    assert verdict.correct_pdf_page_number1 == [
        p + 1 for p in verdict.candidate_source_pages0], case_id


def test_duplicate_display_pick_is_not_an_offset():
    """du-dsp-09 picks candidate page 2 of [2, 4]: ambiguity, not a
    page offset — the picked page is a real occurrence."""
    verdict = _by_id(_verdicts("du-dsp-09"), "cite-fault")
    assert verdict.verdict == "FAIL_AMBIGUOUS"
    assert verdict.observed_page_value == 3  # 1-based display of page 2


# ---------------------------------------------------------------------------
# PAGE_OFFSET: positive and negative examples per stage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id,stage", [
    ("po-ext-01", "extraction"), ("po-ext-02", "extraction"),
    ("po-ext-03", "extraction"),
    ("po-chk-04", "chunking"), ("po-chk-05", "chunking"),
    ("po-chk-06", "chunking"),
    ("po-idx-07", "indexing"), ("po-idx-08", "indexing"),
    ("po-idx-09", "indexing"),
    ("po-dsp-10", "display"), ("po-dsp-11", "display"),
    ("po-dsp-12", "display"),
])
def test_page_offset_first_stage(case_id: str, stage: str):
    verdict = _by_id(_verdicts(case_id), "cite-fault")
    assert verdict.verdict == "FAIL_PAGE_OFFSET", case_id
    assert verdict.fault_type == "PAGE_OFFSET", case_id
    assert verdict.first_fault_stage == stage, case_id


def test_display_zero_based_value_passed_to_viewer_is_offset():
    """§6.2 example shape: value 1 (PDF_INDEX_0) shown as viewer 1
    instead of 2."""
    verdict = _by_id(_verdicts("po-dsp-10"), "cite-fault")
    assert verdict.observed_page_value == 1
    assert verdict.correct_viewer_page1 == [2]


def test_label_seven_is_not_viewer_page_seven():
    """Physical page 0 carries label "7"; display showing viewer 7
    is an offset, not a correct page (R-03 / PAGE_SEMANTICS ex. E)."""
    verdict = _by_id(_verdicts("po-dsp-12"), "cite-fault")
    assert verdict.verdict == "FAIL_PAGE_OFFSET"
    assert verdict.first_fault_stage == "display"
    assert verdict.correct_viewer_page1 == [1]
    assert verdict.observed_page_value == "7"


def test_resolve_display_label_lookup():
    """Label lookup is a table lookup, never arithmetic (R-03)."""
    label_map = {"i": [0], "ii": [1], "iii": [2], "iv": [3]}
    index, kind, _ = resolve_display_to_index0(
        {"citation_page_value": "iv", "citation_page_basis": "PDF_LABEL",
         "viewer_page1": 4}, label_map)
    assert (index, kind) == (3, "ok")
    index, kind, _ = resolve_display_to_index0(
        {"citation_page_value": "ix", "citation_page_basis": "PDF_LABEL",
         "viewer_page1": None}, label_map)
    assert (index, kind) == (None, "label_unresolved")


# ---------------------------------------------------------------------------
# Synthetic bundles: uncertainty is never converted to PASS
# ---------------------------------------------------------------------------

def _synthetic_bundle_and_records():
    """A clean 3-page bundle whose fault quote is on page 1 only."""
    bundle = _bundle("po-chk-05")
    records = _records("po-chk-05")
    return copy.deepcopy(bundle), records


def _analyse(bundle, records, citation_id="cite-fault"):
    citation = next(c for c in bundle["citations"]
                    if c["citation_id"] == citation_id)
    return analyze_citation(
        citation=citation, bundle=bundle, honest_records=records,
        quote_match=locate_quote(records, citation["quote_text"]))


def test_missing_stage_is_unknown_trace_missing_not_pass():
    bundle, records = _synthetic_bundle_and_records()
    bundle["stages"]["missing_stages"] = ["indexing"]
    bundle["stages"].pop("indexing")
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "UNKNOWN_TRACE_MISSING"
    assert verdict.fault_type is None
    assert verdict.first_fault_stage is None
    assert verdict.missing_stages == ["indexing"]


def test_missing_stage_is_not_skipped_to_blame_display():
    """Even when display also disagrees, a missing earlier stage
    forbids blaming any stage."""
    bundle, records = _synthetic_bundle_and_records()
    bundle["stages"]["missing_stages"] = ["chunking"]
    bundle["stages"].pop("chunking")
    for rec in bundle["stages"]["display"]:
        if rec["citation_id"] == "cite-fault":
            rec["viewer_page1"] = rec["viewer_page1"] + 1
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "UNKNOWN_TRACE_MISSING"


@pytest.mark.parametrize(
    "bad", [5, None, "2", [2, "x"]],
    ids=["int", "null", "string", "non-int-member"],
)
def test_non_list_source_pages_is_metadata_missing_not_type_error(bad):
    """T013 P2-02: a non-list (or non-integer) ``source_page_indices0``
    is treated as missing metadata, never a raw ``TypeError``."""
    bundle, records = _synthetic_bundle_and_records()
    for rec in bundle["stages"]["chunking"]:
        if rec["chunk_id"] == "c-fault":
            rec["source_page_indices0"] = bad
    verdict = _by_id(analyze_bundle(bundle, records), "cite-fault")
    assert verdict.verdict == "FAIL_METADATA_MISSING", bad
    assert verdict.fault_type == "PAGE_METADATA_MISSING", bad
    assert verdict.first_fault_stage == "chunking", bad


def test_trace_anchor_pages_ignores_non_list_source_pages():
    """T013 P2-02: an unlocatable quote whose trace anchor carries a
    non-list ``source_page_indices0`` must not raise ``TypeError``."""
    from pagetrace.compare_stages import _trace_anchor_pages
    stages = {
        "chunking": [{"chunk_id": "c1", "source_page_indices0": 5}],
        "indexing": [{"record_id": "v1", "source_page_indices0": None}],
        "display": [],
    }
    assert _trace_anchor_pages(
        {"chunk_id": "c1", "index_record_id": "v1"}, stages) is None


def test_unknown_basis_is_unknown_page_basis():
    bundle, records = _synthetic_bundle_and_records()
    # Repair the chunking fault so display is the first thing checked
    # that can go wrong: use the control citation's clean chain and
    # corrupt only its display basis.
    for rec in bundle["stages"]["chunking"]:
        if rec["chunk_id"] == "c-fault":
            rec["source_page_indices0"] = [2]
    for rec in bundle["stages"]["indexing"]:
        if rec["record_id"] == "v-fault":
            rec["source_page_indices0"] = [2]
            rec["pdf_page_label"] = records[2].pdf_page_label
    for rec in bundle["stages"]["display"]:
        if rec["citation_id"] == "cite-fault":
            rec["citation_page_basis"] = "UNKNOWN"
            rec["citation_page_value"] = 2
            rec["viewer_page1"] = None
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "UNKNOWN_PAGE_BASIS"
    assert verdict.first_fault_stage == "display"


def test_duplicate_with_no_forced_pick_is_ambiguous_not_pass():
    """Duplicate quote, chunk/index keep the full set, display record
    removed: no page is forced, so AMBIGUOUS — not PASS, not a guess."""
    bundle = _bundle("du-dsp-09")
    records = _records("du-dsp-09")
    bundle = copy.deepcopy(bundle)
    bundle["stages"]["display"] = [
        rec for rec in bundle["stages"]["display"]
        if rec["citation_id"] != "cite-fault"]
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "AMBIGUOUS"
    assert verdict.fault_type is None
    assert verdict.first_fault_stage is None
    assert verdict.candidate_source_pages0 == [2, 4]


def test_stage_order_is_fixed_earlier_wrong_stage_wins():
    """Chunking and indexing both wrong (different pages): the first
    fault stage is chunking, not indexing."""
    bundle, records = _synthetic_bundle_and_records()
    for rec in bundle["stages"]["indexing"]:
        if rec["record_id"] == "v-fault":
            rec["source_page_indices0"] = [4]
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "FAIL_PAGE_OFFSET"
    assert verdict.first_fault_stage == "chunking"


def test_out_of_range_display_value_gets_own_reason_not_type_mismatch():
    """T013 P2-04: PDF_NUMBER_1 value 0 (out of range, right type) is
    NEEDS_MANUAL_REVIEW with reason VALUE_OUT_OF_RANGE — not
    VALUE_BASIS_TYPE_MISMATCH. The verdict itself is unchanged."""
    bundle, records = _synthetic_bundle_and_records()
    # Repair the chunking/indexing fault so display is first checked.
    for rec in bundle["stages"]["chunking"]:
        if rec["chunk_id"] == "c-fault":
            rec["source_page_indices0"] = [2]
    for rec in bundle["stages"]["indexing"]:
        if rec["record_id"] == "v-fault":
            rec["source_page_indices0"] = [2]
            rec["pdf_page_label"] = records[2].pdf_page_label
    for rec in bundle["stages"]["display"]:
        if rec["citation_id"] == "cite-fault":
            rec["citation_page_basis"] = "PDF_NUMBER_1"
            rec["citation_page_value"] = 0
            rec["viewer_page1"] = 1
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "NEEDS_MANUAL_REVIEW"
    assert verdict.reason == "VALUE_OUT_OF_RANGE"
    assert verdict.first_fault_stage == "display"


def test_type_mismatch_display_value_keeps_old_reason():
    """T013 P2-04 (control): a genuine type mismatch still reports
    VALUE_BASIS_TYPE_MISMATCH."""
    bundle, records = _synthetic_bundle_and_records()
    for rec in bundle["stages"]["chunking"]:
        if rec["chunk_id"] == "c-fault":
            rec["source_page_indices0"] = [2]
    for rec in bundle["stages"]["indexing"]:
        if rec["record_id"] == "v-fault":
            rec["source_page_indices0"] = [2]
            rec["pdf_page_label"] = records[2].pdf_page_label
    for rec in bundle["stages"]["display"]:
        if rec["citation_id"] == "cite-fault":
            rec["citation_page_basis"] = "PDF_NUMBER_1"
            rec["citation_page_value"] = "2"
            rec["viewer_page1"] = 2
    verdict = _analyse(bundle, records)
    assert verdict.verdict == "NEEDS_MANUAL_REVIEW"
    assert verdict.reason == "VALUE_BASIS_TYPE_MISMATCH"


def test_stage_diffs_mark_needs_manual_review_as_needs_review():
    """T013 P2-13: stage_diffs_for_bundle gives a NEEDS_MANUAL_REVIEW
    verdict its own kind ('needs_review'), not 'offset' — no page was
    guessed, so there is no offset to report."""
    bundle, records = _synthetic_bundle_and_records()
    for rec in bundle["stages"]["chunking"]:
        if rec["chunk_id"] == "c-fault":
            rec["source_page_indices0"] = [2]
    for rec in bundle["stages"]["indexing"]:
        if rec["record_id"] == "v-fault":
            rec["source_page_indices0"] = [2]
            rec["pdf_page_label"] = records[2].pdf_page_label
    for rec in bundle["stages"]["display"]:
        if rec["citation_id"] == "cite-fault":
            rec["citation_page_basis"] = "PDF_NUMBER_1"
            rec["citation_page_value"] = 0
            rec["viewer_page1"] = 1
    assert _by_id(analyze_bundle(bundle, records),
                  "cite-fault").verdict == "NEEDS_MANUAL_REVIEW"
    diffs = stage_diffs_for_bundle(bundle, records)
    kinds = {d.kind for d in diffs if d.stage == "display"}
    assert kinds == {"needs_review"}, kinds


def test_unsupported_span_needs_manual_review():
    """A quote spanning three pages is detected, not located.

    The quote is the tail of page 0 + all of page 1 + the head of
    page 2, joined without spaces at the joins (so no adjacent pair
    contains it either): the locator must report unsupported_span.
    """
    from pagetrace.extract import PageTextRecord
    records = [
        PageTextRecord(0, "1", "TEXT", None,
                       "abcdefghij klmnopqrst uvwxyzabcd"),
        PageTextRecord(1, "2", "TEXT", None,
                       "efghijklmn opqrstuvwx yzabcdefghi"),
        PageTextRecord(2, "3", "TEXT", None,
                       "jklmnopqrs tuvwxyzabc defghijklmn"),
    ]
    quote = ("klmnopqrst uvwxyzabcd"
             "efghijklmn opqrstuvwx yzabcdefghi"
             "jklmnopqrs tuvwxyzabc")
    match = locate_quote(records, quote)
    assert match.span_status == "unsupported_span"
    bundle = {"stages": {"extraction": [], "chunking": [], "indexing": [],
                         "display": [], "missing_stages": []},
              "citations": [{"citation_id": "c1", "quote_text": quote,
                             "chunk_id": "k", "index_record_id": "v"}]}
    verdict = analyze_citation(
        citation=bundle["citations"][0], bundle=bundle,
        honest_records=records, quote_match=match)
    assert verdict.verdict == "NEEDS_MANUAL_REVIEW"
    assert verdict.reason == "UNSUPPORTED_SPAN"
    assert verdict.candidate_source_pages0 == []


# ---------------------------------------------------------------------------
# Verdict value object: report-schema shape
# ---------------------------------------------------------------------------

def test_verdict_to_dict_matches_report_schema():
    """Every result dict for all 48 bundles validates against the
    frozen pagetrace.report/v1 schema (validated as a whole report,
    so the schema's $defs $refs resolve)."""
    from jsonschema import validate
    schema = _load_json(
        PACKAGE_ROOT / "contracts" / "pagetrace.report.v1.schema.json")
    for case_id in _case_ids():
        results = [v.to_dict() for v in _verdicts(case_id)]
        report = {
            "schema": "pagetrace.report/v1",
            "case_id": case_id,
            "document": {
                "file_name": f"{case_id}.pdf",
                "sha256": _spec(case_id)["pdf_sha256"],
                "page_count": _spec(case_id)["page_count"],
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


def test_pass_requires_null_fault_and_stage():
    with pytest.raises(ValueError):
        CitationVerdict(
            citation_id="x", quote_sha256="0" * 64,
            citation_page_value=1, citation_page_basis="PDF_NUMBER_1",
            candidate_source_pages0=[0], expected_source_pages0=[0],
            observed_page_value=1, correct_pdf_page_number1=[1],
            correct_viewer_page1=[1], verdict="PASS",
            fault_type="PAGE_OFFSET", first_fault_stage=None,
            evidence=[])


def test_evidence_item_defaults_to_none_values_not_zero():
    item = EvidenceItem(stage="display", field="viewer_page1", note="n")
    assert item.to_dict()["upstream_value"] is None
    assert item.to_dict()["downstream_value"] is None
