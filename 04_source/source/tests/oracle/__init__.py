"""Independent Oracle for P026 PageTrace (T006) — package overview.

This package is the *independent* checker for the S0 Golden fixtures.
It reads PDFs only through pdfminer.six, derives every conclusion from
the fixture spec + the PDF bytes + the bundle JSON, and never imports
``pagetrace`` or any production module.  The only things shared with
production are the JSON schemas (``pagetrace.bundle/v1``,
``pagetrace.golden/v1``) and the fixed input files themselves
(PROJECT_BOOK.md v1.0.0 §8.2).

Modules (each written from the spec, not from production code):

* :mod:`oracle.pdfread` — per-page text, image detection and page
  labels, all via pdfminer.six.
* :mod:`oracle.textnorm` — §4.2 text folding, page fingerprints, and
  the documented single-glyph repair for pdfminer's undecodable "·".
* :mod:`oracle.locate` — exact quote location, including adjacent
  cross-page spans, by maximal prefix/suffix coverage.
* :mod:`oracle.attribute` — the Extraction → Chunking → Indexing →
  Display stage walk and verdict attribution (§4.3, §5, §7.3).
* :mod:`oracle.api` — the per-case entry point used by the tests and
  by the Golden builder.

Independence is enforced by ``tests/oracle/test_oracle.py``
(no ``pagetrace`` import anywhere under ``tests/oracle/``) and by the
evidence log ``07_evidence/runtime_logs/t006-oracle-independence.log``.
"""

from __future__ import annotations
