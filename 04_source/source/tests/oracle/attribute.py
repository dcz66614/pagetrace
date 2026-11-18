"""Independent stage attribution and verdicts (P026 T006 Oracle).

Written from PROJECT_BOOK.md v1.0.0 §4.3 / §5 / §7.3 and the
``pagetrace.report/v1`` citation-result contract — never from the
production stage-comparison code.  The walk follows the fixed chain

    PDF truth -> Extraction -> Chunking -> Indexing -> Display

using canonical ``pdf_page_index0`` as the baseline; the first
provable difference is ``first_fault_stage``.  No stage is ever
skipped to blame a later one, and no uncertainty is ever converted
to PASS.

Rules applied, in order, for one citation:

0. A missing stage snapshot forbids blaming any stage:
   ``UNKNOWN_TRACE_MISSING``.
1. A quote spanning more than two pages is real but unsupported:
   ``NEEDS_MANUAL_REVIEW``.
2. A quote found on no page is ``FAIL_UNLOCATABLE``.  The reason
   is anchored on the page(s) the trace itself claims (chunk, then
   index): all ``IMAGE_ONLY`` -> ``IMAGE_ONLY``, all ``EMPTY`` ->
   ``EMPTY``, all ``TEXT`` -> ``NO_EXACT_MATCH``, anything else ->
   ``NO_TEXT_LAYER``.  Only a provable extraction failure is blamed
   on extraction: an anchor page honestly ``IMAGE_ONLY`` / ``EMPTY``
   (no text layer to extract), or a bundle extraction record for a
   claimed page that provably differs from the honest pdfminer
   reading.  Otherwise (near miss on a TEXT page whose extraction
   records match the honest reading, or no usable anchor)
   ``first_fault_stage`` is ``None`` and
   ``expected_source_pages0`` is ``None``: the trace-claimed page
   is unconfirmed, never a verified source (FIX-R1 P1-R1-02).  This
   never means "the quoted text does not exist": it may live in a
   raster image, on a blank page, or differ by one character.  No
   OCR is run.
3. Extraction: for every truth page, the bundle record must exist,
   carry the same text state as the honest pdfminer reading, and
   (for TEXT pages) a hash that matches the page (see
   :mod:`oracle.textnorm` for the single-glyph repair).  A missing
   record, a missing hash, or a re-marked state is
   ``PAGE_METADATA_MISSING``; a present-but-different hash is
   ``PAGE_OFFSET`` (another page's text was attached).
4. Chunking / Indexing: the linked record's ``source_page_indices0``
   must equal the upstream set.  A missing record, a missing set
   field, or an emptied ``[]`` set is ``PAGE_METADATA_MISSING``.
   A proper subset of a multi-page duplicate candidate set is
   ``DUPLICATE_TEXT_AMBIGUITY`` (``FAIL_AMBIGUOUS``); a proper
   subset of a cross-page set, or any other disagreement, is
   ``PAGE_OFFSET``.  A chunk record that omits ``text_sha256``, or
   an index record that drops ``pdf_page_label`` (when the honest
   page has one), is ``PAGE_METADATA_MISSING``; an index label
   naming another physical page is ``PAGE_OFFSET``.
5. Display: the value is resolved through its basis — ``PDF_INDEX_0``
   as-is, ``PDF_NUMBER_1`` minus one, ``PDF_LABEL`` by lookup in the
   PDF label table, never by arithmetic (R-03).  A missing record,
   a null value or a null viewer page is ``PAGE_METADATA_MISSING``
   — *unless* the quote is a duplicate and no earlier stage forced
   a single page, in which case the honest answer is ``AMBIGUOUS``
   (no page is guessed).  An ``UNKNOWN`` basis is
   ``UNKNOWN_PAGE_BASIS``.  An unresolvable label, a value/basis
   type mismatch, or an out-of-range value is ``NEEDS_MANUAL_REVIEW``.
   A resolved page that picks one of several duplicate candidates
   is ``FAIL_AMBIGUOUS`` at display; a resolved page outside the
   truth, or a ``viewer_page1`` that is not ``resolved + 1``, is
   ``PAGE_OFFSET``.  For a cross-page span, any page of the span is
   accepted as the display value, provided the viewer page matches
   it.  Otherwise the citation is ``PASS``.

``expected_source_pages0`` is the PDF-truth candidate set for
locatable quotes and the trace-claimed anchor pages for
UNLOCATABLE ones.  ``observed_page_value`` is the display layer's
raw page value, verbatim (``None`` when the display record is
absent or its value is null).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .locate import OracleMatch
from .pdfread import OraclePage
from .textnorm import hash_matches_page

STAGE_ORDER = ("extraction", "chunking", "indexing", "display")

#: Sentinel distinguishing "field absent" from "field present, null".
_MISSING = object()


@dataclass
class OracleEvidence:
    """One provable difference (or honest-uncertainty note)."""

    stage: str
    field: str
    upstream_value: object
    downstream_value: object
    note: str


@dataclass
class OracleResult:
    """Verdict for one citation, in ``pagetrace.report/v1`` shape."""

    citation_id: str
    quote_sha256: str
    citation_page_value: object
    citation_page_basis: str
    candidate_source_pages0: list[int]
    expected_source_pages0: list[int] | None
    observed_page_value: object
    correct_pdf_page_number1: list[int] | None
    correct_viewer_page1: list[int] | None
    verdict: str
    fault_type: str | None
    first_fault_stage: str | None
    reason: str | None = None
    evidence: list[OracleEvidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    missing_stages: list[str] = field(default_factory=list)


@dataclass
class ExtractionDiff:
    """One difference between a bundle extraction record and the
    honest pdfminer reading of the same physical page."""

    pdf_page_index0: int
    kind: str  # "missing" | "state_mismatch" | "hash_mismatch"
    field: str
    upstream_value: object
    downstream_value: object
    note: str


def audit_extraction(pages: list[OraclePage],
                     bundle_extraction: list[dict] | None
                     ) -> list[ExtractionDiff]:
    """Compare every bundle extraction record with the honest
    reading, in physical page order.  A ``None`` hash on a non-TEXT
    page is not a difference (there is no text to hash)."""
    if bundle_extraction is None:
        return [ExtractionDiff(-1, "missing", "extraction", None, None,
                               "extraction stage snapshot is missing")]
    by_index: dict[int, dict] = {}
    for record in bundle_extraction:
        index = record.get("pdf_page_index0")
        if isinstance(index, int) and not isinstance(index, bool):
            by_index.setdefault(index, record)
    diffs: list[ExtractionDiff] = []
    for honest in pages:
        index = honest.pdf_page_index0
        record = by_index.get(index)
        if record is None:
            diffs.append(ExtractionDiff(
                index, "missing", "extraction_record", honest.text_state,
                None, f"no extraction record for physical page {index}"))
            continue
        state = record.get("text_state")
        if state != honest.text_state:
            kind = ("missing" if honest.text_state == "TEXT"
                    and state in ("ERROR", "EMPTY", "IMAGE_ONLY")
                    else "state_mismatch")
            diffs.append(ExtractionDiff(
                index, kind, "text_state", honest.text_state, state,
                f"extraction text_state for page {index} is {state!r}, "
                f"honest pdfminer reading says {honest.text_state!r}"))
            continue
        if honest.text_state == "TEXT":
            if "text_sha256" not in record:
                diffs.append(ExtractionDiff(
                    index, "missing", "text_sha256", honest.text_sha256,
                    None, f"extraction record for page {index} omits "
                          "text_sha256"))
            elif record.get("text_sha256") is None:
                diffs.append(ExtractionDiff(
                    index, "hash_mismatch", "text_sha256",
                    honest.text_sha256, None,
                    f"extraction text_sha256 for page {index} is null "
                    "but the honest page has text"))
            else:
                matched, _repair = hash_matches_page(
                    record.get("text_sha256"), honest.raw_text or "")
                if not matched:
                    diffs.append(ExtractionDiff(
                        index, "hash_mismatch", "text_sha256",
                        honest.text_sha256, record.get("text_sha256"),
                        f"extraction text_sha256 for page {index} does "
                        "not match the honest pdfminer text (text of "
                        "another page attached?)"))
    for index in sorted(by_index):
        if index < 0 or index >= len(pages):
            diffs.append(ExtractionDiff(
                index, "hash_mismatch", "pdf_page_index0", None, index,
                f"extraction record for out-of-range page {index}"))
    return diffs


def _find_record(records: list[dict] | None, key: str,
                 wanted: str | None) -> dict | None:
    if records is None or wanted is None:
        return None
    for record in records:
        if record.get(key) == wanted:
            return record
    return None


def _source_pages(record: dict | None) -> object:
    if record is None:
        return _MISSING
    return record.get("source_page_indices0", _MISSING)


def _label_table(pages: list[OraclePage]) -> dict[str, list[int]]:
    table: dict[str, list[int]] = {}
    for page in pages:
        if page.pdf_page_label is not None:
            table.setdefault(page.pdf_page_label, []).append(
                page.pdf_page_index0)
    return table


def _anchor_pages(citation: dict, stages: dict) -> list[int] | None:
    """Pages the trace itself claims for an unlocatable quote:
    chunk first, then index.  ``None`` when no stage names any page."""
    chunk = _find_record(stages.get("chunking"), "chunk_id",
                         citation.get("chunk_id"))
    pages = _source_pages(chunk)
    if pages is not _MISSING and pages:
        return sorted(pages)  # type: ignore[arg-type]
    index = _find_record(stages.get("indexing"), "record_id",
                         citation.get("index_record_id"))
    pages = _source_pages(index)
    if pages is not _MISSING and pages:
        return sorted(pages)  # type: ignore[arg-type]
    return None


def _unlocatable_reason(anchor: list[int] | None,
                        pages: list[OraclePage]) -> str:
    """Reason for an unlocatable quote, from the anchor pages' honest
    states (see module docstring, rule 2)."""
    if not anchor:
        return "NO_TEXT_LAYER"
    by_index = {p.pdf_page_index0: p for p in pages}
    states = {by_index[p].text_state for p in anchor if p in by_index}
    if states == {"IMAGE_ONLY"}:
        return "IMAGE_ONLY"
    if states == {"EMPTY"}:
        return "EMPTY"
    if states == {"TEXT"}:
        return "NO_EXACT_MATCH"
    return "NO_TEXT_LAYER"


def _resolve_display(display: dict | None,
                     label_table: dict[str, list[int]]
                     ) -> tuple[int | None, str, str]:
    """Resolve a display record to a 0-based page.

    Returns ``(index0, kind, note)`` with kind ``"ok"``,
    ``"missing_record"``, ``"value_missing"``, ``"unknown_basis"``,
    ``"label_unresolved"``, ``"type_mismatch"`` or ``"out_of_range"``.
    """
    if display is None:
        return None, "missing_record", "no display record for this citation"
    value = display.get("citation_page_value", _MISSING)
    basis = display.get("citation_page_basis", _MISSING)
    if value is _MISSING or value is None:
        return None, "value_missing", "citation_page_value is missing or null"
    if basis == "UNKNOWN" or basis is _MISSING:
        return None, "unknown_basis", (
            "citation_page_basis is UNKNOWN; no conversion is allowed")
    if basis == "PDF_INDEX_0":
        if not isinstance(value, int) or isinstance(value, bool):
            return None, "type_mismatch", (
                "PDF_INDEX_0 requires an integer citation_page_value")
        return value, "ok", ""
    if basis == "PDF_NUMBER_1":
        if not isinstance(value, int) or isinstance(value, bool):
            return None, "type_mismatch", (
                "PDF_NUMBER_1 requires an integer citation_page_value")
        if value < 1:
            return None, "out_of_range", (
                "PDF_NUMBER_1 value below 1 names no physical page")
        return value - 1, "ok", ""
    if basis == "PDF_LABEL":
        if not isinstance(value, str):
            return None, "type_mismatch", (
                "PDF_LABEL requires a string citation_page_value")
        named = label_table.get(value)
        if not named:
            return None, "label_unresolved", (
                f"page label {value!r} is not in the PDF label table")
        if len(named) > 1:
            return None, "label_unresolved", (
                f"page label {value!r} names several physical pages {named}")
        return named[0], "ok", ""
    return None, "unknown_basis", f"citation_page_basis {basis!r} is not known"


def _fail(result: OracleResult, verdict: str, fault: str, stage: str,
          evidence: OracleEvidence) -> OracleResult:
    result.verdict = verdict
    result.fault_type = fault
    result.first_fault_stage = stage
    result.evidence = [evidence]
    return result


def _check_set_stage(result: OracleResult, record: dict | None,
                     record_field: str, stage: str,
                     upstream: list[int], is_duplicate: bool,
                     is_cross_page: bool) -> OracleResult | None:
    """Check one set-bearing stage (chunking / indexing).

    Returns a completed (fault) result when this stage is the first
    fault, else ``None`` (the stage agrees with its upstream set)."""
    if record is None:
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", stage, OracleEvidence(
                         stage, record_field, upstream, None,
                         f"no {stage} record for this citation"))
    pages = _source_pages(record)
    if pages is _MISSING:
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", stage, OracleEvidence(
                         stage, "source_page_indices0", upstream, None,
                         f"{stage} record omits source_page_indices0"))
    pages = sorted(pages)  # type: ignore[arg-type]
    if pages == [] and upstream:
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", stage, OracleEvidence(
                         stage, "source_page_indices0", upstream, [],
                         f"{stage} source_page_indices0 was emptied to []"))
    if pages == upstream:
        return None
    if is_duplicate and set(pages) < set(upstream):
        return _fail(result, "FAIL_AMBIGUOUS",
                     "DUPLICATE_TEXT_AMBIGUITY", stage, OracleEvidence(
                         stage, "source_page_indices0", upstream, pages,
                         f"{stage} reduced the multi-page candidate set "
                         f"{upstream} to {pages}; no single page may be "
                         "forced"))
    if is_cross_page and set(pages) < set(upstream):
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", stage,
                     OracleEvidence(
                         stage, "source_page_indices0", upstream, pages,
                         f"{stage} dropped page(s) from the cross-page "
                         f"source set {upstream}"))
    return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", stage,
                 OracleEvidence(
                     stage, "source_page_indices0", upstream, pages,
                     f"{stage} source_page_indices0 {pages} disagrees "
                     f"with upstream {upstream}"))


def analyze_citation(*, citation: dict, bundle: dict,
                     pages: list[OraclePage],
                     match: OracleMatch) -> OracleResult:
    """Attribute one citation: verdict + first fault stage + evidence."""
    stages: dict = bundle.get("stages") or {}
    missing_stages = [
        stage for stage in STAGE_ORDER
        if stage in (stages.get("missing_stages") or [])
        or stages.get(stage) is None
    ]
    citation_id = str(citation.get("citation_id"))
    display_record = _find_record(
        stages.get("display"), "citation_id", citation_id)
    display_value = (display_record.get("citation_page_value")
                     if display_record is not None else None)
    display_basis = (display_record.get("citation_page_basis")
                     if display_record is not None else None)
    result = OracleResult(
        citation_id=citation_id,
        quote_sha256=match.quote_sha256,
        citation_page_value=display_value,
        citation_page_basis=(
            display_basis if display_basis in (
                "PDF_INDEX_0", "PDF_NUMBER_1", "PDF_LABEL", "UNKNOWN")
            else "UNKNOWN"),
        candidate_source_pages0=list(match.candidate_source_pages0),
        expected_source_pages0=None,
        observed_page_value=display_value,
        correct_pdf_page_number1=None,
        correct_viewer_page1=None,
        verdict="PASS", fault_type=None, first_fault_stage=None,
        missing_stages=missing_stages,
    )

    # 0. A missing stage snapshot forbids blaming any stage.
    if missing_stages:
        result.verdict = "UNKNOWN_TRACE_MISSING"
        # T013 P2-05: match production (compare_stages.py), which sets
        # reason="TRACE_MISSING" here. Reason is not an S0 parity
        # field, so this changes no gate; it only makes the two
        # implementations' reason values comparable.
        result.reason = "TRACE_MISSING"
        result.evidence = [OracleEvidence(
            missing_stages[0], "stage_snapshot", None, None,
            "stage snapshot(s) missing: " + ", ".join(missing_stages)
            + "; no stage may be blamed without them")]
        result.notes = ["A stage snapshot is missing, so the first fault "
                        "stage cannot be determined; the verdict is "
                        "UNKNOWN, not PASS."]
        return result

    # 1. Quote spans more than two pages: real but unsupported.
    if match.span_status == "unsupported_span":
        result.verdict = "NEEDS_MANUAL_REVIEW"
        result.reason = "UNSUPPORTED_SPAN"
        result.evidence = [OracleEvidence(
            "extraction", "candidate_source_pages0", None, None,
            "quote spans more than two physical pages; spans over two "
            "pages are unsupported, no page is guessed")]
        result.notes = ["The quote spans more than two physical pages, "
                        "which PageTrace does not locate; manual review "
                        "is required."]
        return result

    # 2. Quote not found in the extractable text layer.
    if not match.candidate_source_pages0:
        anchor = _anchor_pages(citation, stages)
        reason = _unlocatable_reason(anchor, pages)
        result.verdict = "FAIL_UNLOCATABLE"
        result.fault_type = "UNLOCATABLE"
        if reason in ("IMAGE_ONLY", "EMPTY"):
            # Provable extraction failure (PROJECT_BOOK §5): the
            # trace-claimed page honestly has no text layer.
            result.first_fault_stage = "extraction"
            result.expected_source_pages0 = anchor
            blame_note = ""
        else:
            # NO_EXACT_MATCH / NO_TEXT_LAYER (FIX-R1 P1-R1-02):
            # extraction is blamed only if a bundle extraction
            # record for a trace-claimed page provably differs from
            # the honest pdfminer reading; a verified-correct
            # extraction is never blamed for a missing exact match,
            # and the claimed page is not a confirmed source.
            fault_diff = next(
                (d for d in audit_extraction(
                    pages, stages.get("extraction"))
                 if anchor and d.pdf_page_index0 in anchor),
                None)
            if fault_diff is not None:
                result.first_fault_stage = "extraction"
                result.expected_source_pages0 = anchor
                blame_note = (
                    "; the extraction record for the claimed page(s) "
                    "provably differs from the honest pdfminer "
                    "reading, so extraction is blamed")
            else:
                result.first_fault_stage = None
                result.expected_source_pages0 = None
                if anchor:
                    blame_note = (
                        "; no stage can be blamed: the extraction "
                        "records for the trace-claimed page(s) match "
                        "the honest pdfminer reading, so the missing "
                        "exact match does not prove an extraction "
                        "failure, and the claimed page(s) are not a "
                        "confirmed source")
                else:
                    blame_note = (
                        "; no stage can be blamed: no trace anchor "
                        "names the intended page")
        result.reason = reason
        anchor_note = ""
        if anchor:
            by_index = {p.pdf_page_index0: p for p in pages}
            states = sorted({by_index[p].text_state for p in anchor
                             if p in by_index})
            anchor_note = (f"; the trace-claimed page(s) {anchor} are "
                           f"{'/'.join(states)}")
        result.evidence = [OracleEvidence(
            "extraction", "candidate_source_pages0", None, [],
            "quote not found in the extractable text layer"
            + anchor_note + blame_note)]
        result.notes = ["The quote was not found in the extractable text "
                        "layer. This does not establish that the quoted "
                        "text is absent from the document: it may be "
                        "visible only in a raster image, on a blank page, "
                        "or differ by a character from the page text. "
                        "No OCR was run."]
        if result.first_fault_stage is None:
            result.notes.append(
                "No stage is blamed for this citation: the missing "
                "exact match does not prove any stage failed, and "
                "the trace-claimed page(s), if any, are not "
                "confirmed as the quote's source page(s).")
        return result

    # From here the quote is locatable: the truth set is the full
    # candidate set (a cross-page span is one set, not alternatives).
    truth = sorted(match.candidate_source_pages0)
    is_duplicate = (match.span_status == "single_page" and len(truth) > 1)
    is_cross_page = match.span_status == "cross_page"
    result.expected_source_pages0 = truth
    result.correct_pdf_page_number1 = [page + 1 for page in truth]
    result.correct_viewer_page1 = [page + 1 for page in truth]

    # 3. Extraction: per-truth-page record / state / hash.
    diffs = audit_extraction(pages, stages.get("extraction"))
    fault_diff = next(
        (d for d in diffs if d.pdf_page_index0 in truth), None)
    if fault_diff is not None:
        evidence = OracleEvidence(
            "extraction", fault_diff.field,
            fault_diff.upstream_value, fault_diff.downstream_value,
            fault_diff.note)
        if fault_diff.kind == "hash_mismatch":
            return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET",
                         "extraction", evidence)
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", "extraction", evidence)
    upstream = truth

    # 4. Chunking: the linked chunk's source set (+ its text hash).
    chunk_record = _find_record(
        stages.get("chunking"), "chunk_id", citation.get("chunk_id"))
    verdict = _check_set_stage(
        result, chunk_record, "chunk_record", "chunking", upstream,
        is_duplicate, is_cross_page)
    if verdict is not None:
        return verdict
    upstream = sorted(_source_pages(chunk_record))  # type: ignore[arg-type]
    if chunk_record is not None and "text_sha256" not in chunk_record:
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", "chunking", OracleEvidence(
                         "chunking", "text_sha256", None, None,
                         "chunk record omits text_sha256"))

    # 5. Indexing: the linked index record's source set + label.
    index_record = _find_record(
        stages.get("indexing"), "record_id",
        citation.get("index_record_id"))
    verdict = _check_set_stage(
        result, index_record, "index_record", "indexing", upstream,
        is_duplicate, is_cross_page)
    if verdict is not None:
        return verdict
    upstream = sorted(_source_pages(index_record))  # type: ignore[arg-type]
    by_index = {p.pdf_page_index0: p for p in pages}
    if index_record is not None and "pdf_page_label" not in index_record:
        claimed = upstream[0] if upstream else None
        honest_label = (by_index[claimed].pdf_page_label
                        if claimed is not None else None)
        if honest_label is not None:
            return _fail(result, "FAIL_METADATA_MISSING",
                         "PAGE_METADATA_MISSING", "indexing",
                         OracleEvidence(
                             "indexing", "pdf_page_label", honest_label,
                             None,
                             "index record dropped pdf_page_label on "
                             "rebuild"))
    if index_record is not None and upstream:
        honest_label = by_index[upstream[0]].pdf_page_label
        shown_label = index_record.get("pdf_page_label")
        if (shown_label is not None and honest_label is not None
                and shown_label != honest_label):
            return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET",
                         "indexing", OracleEvidence(
                             "indexing", "pdf_page_label", honest_label,
                             shown_label,
                             "index record carries the page label of "
                             "another physical page"))

    # 6. Display: resolve the display value and check the viewer.
    return _check_display(result, display_record, truth, upstream,
                          is_duplicate, is_cross_page,
                          _label_table(pages))


def _check_display(result: OracleResult, display_record: dict | None,
                   truth: list[int], upstream: list[int],
                   is_duplicate: bool, is_cross_page: bool,
                   label_table: dict[str, list[int]]) -> OracleResult:
    """Check the display stage; returns the citation's verdict."""
    if display_record is None:
        if is_duplicate and upstream == truth:
            result.verdict = "AMBIGUOUS"
            result.evidence = [OracleEvidence(
                "display", "display_record", truth, None,
                "no display record forces a single page; the quote "
                "occurs on several pages with no disambiguating anchor")]
            result.notes = ["The quote occurs on several physical pages "
                            "and no stage forced a single page; the source "
                            "page is ambiguous, not guessed."]
            return result
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", "display", OracleEvidence(
                         "display", "display_record", truth, None,
                         "no display record for this citation"))
    if display_record.get("citation_page_basis") == "UNKNOWN":
        result.verdict = "UNKNOWN_PAGE_BASIS"
        result.first_fault_stage = "display"
        result.evidence = [OracleEvidence(
            "display", "citation_page_basis", truth, "UNKNOWN",
            "citation_page_basis is UNKNOWN; the value must be kept "
            "verbatim and no viewer page computed")]
        result.notes = ["The citation basis is UNKNOWN, so no viewer page "
                        "may be computed from the display value."]
        return result
    value = display_record.get("citation_page_value", _MISSING)
    if value is _MISSING or value is None:
        if is_duplicate and upstream == truth:
            result.verdict = "AMBIGUOUS"
            result.evidence = [OracleEvidence(
                "display", "citation_page_value", truth, None,
                "display carries no page value, so no single page was "
                "forced; the quote occurs on several pages with no "
                "disambiguating anchor")]
            result.notes = ["The quote occurs on several physical pages "
                            "and the display layer forced no single page; "
                            "the source page is ambiguous, not guessed."]
            return result
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", "display", OracleEvidence(
                         "display", "citation_page_value", truth, None,
                         "display citation_page_value is missing or null"))
    viewer = display_record.get("viewer_page1", _MISSING)
    if viewer is _MISSING or viewer is None:
        if is_duplicate and upstream == truth:
            result.verdict = "AMBIGUOUS"
            result.evidence = [OracleEvidence(
                "display", "viewer_page1", truth, None,
                "display carries no viewer page, so no single page was "
                "forced; the quote occurs on several pages with no "
                "disambiguating anchor")]
            result.notes = ["The quote occurs on several physical pages "
                            "and the display layer forced no single page; "
                            "the source page is ambiguous, not guessed."]
            return result
        return _fail(result, "FAIL_METADATA_MISSING",
                     "PAGE_METADATA_MISSING", "display", OracleEvidence(
                         "display", "viewer_page1", truth, None,
                         "display viewer_page1 is missing or null"))
    resolved, kind, note = _resolve_display(display_record, label_table)
    if kind in ("label_unresolved", "type_mismatch", "out_of_range"):
        result.verdict = "NEEDS_MANUAL_REVIEW"
        result.first_fault_stage = "display"
        result.reason = ("LABEL_UNRESOLVED" if kind == "label_unresolved"
                         else "VALUE_BASIS_TYPE_MISMATCH")
        result.correct_pdf_page_number1 = None
        result.correct_viewer_page1 = None
        result.evidence = [OracleEvidence(
            "display", "citation_page_value", truth, value, note)]
        result.notes = ["The display page value cannot be resolved "
                        "through its stated basis; no page is guessed."]
        return result
    assert resolved is not None  # kind == "ok" here
    if not isinstance(viewer, int) or isinstance(viewer, bool) or viewer < 1:
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "display",
                     OracleEvidence(
                         "display", "viewer_page1", resolved + 1, viewer,
                         "viewer_page1 is not a valid 1-based page"))
    if is_duplicate:
        if resolved in truth:
            return _fail(result, "FAIL_AMBIGUOUS",
                         "DUPLICATE_TEXT_AMBIGUITY", "display",
                         OracleEvidence(
                             "display", "citation_page_value", truth,
                             [resolved],
                             f"display forced the multi-page candidate set "
                             f"{truth} to the single page {resolved}; no "
                             "single page may be forced"))
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "display",
                     OracleEvidence(
                         "display", "citation_page_value", truth,
                         [resolved],
                         "display page is not one of the candidate pages "
                         f"{truth}"))
    if is_cross_page:
        if resolved in truth and viewer == resolved + 1:
            return result  # PASS (base already carries PASS defaults)
        if resolved not in truth:
            return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET",
                         "display", OracleEvidence(
                             "display", "citation_page_value", truth,
                             [resolved],
                             "display page is outside the cross-page "
                             f"source set {truth}"))
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "display",
                     OracleEvidence(
                         "display", "viewer_page1", resolved + 1, viewer,
                         "viewer_page1 is not resolved + 1"))
    # Single-page truth.
    if resolved != truth[0]:
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "display",
                     OracleEvidence(
                         "display", "citation_page_value", truth,
                         [resolved],
                         f"display page value resolves to physical page "
                         f"{resolved}, not the true source page "
                         f"{truth[0]}"))
    if viewer != resolved + 1:
        return _fail(result, "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "display",
                     OracleEvidence(
                         "display", "viewer_page1", resolved + 1, viewer,
                         "viewer_page1 is not the resolved page + 1; a "
                         "0-based value was handed to the 1-based viewer"))
    return result  # PASS
