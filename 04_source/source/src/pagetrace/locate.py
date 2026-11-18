"""Exact normalised quote location (P026 T003).

Implements PROJECT_BOOK.md v1.0.0 §7.2. Let ``T_i`` be the §4.2
normalised text of physical page ``i`` and ``q`` the normalised quote.

* Single-page candidates: ``C(q) = {i | q is an exact substring of T_i}``.
  Every occurrence is returned — a quote appearing on several pages
  yields the full candidate set (PAGE_SEMANTICS.md R-09); the locator
  never picks one page on its own.
* Cross-page candidates: if no single page contains ``q``, adjacent
  page pairs ``(i, i+1)`` are tried. ``q`` spans the pair when it can
  be split into two non-trivial parts, ``q[:s]`` in ``T_i`` and
  ``q[s:]`` in ``T_{i+1}``. The result records the complete page set,
  e.g. ``[4, 5]`` (R-10). Only adjacent pairs are tried, so there is
  no combinatorial explosion.
* Span over more than 2 physical pages: the locator does not attempt
  unbounded combinations. A bounded probe over adjacent triples
  ``(i, i+1, i+2)`` detects a quote whose three non-trivial parts
  occur in order on three consecutive pages; such a quote is reported
  with ``span_status="unsupported_span"`` and no candidate pages —
  the span is real but unsupported, and must not be guessed.
* ``|C(q)| = 0`` and no cross-page/triple match: ``span_status`` is
  ``"not_found"`` with an empty candidate set. The locator never
  guesses, never lowers a threshold, and never starts OCR.

Precedence is deliberate and documented: a single-page match wins
over a cross-page match. If the whole quote already occurs on one
page, the quote *is* locatable there; additionally reporting a
looser split match on a neighbouring pair would manufacture
candidates. A cross-page match is therefore only searched when no
single page contains the quote.

No semantic model, embedding, fuzzy matching, or OCR is used anywhere
in this module — location is exact substring search on normalised
text only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .extract import PageTextRecord
from .normalize import normalize_text, quote_sha256

SpanStatus = Literal["single_page", "cross_page", "not_found",
                     "unsupported_span"]

#: Minimum length (in normalised characters) of each part of a
#: cross-page split. A part shorter than this is too weak to anchor a
#: page boundary — e.g. a 1-character part matches almost any page.
#: Fixture split halves are ~20 characters, so 4 is far below any real
#: split while still excluding degenerate matches.
MIN_CROSS_PAGE_PART_CHARS = 4


@dataclass(frozen=True)
class QuoteMatch:
    """Location result for one normalised quote.

    ``candidate_source_pages0`` is the complete sorted set of physical
    pages where the quote occurs: single-page matches, or — for a
    cross-page quote — every page of every matching adjacent pair.
    It is ``[]`` when the quote was not found or its span is
    unsupported. ``cross_page_spans`` lists the matching adjacent
    pairs (``[[4, 5]]``); it is ``[]`` for single-page, not-found and
    unsupported-span results. ``unsupported_span`` is True exactly
    when ``span_status == "unsupported_span"``.
    """

    quote_text: str
    normalized_quote: str
    quote_sha256: str
    candidate_source_pages0: list[int]
    cross_page_spans: list[list[int]]
    span_status: SpanStatus
    unsupported_span: bool


def _normalized_page_texts(records: list[PageTextRecord]) -> list[str]:
    return [normalize_text(record.extracted_text or "") for record in records]


def _spans_pair(first: str, second: str, quote: str) -> bool:
    """True if *quote* splits into two non-trivial parts, the first
    occurring in *first* and the second in *second*."""
    min_part = MIN_CROSS_PAGE_PART_CHARS
    if len(quote) < 2 * min_part:
        return False
    for split in range(min_part, len(quote) - min_part + 1):
        if quote[:split] in first and quote[split:] in second:
            return True
    return False


def _spans_triple(first: str, second: str, third: str, quote: str) -> bool:
    """Bounded probe: True if *quote* splits into three non-trivial
    parts occurring in order on three consecutive pages.

    This only *detects* a >2-page span so it can be honestly reported
    as unsupported; it never returns pages as candidates.
    """
    min_part = MIN_CROSS_PAGE_PART_CHARS
    if len(quote) < 3 * min_part:
        return False
    for split1 in range(min_part, len(quote) - 2 * min_part + 1):
        if quote[:split1] not in first:
            continue
        for split2 in range(split1 + min_part,
                            len(quote) - min_part + 1):
            if (quote[split1:split2] in second
                    and quote[split2:] in third):
                return True
    return False


def locate_quote(records: list[PageTextRecord],
                 quote_text: str) -> QuoteMatch:
    """Locate *quote_text* in the extracted pages.

    ``records`` must be the full, in-order extraction of one document
    (indices 0..n-1); an empty or whitespace-only quote can never
    match (the empty string is a substring of everything, so it is
    rejected explicitly instead of returning every page).
    """
    normalized = normalize_text(quote_text)
    digest = quote_sha256(quote_text)
    if normalized == "":
        return QuoteMatch(
            quote_text=quote_text,
            normalized_quote=normalized,
            quote_sha256=digest,
            candidate_source_pages0=[],
            cross_page_spans=[],
            span_status="not_found",
            unsupported_span=False,
        )

    texts = _normalized_page_texts(records)

    # 1. Single-page exact matches — the full candidate set (R-09).
    single = [i for i, text in enumerate(texts) if normalized in text]
    if single:
        return QuoteMatch(
            quote_text=quote_text,
            normalized_quote=normalized,
            quote_sha256=digest,
            candidate_source_pages0=single,
            cross_page_spans=[],
            span_status="single_page",
            unsupported_span=False,
        )

    # 2. Adjacent-page cross-page matches (R-10).
    spans: list[list[int]] = []
    for i in range(len(texts) - 1):
        if _spans_pair(texts[i], texts[i + 1], normalized):
            spans.append([i, i + 1])
    if spans:
        pages = sorted({page for span in spans for page in span})
        return QuoteMatch(
            quote_text=quote_text,
            normalized_quote=normalized,
            quote_sha256=digest,
            candidate_source_pages0=pages,
            cross_page_spans=spans,
            span_status="cross_page",
            unsupported_span=False,
        )

    # 3. Bounded >2-page probe: detect, do not locate.
    for i in range(len(texts) - 2):
        if _spans_triple(texts[i], texts[i + 1], texts[i + 2], normalized):
            return QuoteMatch(
                quote_text=quote_text,
                normalized_quote=normalized,
                quote_sha256=digest,
                candidate_source_pages0=[],
                cross_page_spans=[],
                span_status="unsupported_span",
                unsupported_span=True,
            )

    # 4. Not found anywhere in the text layer: report honestly.
    return QuoteMatch(
        quote_text=quote_text,
        normalized_quote=normalized,
        quote_sha256=digest,
        candidate_source_pages0=[],
        cross_page_spans=[],
        span_status="not_found",
        unsupported_span=False,
    )
