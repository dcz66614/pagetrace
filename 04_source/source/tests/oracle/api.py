"""Per-case entry point for the T006 Oracle.

:func:`analyze_case` takes a PDF path and a ``pagetrace.bundle/v1``
bundle and returns the Oracle's verdict for every citation in the
bundle plus the full extraction audit (every bundle extraction
record compared with the honest pdfminer reading).  It never imports
``pagetrace`` or ``pypdf``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .attribute import (ExtractionDiff, OracleResult, analyze_citation,
                        audit_extraction)
from .locate import OracleMatch, locate_quote
from .pdfread import OraclePage, read_pdf_pages


@dataclass
class OracleCaseResult:
    """Oracle outcome for one fixture case (one PDF + one bundle)."""

    case_id: str
    pdf_path: str
    pages: list[OraclePage] = field(default_factory=list)
    citations: list[OracleResult] = field(default_factory=list)
    extraction_diffs: list[ExtractionDiff] = field(default_factory=list)

    def by_citation_id(self, citation_id: str) -> OracleResult:
        """The result for one citation id (raises KeyError if absent)."""
        for result in self.citations:
            if result.citation_id == citation_id:
                return result
        raise KeyError(citation_id)


def analyze_case(pdf_path: str, bundle: dict,
                 case_id: str = "") -> OracleCaseResult:
    """Run the Oracle on one PDF + bundle.

    Reads the PDF with pdfminer.six, locates every citation's quote
    in that honest text, and attributes each citation through the
    stage walk.  ``case_id`` is carried for reporting only.
    """
    pages = read_pdf_pages(pdf_path)
    page_texts = [page.raw_text or "" for page in pages]
    citations: list[OracleResult] = []
    for citation in bundle.get("citations", []):
        match: OracleMatch = locate_quote(
            page_texts, str(citation.get("quote_text", "")))
        citations.append(analyze_citation(
            citation=citation, bundle=bundle, pages=pages, match=match))
    return OracleCaseResult(
        case_id=case_id or str(bundle.get("case_id", "")),
        pdf_path=pdf_path,
        pages=pages,
        citations=citations,
        extraction_diffs=audit_extraction(
            pages, (bundle.get("stages") or {}).get("extraction")),
    )
