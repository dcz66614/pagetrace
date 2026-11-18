"""T001 — 页码字段语义与契约冻结：边界 fixture + schema 校验测试。

Frozen reference implementation (pure functions, no I/O, no PDF parsing).
Source of truth: PROJECT_BOOK.md v1.0.0 §4.1 (conversion rules), §5, §6.2–§6.4,
and docs/PAGE_SEMANTICS.md (rules R-01–R-10).

These helpers are the frozen semantics. When T003+ moves them into the real
``pagetrace`` package, their behaviour must not change; this file then tests
the package implementation instead of the local copy.

Run:  python -m pytest tests/unit/test_page_semantics.py -q
       (from PACKAGE_ROOT, inside the venv)
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SCHEMA_PATH = PACKAGE_ROOT / "contracts" / "pagetrace.bundle.v1.schema.json"
REPORT_SCHEMA_PATH = PACKAGE_ROOT / "contracts" / "pagetrace.report.v1.schema.json"

# T013 P2-03: the tests below also pin the *production* resolver's
# boundary exception type against the frozen reference implementation
# in this file; src/ is inserted first as a source-checkout fallback.
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.contracts import (  # noqa: E402
    PageSemanticsError as ProdPageSemanticsError,
)
from pagetrace.contracts import (  # noqa: E402
    UnresolvableLabelError as ProdUnresolvableLabelError,
)
from pagetrace.contracts import (  # noqa: E402
    resolve_citation_to_index0 as prod_resolve_citation_to_index0,
)

try:
    import jsonschema
except ImportError:  # pragma: no cover - venv always provides it (dev dep)
    jsonschema = None

PAGE_COUNT = 8  # fixtures use an 8-page PDF, as in PROJECT_BOOK §6.2
SHA256_HEX = "a" * 64
LABEL_MAP = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "A-3": 4, "7": 0}


# ---------------------------------------------------------------------------
# Frozen reference implementation (PROJECT_BOOK §4.1, PAGE_SEMANTICS.md R-01–R-10)
# ---------------------------------------------------------------------------

class PageSemanticsError(ValueError):
    """Base error: invalid page value / basis / range (exit code 2 upstream)."""


class UnknownBasisError(PageSemanticsError):
    """citation_page_basis is UNKNOWN: conversion is forbidden (R-04)."""


class OutOfRangeError(PageSemanticsError):
    """Page value outside [0, page_count-1] / [1, page_count] (R-05)."""


class UnresolvableLabelError(PageSemanticsError):
    """Label has no entry in the PDF label map: must not be guessed (R-03)."""


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
    str for LABEL).
    """
    if basis == "UNKNOWN":
        raise UnknownBasisError(
            "citation_page_basis is UNKNOWN: value must be kept verbatim, "
            "never converted (UNKNOWN_PAGE_BASIS)"
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


# ---------------------------------------------------------------------------
# Fixture helpers: valid bundle / report instances (PROJECT_BOOK §6.2)
# ---------------------------------------------------------------------------

def valid_bundle() -> dict:
    return {
        "schema": "pagetrace.bundle/v1",
        "case_id": "sample-offset-display-001",
        "document": {
            "file_name": "sample.pdf",
            "sha256": SHA256_HEX,
            "page_count": PAGE_COUNT,
        },
        "page_semantics": {
            "canonical_field": "pdf_page_index0",
            "index_base": 0,
            "viewer_base": 1,
        },
        "stages": {
            "extraction": [
                {"pdf_page_index0": 6, "text_state": "TEXT",
                 "text_sha256": SHA256_HEX},
            ],
            "chunking": [
                {"chunk_id": "c-17", "source_page_indices0": [6],
                 "text_sha256": SHA256_HEX},
            ],
            "indexing": [
                {"record_id": "v-17", "source_page_indices0": [6],
                 "pdf_page_label": "7"},
            ],
            "display": [
                {"citation_id": "cite-17", "citation_page_value": 6,
                 "citation_page_basis": "PDF_INDEX_0", "viewer_page1": 6},
            ],
            "missing_stages": [],
        },
        "citations": [
            {"citation_id": "cite-17", "quote_text": "引用中的原文片段",
             "chunk_id": "c-17", "index_record_id": "v-17"},
        ],
    }


def valid_report() -> dict:
    return {
        "schema": "pagetrace.report/v1",
        "case_id": "sample-offset-display-001",
        "document": {
            "file_name": "sample.pdf",
            "sha256": SHA256_HEX,
            "page_count": PAGE_COUNT,
        },
        "tool": {"name": "pagetrace", "version": "0.1.0"},
        "results": [
            {
                "citation_id": "cite-17",
                "quote_sha256": hashlib.sha256("引用中的原文片段".encode()).hexdigest(),
                "citation_page_value": 6,
                "citation_page_basis": "PDF_INDEX_0",
                "candidate_source_pages0": [6],
                "expected_source_pages0": [6],
                "observed_page_value": 6,
                "correct_pdf_page_number1": [7],
                "correct_viewer_page1": [7],
                "verdict": "FAIL_PAGE_OFFSET",
                "fault_type": "PAGE_OFFSET",
                "first_fault_stage": "display",
                "evidence": [
                    {"stage": "display", "field": "viewer_page1",
                     "upstream_value": 6, "downstream_value": 6,
                     "note": "display passed 0-based 6 to a 1-based viewer; "
                             "correct viewer_page1 is 7"},
                ],
            },
        ],
        "summary": {
            "total_citations": 1,
            "pass_count": 0,
            "fail_count": 1,
            "unknown_count": 0,
            "ambiguous_count": 0,
            "normalized_result_sha256": SHA256_HEX,
        },
    }


@pytest.fixture(scope="module")
def bundle_schema():
    return json.loads(BUNDLE_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report_schema():
    return json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(instance: dict, schema: dict) -> None:
    if jsonschema is None:  # pragma: no cover
        pytest.skip("jsonschema not installed")
    validator = jsonschema.validators.validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(instance)


# ---------------------------------------------------------------------------
# F-01–F-07: +1 / -1 only, bounds, viewer is 1-based only
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "index0, expected_number1",
    [(0, 1), (1, 2), (6, 7), (7, 8)],  # F-01, F-02, F-03
    ids=["F-01-first-page-index0-0", "index0-1", "F-02-spec-example-index0-6",
         "F-03-last-page-index0-7"],
)
def test_to_number1_is_plus_one_only(index0, expected_number1):
    assert to_number1(index0, PAGE_COUNT) == expected_number1
    assert to_viewer1(index0, PAGE_COUNT) == expected_number1


@pytest.mark.parametrize(
    "index0",
    [-1, 8, 9, 100],  # F-04 (-1), F-03 (8 == page_count)
    ids=["F-04-index0-minus-1", "F-03-index0-8-eq-page-count",
         "index0-9", "index0-100"],
)
def test_to_number1_rejects_out_of_range(index0):
    with pytest.raises(OutOfRangeError):
        to_number1(index0, PAGE_COUNT)


@pytest.mark.parametrize(
    "viewer",
    [0, 9, 100],  # F-05 (0), F-06 (9 > page_count)
    ids=["F-05-viewer-0-invalid", "F-06-viewer-9-out-of-range", "viewer-100"],
)
def test_viewer_page1_rejects_zero_and_out_of_range(viewer):
    with pytest.raises(OutOfRangeError):
        viewer_to_index0(viewer, PAGE_COUNT)


@pytest.mark.parametrize(
    "viewer, expected_index0",
    [(1, 0), (7, 6), (8, 7)],  # F-07
    ids=["F-07-viewer-1-to-index0-0", "viewer-7-to-index0-6",
         "viewer-8-to-index0-7"],
)
def test_viewer_to_index0_is_minus_one_only(viewer, expected_index0):
    assert viewer_to_index0(viewer, PAGE_COUNT) == expected_index0


def test_spec_section_6_2_example_recomputed():
    """PROJECT_BOOK §6.2: value 6 (PDF_INDEX_0) shown as viewer 6 is wrong;
    the correct viewer_page1 is 7."""
    index0 = resolve_citation_to_index0(6, "PDF_INDEX_0", PAGE_COUNT)
    assert index0 == 6
    assert to_viewer1(index0, PAGE_COUNT) == 7
    assert to_viewer1(index0, PAGE_COUNT) != 6


# ---------------------------------------------------------------------------
# F-08–F-11: labels are looked up, never converted; UNKNOWN never converts
# ---------------------------------------------------------------------------

def test_roman_label_iv_is_lookup_not_arithmetic():  # F-08
    assert label_to_index0("iv", LABEL_MAP) == 3
    assert to_viewer1(label_to_index0("iv", LABEL_MAP), PAGE_COUNT) == 4
    with pytest.raises(PageSemanticsError):
        label_to_index0("iv", {})  # no map: must not fall back to arithmetic
    with pytest.raises(PageSemanticsError):
        resolve_citation_to_index0("iv", "PDF_LABEL", PAGE_COUNT, label_map={})


def test_label_a3_lookup():  # F-09
    assert label_to_index0("A-3", LABEL_MAP) == 4
    assert resolve_citation_to_index0("A-3", "PDF_LABEL", PAGE_COUNT, LABEL_MAP) == 4
    with pytest.raises(UnresolvableLabelError):
        label_to_index0("ix", LABEL_MAP)  # unknown label: no guessing


def test_label_string_7_is_not_number_7():  # F-10
    # The label "7" belongs to physical page index 0 in this fixture's map;
    # it must never be read as 1-based page 7 or 0-based index 7.
    assert resolve_citation_to_index0("7", "PDF_LABEL", PAGE_COUNT, LABEL_MAP) == 0
    assert to_viewer1(0, PAGE_COUNT) == 1
    assert resolve_citation_to_index0("7", "PDF_LABEL", PAGE_COUNT, LABEL_MAP) != 6
    with pytest.raises(PageSemanticsError):
        # A string value with a numeric basis is a type error (R-08).
        resolve_citation_to_index0("7", "PDF_INDEX_0", PAGE_COUNT)


def test_unknown_basis_never_converts():  # F-11
    with pytest.raises(UnknownBasisError):
        resolve_citation_to_index0(6, "UNKNOWN", PAGE_COUNT)
    with pytest.raises(UnknownBasisError):
        resolve_citation_to_index0("iv", "UNKNOWN", PAGE_COUNT)
    with pytest.raises(UnknownBasisError):
        resolve_citation_to_index0(None, "UNKNOWN", PAGE_COUNT)


def test_production_none_label_without_map_raises_unresolvable_label():
    """T013 P2-03: the production resolver must match the frozen
    reference on the boundary input (None, PDF_LABEL, no label map):
    UnresolvableLabelError, not the base PageSemanticsError the old
    None guard raised. With a map present, a None value is still the
    plain null-value error."""
    with pytest.raises(ProdUnresolvableLabelError):
        prod_resolve_citation_to_index0(
            None, "PDF_LABEL", PAGE_COUNT, label_map=None)
    # Reference implementation agrees on this input too.
    with pytest.raises(UnresolvableLabelError):
        resolve_citation_to_index0(
            None, "PDF_LABEL", PAGE_COUNT, label_map=None)
    with pytest.raises(ProdPageSemanticsError):
        prod_resolve_citation_to_index0(
            None, "PDF_LABEL", PAGE_COUNT, label_map=LABEL_MAP)


@pytest.mark.parametrize(
    "basis, value",
    [("PDF_NUMBER_1", 0), ("PDF_NUMBER_1", 9)],  # F-15
    ids=["F-15-number1-0-invalid", "number1-9-out-of-range"],
)
def test_pdf_number_1_rejects_zero_and_overflow(basis, value):
    with pytest.raises(OutOfRangeError):
        resolve_citation_to_index0(value, basis, PAGE_COUNT)


def test_pdf_number_1_resolves():
    assert resolve_citation_to_index0(7, "PDF_NUMBER_1", PAGE_COUNT) == 6
    assert resolve_citation_to_index0(1, "PDF_NUMBER_1", PAGE_COUNT) == 0


# ---------------------------------------------------------------------------
# F-12–F-14: source page sets, cross-page, non-int impostors
# ---------------------------------------------------------------------------

def test_cross_page_source_set():  # F-12
    pages = validate_source_pages0([6, 7], PAGE_COUNT)
    assert pages == [6, 7]
    assert [to_viewer1(p, PAGE_COUNT) for p in pages] == [7, 8]


@pytest.mark.parametrize(
    "indices",
    [[7, 6], [6, 6], [-1], [8], [0, 8], [6, 5]],  # F-13
    ids=["F-13-unsorted", "F-13-duplicate", "F-13-negative",
         "F-13-overflow", "F-13-overflow-tail", "F-13-unsorted-2"],
)
def test_source_pages0_rejects_unsorted_duplicate_out_of_range(indices):
    with pytest.raises(PageSemanticsError):
        validate_source_pages0(indices, PAGE_COUNT)


def test_source_pages0_missing_is_not_empty():  # R-07
    with pytest.raises(PageSemanticsError):
        validate_source_pages0(None, PAGE_COUNT)
    assert validate_source_pages0([], PAGE_COUNT) == []  # verified-empty ≠ missing


@pytest.mark.parametrize(
    "bad",
    [True, False, 6.0, 6.5, "6", None],  # F-14
    ids=["F-14-bool-True", "F-14-bool-False", "F-14-float-6.0",
         "F-14-float-6.5", "F-14-string-6", "F-14-None"],
)
def test_non_integer_page_values_rejected(bad):
    with pytest.raises(PageSemanticsError):
        to_number1(bad, PAGE_COUNT)
    with pytest.raises(PageSemanticsError):
        resolve_citation_to_index0(bad, "PDF_INDEX_0", PAGE_COUNT)


# ---------------------------------------------------------------------------
# Schema validation: bundle + report, incl. bare `page` rejection (F-16)
# ---------------------------------------------------------------------------

def test_schemas_are_valid_draft_2020_12(bundle_schema, report_schema):
    assert bundle_schema["$schema"].endswith("draft/2020-12/schema")
    assert report_schema["$schema"].endswith("draft/2020-12/schema")
    if jsonschema is not None:
        jsonschema.validators.validator_for(bundle_schema).check_schema(bundle_schema)
        jsonschema.validators.validator_for(report_schema).check_schema(report_schema)


def test_packaged_schemas_match_frozen_contracts():
    """T013 P2-08: the schemas shipped inside the installed package
    (src/pagetrace/schemas/) must be byte-identical to the frozen
    contracts/*.json — two copies, one frozen content. The production
    loader prefers the packaged copy (contracts.py _schema_path)."""
    packaged_dir = PACKAGE_ROOT / "src" / "pagetrace" / "schemas"
    for name in ("pagetrace.bundle.v1.schema.json",
                 "pagetrace.report.v1.schema.json"):
        assert (packaged_dir / name).read_bytes() == \
            (PACKAGE_ROOT / "contracts" / name).read_bytes(), name


def test_production_loader_resolves_frozen_schemas():
    """T013 P2-08: contracts.py resolves both schemas to files whose
    bytes are the frozen contracts (packaged copy preferred, repo copy
    as fallback) — so a wheel install validates against the same
    frozen schemas as a source checkout."""
    from pagetrace.contracts import BUNDLE_SCHEMA_PATH as prod_bundle
    from pagetrace.contracts import REPORT_SCHEMA_PATH as prod_report
    assert prod_bundle.read_bytes() == \
        (PACKAGE_ROOT / "contracts"
         / "pagetrace.bundle.v1.schema.json").read_bytes()
    assert prod_report.read_bytes() == \
        (PACKAGE_ROOT / "contracts"
         / "pagetrace.report.v1.schema.json").read_bytes()


def test_valid_bundle_passes_schema(bundle_schema):
    validate(valid_bundle(), bundle_schema)


def test_valid_report_passes_schema(report_schema):
    validate(valid_report(), report_schema)


def test_bundle_rejects_bare_page_field(bundle_schema):  # F-16
    bad = valid_bundle()
    bad["page"] = 6  # the ambiguous bare field: forbidden everywhere
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, bundle_schema)
    bad2 = valid_bundle()
    bad2["stages"]["display"][0]["page"] = 6
    with pytest.raises(jsonschema.ValidationError):
        validate(bad2, bundle_schema)


def test_report_rejects_bare_page_field(report_schema):  # F-16
    bad = valid_report()
    bad["results"][0]["page"] = 7
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, report_schema)


def test_bundle_rejects_viewer_page_zero(bundle_schema):
    bad = valid_bundle()
    bad["stages"]["display"][0]["viewer_page1"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, bundle_schema)


def test_bundle_unknown_basis_forces_viewer_null(bundle_schema):
    bad = valid_bundle()
    bad["stages"]["display"][0]["citation_page_basis"] = "UNKNOWN"
    bad["stages"]["display"][0]["viewer_page1"] = 6  # R-04: must be null
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, bundle_schema)
    ok = valid_bundle()
    ok["stages"]["display"][0]["citation_page_basis"] = "UNKNOWN"
    ok["stages"]["display"][0]["viewer_page1"] = None
    ok["stages"]["display"][0]["citation_page_value"] = 6
    validate(ok, bundle_schema)


def test_bundle_rejects_bad_sha_and_schema_id(bundle_schema):
    bad = valid_bundle()
    bad["document"]["sha256"] = "XYZ"  # not 64 lowercase hex
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, bundle_schema)
    bad2 = valid_bundle()
    bad2["schema"] = "pagetrace.bundle/v2"
    with pytest.raises(jsonschema.ValidationError):
        validate(bad2, bundle_schema)


def test_bundle_rejects_duplicate_source_pages(bundle_schema):
    bad = valid_bundle()
    bad["stages"]["chunking"][0]["source_page_indices0"] = [6, 6]
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, bundle_schema)


def test_report_rejects_bad_verdict_and_mismatched_schema(report_schema):
    bad = valid_report()
    bad["results"][0]["verdict"] = "FAIL_SOMETHING_ELSE"
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, report_schema)
    bad2 = valid_report()
    bad2["schema"] = "pagetrace.report/v2"
    with pytest.raises(jsonschema.ValidationError):
        validate(bad2, report_schema)


def test_report_correct_viewer_equals_correct_number():
    """R-01: correct_viewer_page1 must equal correct_pdf_page_number1."""
    rep = valid_report()
    r = rep["results"][0]
    assert r["correct_viewer_page1"] == r["correct_pdf_page_number1"] == [7]
