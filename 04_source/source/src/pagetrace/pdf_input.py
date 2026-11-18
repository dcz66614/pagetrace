"""PDF input validation (P026 T003).

Reads a local PDF file, verifies it is a readable, unencrypted PDF
within the default limits, and returns its identity: file name, size,
SHA-256 of the exact bytes, page count and per-page labels.

Default limits (PROJECT_BOOK.md v1.0.0 §13 / IMPLEMENTATION_PLAN.md
§T003): files larger than 50 MiB or with more than 500 pages are
rejected. Callers may *lower* the limits; they are never raised above
the defaults by this module — pass explicit values only when a test or
a local configuration deliberately tightens them.

Every rejection is a controlled :class:`PdfInputError` carrying a
machine-readable ``reason``; no corrupt / encrypted / oversized input
ever crashes the caller or is silently skipped.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MiB
DEFAULT_MAX_PAGES = 500

# Machine-readable rejection reasons.
REASON_FILE_NOT_FOUND = "FILE_NOT_FOUND"
REASON_NOT_A_FILE = "NOT_A_FILE"
REASON_TOO_LARGE = "TOO_LARGE"
REASON_CORRUPT = "CORRUPT"
REASON_ENCRYPTED = "ENCRYPTED"
REASON_TOO_MANY_PAGES = "TOO_MANY_PAGES"
REASON_EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
REASON_SHA_MISMATCH = "SHA_MISMATCH"


class PdfInputError(Exception):
    """A controlled rejection of a PDF input.

    Attributes:
        reason: one of the ``REASON_*`` constants above.
        path: the input path as given by the caller (may be None).
    """

    def __init__(self, reason: str, message: str, path: str | None = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.path = path

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.reason}] {self.message}"


@dataclass(frozen=True)
class PdfDocumentInfo:
    """Identity of a validated PDF document.

    ``file_path`` is the path as given by the caller (identity /
    reporting only — extraction must NOT re-open it without a SHA
    re-check, see P1-R1-01); ``file_name``
    is the bare file name only, matching
    ``document.file_name`` in the bundle schema. ``page_labels`` is a
    tuple with one entry per physical page (``None`` where the PDF
    defines no label for that page); its length always equals
    ``page_count``. ``is_encrypted`` is always ``False`` here — an
    encrypted input is rejected by :func:`load_pdf` instead of being
    returned — but the field is kept so the type stays honest about
    what was checked. ``pdf_bytes`` carries the exact validated bytes
    (``None`` only for an info value built without them, e.g. by an
    older caller): extraction parses these bytes. It is excluded from
    ``repr`` / equality so logs and comparisons never dump a whole PDF.
    """

    file_name: str
    file_path: str
    file_size_bytes: int
    sha256: str
    page_count: int
    is_encrypted: bool
    page_labels: tuple[str | None, ...]
    pdf_bytes: bytes | None = field(default=None, repr=False, compare=False)


def load_pdf(
    path: str | os.PathLike[str],
    *,
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    max_pages: int = DEFAULT_MAX_PAGES,
    data: bytes | None = None,
    expected_sha256: str | None = None,
) -> PdfDocumentInfo:
    """Validate *path* as a PDF and return its :class:`PdfDocumentInfo`.

    When *data* is given, those exact bytes are validated and parsed
    (the file is not re-read) and are carried in the returned info as
    ``pdf_bytes`` so extraction parses the verified bytes (P1-R1-01).
    When *expected_sha256* is given, the validated bytes must hash to
    it, otherwise a :class:`PdfInputError` (``SHA_MISMATCH``) is raised.

    Raises :class:`PdfInputError` (never a raw pypdf/OS exception) for:
    missing path, non-file path, size over the limit, unreadable or
    corrupt PDF bytes, encrypted PDF, zero pages, page count over
    the limit, or a SHA-256 mismatch against *expected_sha256*.
    """
    path_str = os.fspath(path)
    if data is None:
        if not os.path.exists(path_str):
            raise PdfInputError(
                REASON_FILE_NOT_FOUND, f"PDF file not found: {path_str}", path_str)
        if not os.path.isfile(path_str):
            raise PdfInputError(
                REASON_NOT_A_FILE, f"PDF path is not a file: {path_str}", path_str)

        file_size = os.path.getsize(path_str)
        if file_size > max_file_size_bytes:
            raise PdfInputError(
                REASON_TOO_LARGE,
                f"PDF is {file_size} bytes, over the limit of "
                f"{max_file_size_bytes} bytes",
                path_str)

        with open(path_str, "rb") as fh:
            data = fh.read()
        # Re-check after reading: the file could have grown between the
        # stat and the read (TOCTOU); the byte count is authoritative.
        if len(data) > max_file_size_bytes:
            raise PdfInputError(
                REASON_TOO_LARGE,
                f"PDF is {len(data)} bytes, over the limit of "
                f"{max_file_size_bytes} bytes",
                path_str)
    elif len(data) > max_file_size_bytes:
        raise PdfInputError(
            REASON_TOO_LARGE,
            f"PDF is {len(data)} bytes, over the limit of "
            f"{max_file_size_bytes} bytes",
            path_str)
    sha256 = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and sha256 != expected_sha256:
        raise PdfInputError(
            REASON_SHA_MISMATCH,
            f"PDF SHA-256 mismatch: expected {expected_sha256}, "
            f"actual bytes hash to {sha256}",
            path_str)

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise PdfInputError(
            REASON_CORRUPT, f"PDF cannot be parsed: {exc}", path_str) from exc
    except Exception as exc:  # pypdf may raise other errors on garbage
        raise PdfInputError(
            REASON_CORRUPT, f"PDF cannot be parsed: {exc}", path_str) from exc

    if reader.is_encrypted:
        raise PdfInputError(
            REASON_ENCRYPTED,
            "PDF is encrypted; no password support in this tool "
            "(no OCR, no decryption attempted)",
            path_str)

    try:
        page_count = len(reader.pages)
    except Exception as exc:
        raise PdfInputError(
            REASON_CORRUPT, f"PDF page list cannot be read: {exc}",
            path_str) from exc
    if page_count == 0:
        raise PdfInputError(
            REASON_EMPTY_DOCUMENT, "PDF has zero pages", path_str)
    if page_count > max_pages:
        raise PdfInputError(
            REASON_TOO_MANY_PAGES,
            f"PDF has {page_count} pages, over the limit of {max_pages}",
            path_str)

    labels = _read_page_labels(reader, page_count)
    return PdfDocumentInfo(
        file_name=Path(path_str).name,
        file_path=path_str,
        file_size_bytes=len(data),
        sha256=sha256,
        page_count=page_count,
        is_encrypted=False,
        page_labels=tuple(labels),
        pdf_bytes=data,
    )


def _read_page_labels(reader: PdfReader, page_count: int) -> list[str | None]:
    """Return one label per physical page, or ``None`` where undefined.

    A failure to read the label tree is not fatal to extraction: the
    affected pages are honestly reported as label-less (``None`` means
    "no label", never page 0 — see PAGE_SEMANTICS.md R-03/R-07).
    """
    try:
        raw_labels = list(reader.page_labels)
    except Exception:
        return [None] * page_count
    labels: list[str | None] = []
    for index in range(page_count):
        if index < len(raw_labels):
            label = raw_labels[index]
            labels.append(None if label is None else str(label))
        else:
            labels.append(None)
    return labels
