"""Independent exact quote location (P026 T006 Oracle).

Written from PROJECT_BOOK.md v1.0.0 §7.2: the candidate set is every
physical page whose folded text contains the folded quote as an exact
substring; a quote occurring on several pages yields the full set —
never a single guessed page.  A quote found on no page is
``not_found``; a quote spread over more than two pages is detected
and reported as ``unsupported_span`` (never located by guessing).

Cross-page spans are found by *maximal prefix/suffix coverage*,
not by enumerating split points: for an adjacent pair ``(i, i+1)``,
take the longest prefix of the quote that occurs anywhere in page
``i`` (found by binary search — prefix occurrence is monotone: if a
prefix of length ``k`` occurs, so does every shorter prefix) and the
longest suffix occurring in page ``i+1``.  The pair spans the quote
exactly when the two together cover it (their lengths sum to at
least the quote length) and each side contributes at least
``MIN_ANCHOR_CHARS`` characters — a shorter anchor could match
almost any page.  Single-page matches take precedence: when the
whole quote already occurs on one page, no looser span is also
reported.

The >2-page probe uses the same coverage idea on triples: the
longest prefix on the first page, the longest suffix on the third,
and the uncovered middle must occur on the middle page.  It only
ever *detects* an unsupported span; it never returns pages.
"""

from __future__ import annotations

from dataclasses import dataclass

from .textnorm import collapse_text, quote_fingerprint

#: Minimum characters each side of a cross-page split must contribute.
#: Fixture split halves are ~20 characters; 4 is far below any real
#: split while excluding degenerate 1-character anchors.
MIN_ANCHOR_CHARS = 4


@dataclass(frozen=True)
class OracleMatch:
    """Location result for one quote."""

    quote_text: str
    normalized_quote: str
    quote_sha256: str
    candidate_source_pages0: list[int]
    cross_page_spans: list[list[int]]
    span_status: str  # "single_page" | "cross_page" | "not_found" | "unsupported_span"
    unsupported_span: bool


def _longest_prefix_in(quote: str, text: str) -> int:
    """Length of the longest prefix of *quote* occurring in *text*."""
    low, high = 0, len(quote)
    while low < high:
        mid = (low + high + 1) // 2
        if quote[:mid] in text:
            low = mid
        else:
            high = mid - 1
    return low


def _longest_suffix_in(quote: str, text: str) -> int:
    """Length of the longest suffix of *quote* occurring in *text*."""
    low, high = 0, len(quote)
    while low < high:
        mid = (low + high + 1) // 2
        if quote[len(quote) - mid:] in text:
            low = mid
        else:
            high = mid - 1
    return low


def _pair_spans(first: str, second: str, quote: str) -> bool:
    """True when the quote is covered by a prefix on *first* and a
    suffix on *second* (each at least MIN_ANCHOR_CHARS long)."""
    if len(quote) < 2 * MIN_ANCHOR_CHARS:
        return False
    prefix = _longest_prefix_in(quote, first)
    if prefix < MIN_ANCHOR_CHARS:
        return False
    suffix = _longest_suffix_in(quote, second)
    if suffix < MIN_ANCHOR_CHARS:
        return False
    return prefix + suffix >= len(quote)


def _triple_spans(first: str, second: str, third: str, quote: str) -> bool:
    """Bounded probe: does the quote need three consecutive pages?

    The longest prefix on the first page and the longest suffix on
    the third page leave an uncovered middle; the span is real when
    that middle (at least MIN_ANCHOR_CHARS long) occurs on the
    middle page.  A few shorter prefix/suffix lengths are also
    tried, because the maximal split is not always the true one.

    T013 P2-07 — SUBSET PROBE, not the production check: production
    ``_spans_triple`` (``src/pagetrace/locate.py``) exhaustively tries
    every split point, while this probe only tries
    ``prefix_max-3..prefix_max`` x ``suffix_max-3..suffix_max``.  A
    triple-span quote whose true split lies outside that window would
    be found by production (``unsupported_span`` ->
    ``NEEDS_MANUAL_REVIEW``) and missed here (``FAIL_UNLOCATABLE``).
    No such input exists in the frozen suite — all 48 specs have
    ``split_pages0`` of length 0 or 2, never 3 — so S0 never exercises
    it; the uncertain verdicts are covered only by unit/integration
    tests (see docs/LIMITATIONS.md).  Do NOT "fix" this by adding a
    3-page fixture: the 48-case suite is frozen.
    """
    if len(quote) < 3 * MIN_ANCHOR_CHARS:
        return False
    prefix_max = _longest_prefix_in(quote, first)
    suffix_max = _longest_suffix_in(quote, third)
    for prefix in range(max(MIN_ANCHOR_CHARS, prefix_max - 3), prefix_max + 1):
        for suffix in range(max(MIN_ANCHOR_CHARS, suffix_max - 3), suffix_max + 1):
            # The split points sit on word boundaries, so the middle
            # part carries the boundary spaces; strip them before the
            # containment check (folded texts never start/end with
            # whitespace, so this cannot manufacture a match).
            middle = quote[prefix:len(quote) - suffix].strip()
            if len(middle) >= MIN_ANCHOR_CHARS and middle in second:
                return True
    return False


def locate_quote(page_texts: list[str], quote_text: str) -> OracleMatch:
    """Locate *quote_text* in the folded per-page texts.

    ``page_texts`` are the raw per-page texts in physical order
    (folding is done here).  An empty or whitespace-only quote can
    never match — the empty string is a substring of everything, so
    it is rejected explicitly instead of returning every page.
    """
    normalized = collapse_text(quote_text)
    digest = quote_fingerprint(quote_text)
    if normalized == "":
        return OracleMatch(quote_text, normalized, digest, [], [],
                           "not_found", False)

    texts = [collapse_text(text or "") for text in page_texts]

    # 1. Single-page exact matches — the full candidate set.
    single = [i for i, text in enumerate(texts) if normalized in text]
    if single:
        return OracleMatch(quote_text, normalized, digest, single, [],
                           "single_page", False)

    # 2. Adjacent-page cross-page matches.
    spans: list[list[int]] = []
    for i in range(len(texts) - 1):
        if _pair_spans(texts[i], texts[i + 1], normalized):
            spans.append([i, i + 1])
    if spans:
        pages = sorted({page for span in spans for page in span})
        return OracleMatch(quote_text, normalized, digest, pages, spans,
                           "cross_page", False)

    # 3. Bounded >2-page probe: detect, do not locate.
    for i in range(len(texts) - 2):
        if _triple_spans(texts[i], texts[i + 1], texts[i + 2], normalized):
            return OracleMatch(quote_text, normalized, digest, [], [],
                               "unsupported_span", True)

    # 4. Not found anywhere in the text layer.
    return OracleMatch(quote_text, normalized, digest, [], [],
                       "not_found", False)
