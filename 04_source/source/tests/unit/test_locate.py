"""T003 — exact normalised quote location tests.

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/unit/test_locate.py -q

Covers (PROJECT_BOOK.md §7.2, §4.2; PAGE_SEMANTICS.md R-09/R-10):
  * all 48 T002 fixtures: fault quotes locate exactly on
    ``expected.candidate_source_pages0`` (duplicates return the full
    set; UNLOCATABLE fault quotes return 0 candidates — including the
    12 image-page quotes, which exist only as raster text and must
    NOT be located from the text layer); control quotes locate on
    their true page(s), cross-page controls on the full ``split_pages0``
    pair;
  * synthetic records: duplicate sentences, adjacent cross-page
    splits, >2-page spans (UNSUPPORTED_SPAN, no guessing), empty
    quotes, and exactness — one changed character, case, punctuation
    or full/half-width swap must NOT match.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

# Production package lives in src/ (T013 P2-08: the top-level stub is gone);
# src/ must be first on sys.path when running from a checkout.
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.extract import PageTextRecord, extract_pages  # noqa: E402
from pagetrace.locate import locate_quote  # noqa: E402
from pagetrace.normalize import quote_sha256  # noqa: E402
from pagetrace.pdf_input import load_pdf  # noqa: E402


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_spec(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "specs" / f"{case_id}.json").read_text(encoding="utf-8"))


def _records(case_id: str) -> list[PageTextRecord]:
    info = load_pdf(str(FIXTURES / "pdfs" / f"{case_id}.pdf"))
    return extract_pages(info)


def _text_record(index: int, text: str) -> PageTextRecord:
    return PageTextRecord(
        pdf_page_index0=index,
        pdf_page_label=str(index + 1),
        text_state="TEXT",
        text_sha256=None,
        extracted_text=text,
    )


def _empty_record(index: int, state: str = "EMPTY") -> PageTextRecord:
    return PageTextRecord(
        pdf_page_index0=index,
        pdf_page_label=str(index + 1),
        text_state=state,  # type: ignore[arg-type]
        text_sha256=None,
        extracted_text="",
    )


# ---------------------------------------------------------------------------
# Fixture-driven location: all 48 cases
# ---------------------------------------------------------------------------

def test_fault_quotes_locate_as_specified():
    """Fault quote candidates == spec expected.candidate_source_pages0
    for all 48 cases — full duplicate sets, single pages, and [] for
    the 12 UNLOCATABLE quotes (image-only / blank / near-miss)."""
    manifest = load_manifest()
    assert len(manifest["cases"]) == 48
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        records = _records(entry["case_id"])
        fault = spec["fault_citation"]
        match = locate_quote(records, fault["quote_text"])
        assert match.candidate_source_pages0 == (
            spec["expected"]["candidate_source_pages0"]), (
            entry["case_id"], spec["fault_type"])
        assert match.quote_sha256 == quote_sha256(fault["quote_text"])
        if spec["expected"]["candidate_source_pages0"]:
            assert match.span_status in ("single_page", "cross_page")
            assert not match.unsupported_span
        else:
            assert match.span_status == "not_found", entry["case_id"]
            assert match.cross_page_spans == []
            assert not match.unsupported_span


def test_control_quotes_locate_on_true_pages():
    """All 48 control quotes locate exactly on their true source
    pages; cross-page controls return the full split pair (R-10)."""
    manifest = load_manifest()
    for entry in manifest["cases"]:
        spec = load_spec(entry["case_id"])
        records = _records(entry["case_id"])
        control = spec["control_citation"]
        match = locate_quote(records, control["quote_text"])
        assert match.candidate_source_pages0 == (
            control["true_source_pages0"]), entry["case_id"]
        if spec["split_pages0"]:
            assert match.span_status == "cross_page", entry["case_id"]
            assert match.cross_page_spans == [spec["split_pages0"]], (
                entry["case_id"])
        else:
            assert match.span_status == "single_page", entry["case_id"]
            assert match.cross_page_spans == []


def test_duplicate_fault_quotes_return_full_candidate_set():
    """The 12 DUPLICATE_TEXT_AMBIGUITY fault quotes return every
    occurrence page (2–3 pages), never a single guessed page (R-09)."""
    manifest = load_manifest()
    duplicates = [e for e in manifest["cases"]
                  if e["fault_type"] == "DUPLICATE_TEXT_AMBIGUITY"]
    assert len(duplicates) == 12
    for entry in duplicates:
        spec = load_spec(entry["case_id"])
        records = _records(entry["case_id"])
        match = locate_quote(records, spec["fault_citation"]["quote_text"])
        assert match.candidate_source_pages0 == (
            spec["duplicate_occurrence_pages0"]), entry["case_id"]
        assert len(match.candidate_source_pages0) >= 2, entry["case_id"]
        assert match.span_status == "single_page"


def test_unlocatable_image_page_quotes_return_zero_candidates():
    """The 12 UNLOCATABLE fault quotes — image-only, blank-page and
    near-miss variants — return 0 candidates. The image-page quotes
    are visible only as raster text: no OCR is started and the text
    layer honestly reports nothing."""
    manifest = load_manifest()
    unlocatable = [e for e in manifest["cases"]
                   if e["fault_type"] == "UNLOCATABLE"]
    assert len(unlocatable) == 12
    variants = {load_spec(e["case_id"])["variant"] for e in unlocatable}
    assert variants == {"image-only-page", "blank-page",
                        "near-miss-quote"}, variants
    for entry in unlocatable:
        spec = load_spec(entry["case_id"])
        records = _records(entry["case_id"])
        match = locate_quote(records, spec["fault_citation"]["quote_text"])
        assert match.candidate_source_pages0 == [], entry["case_id"]
        assert match.span_status == "not_found", entry["case_id"]
        # The quote must not be findable even as a cross-page split:
        # it is absent from the text layer entirely.
        assert match.cross_page_spans == []


def test_cross_page_controls_cover_split_pages():
    """The 18 cross-page split cases: control quote spans exactly the
    two adjacent pages in ``split_pages0`` (R-10)."""
    manifest = load_manifest()
    splits = [e for e in manifest["cases"]
              if load_spec(e["case_id"])["split_pages0"]]
    assert len(splits) == 18
    for entry in splits:
        spec = load_spec(entry["case_id"])
        pages = spec["split_pages0"]
        assert len(pages) == 2 and pages[1] == pages[0] + 1, entry["case_id"]
        records = _records(entry["case_id"])
        match = locate_quote(records, spec["control_citation"]["quote_text"])
        assert match.candidate_source_pages0 == pages, entry["case_id"]
        assert match.span_status == "cross_page"


# ---------------------------------------------------------------------------
# Synthetic records: exactness, duplicates, spans
# ---------------------------------------------------------------------------

def test_duplicate_sentence_returns_all_pages():
    records = [
        _text_record(0, "引言页。"),
        _text_record(1, "重复句：本句在多页出现。"),
        _text_record(2, "其它内容。"),
        _text_record(3, "重复句：本句在多页出现。"),
        _text_record(4, "重复句：本句在多页出现。结尾。"),
    ]
    match = locate_quote(records, "重复句：本句在多页出现。")
    assert match.candidate_source_pages0 == [1, 3, 4]
    assert match.span_status == "single_page"
    assert not match.unsupported_span


def test_cross_page_split_returns_complete_page_set():
    records = [
        _text_record(0, "第一页内容。"),
        _text_record(1, "长句前半部分：引用内容在翻页处断开，页脚。"),
        _text_record(2, "后半部分接续于此，合起来才是一句完整引用。更多内容。"),
        _text_record(3, "第四页内容。"),
    ]
    match = locate_quote(
        records, "长句前半部分：引用内容在翻页处断开，后半部分接续于此，合起来才是一句完整引用。")
    assert match.candidate_source_pages0 == [1, 2]
    assert match.cross_page_spans == [[1, 2]]
    assert match.span_status == "cross_page"
    assert not match.unsupported_span


def test_three_page_span_is_unsupported_not_guessed():
    """A quote split across 3 consecutive pages is detected but NOT
    located: UNSUPPORTED_SPAN, no candidate pages, no unbounded
    combination attempted."""
    records = [
        _text_record(0, "甲部分内容在此第一页出现。"),
        _text_record(1, "乙部分内容在此第二页出现。"),
        _text_record(2, "丙部分内容在此第三页出现。"),
        _text_record(3, "其它页。"),
    ]
    quote = "甲部分内容在此第一页出现。乙部分内容在此第二页出现。丙部分内容在此第三页出现。"
    match = locate_quote(records, quote)
    assert match.span_status == "unsupported_span"
    assert match.unsupported_span is True
    assert match.candidate_source_pages0 == []
    assert match.cross_page_spans == []


def test_empty_and_whitespace_quotes_match_nothing():
    records = [_text_record(0, "任何内容。"), _text_record(1, "更多内容。")]
    for quote in ("", "   ", "\n\t "):
        match = locate_quote(records, quote)
        assert match.candidate_source_pages0 == []
        assert match.span_status == "not_found"


def test_absent_quote_returns_zero_candidates():
    records = [_text_record(0, "第一页内容。"),
               _empty_record(1),
               _text_record(2, "第三页内容。")]
    match = locate_quote(records, "这句话在文档中不存在。")
    assert match.candidate_source_pages0 == []
    assert match.span_status == "not_found"
    assert match.cross_page_spans == []
    assert not match.unsupported_span


def test_one_character_difference_does_not_match():
    """Near-miss: a single changed character (原文 vs 正文) must not
    match — no fuzzy matching, no threshold lowering (§4.2)."""
    records = [_text_record(0, "近似句：引用页码漂移会误导读者定位原文。")]
    match = locate_quote(records, "近似句：引用页码漂移会误导读者定位正文。")
    assert match.candidate_source_pages0 == []
    assert match.span_status == "not_found"


def test_case_punctuation_and_width_differences_do_not_match():
    records = [_text_record(0, "Hello, World. ＡＢＣ １２３")]
    for quote in ("hello, World. ＡＢＣ １２３",   # case differs
                  "Hello World. ＡＢＣ １２３",    # punctuation differs
                  "Hello, World. ABC 123",        # half-width differs
                  "Hello, World. ＡＢＣ １２３ "):  # trailing space: normalises away
        match = locate_quote(records, quote)
        if quote == "Hello, World. ＡＢＣ １２３ ":
            # Whitespace-only difference: normalisation erases it.
            assert match.candidate_source_pages0 == [0], quote
        else:
            assert match.candidate_source_pages0 == [], quote


def test_quote_normalised_across_whitespace_and_line_breaks():
    """A quote written with different line breaks / spacing still
    matches after §4.2 normalisation — the match is on normalised
    text, not raw bytes."""
    records = [_text_record(0, "第一行内容\n第二行内容 第三行")]
    match = locate_quote(records, "第一行内容 第二行内容 第三行")
    assert match.candidate_source_pages0 == [0]
    match = locate_quote(records, "第一行内容\n第二行内容\t第三行")
    assert match.candidate_source_pages0 == [0]


def test_empty_and_error_pages_never_match():
    records = [
        _empty_record(0, "EMPTY"),
        _empty_record(1, "IMAGE_ONLY"),
        PageTextRecord(pdf_page_index0=2, pdf_page_label="3",
                       text_state="ERROR", text_sha256=None,
                       extracted_text=None),
        _text_record(3, "目标句子在此页。"),
    ]
    match = locate_quote(records, "目标句子在此页。")
    assert match.candidate_source_pages0 == [3]
    match = locate_quote(records, "不在任何页上的句子。")
    assert match.candidate_source_pages0 == []


def test_single_page_match_wins_over_cross_page_split():
    """If the whole quote occurs on one page, the locator reports the
    single-page candidates and does not also manufacture a split
    match on a neighbouring pair."""
    records = [
        _text_record(0, "完整句子在此页出现。"),
        _text_record(1, "完整句子在"),
        _text_record(2, "此页出现。其它文字。"),
    ]
    match = locate_quote(records, "完整句子在此页出现。")
    assert match.candidate_source_pages0 == [0]
    assert match.span_status == "single_page"
    assert match.cross_page_spans == []
