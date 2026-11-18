"""T006 Oracle tests — independence, units, and Golden reproduction.

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/oracle -q

Covers:

* independence: no file under ``tests/oracle/`` imports ``pagetrace``
  or ``pypdf`` (the Oracle reads PDFs only through pdfminer.six);
* text folding / fingerprint / single-glyph repair (``textnorm``);
* exact location incl. multi-page candidates, adjacent cross-page
  spans, not-found and >2-page unsupported spans (``locate``);
* pdfminer page reading: labels, text states, image detection,
  fingerprint agreement with bundle hashes on pages pdfminer reads
  exactly (``pdfread``);
* stage attribution on synthetic bundles: missing stage ->
  UNKNOWN_TRACE_MISSING, UNKNOWN basis -> UNKNOWN_PAGE_BASIS,
  duplicate with no forced pick -> AMBIGUOUS, unresolvable label ->
  NEEDS_MANUAL_REVIEW (``attribute``);
* Golden reproduction: the independent Oracle re-derives every entry
  of ``fixtures/golden/expected.json`` from spec + PDF + bundle —
  48 fault citations (12 per fault type), 48 control citations all
  PASS, extraction differences in exactly the 6 coordinator-confirmed
  bundles.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"
ORACLE_DIR = PACKAGE_ROOT / "tests" / "oracle"

sys.path.insert(0, str(PACKAGE_ROOT / "tests"))

from oracle import api as oracle_api  # noqa: E402
from oracle import attribute as oracle_attr  # noqa: E402
from oracle import locate as oracle_locate  # noqa: E402
from oracle import pdfread as oracle_pdfread  # noqa: E402
from oracle import textnorm as oracle_textnorm  # noqa: E402

FAULT_TYPES = (
    "PAGE_OFFSET",
    "PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE",
)

EXPECTED_EXTRACTION_DIFFERING = {
    "mm-ext-01",
    "mm-ext-02",
    "mm-ext-03",
    "po-ext-01",
    "po-ext-02",
    "po-ext-03",
}


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_spec(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "specs" / f"{case_id}.json").read_text(encoding="utf-8"))


def load_bundle(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "bundles" / f"{case_id}.trace.json").read_text(
            encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(
        (FIXTURES / "golden" / "expected.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Independence
# ---------------------------------------------------------------------------

_IMPORT_RE = re.compile(
    r"^\s*(import\s+pagetrace|import\s+pypdf|from\s+pagetrace\b"
    r"|from\s+pypdf\b|import\s+src\b)", re.MULTILINE)


def test_oracle_imports_nothing_from_production():
    """No Oracle source file imports pagetrace, pypdf or src/.

    Docstring *mentions* of those names are allowed; only import
    statements are checked.  The same check is recorded in the
    evidence log ``t006-oracle-independence.log``.
    """
    offenders = []
    for path in sorted(ORACLE_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits = _IMPORT_RE.findall(text)
        if hits:
            offenders.append((path.name, hits))
    # Note: sys.modules is deliberately NOT asserted here — when the
    # parity suite runs in the same pytest process, the production
    # package is imported by the *parity* test module during
    # collection, which says nothing about what the Oracle imports.
    # The source grep above is the independence check.
    assert offenders == [], f"Oracle imports production code: {offenders}"


def test_oracle_modules_do_not_share_production_names():
    """Oracle modules expose their own function objects (no re-export
    of production functions): the attribute walk, locator and text
    folder live in this package, under these names."""
    assert oracle_attr.analyze_citation.__module__.startswith("oracle.")
    assert oracle_locate.locate_quote.__module__.startswith("oracle.")
    assert oracle_textnorm.collapse_text.__module__.startswith("oracle.")
    assert oracle_pdfread.read_pdf_pages.__module__.startswith("oracle.")


# ---------------------------------------------------------------------------
# textnorm
# ---------------------------------------------------------------------------

def test_collapse_text_follows_section_4_2():
    assert oracle_textnorm.collapse_text("a\r\nb\rc  d") == "a b c d"
    assert oracle_textnorm.collapse_text("  padded  ") == "padded"
    # Punctuation, case and full/half-width are preserved, never folded.
    assert oracle_textnorm.collapse_text("Hello, 世界！") == "Hello, 世界！"
    assert oracle_textnorm.collapse_text("ＡＢＣ") == "ＡＢＣ"
    # NFC: decomposed e + combining accent folds to the composed form.
    assert oracle_textnorm.collapse_text("é") == "é"


def test_fingerprint_is_deterministic_sha256():
    text = "关键引文po-ext-01：页码漂移误导定位。"
    assert oracle_textnorm.fingerprint(text) == hashlib.sha256(
        oracle_textnorm.collapse_text(text).encode("utf-8")).hexdigest()
    assert oracle_textnorm.quote_fingerprint(text) == \
        oracle_textnorm.fingerprint(text)


def test_hash_matches_page_exact_and_repair():
    # Exact match, no repair needed.
    page_text = "故障类别 PAGE_OFFSET 首错阶段 extraction"
    bundle_hash = oracle_textnorm.fingerprint(page_text)
    matched, repair = oracle_textnorm.hash_matches_page(bundle_hash, page_text)
    assert matched and repair is None
    # pdfminer drops "·": the bundle hash is over "A · B" while the
    # pdfminer text reads "A B" — the single-glyph repair must match.
    bundle_hash = oracle_textnorm.fingerprint("A · B")
    matched, repair = oracle_textnorm.hash_matches_page(bundle_hash, "A B")
    assert matched and repair is not None and "U+00B7" in repair
    # A hash belonging to a different page cannot be repaired.
    other_hash = oracle_textnorm.fingerprint("entirely different page text")
    matched, _ = oracle_textnorm.hash_matches_page(other_hash, "A B")
    assert not matched
    # No hash at all never matches.
    assert oracle_textnorm.hash_matches_page(None, "A B") == (False, None)


# ---------------------------------------------------------------------------
# locate
# ---------------------------------------------------------------------------

def test_locate_single_page_full_candidate_set():
    texts = ["alpha beta gamma", "beta gamma delta", "unrelated"]
    match = oracle_locate.locate_quote(texts, "beta gamma")
    assert match.candidate_source_pages0 == [0, 1]
    assert match.span_status == "single_page"


def test_locate_cross_page_span_by_coverage():
    texts = ["first half of the quote here, then footer",
             "header lines, second half of the quote here"]
    match = oracle_locate.locate_quote(
        texts, "first half of the quote here, then footer second half")
    # The quote as a whole is on no single page; the pair covers it.
    assert match.span_status == "cross_page"
    assert match.candidate_source_pages0 == [0, 1]
    assert match.cross_page_spans == [[0, 1]]


def test_locate_not_found_and_empty_quote():
    texts = ["some page text", "more text"]
    match = oracle_locate.locate_quote(texts, "absent sentence here")
    assert match.candidate_source_pages0 == []
    assert match.span_status == "not_found"
    match = oracle_locate.locate_quote(texts, "   ")
    assert match.candidate_source_pages0 == []
    assert match.span_status == "not_found"


def test_locate_unsupported_triple_span():
    texts = ["part one of a long quote",
             "part two of a long quote",
             "part three of a long quote"]
    match = oracle_locate.locate_quote(
        texts, "part one of a long quote part two of a long quote "
               "part three of a long quote")
    assert match.span_status == "unsupported_span"
    assert match.unsupported_span
    assert match.candidate_source_pages0 == []


def test_locate_single_page_beats_cross_page():
    texts = ["the whole quote sits here", "the whole quote sits here too"]
    match = oracle_locate.locate_quote(texts, "the whole quote sits here")
    assert match.span_status == "single_page"
    assert match.candidate_source_pages0 == [0, 1]
    assert match.cross_page_spans == []


# ---------------------------------------------------------------------------
# pdfread (real fixture PDFs, pdfminer only)
# ---------------------------------------------------------------------------

def test_pdfread_labels_match_manifest():
    manifest = load_manifest()
    for case in manifest["cases"]:
        pages = oracle_pdfread.read_pdf_pages(
            str(FIXTURES / "pdfs" / case["pdf_file_name"]))
        assert len(pages) == case["page_count"]
        assert [p.pdf_page_label for p in pages] == case["page_labels"]


def test_pdfread_states_and_image_detection():
    pages = oracle_pdfread.read_pdf_pages(
        str(FIXTURES / "pdfs" / "un-ext-01.pdf"))
    assert pages[2].text_state == "IMAGE_ONLY"
    assert pages[2].raw_text == ""
    assert pages[2].text_sha256 is None
    assert pages[0].text_state == "TEXT"
    pages = oracle_pdfread.read_pdf_pages(
        str(FIXTURES / "pdfs" / "un-ext-05.pdf"))
    assert pages[2].text_state == "EMPTY"
    pages = oracle_pdfread.read_pdf_pages(
        str(FIXTURES / "pdfs" / "po-ext-01.pdf"))
    assert pages[0].text_state == "EMPTY"


def test_pdfread_fingerprint_agrees_with_bundle_off_header_pages():
    """On pages pdfminer reads exactly, the Oracle fingerprint equals
    the bundle's honest hash.  (Page 0 carries the "·" header, so it
    is verified through the repair path instead — see
    test_hash_matches_page_exact_and_repair.)"""
    bundle = load_bundle("po-ext-01")
    pages = oracle_pdfread.read_pdf_pages(
        str(FIXTURES / "pdfs" / "po-ext-01.pdf"))
    by_index = {r["pdf_page_index0"]: r
                for r in bundle["stages"]["extraction"]}
    assert pages[1].text_sha256 == by_index[1]["text_sha256"]
    assert pages[4].text_sha256 == by_index[4]["text_sha256"]


# ---------------------------------------------------------------------------
# attribute (synthetic bundles — no PDF needed)
# ---------------------------------------------------------------------------

def _synthetic_pages() -> list[oracle_pdfread.OraclePage]:
    return [
        oracle_pdfread.OraclePage(
            0, "1", "TEXT",
            oracle_textnorm.fingerprint("page zero text"), "page zero text"),
        oracle_pdfread.OraclePage(
            1, "2", "TEXT",
            oracle_textnorm.fingerprint("the quote lives here"),
            "the quote lives here"),
        oracle_pdfread.OraclePage(
            2, "3", "TEXT",
            oracle_textnorm.fingerprint("page two text"), "page two text"),
    ]


def _synthetic_bundle(**overrides) -> dict:
    bundle = {
        "case_id": "synthetic",
        "stages": {
            "extraction": [
                {"pdf_page_index0": 0, "pdf_page_label": "1",
                 "text_state": "TEXT",
                 "text_sha256": oracle_textnorm.fingerprint("page zero text")},
                {"pdf_page_index0": 1, "pdf_page_label": "2",
                 "text_state": "TEXT",
                 "text_sha256": oracle_textnorm.fingerprint(
                     "the quote lives here")},
                {"pdf_page_index0": 2, "pdf_page_label": "3",
                 "text_state": "TEXT",
                 "text_sha256": oracle_textnorm.fingerprint("page two text")},
            ],
            "chunking": [
                {"chunk_id": "c-1", "source_page_indices0": [1],
                 "text_sha256": oracle_textnorm.fingerprint(
                     "the quote lives here")},
            ],
            "indexing": [
                {"record_id": "v-1", "source_page_indices0": [1],
                 "pdf_page_label": "2"},
            ],
            "display": [
                {"citation_id": "cite-1",
                 "citation_page_basis": "PDF_NUMBER_1",
                 "citation_page_value": 2, "viewer_page1": 2},
            ],
            "missing_stages": [],
        },
        "citations": [
            {"citation_id": "cite-1", "quote_text": "the quote lives here",
             "chunk_id": "c-1", "index_record_id": "v-1"},
        ],
    }
    for key, value in overrides.items():
        bundle["stages"][key] = value
    return bundle


def _analyze_synthetic(bundle: dict) -> oracle_attr.OracleResult:
    pages = _synthetic_pages()
    match = oracle_locate.locate_quote(
        [p.raw_text or "" for p in pages], "the quote lives here")
    return oracle_attr.analyze_citation(
        citation=bundle["citations"][0], bundle=bundle, pages=pages,
        match=match)


def test_attribute_synthetic_pass():
    assert _analyze_synthetic(_synthetic_bundle()).verdict == "PASS"


def test_attribute_missing_stage_is_unknown_never_pass():
    bundle = _synthetic_bundle()
    bundle["stages"]["missing_stages"] = ["indexing"]
    result = _analyze_synthetic(bundle)
    assert result.verdict == "UNKNOWN_TRACE_MISSING"
    assert result.first_fault_stage is None
    # T013 P2-05: the Oracle now carries the same reason as production
    # (TRACE_MISSING) instead of null.
    assert result.reason == "TRACE_MISSING"


def test_attribute_unknown_basis():
    bundle = _synthetic_bundle()
    bundle["stages"]["display"] = [
        {"citation_id": "cite-1", "citation_page_basis": "UNKNOWN",
         "citation_page_value": 2, "viewer_page1": None},
    ]
    result = _analyze_synthetic(bundle)
    assert result.verdict == "UNKNOWN_PAGE_BASIS"
    assert result.first_fault_stage == "display"


def test_attribute_duplicate_with_no_forced_pick_is_ambiguous():
    pages = [
        oracle_pdfread.OraclePage(
            0, "1", "TEXT",
            oracle_textnorm.fingerprint("repeated sentence here"),
            "repeated sentence here"),
        oracle_pdfread.OraclePage(
            1, "2", "TEXT",
            oracle_textnorm.fingerprint("repeated sentence here"),
            "repeated sentence here"),
    ]
    bundle = {
        "case_id": "synthetic-dup",
        "stages": {
            "extraction": [
                {"pdf_page_index0": 0, "pdf_page_label": "1",
                 "text_state": "TEXT",
                 "text_sha256": oracle_textnorm.fingerprint(
                     "repeated sentence here")},
                {"pdf_page_index0": 1, "pdf_page_label": "2",
                 "text_state": "TEXT",
                 "text_sha256": oracle_textnorm.fingerprint(
                     "repeated sentence here")},
            ],
            "chunking": [
                {"chunk_id": "c-1", "source_page_indices0": [0, 1],
                 "text_sha256": oracle_textnorm.fingerprint(
                     "repeated sentence here")},
            ],
            "indexing": [
                {"record_id": "v-1", "source_page_indices0": [0, 1],
                 "pdf_page_label": "1"},
            ],
            "display": [],
            "missing_stages": [],
        },
        "citations": [
            {"citation_id": "cite-1",
             "quote_text": "repeated sentence here",
             "chunk_id": "c-1", "index_record_id": "v-1"},
        ],
    }
    match = oracle_locate.locate_quote(
        [p.raw_text or "" for p in pages], "repeated sentence here")
    assert match.candidate_source_pages0 == [0, 1]
    result = oracle_attr.analyze_citation(
        citation=bundle["citations"][0], bundle=bundle, pages=pages,
        match=match)
    assert result.verdict == "AMBIGUOUS"
    assert result.first_fault_stage is None
    assert result.expected_source_pages0 == [0, 1]


def test_attribute_unresolvable_label_is_manual_review():
    bundle = _synthetic_bundle()
    bundle["stages"]["display"] = [
        {"citation_id": "cite-1", "citation_page_basis": "PDF_LABEL",
         "citation_page_value": "ZZZ", "viewer_page1": 9},
    ]
    result = _analyze_synthetic(bundle)
    assert result.verdict == "NEEDS_MANUAL_REVIEW"
    assert result.first_fault_stage == "display"


# ---------------------------------------------------------------------------
# Golden reproduction (the whole S0 fixture set, Oracle only)
# ---------------------------------------------------------------------------

def test_golden_reproduced_by_oracle():
    """The Oracle re-derives every Golden entry from spec + PDF +
    bundle.  Golden was built by running this same Oracle and then
    cross-checked against spec.expected (see the audit evidence
    file); this test pins the file to the Oracle's conclusions."""
    golden = load_golden()
    assert golden["format"] == "pagetrace.golden/v1"
    assert len(golden["cases"]) == 48
    fault_counts: dict[str, int] = {}
    for entry in golden["cases"]:
        case_id = entry["case_id"]
        bundle = load_bundle(case_id)
        result = oracle_api.analyze_case(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]), bundle, case_id)
        fault = result.by_citation_id("cite-fault")
        control = result.by_citation_id("cite-control")
        for key in ("verdict", "fault_type", "first_fault_stage",
                    "candidate_source_pages0", "expected_source_pages0",
                    "observed_page_value"):
            assert fault.__dict__[key] == entry["fault"][key], (
                f"{case_id} fault {key}: oracle {fault.__dict__[key]!r} "
                f"!= golden {entry['fault'][key]!r}")
        assert fault.reason == entry["fault"]["unlocatable_reason"]
        for key in ("verdict", "candidate_source_pages0",
                    "expected_source_pages0", "observed_page_value"):
            assert control.__dict__[key] == entry["control"][key], (
                f"{case_id} control {key}: oracle {control.__dict__[key]!r} "
                f"!= golden {entry['control'][key]!r}")
        assert control.verdict == "PASS"
        fault_counts[fault.fault_type] = \
            fault_counts.get(fault.fault_type, 0) + 1
        assert entry["fault"]["basis"], f"{case_id}: fault basis is empty"
        assert entry["control"]["basis"], f"{case_id}: control basis empty"
    assert fault_counts == {name: 12 for name in FAULT_TYPES}


def test_golden_extraction_audit_matches_confirmed_fact():
    """Extraction differences from the honest pdfminer reading exist
    in exactly the 6 coordinator-confirmed bundles, with the
    confirmed shapes (po-ext hash swaps, mm-ext ERROR / omitted hash
    / omitted record)."""
    golden = load_golden()
    differing = {
        entry["case_id"] for entry in golden["cases"]
        if entry["extraction_audit"]["diffs"]
    }
    assert differing == EXPECTED_EXTRACTION_DIFFERING
    by_id = {entry["case_id"]: entry for entry in golden["cases"]}
    assert [d["pdf_page_index0"] for d in
            by_id["po-ext-01"]["extraction_audit"]["diffs"]] == [2, 3]
    assert [d["pdf_page_index0"] for d in
            by_id["po-ext-02"]["extraction_audit"]["diffs"]] == [0, 1]
    assert [d["pdf_page_index0"] for d in
            by_id["po-ext-03"]["extraction_audit"]["diffs"]] == [3, 6]
    assert by_id["mm-ext-01"]["extraction_audit"]["diffs"][0]["kind"] == \
        "missing"
    assert by_id["mm-ext-02"]["extraction_audit"]["diffs"][0]["field"] == \
        "text_sha256"
    assert by_id["mm-ext-03"]["extraction_audit"]["diffs"][0]["field"] == \
        "extraction_record"


def test_golden_unlocatable_reasons_are_4_4_4():
    """IMAGE_ONLY x4 / EMPTY x4 / NO_EXACT_MATCH x4 — the confirmed
    fixture fact.

    FIX-R1 P1-R1-02: attribution is 8 x extraction (IMAGE_ONLY /
    EMPTY, provable extraction failure) + 4 x null (near-miss
    NO_EXACT_MATCH, no stage can be blamed); the reason split 4/4/4
    is unchanged.
    """
    golden = load_golden()
    reasons: dict[str, int] = {}
    for entry in golden["cases"]:
        if entry["fault"]["fault_type"] == "UNLOCATABLE":
            if entry["case_id"] in ("un-ext-09", "un-ext-10",
                                    "un-ext-11", "un-ext-12"):
                assert entry["fault"]["first_fault_stage"] is None
                assert entry["fault"]["expected_source_pages0"] is None
            else:
                assert entry["fault"]["first_fault_stage"] == "extraction"
            reason = entry["fault"]["unlocatable_reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
    assert reasons == {"IMAGE_ONLY": 4, "EMPTY": 4, "NO_EXACT_MATCH": 4}
