"""P026 T010 — frozen contracts and page semantics for PageTrace bundles.

Source of truth (frozen by T001, PROJECT_BOOK.md v1.0.0):

* ``contracts/pagetrace.bundle.v1.schema.json`` — ``pagetrace.bundle/v1``
* ``contracts/pagetrace.report.v1.schema.json`` — ``pagetrace.report/v1``
* ``docs/PAGE_SEMANTICS.md`` — rules R-01–R-10 (human-readable same contract;
  on conflict the JSON Schema wins and the conflict is a defect, not a
  local judgement call).

This module does NOT rewrite schema semantics: it loads the frozen schema
files as-is and validates instances against them with ``jsonschema``
(Draft 2020-12). The pure page-conversion helpers below are the T001
frozen reference implementation (identical behaviour to
``tests/unit/test_page_semantics.py``); moving them here changes no
semantics.

Unknown-field policy (FIXED — see ``UNKNOWN_FIELD_POLICY`` and §7 of
``docs/PAGE_SEMANTICS.md``): **REJECT**. Every object in both frozen
schemas sets ``additionalProperties: false`` and a bare field named
``page`` is not a listed property anywhere, so any unknown field — a
bare ``page``, ``pageNo``, ``page_no``, a typo, a future field — fails
schema validation. There is no lenient mode and no flag to change this:
an external system that adds a field must get a new schema version
(``pagetrace.bundle/v2``), never a silent accept here. Unknown schema
identifiers are rejected the same way (``schema`` is a ``const``).

Field mapping (bundle ``pagetrace.bundle/v1`` → canonical meaning).
The canonical page identity is always ``pdf_page_index0`` (0-based);
everything else is a derivation, a display value, or a verbatim
external observation — never an implicit conversion:

======================  ==================  ======================================
field                  basis / type      meaning (never converted implicitly)
======================  ==================  ======================================
``schema``              const string      ``pagetrace.bundle/v1`` exactly
``case_id``             string            case identifier (``^[A-Za-z0-9][A-Za-z0-9._-]*$``)
``document.file_name``  string            PDF file name only (no directory)
``document.sha256``     64-hex string     SHA-256 of the exact PDF bytes
``document.page_count`` int 1–500        physical page count; bounds all indices
``page_semantics.*``    consts            canonical_field=``pdf_page_index0``,
                                          index_base=0, viewer_base=1
``stages.extraction[]`` records          one per physical page, in index order;
                       ``pdf_page_index0`` 0-based physical page
                       ``pdf_page_label``  label string or null (lookup only)
                       ``text_state``    TEXT / EMPTY / IMAGE_ONLY / ERROR
                       ``text_sha256``   hash of normalised text, or null
``stages.chunking[]``   records          ``chunk_id``; ``source_page_indices0``
                                          (sorted, de-duplicated, 0-based);
                                          ``text_sha256`` or null
``stages.indexing[]``   records          ``record_id``; ``source_page_indices0``;
                                          ``pdf_page_label`` or null
``stages.display[]``    records          ``citation_id``; raw ``citation_page_value``
                                          verbatim + ``citation_page_basis``;
                                          ``viewer_page1`` 1-based or null
``stages.missing_stages`` enum[]         stages with NO snapshot at all; an
                                          absent stage MUST be listed here
``citations[]``         records          ``citation_id``; ``quote_text`` verbatim;
                                          ``chunk_id`` / ``index_record_id``
                                          (nullable references into the stages)
======================  ==================  ======================================

``citation_page_value`` / ``citation_page_basis`` (R-04, R-08):

* ``PDF_INDEX_0`` — value is an int, the 0-based physical index itself.
* ``PDF_NUMBER_1`` — value is an int, the 1-based physical page number.
* ``PDF_LABEL`` — value is a string, a PDF page label (looked up, never
  parsed as a number, R-03).
* ``UNKNOWN`` — value may be int / string / null; it is kept verbatim and
  NEVER converted (``viewer_page1`` must be null, R-04).

``null`` is not ``0`` and not ``[]`` (R-07): a null page value means "the
source gave no page value", an empty ``source_page_indices0`` means
"verified empty set", and ``0`` is the legitimate first physical page.
Missing a whole stage is recorded in ``missing_stages`` — an empty stage
array is *not* passed off as "checked and clean".
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema

__all__ = [
    "BUNDLE_SCHEMA_ID",
    "REPORT_SCHEMA_ID",
    "BUNDLE_SCHEMA_PATH",
    "REPORT_SCHEMA_PATH",
    "STAGES",
    "CITATION_PAGE_BASES",
    "UNKNOWN_FIELD_POLICY",
    "FIELD_MAPPING",
    "PageSemanticsError",
    "UnknownBasisError",
    "OutOfRangeError",
    "UnresolvableLabelError",
    "SchemaValidationError",
    "BundleValidationError",
    "load_bundle_schema",
    "load_report_schema",
    "validate_bundle_schema",
    "validate_report_schema",
    "validate_against_schema",
    "to_number1",
    "to_index0",
    "to_viewer1",
    "viewer_to_index0",
    "label_to_index0",
    "resolve_citation_to_index0",
    "validate_source_pages0",
]

# Frozen identifiers / paths
# ---------------------------------------------------------------------------

BUNDLE_SCHEMA_ID = "pagetrace.bundle/v1"
REPORT_SCHEMA_ID = "pagetrace.report/v1"

# Schema files: the frozen contracts live in <PACKAGE_ROOT>/contracts/
# (the T001 authority, hashed in the T012 review pack), and byte-identical
# copies ship inside this package at src/pagetrace/schemas/ so the
# *installed* package works without a source checkout (T013 P2-08:
# the old PACKAGE_ROOT/contracts/ path does not exist in a wheel).
# The packaged copy is tried first; the repo copy is the fallback.
# tests/unit/test_page_semantics.py pins the two copies byte-identical.
PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _schema_path(file_name: str) -> Path:
    packaged = Path(__file__).resolve().parent / "schemas" / file_name
    if packaged.is_file():
        return packaged
    return PACKAGE_ROOT / "contracts" / file_name


BUNDLE_SCHEMA_PATH = _schema_path("pagetrace.bundle.v1.schema.json")
REPORT_SCHEMA_PATH = _schema_path("pagetrace.report.v1.schema.json")

STAGES = ("extraction", "chunking", "indexing", "display")
CITATION_PAGE_BASES = ("PDF_INDEX_0", "PDF_NUMBER_1", "PDF_LABEL", "UNKNOWN")

#: Unknown-field policy, fixed by the frozen schemas (see module docstring).
#: ``"reject"`` — any field not listed in the schema fails validation.
#: There is no lenient mode.
UNKNOWN_FIELD_POLICY = "reject"

#: Field mapping table (bundle leaf field -> canonical meaning). Keys are
#: dotted paths in a ``pagetrace.bundle/v1`` instance; values are short
#: human-readable meanings. This is documentation, not a second schema:
#: the JSON Schema files remain the only validation authority.
FIELD_MAPPING = {
    "schema": "schema identifier, const 'pagetrace.bundle/v1'",
    "case_id": "case identifier",
    "document.file_name": "PDF file name only (no directory, no absolute path)",
    "document.sha256": "SHA-256 (lowercase hex) of the exact PDF bytes",
    "document.page_count": "physical page count, 1-500; bounds every index",
    "page_semantics.canonical_field": "const 'pdf_page_index0'",
    "page_semantics.index_base": "const 0 (pdf_page_index0 is 0-based)",
    "page_semantics.viewer_base": "const 1 (viewer_page1 is 1-based)",
    "stages.extraction[].pdf_page_index0": "canonical 0-based physical page",
    "stages.extraction[].pdf_page_label": "PDF page label string or null (lookup only, never arithmetic)",
    "stages.extraction[].text_state": "TEXT / EMPTY / IMAGE_ONLY / ERROR",
    "stages.extraction[].text_sha256": "SHA-256 of normalised extracted text, or null",
    "stages.chunking[].chunk_id": "chunk identifier",
    "stages.chunking[].source_page_indices0": "sorted, de-duplicated 0-based physical pages",
    "stages.chunking[].text_sha256": "SHA-256 of the chunk text, or null",
    "stages.indexing[].record_id": "index record identifier",
    "stages.indexing[].source_page_indices0": "sorted, de-duplicated 0-based physical pages",
    "stages.indexing[].pdf_page_label": "PDF page label string or null",
    "stages.display[].citation_id": "citation identifier",
    "stages.display[].citation_page_value": "raw page value as emitted, verbatim (int / string / null)",
    "stages.display[].citation_page_basis": "basis of citation_page_value: PDF_INDEX_0 / PDF_NUMBER_1 / PDF_LABEL / UNKNOWN",
    "stages.display[].viewer_page1": "page handed to the viewer, 1-based, or null; UNKNOWN basis forces null",
    "stages.missing_stages": "stages with no snapshot at all (explicit; never inferred from an empty array)",
    "citations[].citation_id": "citation identifier",
    "citations[].quote_text": "verbatim quoted text as cited",
    "citations[].chunk_id": "chunk the quote came from, or null",
    "citations[].index_record_id": "index record the quote came from, or null",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class PageSemanticsError(ValueError):
    """Base error: invalid page value / basis / range (exit code 2 upstream)."""


class UnknownBasisError(PageSemanticsError):
    """citation_page_basis is UNKNOWN: conversion is forbidden (R-04)."""


class OutOfRangeError(PageSemanticsError):
    """Page value outside [0, page_count-1] / [1, page_count] (R-05)."""


class UnresolvableLabelError(PageSemanticsError):
    """Label has no entry in the PDF label map: must not be guessed (R-03)."""


class SchemaValidationError(PageSemanticsError):
    """Instance fails the frozen JSON Schema (incl. unknown fields).

    ``errors`` is the list of human-readable ``jsonschema`` messages
    (``<json-pointer>: <message>``), sorted by path for determinism.
    """

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = list(errors) if errors else [message]


class BundleValidationError(PageSemanticsError):
    """Bundle fails a runtime (cross-field) rule the schema cannot express.

    ``errors`` lists every collected violation (validation collects all
    of them instead of failing on the first, so one run reports the whole
    picture). ``code`` is a stable machine tag, e.g.
    ``INPUT_HASH_MISMATCH`` for a document-hash mismatch.
    """

    def __init__(self, message: str, errors: list[str] | None = None,
                 code: str | None = None):
        super().__init__(message)
        self.errors = list(errors) if errors else [message]
        self.code = code


# ---------------------------------------------------------------------------
# Schema loading / validation (frozen files, loaded as-is)
# ---------------------------------------------------------------------------

_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema_file(path: Path) -> dict:
    key = str(path)
    if key not in _SCHEMA_CACHE:
        with open(path, encoding="utf-8") as fh:
            _SCHEMA_CACHE[key] = json.load(fh)
    return copy.deepcopy(_SCHEMA_CACHE[key])


def load_bundle_schema() -> dict:
    """Return a deep copy of the frozen ``pagetrace.bundle/v1`` schema."""
    return _load_schema_file(BUNDLE_SCHEMA_PATH)


def load_report_schema() -> dict:
    """Return a deep copy of the frozen ``pagetrace.report/v1`` schema."""
    return _load_schema_file(REPORT_SCHEMA_PATH)


def validate_against_schema(instance: dict, schema: dict,
                            kind: str) -> None:
    """Validate *instance* against *schema* (Draft 2020-12).

    Raises :class:`SchemaValidationError` listing every violation, sorted
    by JSON pointer. Unknown fields are rejected here because both frozen
    schemas set ``additionalProperties: false`` on every object.
    """
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(instance),
                    key=lambda e: (list(e.absolute_path), e.message))
    if errors:
        messages = [
            f"{'/' + '/'.join(str(p) for p in e.absolute_path) if e.absolute_path else '<root>'}: {e.message}"
            for e in errors
        ]
        raise SchemaValidationError(
            f"{kind} fails schema validation ({len(messages)} error(s)): "
            + "; ".join(messages),
            errors=messages,
        )


def validate_bundle_schema(instance: dict) -> None:
    """Validate a bundle instance against the frozen bundle schema.

    Checks the schema identifier first, so a wrong version (e.g.
    ``pagetrace.bundle/v2`` or a report instance) is rejected with a
    clear message before any field-level detail.
    """
    if not isinstance(instance, dict):
        raise SchemaValidationError(
            f"bundle must be a JSON object, got {type(instance).__name__}")
    if instance.get("schema") != BUNDLE_SCHEMA_ID:
        raise SchemaValidationError(
            f"schema must be exactly {BUNDLE_SCHEMA_ID!r}, "
            f"got {instance.get('schema')!r}")
    validate_against_schema(instance, load_bundle_schema(), "bundle")


def validate_report_schema(instance: dict) -> None:
    """Validate a report instance against the frozen report schema."""
    if not isinstance(instance, dict):
        raise SchemaValidationError(
            f"report must be a JSON object, got {type(instance).__name__}")
    if instance.get("schema") != REPORT_SCHEMA_ID:
        raise SchemaValidationError(
            f"schema must be exactly {REPORT_SCHEMA_ID!r}, "
            f"got {instance.get('schema')!r}")
    validate_against_schema(instance, load_report_schema(), "report")


# ---------------------------------------------------------------------------
# Frozen pure page semantics (T001 reference implementation, verbatim
# behaviour; R-01–R-10, docs/PAGE_SEMANTICS.md §2/§6).
# ---------------------------------------------------------------------------

def _require_int(value, field: str) -> int:
    # JSON `true` is an int subclass in Python; a bool is never a page (F-14).
    if isinstance(value, bool) or not isinstance(value, int):
        raise PageSemanticsError(f"{field} must be an integer, got {value!r}")
    return value


def _check_index0(index0: int, page_count: int) -> int:
    if not 0 <= index0 <= page_count - 1:
        raise OutOfRangeError(
            f"pdf_page_index0={index0} out of range [0, {page_count - 1}]"
        )
    return index0


def _check_number1(number1: int, page_count: int) -> int:
    if not 1 <= number1 <= page_count:
        raise OutOfRangeError(
            f"1-based page number={number1} out of range [1, {page_count}]"
        )
    return number1


def to_number1(index0: int, page_count: int) -> int:
    """R-01: the ONLY 0-based -> 1-based conversion is +1."""
    _require_int(index0, "pdf_page_index0")
    return _check_index0(index0, page_count) + 1


def to_index0(number1: int, page_count: int) -> int:
    """R-02: the ONLY 1-based -> 0-based conversion is -1."""
    _require_int(number1, "pdf_page_number1")
    return _check_number1(number1, page_count) - 1


def to_viewer1(index0: int, page_count: int) -> int:
    """R-01/R-06: viewer target is 1-based, strictly index0 + 1."""
    return to_number1(index0, page_count)


def viewer_to_index0(viewer_page1: int, page_count: int) -> int:
    """R-02: viewer_page1 0 is invalid; anything else is -1, range-checked."""
    _require_int(viewer_page1, "viewer_page1")
    return _check_number1(viewer_page1, page_count) - 1


def label_to_index0(label, label_map: dict) -> int:
    """R-03: labels are looked up, never arithmetically converted."""
    if not isinstance(label, str):
        raise PageSemanticsError(f"pdf_page_label must be a string, got {label!r}")
    if label not in label_map:
        raise UnresolvableLabelError(f"label {label!r} has no entry in the PDF label map")
    return label_map[label]


def resolve_citation_to_index0(value, basis: str, page_count: int,
                               label_map: dict | None = None) -> int:
    """Resolve an external citation page value to canonical pdf_page_index0.

    R-04: UNKNOWN basis raises UnknownBasisError and is never converted.
    R-08: value/basis type agreement is enforced (int for INDEX_0/NUMBER_1,
    str for LABEL). A ``None`` value means "the source gave no page value"
    and is the caller's missing-data signal, not a page: it raises
    :class:`PageSemanticsError` here rather than being guessed as 0.
    Exception (T013 P2-03): with basis ``PDF_LABEL`` and no label map,
    :class:`UnresolvableLabelError` is raised even for a ``None`` value —
    the missing map is the more specific failure, matching the T001
    frozen reference implementation in ``tests/unit/test_page_semantics.py``.
    """
    if basis == "UNKNOWN":
        raise UnknownBasisError(
            "citation_page_basis is UNKNOWN: value must be kept verbatim, "
            "never converted (UNKNOWN_PAGE_BASIS)"
        )
    # T013 P2-03: the label-map check comes before the None guard. The
    # T001 reference implementation raises UnresolvableLabelError for
    # (None, PDF_LABEL, no map); the old order raised the base
    # PageSemanticsError here instead. With a map present, a None value
    # is still the plain null-value error below.
    if basis == "PDF_LABEL" and label_map is None:
        raise UnresolvableLabelError("no PDF label map available")
    if value is None:
        raise PageSemanticsError(
            f"citation_page_value is null for basis {basis}: no page value "
            "was given; missing must not be defaulted to 0 (R-07)"
        )
    if basis == "PDF_INDEX_0":
        _require_int(value, "citation_page_value")
        return _check_index0(value, page_count)
    if basis == "PDF_NUMBER_1":
        _require_int(value, "citation_page_value")
        return _check_number1(value, page_count) - 1
    if basis == "PDF_LABEL":
        if label_map is None:
            raise UnresolvableLabelError("no PDF label map available")
        return label_to_index0(value, label_map)
    raise PageSemanticsError(f"unknown citation_page_basis {basis!r}")


def validate_source_pages0(indices, page_count: int) -> list[int]:
    """R-05/R-07: source_page_indices0 must be sorted, de-duplicated,
    non-negative and in range. Missing (None) is NOT an empty list."""
    if indices is None:
        raise PageSemanticsError("source_page_indices0 is missing, not empty")
    if not isinstance(indices, list) or any(
        isinstance(v, bool) or not isinstance(v, int) for v in indices
    ):
        raise PageSemanticsError("source_page_indices0 must be a list of integers")
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise PageSemanticsError(
            f"source_page_indices0 must be sorted and de-duplicated, got {indices!r}"
        )
    for v in indices:
        _check_index0(v, page_count)
    return list(indices)


def sha256_hex(data: bytes) -> str:
    """SHA-256 (lowercase hex) of *data* (exact PDF bytes)."""
    return hashlib.sha256(data).hexdigest()
