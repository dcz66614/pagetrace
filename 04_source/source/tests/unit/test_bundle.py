"""T010 — Bundle normalisation & schema validation (P026).

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/unit/test_bundle.py -q

Covers (TASK-010, PROJECT_BOOK.md v1.0.0 §6.2–§6.3,
docs/PAGE_SEMANTICS.md R-01–R-10, T001 frozen schemas):

* all 48 T002 bundles (``fixtures/bundles/*.trace.json``) parse and
  validate — they are real legal bundles, including ones that carry
  deliberate *fault data* (offset display values, missing records,
  null viewer pages, dangling references). Fault data is accepted and
  exposed; only structural breakage is rejected;
* 9 valid variant fixtures + 44 invalid fixtures in
  ``tests/unit/fixtures_bundle/`` (schema-version errors, bare ``page``
  fields, unknown fields, duplicate ids, out-of-range pages, value /
  basis type mismatches, bool/float impostors, lying ``missing_stages``,
  bad hashes, bad ``page_count`` / ``case_id``);
* raw-value preservation (no implicit 0/1-based conversion, no
  defaulting of null to 0, deep-copy isolation);
* missing-stage explicitness (``missing_stages`` / ``empty_stages`` /
  ``is_stage_present``; R-07 missing != empty != zero);
* document-hash verification against real PDF bytes
  (``INPUT_HASH_MISMATCH``);
* the frozen conversion helpers (spot-checks of T001 F-01–F-16) and
  the fixed unknown-field policy (``"reject"``).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"
T010_FIXTURES = Path(__file__).resolve().parent / "fixtures_bundle"

# Production package lives in src/ (T013 P2-08: the top-level stub is gone);
# src/ must be first on sys.path when running from a checkout.
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace import contracts as C  # noqa: E402
from pagetrace.trace_bundle import (  # noqa: E402
    TraceBundle,
    load_bundle,
    load_bundle_file,
    parse_bundle,
    parse_bundle_json,
)

SHA = "a" * 64
PAGE_COUNT = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def valid_bundle() -> dict:
    """Minimal valid 8-page bundle (same shape as T001 valid_bundle())."""
    return {
        "schema": "pagetrace.bundle/v1",
        "case_id": "sample-offset-display-001",
        "document": {"file_name": "sample.pdf", "sha256": SHA,
                     "page_count": PAGE_COUNT},
        "page_semantics": {"canonical_field": "pdf_page_index0",
                           "index_base": 0, "viewer_base": 1},
        "stages": {
            "extraction": [
                {"pdf_page_index0": 6, "text_state": "TEXT",
                 "text_sha256": SHA},
            ],
            "chunking": [
                {"chunk_id": "c-17", "source_page_indices0": [6],
                 "text_sha256": SHA},
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


def t002_bundle_paths() -> list[Path]:
    return sorted((FIXTURES / "bundles").glob("*.trace.json"))


def t010_fixture_paths(prefix: str) -> list[Path]:
    return sorted(T010_FIXTURES.glob(f"{prefix}-*.json"))


# ---------------------------------------------------------------------------
# 1. All 48 T002 bundles are legal and parse
# ---------------------------------------------------------------------------

def test_t002_fixture_count_is_48():
    assert len(t002_bundle_paths()) == 48


@pytest.mark.parametrize("path", t002_bundle_paths(), ids=lambda p: p.stem)
def test_t002_bundle_parses(path):
    bundle = load_bundle_file(path)
    assert bundle.schema == "pagetrace.bundle/v1"
    assert bundle.case_id == path.stem.replace(".trace", "")
    assert bundle.page_count >= 1
    # Raw document preserved exactly as in the file.
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert bundle.to_dict() == raw
    assert bundle.document_sha256 == raw["document"]["sha256"]
    assert bundle.file_name == raw["document"]["file_name"]
    # T002 never drops a whole stage: missing_stages is always [].
    assert bundle.missing_stages == []
    assert bundle.present_stages == ["extraction", "chunking",
                                     "indexing", "display"]
    assert bundle.empty_stages == []


@pytest.mark.parametrize("path", t002_bundle_paths(), ids=lambda p: p.stem)
def test_t002_bundle_page_count_matches_spec(path):
    bundle = load_bundle_file(path)
    spec = json.loads(
        (FIXTURES / "specs" / f"{bundle.case_id}.json").read_text(
            encoding="utf-8"))
    assert bundle.page_count == spec["page_count"]
    assert bundle.document_sha256 == spec["pdf_sha256"]
    # Extraction covers every physical page, in order — except mm-ext-03,
    # whose fault IS an omitted extraction record (page 4 of 7): the
    # parser records the gap instead of rejecting the bundle.
    if bundle.case_id == "mm-ext-03":
        assert bundle.missing_extraction_pages == [4]
    else:
        assert bundle.missing_extraction_pages == []
        assert sorted(bundle.extraction_by_index) == list(
            range(bundle.page_count))


@pytest.mark.parametrize("path", t002_bundle_paths(), ids=lambda p: p.stem)
def test_t002_bundle_document_hash_matches_real_pdf(path):
    bundle = load_bundle_file(path)
    pdf_path = FIXTURES / "pdfs" / bundle.file_name
    assert pdf_path.exists()
    bundle.verify_document_hash_file(pdf_path)
    assert bundle.document_hash_matches(pdf_path.read_bytes())


# ---------------------------------------------------------------------------
# 2. Fault data in T002 bundles is ACCEPTED (and exposed), not rejected
# ---------------------------------------------------------------------------

def test_mm_chk_05_dangling_chunk_ref_is_exposed_not_rejected():
    bundle = load_bundle_file(FIXTURES / "bundles" / "mm-chk-05.trace.json")
    assert bundle.unresolved_chunk_refs == ["c-fault"]
    assert bundle.citation("cite-fault")["chunk_id"] == "c-fault"
    assert bundle.chunk_record("c-fault") is None


def test_mm_idx_08_dangling_index_ref_is_exposed_not_rejected():
    bundle = load_bundle_file(FIXTURES / "bundles" / "mm-idx-08.trace.json")
    assert bundle.unresolved_index_refs == ["v-fault"]
    assert bundle.index_record("v-fault") is None


def test_mm_dsp_10_missing_display_record_is_exposed_not_rejected():
    bundle = load_bundle_file(FIXTURES / "bundles" / "mm-dsp-10.trace.json")
    assert bundle.citations_without_display == ["cite-fault"]
    assert bundle.display_record("cite-fault") is None
    with pytest.raises(C.PageSemanticsError):
        bundle.raw_citation_page_value("cite-fault")


def test_mm_dsp_11_null_display_value_preserved_not_defaulted():
    bundle = load_bundle_file(FIXTURES / "bundles" / "mm-dsp-11.trace.json")
    rec = bundle.display_record("cite-fault")
    assert rec["citation_page_value"] is None
    assert rec["viewer_page1"] is None
    assert rec["citation_page_basis"] == "PDF_NUMBER_1"
    # Null is missing, not 0: resolving must refuse, not guess page 0.
    with pytest.raises(C.PageSemanticsError):
        bundle.resolve_citation_to_index0("cite-fault")


def test_mm_dsp_12_null_viewer_preserved():
    bundle = load_bundle_file(FIXTURES / "bundles" / "mm-dsp-12.trace.json")
    rec = bundle.display_record("cite-fault")
    assert rec["citation_page_value"] == 6
    assert rec["viewer_page1"] is None


def test_po_dsp_10_offset_value_preserved_verbatim():
    # Display passed 0-based 1 to a 1-based viewer (correct viewer is 2).
    # The parser keeps the raw (wrong) values; judging them is T004's job.
    bundle = load_bundle_file(FIXTURES / "bundles" / "po-dsp-10.trace.json")
    assert bundle.raw_citation_page_value("cite-fault") == 1
    assert isinstance(bundle.raw_citation_page_value("cite-fault"), int)
    assert bundle.display_record("cite-fault")["viewer_page1"] == 1
    assert bundle.resolve_citation_to_index0("cite-fault") == 1
    assert bundle.correct_viewer_page1("cite-fault") == 2


def test_po_dsp_12_label_string_7_is_not_number_7():
    # Label "7" looked up in this PDF's label map; never read as page 7.
    bundle = load_bundle_file(FIXTURES / "bundles" / "po-dsp-12.trace.json")
    value = bundle.raw_citation_page_value("cite-fault")
    assert value == "7" and isinstance(value, str)
    assert bundle.display_record("cite-fault")["viewer_page1"] == 7
    index0 = bundle.resolve_citation_to_index0("cite-fault")
    assert index0 == bundle.label_map["7"]
    assert bundle.correct_viewer_page1("cite-fault") == index0 + 1
    assert bundle.correct_viewer_page1("cite-fault") != 7


# ---------------------------------------------------------------------------
# 3. Valid variant fixtures (9)
# ---------------------------------------------------------------------------

def test_valid_fixture_count_is_9():
    assert len(t010_fixture_paths("valid")) == 9


@pytest.mark.parametrize("path", t010_fixture_paths("valid"),
                         ids=lambda p: p.stem)
def test_valid_fixture_parses(path):
    bundle = load_bundle_file(path)
    assert bundle.schema == "pagetrace.bundle/v1"
    assert bundle.to_dict() == json.loads(
        path.read_text(encoding="utf-8"))


def test_valid_missing_chunking_is_explicit():
    bundle = load_bundle_file(
        T010_FIXTURES / "valid-missing-chunking.json")
    assert bundle.missing_stages == ["chunking"]
    assert bundle.is_stage_missing("chunking")
    assert not bundle.is_stage_present("chunking")
    assert bundle.present_stages == ["extraction", "indexing", "display"]
    assert bundle.chunk_record("c-17") is None


def test_valid_missing_display_and_extraction():
    bundle = load_bundle_file(
        T010_FIXTURES / "valid-missing-display-extraction.json")
    assert bundle.missing_stages == ["extraction", "display"]
    assert bundle.missing_extraction_pages == list(range(PAGE_COUNT))
    assert bundle.citations_without_display == ["cite-17"]


def test_valid_unknown_basis_kept_verbatim_never_converted():
    bundle = load_bundle_file(T010_FIXTURES / "valid-unknown-basis.json")
    assert bundle.raw_citation_page_value("cite-17") == 6
    assert bundle.raw_citation_page_basis("cite-17") == "UNKNOWN"
    assert bundle.display_record("cite-17")["viewer_page1"] is None
    with pytest.raises(C.UnknownBasisError):
        bundle.resolve_citation_to_index0("cite-17")


def test_valid_label_citation_resolves_by_lookup():
    bundle = load_bundle_file(T010_FIXTURES / "valid-label-citation.json")
    assert bundle.raw_citation_page_value("cite-17") == "iv"
    assert bundle.resolve_citation_to_index0("cite-17") == 3
    assert bundle.correct_viewer_page1("cite-17") == 4
    assert bundle.label_to_index0("iv") == 3
    with pytest.raises(C.UnresolvableLabelError):
        bundle.label_to_index0("ix")


def test_valid_cross_page_source_set_kept_whole():
    bundle = load_bundle_file(T010_FIXTURES / "valid-cross-page.json")
    assert bundle.chunk_record("c-17")["source_page_indices0"] == [6, 7]
    assert bundle.index_record("v-17")["source_page_indices0"] == [6, 7]


def test_valid_empty_source_set_is_not_missing():
    bundle = load_bundle_file(
        T010_FIXTURES / "valid-empty-source-set.json")
    assert bundle.chunk_record("c-17")["source_page_indices0"] == []


def test_valid_first_page_zero_is_a_real_page():
    bundle = load_bundle_file(T010_FIXTURES / "valid-first-page.json")
    assert bundle.raw_citation_page_value("cite-17") == 0
    assert bundle.resolve_citation_to_index0("cite-17") == 0
    assert bundle.correct_viewer_page1("cite-17") == 1


def test_valid_empty_chunking_array_is_not_clean():
    # Present-but-empty: recorded in empty_stages, never "checked clean".
    bundle = load_bundle_file(
        T010_FIXTURES / "valid-empty-chunking-array.json")
    assert bundle.is_stage_present("chunking")
    assert bundle.missing_stages == []
    assert bundle.empty_stages == ["chunking"]


def test_valid_null_display_value_preserved():
    bundle = load_bundle_file(
        T010_FIXTURES / "valid-null-display-value.json")
    rec = bundle.display_record("cite-17")
    assert rec["citation_page_value"] is None
    assert rec["viewer_page1"] is None


# ---------------------------------------------------------------------------
# 4. Invalid fixtures (44) — every one must be rejected
# ---------------------------------------------------------------------------

def test_invalid_fixture_count_is_44():
    assert len(t010_fixture_paths("inv")) == 44


@pytest.mark.parametrize("path", t010_fixture_paths("inv"),
                         ids=lambda p: p.stem)
def test_invalid_fixture_rejected(path):
    with pytest.raises((C.SchemaValidationError, C.BundleValidationError)):
        load_bundle_file(path)


@pytest.mark.parametrize("path", t010_fixture_paths("inv"),
                         ids=lambda p: p.stem)
def test_invalid_fixture_error_names_the_problem(path):
    # The raised error carries a non-empty, collected .errors list.
    with pytest.raises((C.SchemaValidationError, C.BundleValidationError)) as excinfo:
        load_bundle_file(path)
    assert getattr(excinfo.value, "errors", None)


# ---------------------------------------------------------------------------
# 5. Schema version / unknown fields (hard assertions, in-code)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_schema", [
    "pagetrace.bundle/v2", "pagetrace.bundle/v1.0", "pagetrace.report/v1",
    "bundle/v1", "", None,
])
def test_schema_version_error_rejected(bad_schema):
    data = valid_bundle()
    if bad_schema is None:
        data.pop("schema")
    else:
        data["schema"] = bad_schema
    with pytest.raises(C.SchemaValidationError):
        parse_bundle(data)


def test_unknown_field_policy_is_fixed_reject():
    assert C.UNKNOWN_FIELD_POLICY == "reject"
    # The frozen schema itself enforces it on every object.
    schema = C.load_bundle_schema()

    def walk(node):
        if isinstance(node, dict):
            # Real object schemas carry type "object"; conditional
            # subschemas (the display record's if/then) only constrain
            # a subset and carry no additionalProperties of their own.
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, node
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(schema)


@pytest.mark.parametrize("field", ["page", "pageNo", "page_no", "pagenum"])
def test_bare_page_field_rejected_anywhere(field):
    data = valid_bundle()
    data[field] = 6
    with pytest.raises(C.SchemaValidationError):
        parse_bundle(data)
    data = valid_bundle()
    data["stages"]["display"][0][field] = 6
    with pytest.raises(C.SchemaValidationError):
        parse_bundle(data)


def test_field_mapping_table_covers_bundle_fields():
    # Every documented mapping key names a real bundle path.
    for dotted in C.FIELD_MAPPING:
        assert dotted.split(".")[0].replace("[]", "") in {
            "schema", "case_id", "document", "page_semantics",
            "stages", "citations"}


# ---------------------------------------------------------------------------
# 6. Raw preservation / no implicit conversion
# ---------------------------------------------------------------------------

def test_no_implicit_conversion_on_parse():
    # INDEX_0 value 6 shown as viewer 6: parser keeps both raw values;
    # the +1 conversion is only available through explicit helpers.
    bundle = parse_bundle(valid_bundle())
    assert bundle.raw_citation_page_value("cite-17") == 6
    assert bundle.display_record("cite-17")["viewer_page1"] == 6
    assert bundle.resolve_citation_to_index0("cite-17") == 6
    assert bundle.correct_viewer_page1("cite-17") == 7
    assert C.to_number1(6, PAGE_COUNT) == 7
    assert C.to_viewer1(6, PAGE_COUNT) == 7
    assert C.viewer_to_index0(7, PAGE_COUNT) == 6


def test_input_mutation_after_parse_does_not_leak_in():
    data = valid_bundle()
    bundle = parse_bundle(data)
    data["stages"]["display"][0]["citation_page_value"] = 999
    data["citations"][0]["quote_text"] = "tampered"
    assert bundle.raw_citation_page_value("cite-17") == 6
    assert bundle.citation("cite-17")["quote_text"] == "引用中的原文片段"


def test_output_mutation_does_not_leak_back():
    bundle = parse_bundle(valid_bundle())
    out = bundle.to_dict()
    out["stages"]["display"][0]["citation_page_value"] = 999
    assert bundle.raw_citation_page_value("cite-17") == 6
    raw = bundle.raw
    raw["document"]["page_count"] = 1
    assert bundle.page_count == PAGE_COUNT


def test_string_7_and_int_7_are_different_observations():
    label_bundle = load_bundle_file(
        T010_FIXTURES / "valid-label-citation.json")
    assert label_bundle.raw_citation_page_value("cite-17") == "7" or \
        label_bundle.raw_citation_page_value("cite-17") == "iv"
    int_bundle = parse_bundle(valid_bundle())
    assert int_bundle.raw_citation_page_value("cite-17") == 6
    assert isinstance(int_bundle.raw_citation_page_value("cite-17"), int)


def test_json_round_trip_is_stable():
    bundle = parse_bundle(valid_bundle())
    reparsed = parse_bundle_json(bundle.to_json())
    assert reparsed.to_dict() == bundle.to_dict()


# ---------------------------------------------------------------------------
# 7. Runtime rules: ranges, duplicates, missing-stage lies, bool/float
# ---------------------------------------------------------------------------

def test_out_of_range_pages_rejected():
    cases = [
        lambda b: b["stages"]["extraction"][0].update(pdf_page_index0=8),
        lambda b: b["stages"]["chunking"][0].update(source_page_indices0=[8]),
        lambda b: b["stages"]["display"][0].update(viewer_page1=9),
        lambda b: b["stages"]["display"][0].update(citation_page_value=8),
        lambda b: b["stages"]["display"][0].update(
            citation_page_basis="PDF_NUMBER_1", citation_page_value=0),
    ]
    for mutate in cases:
        data = valid_bundle()
        mutate(data)
        with pytest.raises((C.SchemaValidationError, C.BundleValidationError)):
            parse_bundle(data)


def test_duplicate_ids_rejected():
    cases = [
        lambda b: b["citations"].append(dict(b["citations"][0])),
        lambda b: b["stages"]["chunking"].append(
            {"chunk_id": "c-17", "source_page_indices0": [0]}),
        lambda b: b["stages"]["indexing"].append(
            {"record_id": "v-17", "source_page_indices0": [0]}),
        lambda b: b["stages"]["display"].append(
            dict(b["stages"]["display"][0])),
        lambda b: b["stages"]["extraction"].append(
            {"pdf_page_index0": 6, "text_state": "TEXT"}),
    ]
    for mutate in cases:
        data = valid_bundle()
        mutate(data)
        with pytest.raises((C.SchemaValidationError, C.BundleValidationError)):
            parse_bundle(data)


def test_unsorted_source_pages_rejected():
    data = valid_bundle()
    data["stages"]["chunking"][0]["source_page_indices0"] = [7, 6]
    with pytest.raises(C.BundleValidationError):
        parse_bundle(data)


def test_missing_stage_lies_rejected():
    data = valid_bundle()
    data["stages"].pop("chunking")  # absent but not listed
    with pytest.raises(C.BundleValidationError):
        parse_bundle(data)
    data = valid_bundle()
    data["stages"]["missing_stages"] = ["chunking"]  # listed but present
    with pytest.raises(C.BundleValidationError):
        parse_bundle(data)


def test_bool_and_float_page_values_rejected():
    for bad in (True, False, 6.0, "6", None):
        # None is allowed by the schema (missing signal) — it must NOT
        # be rejected here; resolve() refuses it instead (tested above).
        data = valid_bundle()
        data["stages"]["display"][0]["citation_page_value"] = bad
        if bad is None:
            bundle = parse_bundle(data)
            assert bundle.raw_citation_page_value("cite-17") is None
        else:
            with pytest.raises(
                    (C.SchemaValidationError, C.BundleValidationError)):
                parse_bundle(data)


def test_value_basis_type_mismatch_rejected():
    data = valid_bundle()
    data["stages"]["display"][0].update(
        citation_page_basis="PDF_LABEL", citation_page_value=7)
    with pytest.raises(C.BundleValidationError):
        parse_bundle(data)
    data = valid_bundle()
    data["stages"]["display"][0].update(
        citation_page_basis="PDF_INDEX_0", citation_page_value="6")
    with pytest.raises(C.BundleValidationError):
        parse_bundle(data)


def test_runtime_errors_are_collected_not_fail_fast():
    # Two independent violations in one bundle -> both reported.
    data = valid_bundle()
    data["stages"]["chunking"][0]["source_page_indices0"] = [7, 6]
    data["stages"]["display"][0]["viewer_page1"] = 9
    with pytest.raises(C.BundleValidationError) as excinfo:
        parse_bundle(data)
    assert len(excinfo.value.errors) >= 2


# ---------------------------------------------------------------------------
# 8. Document hash verification (PROJECT_BOOK §6.3)
# ---------------------------------------------------------------------------

def test_hash_mismatch_rejected_with_code():
    bundle = load_bundle_file(FIXTURES / "bundles" / "du-chk-01.trace.json")
    pdf_bytes = (FIXTURES / "pdfs" / "du-chk-01.pdf").read_bytes()
    assert hashlib.sha256(pdf_bytes).hexdigest() == bundle.document_sha256
    bundle.verify_document_hash(pdf_bytes)
    with pytest.raises(C.BundleValidationError) as excinfo:
        bundle.verify_document_hash(b"not the real pdf")
    assert excinfo.value.code == "INPUT_HASH_MISMATCH"
    assert "INPUT_HASH_MISMATCH" in str(excinfo.value)
    assert not bundle.document_hash_matches(b"not the real pdf")


def test_hash_mismatch_via_file():
    bundle = load_bundle_file(FIXTURES / "bundles" / "du-chk-01.trace.json")
    with pytest.raises(C.BundleValidationError) as excinfo:
        bundle.verify_document_hash_file(
            FIXTURES / "pdfs" / "du-chk-02.pdf")
    assert excinfo.value.code == "INPUT_HASH_MISMATCH"


# ---------------------------------------------------------------------------
# 9. Loading entry points / malformed input
# ---------------------------------------------------------------------------

def test_load_bundle_accepts_dict_json_str_bytes_and_path():
    data = valid_bundle()
    assert parse_bundle(data).case_id == "sample-offset-display-001"
    text = json.dumps(data, ensure_ascii=False)
    assert parse_bundle_json(text).case_id == "sample-offset-display-001"
    assert parse_bundle_json(text.encode("utf-8")).case_id == \
        "sample-offset-display-001"
    assert load_bundle(data).case_id == "sample-offset-display-001"
    assert load_bundle(text).case_id == "sample-offset-display-001"
    assert load_bundle(text.encode("utf-8")).case_id == \
        "sample-offset-display-001"
    path = T010_FIXTURES / "valid-first-page.json"
    assert load_bundle(path).case_id == "sample-offset-display-001"
    assert load_bundle(str(path)).case_id == "sample-offset-display-001"
    assert load_bundle_file(path).case_id == "sample-offset-display-001"


def test_malformed_json_and_non_object_rejected():
    with pytest.raises(C.BundleValidationError):
        parse_bundle_json("{not json")
    with pytest.raises(C.SchemaValidationError):
        parse_bundle([1, 2, 3])
    with pytest.raises(C.BundleValidationError):
        load_bundle_file(PACKAGE_ROOT / "no-such-bundle.json")
    with pytest.raises(TypeError):
        load_bundle(42)


def test_unknown_stage_name_rejected_by_accessors():
    bundle = parse_bundle(valid_bundle())
    with pytest.raises(ValueError):
        bundle.is_stage_present("ocr")


# ---------------------------------------------------------------------------
# 10. Frozen conversion helpers (T001 F-01–F-16 spot checks)
# ---------------------------------------------------------------------------

def test_conversion_helpers_spot_checks():
    assert C.to_number1(0, PAGE_COUNT) == 1          # F-01
    assert C.to_number1(6, PAGE_COUNT) == 7          # F-02
    assert C.to_number1(7, PAGE_COUNT) == 8          # F-03
    assert C.viewer_to_index0(1, PAGE_COUNT) == 0    # F-07
    with pytest.raises(C.OutOfRangeError):
        C.to_number1(-1, PAGE_COUNT)                 # F-04
    with pytest.raises(C.OutOfRangeError):
        C.to_number1(8, PAGE_COUNT)                  # F-03 boundary
    with pytest.raises(C.OutOfRangeError):
        C.viewer_to_index0(0, PAGE_COUNT)            # F-05
    with pytest.raises(C.OutOfRangeError):
        C.viewer_to_index0(9, PAGE_COUNT)            # F-06
    label_map = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "A-3": 4, "7": 0}
    assert C.label_to_index0("iv", label_map) == 3   # F-08
    assert C.label_to_index0("A-3", label_map) == 4  # F-09
    assert C.label_to_index0("7", label_map) == 0    # F-10
    with pytest.raises(C.UnresolvableLabelError):
        C.label_to_index0("ix", label_map)
    with pytest.raises(C.UnknownBasisError):         # F-11
        C.resolve_citation_to_index0(6, "UNKNOWN", PAGE_COUNT)
    assert C.validate_source_pages0([6, 7], PAGE_COUNT) == [6, 7]  # F-12
    with pytest.raises(C.PageSemanticsError):        # F-13
        C.validate_source_pages0([7, 6], PAGE_COUNT)
    with pytest.raises(C.PageSemanticsError):        # F-14 bool
        C.to_number1(True, PAGE_COUNT)
    with pytest.raises(C.PageSemanticsError):        # F-14 float
        C.to_number1(6.0, PAGE_COUNT)
    with pytest.raises(C.OutOfRangeError):           # F-15
        C.resolve_citation_to_index0(0, "PDF_NUMBER_1", PAGE_COUNT)
    assert C.resolve_citation_to_index0(
        7, "PDF_NUMBER_1", PAGE_COUNT) == 6


def test_report_schema_validation():
    report = {
        "schema": "pagetrace.report/v1",
        "case_id": "sample-offset-display-001",
        "document": {"file_name": "sample.pdf", "sha256": SHA,
                     "page_count": PAGE_COUNT},
        "tool": {"name": "pagetrace", "version": "0.1.0"},
        "results": [],
        "summary": {"total_citations": 0, "pass_count": 0, "fail_count": 0,
                    "unknown_count": 0, "ambiguous_count": 0,
                    "normalized_result_sha256": None},
    }
    C.validate_report_schema(report)
    bad = copy.deepcopy(report)
    bad["schema"] = "pagetrace.report/v2"
    with pytest.raises(C.SchemaValidationError):
        C.validate_report_schema(bad)
    bad = copy.deepcopy(report)
    bad["results"] = [{"page": 6}]
    with pytest.raises(C.SchemaValidationError):
        C.validate_report_schema(bad)
