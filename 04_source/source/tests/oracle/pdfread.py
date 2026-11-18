"""Independent PDF reading for the T006 Oracle (pdfminer.six only).

One :class:`OraclePage` per physical page: the raw text pdfminer
reads, the honestly derived text state, the page label from the PDF
catalog, and the folded-text fingerprint.  Nothing here imports
``pypdf`` or ``pagetrace``; the pypdf path is used only by the
*evidence* contrast script (``t006-pdfminer-pypdf-contrast.log``),
never by this module.

Text states (PROJECT_BOOK.md §4.3, stage Extraction):

* ``TEXT`` — pdfminer returned non-blank text.
* ``EMPTY`` — no text and no embedded image (a genuinely blank page).
* ``IMAGE_ONLY`` — no text, but the page embeds at least one image
  (a scanned / raster page).  No OCR is ever started.
* ``ERROR`` — pdfminer raised while reading the page.

Image detection walks the page's XObject tree with pdfminer objects
only: a ``/Subtype /Image`` XObject anywhere in the tree (including
inside a Form XObject's resources) counts.  pdfminer represents
streams as :class:`pdfminer.pdftypes.PDFStream`, which is *not* a
``dict`` — its dictionary lives in ``.attrs`` — so both shapes are
handled by :func:`_as_dict`.

Page labels come from the catalog ``/PageLabels /Nums`` array
(``[{start, {S, P, St}}, ...]``), interpreted directly: ``D`` decimal,
``R``/``r`` roman, ``A``/``a`` alphabetic, optional prefix ``P``,
first number ``St``.  Labels are looked up, never computed by
arithmetic on a neighbouring page.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import PDFStream, resolve1

from .textnorm import fingerprint


@dataclass(frozen=True)
class OraclePage:
    """Honest per-page reading of one physical PDF page."""

    pdf_page_index0: int
    pdf_page_label: str | None
    text_state: str  # "TEXT" | "EMPTY" | "IMAGE_ONLY" | "ERROR"
    text_sha256: str | None  # fingerprint of folded text, TEXT pages only
    raw_text: str | None  # pdfminer text exactly as read (""/None on failure)


def _as_dict(obj: object) -> dict | None:
    """Resolve a pdfminer object to its dictionary, if it has one."""
    try:
        resolved = resolve1(obj)
    except Exception:
        return None
    if isinstance(resolved, dict):
        return resolved
    if isinstance(resolved, PDFStream):
        attrs = resolved.attrs
        return attrs if isinstance(attrs, dict) else None
    return None


def _literal_name(value: object) -> str | None:
    """Name of a pdfminer literal (``/Image`` -> ``"Image"``)."""
    resolved = resolve1(value) if value is not None else None
    name = getattr(resolved, "name", None)
    if isinstance(name, str):
        return name
    if resolved is None:
        return None
    text = str(resolved).strip()
    return text.lstrip("/").strip("'") or None


def _tree_has_image(obj: object, depth: int = 0) -> bool:
    """True when *obj* (or anything nested in its resources) is an
    image XObject.  Recursion is bounded: fixture trees are shallow."""
    if depth > 6:
        return False
    node = _as_dict(obj)
    if node is None:
        return False
    if _literal_name(node.get("Subtype")) == "Image":
        return True
    resources = _as_dict(node.get("Resources"))
    if resources is None:
        return False
    xobjects = resources.get("XObject")
    if xobjects is None:
        return False
    try:
        xobjects = resolve1(xobjects)
    except Exception:
        return False
    if not isinstance(xobjects, dict):
        return False
    return any(_tree_has_image(child, depth + 1) for child in xobjects.values())


def _page_has_image(page: PDFPage) -> bool:
    """True when the page embeds at least one image XObject."""
    resources = _as_dict(page.resources)
    if resources is None:
        return False
    xobjects = resources.get("XObject")
    if xobjects is None:
        return False
    try:
        xobjects = resolve1(xobjects)
    except Exception:
        return False
    if not isinstance(xobjects, dict):
        return False
    return any(_tree_has_image(child) for child in xobjects.values())


def _roman(number: int, upper: bool) -> str:
    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
             (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
             (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    remaining = number
    for value, numeral in table:
        while remaining >= value:
            out += numeral
            remaining -= value
    return out if upper else out.lower()


def _letters(number: int, upper: bool) -> str:
    out = ""
    remaining = number
    while remaining > 0:
        remaining, rem = divmod(remaining - 1, 26)
        out = chr(ord("A") + rem) + out
    return out if upper else out.lower()


def _labels_from_catalog(document: PDFDocument, page_count: int) -> list[str | None]:
    """Page labels from the catalog /PageLabels tree (or all None)."""
    try:
        catalog = _as_dict(document.catalog) or {}
        tree = _as_dict(catalog.get("PageLabels"))
        nums = resolve1(tree.get("Nums")) if tree is not None else None
    except Exception:
        return [None] * page_count
    if not isinstance(nums, list) or not nums:
        return [None] * page_count
    ranges: list[tuple[int, dict]] = []
    for pos in range(0, len(nums) - 1, 2):
        try:
            start = resolve1(nums[pos])
            spec = _as_dict(nums[pos + 1]) or {}
        except Exception:
            continue
        if isinstance(start, int):
            ranges.append((start, spec))
    labels: list[str | None] = []
    for index in range(page_count):
        chosen: tuple[int, dict] | None = None
        for start, spec in ranges:
            if start <= index:
                chosen = (start, spec)
            else:
                break
        if chosen is None:
            labels.append(None)
            continue
        start, spec = chosen
        style = _literal_name(spec.get("S")) or "D"
        prefix = spec.get("P")
        prefix = resolve1(prefix) if prefix is not None else b""
        if isinstance(prefix, bytes):
            prefix = prefix.decode("latin-1")
        elif not isinstance(prefix, str):
            prefix = ""
        try:
            first = resolve1(spec.get("St")) or 1
            number = int(first) + (index - start)
        except Exception:
            labels.append(None)
            continue
        if style == "D":
            body = str(number)
        elif style == "R":
            body = _roman(number, upper=True)
        elif style == "r":
            body = _roman(number, upper=False)
        elif style == "A":
            body = _letters(number, upper=True)
        elif style == "a":
            body = _letters(number, upper=False)
        else:
            body = str(number)
        labels.append(prefix + body)
    return labels


def read_pdf_pages(pdf_path: str) -> list[OraclePage]:
    """Read every physical page of *pdf_path* with pdfminer.six.

    Pages are read in physical order; exactly one record is produced
    per page and no page is ever silently skipped.
    """
    with open(pdf_path, "rb") as handle:
        pages = list(PDFPage.get_pages(handle))
        # Image flags and labels must be resolved while the handle is
        # open: page objects resolve their resources lazily from it.
        image_flags = [_page_has_image(page) for page in pages]
        # The catalog is read from a second parse: PDFPage.get_pages
        # consumes the handle, so labels are resolved independently.
        handle.seek(0)
        from pdfminer.pdfparser import PDFParser

        document = PDFDocument(PDFParser(handle))
        labels = _labels_from_catalog(document, len(pages))
    result: list[OraclePage] = []
    for index in range(len(pages)):
        try:
            buffer = io.StringIO()
            with open(pdf_path, "rb") as handle:
                extract_text_to_fp(
                    handle, buffer, page_numbers=[index],
                    output_type="text", codec="utf-8",
                    laparams=LAParams())
            raw = buffer.getvalue()
        except Exception:
            result.append(OraclePage(
                pdf_page_index0=index,
                pdf_page_label=labels[index] if index < len(labels) else None,
                text_state="ERROR", text_sha256=None, raw_text=None))
            continue
        label = labels[index] if index < len(labels) else None
        if raw is None or raw.strip() == "":
            state = "IMAGE_ONLY" if image_flags[index] else "EMPTY"
            result.append(OraclePage(
                pdf_page_index0=index, pdf_page_label=label,
                text_state=state, text_sha256=None, raw_text=""))
        else:
            result.append(OraclePage(
                pdf_page_index0=index, pdf_page_label=label,
                text_state="TEXT", text_sha256=fingerprint(raw),
                raw_text=raw))
    return result
