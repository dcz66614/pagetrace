"""Independent text folding and page fingerprinting (P026 T006 Oracle).

Written from PROJECT_BOOK.md v1.0.0 §4.2 only: Unicode NFC, CRLF/CR
folded to LF, every run of whitespace collapsed to one space, ends
stripped.  Punctuation, case and full/half-width differences are
preserved — a quote differing by one character is a *different*
string and must not match.

Page fingerprints are SHA-256 of the folded text (UTF-8).  A bundle
extraction record is honest for a page when its ``text_sha256`` equals
the fingerprint of the text pdfminer read from that same page.

Known pdfminer divergence — the single-glyph repair
----------------------------------------------------
pdfminer.six cannot decode the "·" (U+00B7, MIDDLE DOT) glyph in the
synthetic fixture PDFs: it silently drops the character (and the
whitespace around it collapses).  The evidence log
``t006-pdfminer-pypdf-contrast.log`` proves, page by page over all
312 fixture pages, that this is the *only* divergence between the
pdfminer text and the pypdf text: 31 pages differ, every one of them
only by a missing "·" (and its neighbouring space).  No citation
quote in any fixture contains "·", so quote location is unaffected.

Because the bundle hashes were computed over the pypdf text (which
keeps "·"), a naive fingerprint comparison would falsely accuse every
honest page-0 header page.  :func:`hash_matches_page` therefore tries,
after an exact fingerprint match fails, every *single-glyph repair*:
replace one whitespace character with " · ", or insert one "·" at any
position, and re-hash.  A repair match proves the bundle hash is the
hash of this page's text modulo exactly one undecodable glyph; a
repair is recorded in the evidence whenever it is used.  A hash that
belongs to a *different* page (the po-ext swaps) cannot be repaired
this way — inserting one glyph into the wrong page's text does not
produce another page's hash — so genuine swaps are still caught.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RUN = re.compile(r"\s+")

#: The one glyph pdfminer.six drops in these PDFs (see module docstring).
UNDECODABLE_GLYPH = "·"


def collapse_text(text: str) -> str:
    """Fold *text* per §4.2: NFC, line endings to LF, whitespace runs
    to a single space, stripped at both ends."""
    folded = unicodedata.normalize("NFC", text)
    folded = folded.replace("\r\n", "\n").replace("\r", "\n")
    folded = _WHITESPACE_RUN.sub(" ", folded)
    return folded.strip()


def fingerprint(text: str) -> str:
    """SHA-256 (lowercase hex) of the folded form of *text*."""
    return hashlib.sha256(collapse_text(text).encode("utf-8")).hexdigest()


def quote_fingerprint(quote_text: str) -> str:
    """SHA-256 of the folded quote (the report stores the hash, never
    the quote text itself)."""
    return fingerprint(quote_text)


def _repair_candidates(folded: str) -> list[str]:
    """All texts reachable from *folded* by one undecodable-glyph
    repair: replace one single space with " · ", or insert one "·"
    at any character position."""
    candidates: list[str] = []
    for pos, ch in enumerate(folded):
        if ch == " ":
            candidates.append(folded[:pos] + " · " + folded[pos + 1:])
    for pos in range(len(folded) + 1):
        candidates.append(folded[:pos] + UNDECODABLE_GLYPH + folded[pos:])
    return candidates


def hash_matches_page(bundle_hash: str | None, page_text: str) -> tuple[bool, str | None]:
    """Check a bundle ``text_sha256`` against pdfminer page text.

    Returns ``(matched, repair)`` where ``repair`` is ``None`` for an
    exact fingerprint match, a short description when a single-glyph
    repair produced the match, and ``None`` (with ``matched`` False)
    when neither matches.  ``bundle_hash`` of ``None`` never matches.
    """
    if bundle_hash is None:
        return False, None
    folded = collapse_text(page_text)
    if hashlib.sha256(folded.encode("utf-8")).hexdigest() == bundle_hash:
        return True, None
    for candidate in _repair_candidates(folded):
        if hashlib.sha256(candidate.encode("utf-8")).hexdigest() == bundle_hash:
            return True, (
                "single-glyph repair: bundle hash matches this page's "
                "pdfminer text with one U+00B7 re-inserted "
                "(pdfminer drops '·'; see t006-pdfminer-pypdf-contrast.log)"
            )
    return False, None
