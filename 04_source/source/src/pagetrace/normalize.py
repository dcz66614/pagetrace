"""Text normalisation (P026 T003).

Implements PROJECT_BOOK.md v1.0.0 §4.2 exactly:

* Unicode NFC normalisation;
* CRLF / CR unified to LF;
* every run of whitespace collapsed to a single space (and stripped at
  the ends, so a normalised text never starts or ends with whitespace).

What is deliberately NOT done: no case folding, no punctuation changes,
no full-width/half-width conversion, no fuzzy matching, no spelling
correction, no semantic similarity, no translation. A quote that differs
from the page text by one punctuation mark, one case change, or one
full-width/half-width swap is a *different* normalised string and will
not match (see ``locate.py``).

This module is byte-identical in behaviour to the T002 fixture
generator's ``norm_text`` (``tools/generate_fixtures.py``), so hashes
computed here agree with the fixture bundles.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Return the §4.2 normalised form of *text*.

    NFC, then CRLF/CR -> LF, then every whitespace run -> one space,
    then strip leading/trailing whitespace.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RUN.sub(" ", text)
    return text.strip()


def sha256_hex_of_normalized(text: str) -> str:
    """SHA-256 (lowercase hex) of the normalised form of *text*.

    This is the hash used for ``PageTextRecord.text_sha256`` (hash of the
    normalised extracted page text) and it matches the ``text_sha256``
    values in the T002 fixture bundles, which hash the normalised
    extracted text the same way.
    """
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def quote_sha256(quote_text: str) -> str:
    """SHA-256 (lowercase hex) of the normalised quote text.

    Per T001 ``docs/PAGE_SEMANTICS.md`` §1.3, ``quote_sha256`` is the
    SHA-256 of the §4.2-normalised quote; the report stores the hash,
    not the quote text itself.
    """
    return sha256_hex_of_normalized(quote_text)
