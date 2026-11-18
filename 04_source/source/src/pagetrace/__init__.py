"""PageTrace (P026) — PDF citation page-drift detector.

Production package (T003+): PDF input validation, per-page text
extraction, §4.2 normalisation and exact quote location. T001 froze
the page-number contracts (``contracts/``, ``docs/PAGE_SEMANTICS.md``);
the top-level ``pagetrace`` stub that used to carry them was removed
by T013 (P2-08) when the src layout became the installed package.
"""

__version__ = "0.1.0"
