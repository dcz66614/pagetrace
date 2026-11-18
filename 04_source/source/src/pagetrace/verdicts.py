"""Four fault classes and verdict states (P026 T004).

Implements PROJECT_BOOK.md v1.0.0 §5 and docs/PAGE_SEMANTICS.md §4.

Verdicts (exactly the ``pagetrace.report/v1`` enum):

* ``PASS`` — the citation lands on its true source page(s).
* ``FAIL_PAGE_OFFSET`` / fault ``PAGE_OFFSET`` — a stage's physical
  page index / page number disagrees with canonical ``pdf_page_index0``
  (0/1-base confusion or a +/-1 shift).
* ``FAIL_METADATA_MISSING`` / fault ``PAGE_METADATA_MISSING`` — an
  upstream source page identity exists but a downstream stage lost or
  emptied it (record absent, field absent, ``source_page_indices0``
  emptied to ``[]``, a display value / viewer page null).
* ``FAIL_AMBIGUOUS`` / fault ``DUPLICATE_TEXT_AMBIGUITY`` — a
  multi-page candidate set was wrongly reduced to a single page by
  some stage. The full candidate set is kept; no page is guessed.
* ``FAIL_UNLOCATABLE`` / fault ``UNLOCATABLE`` — the quote is not
  found in the extractable text layer. This never means "the quoted
  text does not exist": the visible text may live on an image-only
  page, a blank page may carry nothing, or the quote may differ by
  one character (near miss). The ``reason`` field records which of
  ``IMAGE_ONLY`` / ``EMPTY`` / ``NO_EXACT_MATCH`` / ``NO_TEXT_LAYER``
  applies, anchored on the page(s) the trace itself claims.
* ``UNKNOWN_TRACE_MISSING`` — a stage snapshot is missing, so no
  stage may be blamed. Never converted to PASS.
* ``UNKNOWN_PAGE_BASIS`` — ``citation_page_basis`` is ``UNKNOWN``;
  no viewer page may be computed (R-04).
* ``AMBIGUOUS`` — the quote occurs on several pages, every stage
  that carries a source set preserved the full set, and no stage
  forced a single page (e.g. the display record that would have
  forced a pick is absent). Honest uncertainty, not a fault verdict.
* ``NEEDS_MANUAL_REVIEW`` — exact matching failed in a way no rule
  covers (unsupported >2-page span, an unresolvable page label, a
  value/basis type mismatch); the tool refuses to guess a page.

``first_fault_stage`` is the first stage, in the fixed order
Extraction → Chunking → Indexing → Display, where a difference is
provable. It is ``None`` for ``PASS`` and for uncertainty verdicts
that blame no stage (``UNKNOWN_TRACE_MISSING``,
``NEEDS_MANUAL_REVIEW``); it is ``"display"`` for
``UNKNOWN_PAGE_BASIS`` because the unusable basis lives in the
display record itself. It is also ``None`` for ``FAIL_UNLOCATABLE``
with reason ``NO_EXACT_MATCH`` / ``NO_TEXT_LAYER`` when no
extraction failure is provable (FIX-R1 P1-R1-02): the quote differs
by one character from a sentence on a TEXT page and the extraction
trace matches the honest extraction, so no stage can be blamed and
the trace-claimed page is not a confirmed source
(``expected_source_pages0`` is ``None`` too). Only a page that
honestly has no text layer (``IMAGE_ONLY`` / ``EMPTY``) or a
provably wrong extraction record blames ``"extraction"`` for
UNLOCATABLE.

This module defines the verdict values and the report-shaped result
type only; the stage-by-stage comparison lives in
:mod:`pagetrace.compare_stages`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# --- Stage order (PROJECT_BOOK §4.3, §7.3). Fixed; never reordered. ---
STAGE_ORDER: tuple[str, str, str, str] = (
    "extraction",
    "chunking",
    "indexing",
    "display",
)
Stage = Literal["extraction", "chunking", "indexing", "display"]

# --- Verdicts (pagetrace.report/v1 citation_result.verdict enum). ---
VERDICT_PASS = "PASS"
VERDICT_FAIL_PAGE_OFFSET = "FAIL_PAGE_OFFSET"
VERDICT_FAIL_METADATA_MISSING = "FAIL_METADATA_MISSING"
VERDICT_FAIL_AMBIGUOUS = "FAIL_AMBIGUOUS"
VERDICT_FAIL_UNLOCATABLE = "FAIL_UNLOCATABLE"
VERDICT_UNKNOWN_TRACE_MISSING = "UNKNOWN_TRACE_MISSING"
VERDICT_UNKNOWN_PAGE_BASIS = "UNKNOWN_PAGE_BASIS"
VERDICT_AMBIGUOUS = "AMBIGUOUS"
VERDICT_NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"

VERDICTS: frozenset[str] = frozenset({
    VERDICT_PASS,
    VERDICT_FAIL_PAGE_OFFSET,
    VERDICT_FAIL_METADATA_MISSING,
    VERDICT_FAIL_AMBIGUOUS,
    VERDICT_FAIL_UNLOCATABLE,
    VERDICT_UNKNOWN_TRACE_MISSING,
    VERDICT_UNKNOWN_PAGE_BASIS,
    VERDICT_AMBIGUOUS,
    VERDICT_NEEDS_MANUAL_REVIEW,
})

FAIL_VERDICTS: frozenset[str] = frozenset({
    VERDICT_FAIL_PAGE_OFFSET,
    VERDICT_FAIL_METADATA_MISSING,
    VERDICT_FAIL_AMBIGUOUS,
    VERDICT_FAIL_UNLOCATABLE,
})

UNKNOWN_VERDICTS: frozenset[str] = frozenset({
    VERDICT_UNKNOWN_TRACE_MISSING,
    VERDICT_UNKNOWN_PAGE_BASIS,
})

# --- Fault types (PROJECT_BOOK §5). None for PASS / uncertainty. ---
FAULT_PAGE_OFFSET = "PAGE_OFFSET"
FAULT_METADATA_MISSING = "PAGE_METADATA_MISSING"
FAULT_DUPLICATE_TEXT_AMBIGUITY = "DUPLICATE_TEXT_AMBIGUITY"
FAULT_UNLOCATABLE = "UNLOCATABLE"

FAULT_TYPES: frozenset[str] = frozenset({
    FAULT_PAGE_OFFSET,
    FAULT_METADATA_MISSING,
    FAULT_DUPLICATE_TEXT_AMBIGUITY,
    FAULT_UNLOCATABLE,
})

VERDICT_TO_FAULT: dict[str, str | None] = {
    VERDICT_PASS: None,
    VERDICT_FAIL_PAGE_OFFSET: FAULT_PAGE_OFFSET,
    VERDICT_FAIL_METADATA_MISSING: FAULT_METADATA_MISSING,
    VERDICT_FAIL_AMBIGUOUS: FAULT_DUPLICATE_TEXT_AMBIGUITY,
    VERDICT_FAIL_UNLOCATABLE: FAULT_UNLOCATABLE,
    VERDICT_UNKNOWN_TRACE_MISSING: None,
    VERDICT_UNKNOWN_PAGE_BASIS: None,
    VERDICT_AMBIGUOUS: None,
    VERDICT_NEEDS_MANUAL_REVIEW: None,
}

# --- Machine-readable reasons for UNLOCATABLE / uncertainty. ---
#: The trace-claimed page is a scanned / raster page: no text layer.
REASON_IMAGE_ONLY = "IMAGE_ONLY"
#: The trace-claimed page is blank: no text layer content at all.
REASON_EMPTY = "EMPTY"
#: The trace-claimed page has a text layer but the normalised quote
#: does not occur in it exactly (near miss: one character differs).
REASON_NO_EXACT_MATCH = "NO_EXACT_MATCH"
#: No text layer could confirm the quote and no trace anchor names
#: the intended page, so the specific page state is unknown. The
#: quote is still UNLOCATABLE, never "does not exist".
REASON_NO_TEXT_LAYER = "NO_TEXT_LAYER"
#: The quote spans more than two physical pages (unsupported span).
REASON_UNSUPPORTED_SPAN = "UNSUPPORTED_SPAN"
#: A page label could not be resolved through the PDF label table.
REASON_LABEL_UNRESOLVED = "LABEL_UNRESOLVED"
#: citation_page_value type disagrees with citation_page_basis (R-08).
REASON_VALUE_BASIS_TYPE_MISMATCH = "VALUE_BASIS_TYPE_MISMATCH"
#: citation_page_value is an integer but outside the range its basis
#: allows (T013 P2-04; e.g. PDF_NUMBER_1 value 0 names no physical
#: page, R-02). Distinct from a type mismatch: the value has the right
#: type, it is just out of range.
REASON_VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
#: A stage snapshot is missing (listed in missing_stages).
REASON_TRACE_MISSING = "TRACE_MISSING"


@dataclass(frozen=True)
class EvidenceItem:
    """One stage-diff evidence item (report schema evidence_item).

    ``stage`` and ``field`` are always present; ``upstream_value`` is
    the value at the earlier stage (or the PDF truth) and
    ``downstream_value`` the value at the later stage. A missing value
    is ``None`` — never 0 or ``[]`` used as a placeholder (R-07).
    """

    stage: str
    field: str
    upstream_value: object = None
    downstream_value: object = None
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "field": self.field,
            "upstream_value": self.upstream_value,
            "downstream_value": self.downstream_value,
            "note": self.note,
        }


@dataclass(frozen=True)
class CitationVerdict:
    """Verdict for one citation.

    Field names and meanings follow ``pagetrace.report/v1``
    ``citation_result`` (docs/PAGE_SEMANTICS.md §1.3):

    * ``candidate_source_pages0`` — every physical page where the
      normalised quote was actually found (``[]`` when unlocatable);
      never reduced to a single page (R-09).
    * ``expected_source_pages0`` — the authoritative source set the
      trace should have carried (the PDF-truth candidate set for
      locatable quotes; for UNLOCATABLE, the trace-claimed anchor
      pages only when the anchor page honestly has no text layer or
      its extraction record provably differs — otherwise ``None``,
      the claimed page is unconfirmed); ``None`` when the trace
      gives no usable source set (trace missing / unsupported span /
      near-miss UNLOCATABLE with no provable extraction failure,
      FIX-R1 P1-R1-02).
    * ``observed_page_value`` — the display layer's raw page value,
      verbatim; ``None`` when the display record is absent or its
      value is null.
    * ``correct_pdf_page_number1`` / ``correct_viewer_page1`` —
      1-based correct pages (``index0 + 1`` each); ``None`` when no
      correct page can be stated (UNLOCATABLE / UNKNOWN /
      NEEDS_MANUAL_REVIEW).
    * ``reason`` — machine-readable status for UNLOCATABLE /
      uncertainty verdicts (``IMAGE_ONLY`` / ``EMPTY`` /
      ``NO_EXACT_MATCH`` / ``NO_TEXT_LAYER`` / ...); ``None`` for
      PASS and for the offset / missing / ambiguous fault verdicts.
    * ``missing_stages`` — stages with no snapshot (``[]`` when the
      trace is complete for this citation).
    * ``notes`` — human-readable notes; for UNLOCATABLE they always
      state that the quote was not found *in the extractable text
      layer* and that this does not establish the quoted text is
      absent from the document.
    """

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
    evidence: list[EvidenceItem] = field(default_factory=list)
    reason: str | None = None
    missing_stages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"unknown verdict: {self.verdict!r}")
        if self.fault_type is not None and self.fault_type not in FAULT_TYPES:
            raise ValueError(f"unknown fault_type: {self.fault_type!r}")
        if VERDICT_TO_FAULT[self.verdict] != self.fault_type:
            raise ValueError(
                f"verdict {self.verdict} requires fault_type "
                f"{VERDICT_TO_FAULT[self.verdict]!r}, got {self.fault_type!r}")
        if self.verdict == VERDICT_PASS:
            if self.first_fault_stage is not None:
                raise ValueError("PASS must have first_fault_stage None")
        if self.first_fault_stage is not None \
                and self.first_fault_stage not in STAGE_ORDER:
            raise ValueError(
                f"unknown first_fault_stage: {self.first_fault_stage!r}")
        if (self.correct_pdf_page_number1 is None) != (
                self.correct_viewer_page1 is None):
            raise ValueError(
                "correct_pdf_page_number1 and correct_viewer_page1 must "
                "be null together or present together")
        if (self.correct_pdf_page_number1 is not None
                and self.correct_pdf_page_number1
                != self.correct_viewer_page1):
            raise ValueError(
                "correct_viewer_page1 must equal correct_pdf_page_number1")

    def to_dict(self) -> dict:
        """Report-schema-shaped dict (``citation_result``).

        ``reason`` and ``missing_stages`` are T004 working state, not
        report-schema fields; ``reason`` is folded into ``notes`` so
        nothing is lost.
        """
        notes = list(self.notes)
        if self.reason is not None:
            notes = [f"reason: {self.reason}"] + notes
        if self.missing_stages:
            notes = notes + [
                f"missing_stages: {','.join(self.missing_stages)}"]
        return {
            "citation_id": self.citation_id,
            "quote_sha256": self.quote_sha256,
            "citation_page_value": self.citation_page_value,
            "citation_page_basis": self.citation_page_basis,
            "candidate_source_pages0": list(self.candidate_source_pages0),
            "expected_source_pages0": (
                list(self.expected_source_pages0)
                if self.expected_source_pages0 is not None else None),
            "observed_page_value": self.observed_page_value,
            "correct_pdf_page_number1": (
                list(self.correct_pdf_page_number1)
                if self.correct_pdf_page_number1 is not None else None),
            "correct_viewer_page1": (
                list(self.correct_viewer_page1)
                if self.correct_viewer_page1 is not None else None),
            "verdict": self.verdict,
            "fault_type": self.fault_type,
            "first_fault_stage": self.first_fault_stage,
            "evidence": [item.to_dict() for item in self.evidence],
            "notes": notes,
        }
