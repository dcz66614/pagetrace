"""Per-page text extraction with pypdf (P026 T003).

One :class:`PageTextRecord` is produced for every physical page —
indices are continuous from 0, no page is ever silently skipped.
A page that fails to extract is recorded with ``text_state="ERROR"``
(``extracted_text`` and ``text_sha256`` are ``None``) instead of being
dropped.

Text states (PROJECT_BOOK.md §4.3, stage Extraction):

* ``TEXT`` — pypdf returned non-blank text.
* ``EMPTY`` — no text layer content and no embedded images (a genuinely
  blank page).
* ``IMAGE_ONLY`` — no text layer content, but the page embeds at least
  one image (a scanned / raster page). No OCR is ever started: the
  visible raster text is *not* recoverable from the text layer and the
  record honestly says so.
* ``ERROR`` — ``extract_text()`` raised, or image enumeration failed
  (the page could not be honestly classified — it is never reported
  ``EMPTY`` just because the image check could not run, P2 image-enum).

``text_sha256`` is the SHA-256 of the §4.2-normalised extracted text
(see :mod:`pagetrace.normalize`), which is exactly how the T002
fixture bundles compute their extraction ``text_sha256`` values; it is
``None`` for ``EMPTY`` / ``IMAGE_ONLY`` / ``ERROR`` pages (there is no
extracted text to hash — ``None`` means "no text", not "empty text").
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Literal

from pypdf import PdfReader

from .normalize import sha256_hex_of_normalized
from .pdf_input import (
    REASON_SHA_MISMATCH,
    PdfDocumentInfo,
    PdfInputError,
    load_pdf,
)

TextState = Literal["TEXT", "EMPTY", "IMAGE_ONLY", "ERROR"]


@dataclass(frozen=True)
class PageTextRecord:
    """Extraction result for one physical PDF page.

    ``pdf_page_index0`` is the canonical page identity (0-based).
    ``pdf_page_label`` is the PDF page label, or ``None`` when the PDF
    defines no label for the page. ``extracted_text`` is the raw text
    exactly as pypdf returned it (``""`` for ``EMPTY``/``IMAGE_ONLY``,
    ``None`` only when extraction raised). ``text_sha256`` is the
    SHA-256 of the normalised extracted text for ``TEXT`` pages and
    ``None`` otherwise.
    """

    pdf_page_index0: int
    pdf_page_label: str | None
    text_state: TextState
    text_sha256: str | None
    extracted_text: str | None


def _page_has_images(page) -> bool | None:
    """True if the page embeds at least one image, False if it
    certainly embeds none, ``None`` if image enumeration itself failed.

    The third outcome must stay distinct from "no images": a failure
    here means the page cannot be honestly classified, so the caller
    reports the page ``ERROR`` instead of misreporting it ``EMPTY``
    (a page that could not be checked for images is not a blank page).
    """
    try:
        return len(page.images) > 0
    except Exception:
        return None


def _extract_one_page(page, pdf_page_index0: int,
                      pdf_page_label: str | None) -> PageTextRecord:
    try:
        raw = page.extract_text()
    except Exception:
        return PageTextRecord(
            pdf_page_index0=pdf_page_index0,
            pdf_page_label=pdf_page_label,
            text_state="ERROR",
            text_sha256=None,
            extracted_text=None,
        )
    if raw is None or raw.strip() == "":
        has_images = _page_has_images(page)
        if has_images is None:
            # Image enumeration failed: the page cannot be honestly
            # classified as EMPTY or IMAGE_ONLY (same ERROR handling
            # as an extract_text() failure above).
            return PageTextRecord(
                pdf_page_index0=pdf_page_index0,
                pdf_page_label=pdf_page_label,
                text_state="ERROR",
                text_sha256=None,
                extracted_text=None,
            )
        state: TextState = "IMAGE_ONLY" if has_images else "EMPTY"
        return PageTextRecord(
            pdf_page_index0=pdf_page_index0,
            pdf_page_label=pdf_page_label,
            text_state=state,
            text_sha256=None,
            extracted_text="",
        )
    return PageTextRecord(
        pdf_page_index0=pdf_page_index0,
        pdf_page_label=pdf_page_label,
        text_state="TEXT",
        text_sha256=sha256_hex_of_normalized(raw),
        extracted_text=raw,
    )


def extract_pages(info: PdfDocumentInfo) -> list[PageTextRecord]:
    """Extract every page of a validated document.

    Returns exactly ``info.page_count`` records, in physical order,
    with indices 0..``page_count - 1``. The pages are parsed from the
    exact bytes validated by :func:`pagetrace.pdf_input.load_pdf`
    (``info.pdf_bytes``) — the path is never re-opened on that path,
    so a file swapped after validation cannot leak its content into
    the result (P1-R1-01 TOCTOU). Only when an info value carries no
    bytes (built by an older caller) is the path re-read, and then its
    SHA-256 must still match ``info.sha256`` — a mismatch raises
    :class:`PdfInputError` (``SHA_MISMATCH``) instead of extracting
    the swapped file. A page-count change is likewise rejected
    (``CORRUPT``).
    """
    if info.pdf_bytes is not None:
        data = info.pdf_bytes
        if hashlib.sha256(data).hexdigest() != info.sha256:
            raise PdfInputError(
                "CORRUPT",
                "validated PDF bytes no longer match the recorded "
                f"SHA-256 ({info.sha256})",
                info.file_path)
    else:
        try:
            with open(info.file_path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            raise PdfInputError(
                "CORRUPT",
                f"PDF cannot be re-opened for extraction: {exc}",
                info.file_path) from exc
        if hashlib.sha256(data).hexdigest() != info.sha256:
            raise PdfInputError(
                REASON_SHA_MISMATCH,
                "PDF changed between validation and extraction: "
                f"file on disk no longer hashes to {info.sha256}",
                info.file_path)
    try:
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
    except PdfInputError:
        raise
    except Exception as exc:
        raise PdfInputError(
            "CORRUPT", f"PDF cannot be re-opened for extraction: {exc}",
            info.file_path) from exc
    if page_count != info.page_count:
        raise PdfInputError(
            "CORRUPT",
            f"PDF page count changed between validation "
            f"({info.page_count}) and extraction ({page_count})",
            info.file_path)
    labels = info.page_labels
    return [
        _extract_one_page(page, index,
                          labels[index] if index < len(labels) else None)
        for index, page in enumerate(reader.pages)
    ]


def _require_disk_matches(path: str, expected_sha256: str) -> None:
    """Fail closed: the file on disk must still hash to *expected_sha256*.

    Used when the caller supplies already-verified bytes *and* the hash
    they were verified against: a swap between verification and
    extraction is rejected here instead of being silently analysed.
    """
    try:
        with open(path, "rb") as fh:
            current = fh.read()
    except OSError as exc:
        raise PdfInputError(
            "CORRUPT",
            f"PDF cannot be re-read to confirm it is unchanged: {exc}",
            path) from exc
    if hashlib.sha256(current).hexdigest() != expected_sha256:
        raise PdfInputError(
            REASON_SHA_MISMATCH,
            "PDF changed between verification and extraction: "
            f"file on disk no longer hashes to {expected_sha256}",
            path)


def extract_pdf(
    path: str,
    *,
    max_file_size_bytes: int | None = None,
    max_pages: int | None = None,
    pdf_bytes: bytes | None = None,
    expected_sha256: str | None = None,
) -> tuple[PdfDocumentInfo, list[PageTextRecord]]:
    """Validate *path* and extract all of its pages.

    Convenience wrapper over :func:`pagetrace.pdf_input.load_pdf` and
    :func:`extract_pages`. Limit overrides are passed through only
    when given (``None`` keeps the defaults). When *pdf_bytes* is
    given, those exact bytes are validated and extracted (the path is
    not re-read for content); when *expected_sha256* is also given,
    the file on disk must still hash to it as well — a swap between
    verification and extraction is rejected (``SHA_MISMATCH``)
    instead of analysed.
    """
    kwargs: dict = {}
    if max_file_size_bytes is not None:
        kwargs["max_file_size_bytes"] = max_file_size_bytes
    if max_pages is not None:
        kwargs["max_pages"] = max_pages
    if pdf_bytes is not None:
        kwargs["data"] = pdf_bytes
    if expected_sha256 is not None:
        kwargs["expected_sha256"] = expected_sha256
    if pdf_bytes is not None and expected_sha256 is not None:
        _require_disk_matches(path, expected_sha256)
    info = load_pdf(path, **kwargs)
    return info, extract_pages(info)
