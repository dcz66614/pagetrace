"""Stage comparison and first-fault attribution (P026 T004).

Implements PROJECT_BOOK.md v1.0.0 §4.3 / §5 / §7.3 and
docs/PAGE_SEMANTICS.md §4: compare the source page identity along
the fixed chain

    PDF truth -> Extraction -> Chunking -> Indexing -> Display

using canonical ``pdf_page_index0`` as the baseline. The first
provable difference is ``first_fault_stage``.

How each stage is observed for one citation (``truth`` is the
locator's candidate set on the honestly extracted PDF):

* Extraction — for every truth page, the bundle extraction record
  must exist, carry the same ``text_state`` as the honest record,
  and (for TEXT pages) the same ``text_sha256``. A missing record,
  a missing hash field, or a TEXT page re-marked ``ERROR`` is
  ``PAGE_METADATA_MISSING``; a present-but-different hash is
  ``PAGE_OFFSET`` (the record attached a neighbour page's text).
* Chunking / Indexing — the linked record's
  ``source_page_indices0`` must equal the upstream set. A missing
  record, a missing ``text_sha256`` / ``pdf_page_label`` field, or
  an emptied ``[]`` set is ``PAGE_METADATA_MISSING``. A proper
  subset of a multi-page duplicate candidate set is
  ``DUPLICATE_TEXT_AMBIGUITY`` (``FAIL_AMBIGUOUS``); any other
  disagreement is ``PAGE_OFFSET``.
* Display — the display record is resolved to a 0-based index
  through ``citation_page_basis`` (``PDF_INDEX_0``: value as-is;
  ``PDF_NUMBER_1``: value - 1; ``PDF_LABEL``: PDF label-table
  lookup, never arithmetic — R-03). A missing record, a null
  ``citation_page_value`` or a null ``viewer_page1`` is
  ``PAGE_METADATA_MISSING``. An ``UNKNOWN`` basis is
  ``UNKNOWN_PAGE_BASIS``. A resolved page that disagrees with the
  truth, or a ``viewer_page1`` that is not ``resolved + 1``, is
  ``PAGE_OFFSET`` (R-01/R-06); a resolved page that picks one of
  several duplicate candidates is ``FAIL_AMBIGUOUS``.

Special cases, all decided by explicit input, never by guessing:

* Any stage snapshot missing (``stages.missing_stages`` or an
  absent stage key) → ``UNKNOWN_TRACE_MISSING``; the walk stops
  before blaming any stage.
* Quote not found in the text layer (0 candidates) →
  ``FAIL_UNLOCATABLE``. The reason is anchored on the page(s) the
  trace itself claims (chunk, then index): ``IMAGE_ONLY`` /
  ``EMPTY`` / ``NO_EXACT_MATCH``; with no anchor, ``NO_TEXT_LAYER``.
  Only a provable extraction failure is blamed on extraction: an
  anchor page honestly ``IMAGE_ONLY`` / ``EMPTY`` (no text layer to
  extract), or a bundle extraction record for a claimed page that
  provably differs from the honest extraction. Otherwise — a near
  miss on a TEXT page whose extraction records match the honest
  extraction, or no usable anchor — ``first_fault_stage`` is
  ``None`` and ``expected_source_pages0`` is ``None``: the
  trace-claimed page is unconfirmed, never a verified source. The
  notes always state that this does not establish the quoted text
  is absent from the document.
* Duplicate quote, every set-bearing stage preserved the full
  candidate set, and the display stage recorded no forced pick
  (record absent, or value / viewer null) → ``AMBIGUOUS``.
  A stage that *does* force a single page is ``FAIL_AMBIGUOUS``
  at that stage instead.
* Cross-page quote (one adjacent span): the source set is the
  whole span; a display value naming any page of the span is
  accepted (the v1 display record carries a single value, and the
  fixture control citations show the span's first page).
* A quote spanning more than two pages, an unresolvable label, a
  value/basis type mismatch, or an out-of-range display value →
  ``NEEDS_MANUAL_REVIEW`` (T013 P2-04: out-of-range carries reason
  ``VALUE_OUT_OF_RANGE``, a type mismatch ``VALUE_BASIS_TYPE_MISMATCH``).

No stage is ever skipped to blame a later one, and no uncertainty
is ever converted to PASS.
"""

from __future__ import annotations

from dataclasses import dataclass

from .extract import PageTextRecord
from .locate import QuoteMatch, locate_quote
from .normalize import quote_sha256
from .verdicts import (
    REASON_EMPTY,
    REASON_IMAGE_ONLY,
    REASON_LABEL_UNRESOLVED,
    REASON_NO_EXACT_MATCH,
    REASON_NO_TEXT_LAYER,
    REASON_TRACE_MISSING,
    REASON_UNSUPPORTED_SPAN,
    REASON_VALUE_BASIS_TYPE_MISMATCH,
    REASON_VALUE_OUT_OF_RANGE,
    STAGE_ORDER,
    VERDICT_AMBIGUOUS,
    VERDICT_FAIL_AMBIGUOUS,
    VERDICT_FAIL_METADATA_MISSING,
    VERDICT_FAIL_PAGE_OFFSET,
    VERDICT_FAIL_UNLOCATABLE,
    VERDICT_NEEDS_MANUAL_REVIEW,
    VERDICT_PASS,
    VERDICT_UNKNOWN_PAGE_BASIS,
    VERDICT_UNKNOWN_TRACE_MISSING,
    CitationVerdict,
    EvidenceItem,
)

#: Sentinel distinguishing "field absent" from "field present, null".
_MISSING = object()

# Stage names as they appear in a bundle's ``stages`` mapping.
STAGE_EXTRACTION = "extraction"
STAGE_CHUNKING = "chunking"
STAGE_INDEXING = "indexing"
STAGE_DISPLAY = "display"


@dataclass(frozen=True)
class StageDiff:
    """One provable difference between two adjacent observations.

    ``kind`` is one of ``missing`` (record / field / value absent or
    emptied), ``offset`` (a present value disagrees with the
    upstream truth), ``hash_mismatch`` (extraction text hash differs
    from the honest extraction), ``state_mismatch`` (extraction text
    state differs), ``reduced`` (a multi-page candidate set was
    shrunk to a proper subset), or ``needs_review`` (a
    ``NEEDS_MANUAL_REVIEW`` verdict's evidence: no page was guessed,
    manual review is required; T013 P2-13). ``pdf_page_index0`` is set for
    per-page extraction diffs and ``None`` for per-citation diffs.
    """

    stage: str
    field: str
    kind: str
    pdf_page_index0: int | None
    upstream_value: object
    downstream_value: object
    note: str

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "field": self.field,
            "kind": self.kind,
            "pdf_page_index0": self.pdf_page_index0,
            "upstream_value": self.upstream_value,
            "downstream_value": self.downstream_value,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Extraction comparison (per page, against the honest extraction)
# ---------------------------------------------------------------------------

def compare_extraction(
    honest_records: list[PageTextRecord],
    bundle_extraction: list[dict] | None,
) -> list[StageDiff]:
    """Compare every bundle extraction record with the honest one.

    ``bundle_extraction`` is ``None`` when the stage snapshot is
    missing (the caller reports ``UNKNOWN_TRACE_MISSING``; this
    function then returns one ``missing`` diff for the stage).
    Returns one diff per differing page, in physical page order.
    A bundle record whose ``text_sha256`` is ``None`` for a non-TEXT
    honest page is *not* a difference (there is no text to hash);
    a missing ``text_sha256`` *key* on a TEXT page is.
    """
    if bundle_extraction is None:
        return [StageDiff(
            stage=STAGE_EXTRACTION, field="extraction", kind="missing",
            pdf_page_index0=None, upstream_value=None, downstream_value=None,
            note="extraction stage snapshot is missing")]
    by_index: dict[int, dict] = {}
    for record in bundle_extraction:
        index = record.get("pdf_page_index0")
        if isinstance(index, int) and not isinstance(index, bool):
            by_index.setdefault(index, record)
    diffs: list[StageDiff] = []
    for honest in honest_records:
        index = honest.pdf_page_index0
        record = by_index.get(index)
        if record is None:
            diffs.append(StageDiff(
                stage=STAGE_EXTRACTION, field="extraction_record",
                kind="missing", pdf_page_index0=index,
                upstream_value=honest.text_state, downstream_value=None,
                note=f"no extraction record for physical page {index}"))
            continue
        state = record.get("text_state")
        if state != honest.text_state:
            kind = ("missing" if honest.text_state == "TEXT"
                    and state in ("ERROR", "EMPTY", "IMAGE_ONLY")
                    else "state_mismatch")
            diffs.append(StageDiff(
                stage=STAGE_EXTRACTION, field="text_state", kind=kind,
                pdf_page_index0=index,
                upstream_value=honest.text_state, downstream_value=state,
                note=f"extraction text_state for page {index} is "
                     f"{state!r}, honest extraction says "
                     f"{honest.text_state!r}"))
            # A re-marked state already explains the page; a hash
            # comparison against it would be a second, dependent diff.
            continue
        if honest.text_state == "TEXT":
            if "text_sha256" not in record:
                diffs.append(StageDiff(
                    stage=STAGE_EXTRACTION, field="text_sha256",
                    kind="missing", pdf_page_index0=index,
                    upstream_value=honest.text_sha256, downstream_value=None,
                    note=f"extraction record for page {index} omits "
                         f"text_sha256"))
            elif record.get("text_sha256") != honest.text_sha256:
                diffs.append(StageDiff(
                    stage=STAGE_EXTRACTION, field="text_sha256",
                    kind="hash_mismatch", pdf_page_index0=index,
                    upstream_value=honest.text_sha256,
                    downstream_value=record.get("text_sha256"),
                    note=f"extraction text_sha256 for page {index} does "
                         f"not match the honest extraction (text of "
                         f"another page attached?)"))
    for index in sorted(by_index):
        if index < 0 or index >= len(honest_records):
            diffs.append(StageDiff(
                stage=STAGE_EXTRACTION, field="pdf_page_index0",
                kind="offset", pdf_page_index0=index,
                upstream_value=None, downstream_value=index,
                note=f"extraction record for out-of-range page {index}"))
    return diffs


# ---------------------------------------------------------------------------
# Display resolution
# ---------------------------------------------------------------------------

def label_map_from_records(
    honest_records: list[PageTextRecord],
) -> dict[str, list[int]]:
    """PDF page-label table: label string -> physical pages (0-based).

    Labels are looked up, never converted arithmetically (R-03).
    A label naming several pages maps to all of them, so a label
    lookup that is not unique is honestly unresolvable.
    """
    table: dict[str, list[int]] = {}
    for record in honest_records:
        if record.pdf_page_label is not None:
            table.setdefault(record.pdf_page_label, []).append(
                record.pdf_page_index0)
    return table


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def resolve_display_to_index0(
    display_record: dict | None,
    label_map: dict[str, list[int]],
) -> tuple[int | None, str, str]:
    """Resolve a display record to a 0-based physical page.

    Returns ``(index0, kind, note)`` where ``kind`` is ``"ok"``,
    ``"missing_record"``, ``"value_missing"``, ``"unknown_basis"``,
    ``"label_unresolved"``, ``"type_mismatch"`` or
    ``"out_of_range"``. The resolved index is the page the display
    *value* names; the caller separately checks ``viewer_page1``.
    """
    if display_record is None:
        return None, "missing_record", "no display record for this citation"
    value = display_record.get("citation_page_value", _MISSING)
    basis = display_record.get("citation_page_basis", _MISSING)
    if value is _MISSING or value is None:
        return None, "value_missing", \
            "citation_page_value is missing or null"
    if basis == "UNKNOWN" or basis is _MISSING:
        return None, "unknown_basis", \
            "citation_page_basis is UNKNOWN; no conversion is allowed (R-04)"
    if basis == "PDF_INDEX_0":
        if not _is_int(value):
            return None, "type_mismatch", \
                "PDF_INDEX_0 requires an integer citation_page_value (R-08)"
        return value, "ok", ""  # type: ignore[return-value]
    if basis == "PDF_NUMBER_1":
        if not _is_int(value):
            return None, "type_mismatch", \
                "PDF_NUMBER_1 requires an integer citation_page_value (R-08)"
        if value < 1:
            return None, "out_of_range", \
                "PDF_NUMBER_1 value 0 names no physical page (R-02)"
        return value - 1, "ok", ""
    if basis == "PDF_LABEL":
        if not isinstance(value, str):
            return None, "type_mismatch", \
                "PDF_LABEL requires a string citation_page_value (R-08)"
        pages = label_map.get(value)
        if not pages:
            return None, "label_unresolved", \
                f"page label {value!r} is not in the PDF label table (R-03)"
        if len(pages) > 1:
            return None, "label_unresolved", \
                f"page label {value!r} names several physical pages {pages}"
        return pages[0], "ok", ""
    return None, "unknown_basis", \
        f"citation_page_basis {basis!r} is not a known basis"


# ---------------------------------------------------------------------------
# Per-citation stage walk
# ---------------------------------------------------------------------------

def _find_record(records: list[dict] | None, key: str,
                 wanted: str | None) -> dict | None:
    if records is None or wanted is None:
        return None
    for record in records:
        if record.get(key) == wanted:
            return record
    return None


def _source_pages(record: dict | None) -> object:
    """``source_page_indices0`` value, or the ``_MISSING`` sentinel."""
    if record is None:
        return _MISSING
    return record.get("source_page_indices0", _MISSING)


def _evidence(diff: StageDiff) -> EvidenceItem:
    return EvidenceItem(
        stage=diff.stage, field=diff.field,
        upstream_value=diff.upstream_value,
        downstream_value=diff.downstream_value, note=diff.note)


def _fail(verdict: str, fault: str, stage: str, diff: StageDiff,
          base: dict) -> CitationVerdict:
    return CitationVerdict(
        verdict=verdict, fault_type=fault, first_fault_stage=stage,
        evidence=[_evidence(diff)], **base)


def analyze_citation(
    *,
    citation: dict,
    bundle: dict,
    honest_records: list[PageTextRecord],
    quote_match: QuoteMatch,
) -> CitationVerdict:
    """Attribute one citation: verdict + first fault stage + evidence.

    ``citation`` is one entry of ``bundle["citations"]``,
    ``bundle`` the ``pagetrace.bundle/v1`` trace, ``honest_records``
    the production extraction of the same PDF, and ``quote_match``
    the :func:`pagetrace.locate.locate_quote` result for the
    citation's quote on those records.
    """
    stages: dict = bundle.get("stages") or {}
    missing_stages: list[str] = [
        stage for stage in STAGE_ORDER
        if stage in (stages.get("missing_stages") or [])
        or stages.get(stage) is None
    ]
    citation_id = str(citation.get("citation_id"))
    quote_text = str(citation.get("quote_text", ""))
    digest = quote_sha256(quote_text)
    candidates = list(quote_match.candidate_source_pages0)
    correct1 = [page + 1 for page in candidates] or None
    display_record = _find_record(
        stages.get("display"), "citation_id", citation_id)
    display_value = (display_record.get("citation_page_value")
                     if display_record is not None else None)
    display_basis = (display_record.get("citation_page_basis")
                     if display_record is not None else None)

    base: dict = {
        "citation_id": citation_id,
        "quote_sha256": digest,
        "citation_page_value": display_value,
        # A display record that does not exist has no basis to copy;
        # UNKNOWN is the honest value (never a guessed basis).
        "citation_page_basis": (
            display_basis if display_basis in (
                "PDF_INDEX_0", "PDF_NUMBER_1", "PDF_LABEL", "UNKNOWN")
            else "UNKNOWN"),
        "candidate_source_pages0": candidates,
        "expected_source_pages0": None,
        "observed_page_value": display_value,
        "correct_pdf_page_number1": correct1,
        "correct_viewer_page1": correct1,
        "missing_stages": missing_stages,
    }

    # 0. A missing stage snapshot forbids blaming any stage (§4.3).
    if missing_stages:
        return CitationVerdict(
            verdict=VERDICT_UNKNOWN_TRACE_MISSING, fault_type=None,
            first_fault_stage=None, reason=REASON_TRACE_MISSING,
            evidence=[EvidenceItem(
                stage=missing_stages[0], field="stage_snapshot",
                upstream_value=None, downstream_value=None,
                note="stage snapshot(s) missing: "
                     + ", ".join(missing_stages)
                     + "; no stage may be blamed without them")],
            notes=["A stage snapshot is missing, so the first fault "
                   "stage cannot be determined; the verdict is UNKNOWN, "
                   "not PASS."],
            **base)

    label_map = label_map_from_records(honest_records)
    honest_by_index = {r.pdf_page_index0: r for r in honest_records}

    # 1. Quote spans more than two pages: real but unsupported (§7.2).
    if quote_match.span_status == "unsupported_span":
        return CitationVerdict(
            verdict=VERDICT_NEEDS_MANUAL_REVIEW, fault_type=None,
            first_fault_stage=None,
            reason=REASON_UNSUPPORTED_SPAN,
            evidence=[EvidenceItem(
                stage=STAGE_EXTRACTION, field="candidate_source_pages0",
                upstream_value=None, downstream_value=None,
                note="quote spans more than two physical pages; "
                     "spans over two pages are unsupported, no page "
                     "is guessed")],
            notes=["The quote spans more than two physical pages, "
                   "which PageTrace does not locate; manual review "
                   "is required."],
            **base)

    # 2. Quote not found in the extractable text layer.
    if not candidates:
        anchor = _trace_anchor_pages(citation, stages)
        reason, anchor_note = _unlocatable_reason(anchor, honest_by_index)
        if reason in (REASON_IMAGE_ONLY, REASON_EMPTY):
            # Provable extraction failure (PROJECT_BOOK §5): the
            # trace-claimed page honestly has no text layer, so
            # extraction is the first provable difference.
            first_stage: str | None = STAGE_EXTRACTION
            expected: list[int] | None = anchor
            blame_note = ""
        else:
            # NO_EXACT_MATCH / NO_TEXT_LAYER (FIX-R1 P1-R1-02): the
            # quote differs from the page text, or no page is named.
            # Extraction is blamed only if a bundle extraction record
            # for a trace-claimed page provably differs from the
            # honest extraction; a verified-correct extraction is
            # never blamed for a missing exact match, and the claimed
            # page is not a confirmed source.
            fault_diff = next(
                (d for d in compare_extraction(
                    honest_records, stages.get("extraction"))
                 if anchor and d.pdf_page_index0 in anchor),
                None)
            if fault_diff is not None:
                first_stage = STAGE_EXTRACTION
                expected = anchor
                blame_note = (
                    "; the extraction record for the claimed page(s) "
                    "provably differs from the honest extraction, so "
                    "extraction is blamed")
            else:
                first_stage = None
                expected = None
                if anchor:
                    blame_note = (
                        "; no stage can be blamed: the extraction "
                        "records for the trace-claimed page(s) match "
                        "the honest extraction, so the missing exact "
                        "match does not prove an extraction failure, "
                        "and the claimed page(s) are not a confirmed "
                        "source")
                else:
                    blame_note = (
                        "; no stage can be blamed: no trace anchor "
                        "names the intended page")
        notes = ["The quote was not found in the extractable text "
                 "layer. This does not establish that the quoted "
                 "text is absent from the document: it may be "
                 "visible only in a raster image, on a blank page, "
                 "or differ by a character from the page text. "
                 "No OCR was run."]
        if first_stage is None:
            notes.append(
                "No stage is blamed for this citation: the missing "
                "exact match does not prove any stage failed, and "
                "the trace-claimed page(s), if any, are not "
                "confirmed as the quote's source page(s).")
        return CitationVerdict(
            verdict=VERDICT_FAIL_UNLOCATABLE, fault_type="UNLOCATABLE",
            first_fault_stage=first_stage,
            expected_source_pages0=expected,
            correct_pdf_page_number1=None, correct_viewer_page1=None,
            reason=reason,
            evidence=[EvidenceItem(
                stage=STAGE_EXTRACTION,
                field="candidate_source_pages0",
                upstream_value=None, downstream_value=[],
                note="quote not found in the extractable text layer"
                     + anchor_note + blame_note)],
            notes=notes,
            **{k: v for k, v in base.items()
               if k not in ("expected_source_pages0",
                            "correct_pdf_page_number1",
                            "correct_viewer_page1")})

    # From here the quote is locatable: the truth set is the full
    # candidate set (a cross-page span is one set, not alternatives).
    truth = sorted(candidates)
    is_duplicate = (quote_match.span_status == "single_page"
                    and len(truth) > 1)
    is_cross_page = quote_match.span_status == "cross_page"
    base["expected_source_pages0"] = truth

    # 3. Extraction: per-truth-page record / state / hash (§4.3.1).
    extraction_diffs = compare_extraction(
        honest_records, stages.get("extraction"))
    fault_diff = next(
        (d for d in extraction_diffs
         if d.pdf_page_index0 in truth), None)
    if fault_diff is not None:
        if fault_diff.kind == "hash_mismatch":
            return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                         STAGE_EXTRACTION, fault_diff, base)
        if fault_diff.kind in ("missing", "state_mismatch"):
            return _fail(VERDICT_FAIL_METADATA_MISSING,
                         "PAGE_METADATA_MISSING", STAGE_EXTRACTION,
                         fault_diff, base)
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_EXTRACTION, fault_diff, base)
    upstream = truth

    # 4. Chunking: the linked chunk's source set (§4.3.2).
    chunk_record = _find_record(
        stages.get("chunking"), "chunk_id", citation.get("chunk_id"))
    verdict = _check_source_stage(
        record=chunk_record, record_field="chunk_record",
        stage=STAGE_CHUNKING, upstream=upstream,
        is_duplicate=is_duplicate, is_cross_page=is_cross_page,
        base=base, honest_records=honest_records)
    if verdict is not None:
        return verdict
    chunk_pages = _source_pages(chunk_record)
    upstream = sorted(chunk_pages)  # type: ignore[arg-type]
    # A chunk text hash that the trace omits is lost metadata (§5).
    if chunk_record is not None and "text_sha256" not in chunk_record:
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", STAGE_CHUNKING,
                     StageDiff(stage=STAGE_CHUNKING, field="text_sha256",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=None, downstream_value=None,
                               note="chunk record omits text_sha256"),
                     base)

    # 5. Indexing: the linked index record's source set + label (§4.3.3).
    index_record = _find_record(
        stages.get("indexing"), "record_id",
        citation.get("index_record_id"))
    verdict = _check_source_stage(
        record=index_record, record_field="index_record",
        stage=STAGE_INDEXING, upstream=upstream,
        is_duplicate=is_duplicate, is_cross_page=is_cross_page,
        base=base, honest_records=honest_records)
    if verdict is not None:
        return verdict
    index_pages = _source_pages(index_record)
    upstream = sorted(index_pages)  # type: ignore[arg-type]
    if index_record is not None and "pdf_page_label" not in index_record:
        claimed = upstream[0] if upstream else None
        honest_label = (honest_by_index[claimed].pdf_page_label
                        if claimed is not None else None)
        if honest_label is not None:
            return _fail(VERDICT_FAIL_METADATA_MISSING,
                         "PAGE_METADATA_MISSING", STAGE_INDEXING,
                         StageDiff(
                             stage=STAGE_INDEXING,
                             field="pdf_page_label", kind="missing",
                             pdf_page_index0=None,
                             upstream_value=honest_label,
                             downstream_value=None,
                             note="index record dropped pdf_page_label "
                                  "on rebuild"),
                         base)
    if index_record is not None and upstream:
        honest_label = honest_by_index[upstream[0]].pdf_page_label
        shown_label = index_record.get("pdf_page_label")
        if shown_label is not None and honest_label is not None \
                and shown_label != honest_label:
            return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                         STAGE_INDEXING,
                         StageDiff(
                             stage=STAGE_INDEXING, field="pdf_page_label",
                             kind="offset", pdf_page_index0=None,
                             upstream_value=honest_label,
                             downstream_value=shown_label,
                             note="index record carries the page label of "
                                  "another physical page"),
                         base)

    # 6. Display: resolve the display value and check the viewer (§4.3.4).
    return _check_display(
        display_record=display_record, label_map=label_map,
        truth=truth, upstream=upstream, is_duplicate=is_duplicate,
        is_cross_page=is_cross_page, base=base)


def _check_source_stage(*, record: dict | None, record_field: str,
                        stage: str, upstream: list[int],
                        is_duplicate: bool, is_cross_page: bool,
                        base: dict,
                        honest_records: list[PageTextRecord],
                        ) -> CitationVerdict | None:
    """Check one set-bearing stage (chunking / indexing).

    Returns a verdict when this stage is the first fault, else None
    (the stage agrees with its upstream set).
    """
    if record is None:
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", stage,
                     StageDiff(stage=stage, field=record_field,
                               kind="missing", pdf_page_index0=None,
                               upstream_value=upstream,
                               downstream_value=None,
                               note=f"no {stage} record for this citation"),
                     base)
    pages = _source_pages(record)
    if pages is _MISSING:
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", stage,
                     StageDiff(stage=stage,
                               field="source_page_indices0",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=upstream,
                               downstream_value=None,
                               note=f"{stage} record omits "
                                    f"source_page_indices0"),
                     base)
    # T013 P2-02: an unvalidated bundle may carry a non-list (or a list
    # with non-integer members) as source_page_indices0. That used to
    # raise a raw TypeError from sorted(); it is now treated as lost
    # metadata (PAGE_METADATA_MISSING), never a crash. The CLI path is
    # unaffected: TraceBundle schema validation rejects it first.
    if not isinstance(pages, list) or any(
            not _is_int(p) for p in pages):
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", stage,
                     StageDiff(stage=stage,
                               field="source_page_indices0",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=upstream,
                               downstream_value=None,
                               note=f"{stage} source_page_indices0 is not "
                                    f"a list of integers "
                                    f"(got {pages!r}); treated as missing "
                                    f"metadata"),
                     base)
    pages = sorted(pages)
    if pages == [] and upstream:
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", stage,
                     StageDiff(stage=stage,
                               field="source_page_indices0",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=upstream, downstream_value=[],
                               note=f"{stage} source_page_indices0 was "
                                    f"emptied to []"),
                     base)
    if pages == upstream:
        return None
    if is_duplicate and set(pages) < set(upstream):
        return _fail(VERDICT_FAIL_AMBIGUOUS,
                     "DUPLICATE_TEXT_AMBIGUITY", stage,
                     StageDiff(stage=stage,
                               field="source_page_indices0",
                               kind="reduced", pdf_page_index0=None,
                               upstream_value=upstream,
                               downstream_value=pages,
                               note=f"{stage} reduced the multi-page "
                                    f"candidate set {upstream} to {pages}; "
                                    f"no single page may be forced"),
                     base)
    if is_cross_page and set(pages) < set(upstream):
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET", stage,
                     StageDiff(stage=stage,
                               field="source_page_indices0",
                               kind="offset", pdf_page_index0=None,
                               upstream_value=upstream,
                               downstream_value=pages,
                               note=f"{stage} dropped page(s) from the "
                                    f"cross-page source set {upstream}"),
                     base)
    return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET", stage,
                 StageDiff(stage=stage, field="source_page_indices0",
                           kind="offset", pdf_page_index0=None,
                           upstream_value=upstream,
                           downstream_value=pages,
                           note=f"{stage} source_page_indices0 {pages} "
                                f"disagrees with upstream {upstream}"),
                 base)


def _check_display(*, display_record: dict | None,
                   label_map: dict[str, list[int]], truth: list[int],
                   upstream: list[int], is_duplicate: bool,
                   is_cross_page: bool,
                   base: dict) -> CitationVerdict:
    """Check the display stage; returns the citation's verdict."""
    # No display record at all.
    if display_record is None:
        if is_duplicate and upstream == truth:
            # No stage forced a single page: honest ambiguity, not a
            # missing-metadata fault (see module docstring).
            return CitationVerdict(
                verdict=VERDICT_AMBIGUOUS, fault_type=None,
                first_fault_stage=None, reason=None,
                evidence=[EvidenceItem(
                    stage=STAGE_DISPLAY, field="display_record",
                    upstream_value=truth, downstream_value=None,
                    note="no display record forces a single page; "
                         "the quote occurs on several pages with no "
                         "disambiguating anchor")],
                notes=["The quote occurs on several physical pages "
                       "and no stage forced a single page; the "
                       "source page is ambiguous, not guessed."],
                **base)
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="display_record",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=truth, downstream_value=None,
                               note="no display record for this citation"),
                     base)
    # An UNKNOWN basis is checked before any null-value / null-viewer
    # check: the schema forces viewer_page1 to null exactly when the
    # basis is UNKNOWN (R-04), so a null viewer there is not lost
    # metadata — it is the correct consequence of an unknown basis.
    if display_record.get("citation_page_basis") == "UNKNOWN":
        return CitationVerdict(
            verdict=VERDICT_UNKNOWN_PAGE_BASIS, fault_type=None,
            first_fault_stage=STAGE_DISPLAY,
            evidence=[EvidenceItem(
                stage=STAGE_DISPLAY, field="citation_page_basis",
                upstream_value=truth, downstream_value="UNKNOWN",
                note="citation_page_basis is UNKNOWN; the value must "
                     "be kept verbatim and no viewer page computed "
                     "(R-04)")],
            notes=["The citation basis is UNKNOWN, so no viewer page "
                   "may be computed from the display value."],
            **base)
    value = display_record.get("citation_page_value", _MISSING)
    if value is _MISSING or value is None:
        if is_duplicate and upstream == truth:
            return CitationVerdict(
                verdict=VERDICT_AMBIGUOUS, fault_type=None,
                first_fault_stage=None, reason=None,
                evidence=[EvidenceItem(
                    stage=STAGE_DISPLAY, field="citation_page_value",
                    upstream_value=truth, downstream_value=None,
                    note="display carries no page value, so no single "
                         "page was forced; the quote occurs on several "
                         "pages with no disambiguating anchor")],
                notes=["The quote occurs on several physical pages "
                       "and the display layer forced no single page; "
                       "the source page is ambiguous, not guessed."],
                **base)
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY,
                               field="citation_page_value", kind="missing",
                               pdf_page_index0=None, upstream_value=truth,
                               downstream_value=None,
                               note="display citation_page_value is "
                                    "missing or null"),
                     base)
    viewer = display_record.get("viewer_page1", _MISSING)
    if viewer is _MISSING or viewer is None:
        if is_duplicate and upstream == truth:
            return CitationVerdict(
                verdict=VERDICT_AMBIGUOUS, fault_type=None,
                first_fault_stage=None, reason=None,
                evidence=[EvidenceItem(
                    stage=STAGE_DISPLAY, field="viewer_page1",
                    upstream_value=truth, downstream_value=None,
                    note="display carries no viewer page, so no single "
                         "page was forced; the quote occurs on several "
                         "pages with no disambiguating anchor")],
                notes=["The quote occurs on several physical pages "
                       "and the display layer forced no single page; "
                       "the source page is ambiguous, not guessed."],
                **base)
        return _fail(VERDICT_FAIL_METADATA_MISSING,
                     "PAGE_METADATA_MISSING", STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="viewer_page1",
                               kind="missing", pdf_page_index0=None,
                               upstream_value=truth, downstream_value=None,
                               note="display viewer_page1 is missing "
                                    "or null"),
                     base)
    # (UNKNOWN basis was already handled above, before the null-value
    # and null-viewer checks.)
    resolved, kind, note = resolve_display_to_index0(
        display_record, label_map)
    if kind == "label_unresolved":
        return CitationVerdict(
            verdict=VERDICT_NEEDS_MANUAL_REVIEW, fault_type=None,
            first_fault_stage=STAGE_DISPLAY,
            reason=REASON_LABEL_UNRESOLVED,
            correct_pdf_page_number1=None, correct_viewer_page1=None,
            evidence=[EvidenceItem(
                stage=STAGE_DISPLAY, field="citation_page_value",
                upstream_value=truth, downstream_value=value, note=note)],
            notes=["The display page label cannot be resolved "
                   "through the PDF label table; no page is guessed."],
            **{k: v for k, v in base.items()
               if k not in ("correct_pdf_page_number1",
                            "correct_viewer_page1")})
    if kind in ("type_mismatch", "out_of_range"):
        # T013 P2-04: an out-of-range value is not a type mismatch.
        # The verdict stays NEEDS_MANUAL_REVIEW either way; only the
        # machine-readable reason differs. The Oracle still maps both
        # to VALUE_BASIS_TYPE_MISMATCH (attribute.py:579-586) — reason
        # is not an S0 parity field, so the gate is unaffected; the
        # divergence is recorded in docs/LIMITATIONS.md.
        if kind == "out_of_range":
            reason = REASON_VALUE_OUT_OF_RANGE
            notes = ["The display page value is outside the range its "
                     "basis allows (R-02/R-05); no page is guessed."]
        else:
            reason = REASON_VALUE_BASIS_TYPE_MISMATCH
            notes = ["The display page value disagrees with its stated "
                     "basis (R-08); no page is guessed."]
        return CitationVerdict(
            verdict=VERDICT_NEEDS_MANUAL_REVIEW, fault_type=None,
            first_fault_stage=STAGE_DISPLAY,
            reason=reason,
            correct_pdf_page_number1=None, correct_viewer_page1=None,
            evidence=[EvidenceItem(
                stage=STAGE_DISPLAY, field="citation_page_value",
                upstream_value=truth, downstream_value=value, note=note)],
            notes=notes,
            **{k: v for k, v in base.items()
               if k not in ("correct_pdf_page_number1",
                            "correct_viewer_page1")})
    # kind == "ok" here (missing_record / value_missing were handled).
    assert resolved is not None
    if not _is_int(viewer) or viewer < 1:
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="viewer_page1",
                               kind="offset", pdf_page_index0=None,
                               upstream_value=resolved + 1,
                               downstream_value=viewer,
                               note="viewer_page1 is not a valid 1-based "
                                    "page (R-02)"),
                     base)
    if is_duplicate:
        if resolved in truth:
            return _fail(VERDICT_FAIL_AMBIGUOUS,
                         "DUPLICATE_TEXT_AMBIGUITY", STAGE_DISPLAY,
                         StageDiff(
                             stage=STAGE_DISPLAY,
                             field="citation_page_value", kind="reduced",
                             pdf_page_index0=None, upstream_value=truth,
                             downstream_value=[resolved],
                             note="display forced the multi-page "
                                  f"candidate set {truth} to the single "
                                  f"page {resolved}; no single page may "
                                  f"be forced"),
                         base)
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY,
                               field="citation_page_value", kind="offset",
                               pdf_page_index0=None, upstream_value=truth,
                               downstream_value=[resolved],
                               note="display page is not one of the "
                                    f"candidate pages {truth}"),
                     base)
    if is_cross_page:
        if resolved in truth and viewer == resolved + 1:
            return _pass(base)
        if resolved not in truth:
            return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                         STAGE_DISPLAY,
                         StageDiff(stage=STAGE_DISPLAY,
                                   field="citation_page_value",
                                   kind="offset", pdf_page_index0=None,
                                   upstream_value=truth,
                                   downstream_value=[resolved],
                                   note="display page is outside the "
                                        f"cross-page source set {truth}"),
                         base)
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="viewer_page1",
                               kind="offset", pdf_page_index0=None,
                               upstream_value=resolved + 1,
                               downstream_value=viewer,
                               note="viewer_page1 is not resolved + 1 "
                                    "(R-01)"),
                     base)
    # Single-page truth.
    if resolved != truth[0]:
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY,
                               field="citation_page_value", kind="offset",
                               pdf_page_index0=None, upstream_value=truth,
                               downstream_value=[resolved],
                               note="display page value resolves to "
                                    f"physical page {resolved}, not the "
                                    f"true source page {truth[0]}"),
                     base)
    if viewer != resolved + 1:
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="viewer_page1",
                               kind="offset", pdf_page_index0=None,
                               upstream_value=resolved + 1,
                               downstream_value=viewer,
                               note="viewer_page1 is not the resolved "
                                    "page + 1 (R-01/R-06); a 0-based "
                                    "value was handed to the 1-based "
                                    "viewer"),
                     base)
    return _pass(base)


def _pass(base: dict) -> CitationVerdict:
    return CitationVerdict(
        verdict=VERDICT_PASS, fault_type=None, first_fault_stage=None,
        evidence=[], notes=[], **base)


def _trace_anchor_pages(citation: dict, stages: dict) -> list[int] | None:
    """Pages the trace itself claims for an unlocatable quote.

    Chunk first, then index. There is no display fallback: the
    display value is a single observed page, not a source set, so it
    cannot anchor the trace-claimed pages. ``None`` when no stage
    names any page.
    """
    chunk = _find_record(stages.get("chunking"), "chunk_id",
                         citation.get("chunk_id"))
    pages = _source_pages(chunk)
    # T013 P2-02: only a list of integers names pages; anything else
    # (a bare int, null, a list with non-integers) names none.
    if isinstance(pages, list) and pages and all(
            _is_int(p) for p in pages):
        return sorted(pages)
    index = _find_record(stages.get("indexing"), "record_id",
                         citation.get("index_record_id"))
    pages = _source_pages(index)
    if isinstance(pages, list) and pages and all(
            _is_int(p) for p in pages):
        return sorted(pages)
    return None


def _unlocatable_reason(
    anchor: list[int] | None,
    honest_by_index: dict[int, PageTextRecord],
) -> tuple[str, str]:
    """Reason + evidence note for an unlocatable quote."""
    if not anchor:
        image_pages = sorted(
            i for i, r in honest_by_index.items()
            if r.text_state == "IMAGE_ONLY")
        return REASON_NO_TEXT_LAYER, (
            "; no trace anchor names the intended page"
            + (f" (document has image-only pages {image_pages})"
               if image_pages else "")
            + "; the specific page state is unknown")
    states = {honest_by_index[p].text_state for p in anchor
              if p in honest_by_index}
    if states == {"IMAGE_ONLY"}:
        return REASON_IMAGE_ONLY, (
            f"; the trace-claimed page(s) {anchor} are IMAGE_ONLY "
            f"(scanned / raster pages, no text layer)")
    if states == {"EMPTY"}:
        return REASON_EMPTY, (
            f"; the trace-claimed page(s) {anchor} are EMPTY "
            f"(blank pages, no text layer content)")
    if states == {"TEXT"}:
        return REASON_NO_EXACT_MATCH, (
            f"; the trace-claimed page(s) {anchor} have a text layer "
            f"but the normalised quote does not occur in it exactly")
    return REASON_NO_TEXT_LAYER, (
        f"; the trace-claimed page(s) {anchor} have mixed text "
        f"states {sorted(states)}; the specific page state is unknown")


# ---------------------------------------------------------------------------
# Bundle-level entry points
# ---------------------------------------------------------------------------

def analyze_bundle(
    bundle: dict,
    honest_records: list[PageTextRecord],
) -> list[CitationVerdict]:
    """Verdicts for every citation in *bundle*, in bundle order."""
    return [
        analyze_citation(
            citation=citation, bundle=bundle,
            honest_records=honest_records,
            quote_match=locate_quote(
                honest_records, str(citation.get("quote_text", ""))))
        for citation in bundle.get("citations", [])
    ]


def stage_diffs_for_bundle(
    bundle: dict,
    honest_records: list[PageTextRecord],
) -> list[StageDiff]:
    """All provable stage diffs for a bundle (evidence JSON).

    The per-page extraction diffs against the honest extraction,
    followed by the per-citation set/value diffs implied by each
    citation's verdict evidence. Extraction diffs are the global
    check the coordinator's six-bundle fact rests on; the
    per-citation diffs are the first-divergence evidence.
    """
    stages: dict = bundle.get("stages") or {}
    diffs = compare_extraction(honest_records, stages.get("extraction"))
    for verdict in analyze_bundle(bundle, honest_records):
        for item in verdict.evidence:
            if verdict.verdict == VERDICT_FAIL_AMBIGUOUS:
                kind = "reduced"
            elif verdict.verdict in (VERDICT_FAIL_METADATA_MISSING,
                                     VERDICT_UNKNOWN_TRACE_MISSING):
                kind = "missing"
            elif verdict.verdict == VERDICT_FAIL_UNLOCATABLE:
                kind = "not_found"
            elif verdict.verdict == VERDICT_NEEDS_MANUAL_REVIEW:
                # T013 P2-13: manual-review evidence is not an offset —
                # no page was guessed, so it gets its own kind.
                kind = "needs_review"
            else:
                kind = "offset"
            diffs.append(StageDiff(
                stage=item.stage, field=item.field, kind=kind,
                pdf_page_index0=None,
                upstream_value=item.upstream_value,
                downstream_value=item.downstream_value,
                note=f"{verdict.citation_id}: {item.note}"))
    return diffs
