"""T006 parity — production implementation vs independent Oracle.

Run from PACKAGE_ROOT, inside the venv:
    python -m pytest tests/integration/test_oracle_parity.py -q

PROJECT_BOOK.md v1.0.0 §8.3 item 4: production and the independent
Oracle must agree on *all* 48 fault citations (and on the 48 normal
control citations) in ``fault_type / verdict / first_fault_stage /
expected_source_pages0 / observed_page_value`` — plus the candidate
page set, which both sides derive from the PDF text.  This test is
the check: it runs the production analyser (pypdf path) and the
Oracle (pdfminer.six path) over the same frozen inputs and compares
those fields citation by citation.

It also compares the extraction audits: the per-page differences
between each bundle's extraction records and the honest reading
must be the same pages, kinds and fields on both sides.  Hash
*values* are not compared for page 0: the production honest hash is
over the pypdf text (which keeps the "·" glyph) while the Oracle
fingerprint is over the pdfminer text (which drops it) — the two
fingerprints of the same honest page differ by exactly that glyph,
which is why the Oracle verifies page-0 hashes through the
documented single-glyph repair instead (see
``oracle.textnorm.hash_matches_page`` and
``t006-pdfminer-pypdf-contrast.log``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))
sys.path.insert(0, str(PACKAGE_ROOT / "tests"))

from pagetrace.compare_stages import (  # noqa: E402
    analyze_bundle, compare_extraction)
from pagetrace.extract import extract_pdf  # noqa: E402

from oracle.api import analyze_case  # noqa: E402

#: The five §8.3 item 4 parity fields, plus the candidate set.
PARITY_FIELDS = (
    "fault_type",
    "verdict",
    "first_fault_stage",
    "expected_source_pages0",
    "observed_page_value",
    "candidate_source_pages0",
)


def load_manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def load_bundle(case_id: str) -> dict:
    return json.loads(
        (FIXTURES / "bundles" / f"{case_id}.trace.json").read_text(
            encoding="utf-8"))


def load_golden() -> dict:
    return json.loads(
        (FIXTURES / "golden" / "expected.json").read_text(encoding="utf-8"))


def _production_results(case_id: str, bundle: dict):
    pdf_path = str(FIXTURES / "pdfs" / bundle["document"]["file_name"])
    _, honest = extract_pdf(pdf_path)
    verdicts = analyze_bundle(bundle, honest)
    extraction = compare_extraction(
        honest, bundle["stages"].get("extraction"))
    return verdicts, extraction


def test_production_oracle_parity_all_48():
    """§8.3 item 4: production == Oracle on every citation of every
    case, on all parity fields (96 citations)."""
    manifest = load_manifest()
    assert len(manifest["cases"]) == 48
    mismatches: list[str] = []
    for case in manifest["cases"]:
        case_id = case["case_id"]
        bundle = load_bundle(case_id)
        production, _ = _production_results(case_id, bundle)
        oracle = analyze_case(
            str(FIXTURES / "pdfs" / case["pdf_file_name"]), bundle, case_id)
        prod_by_id = {v.citation_id: v for v in production}
        assert set(prod_by_id) == {"cite-fault", "cite-control"}
        for citation_id, prod in prod_by_id.items():
            ora = oracle.by_citation_id(citation_id)
            for field_name in PARITY_FIELDS:
                prod_value = getattr(prod, field_name)
                ora_value = getattr(ora, field_name)
                if prod_value != ora_value:
                    mismatches.append(
                        f"{case_id}/{citation_id} {field_name}: "
                        f"production={prod_value!r} oracle={ora_value!r}")
    assert mismatches == [], (
        f"production/Oracle parity failures ({len(mismatches)}):\n"
        + "\n".join(mismatches))


def test_production_oracle_extraction_audit_parity():
    """The extraction audit agrees on both sides: same differing
    pages, same kinds, same fields — in exactly the 6 confirmed
    bundles, and nowhere else."""
    manifest = load_manifest()
    differing: dict[str, list[tuple]] = {}
    for case in manifest["cases"]:
        case_id = case["case_id"]
        bundle = load_bundle(case_id)
        _, production = _production_results(case_id, bundle)
        oracle = analyze_case(
            str(FIXTURES / "pdfs" / case["pdf_file_name"]), bundle, case_id)
        prod_triples = sorted(
            (d.pdf_page_index0, d.kind, d.field) for d in production)
        ora_triples = sorted(
            (d.pdf_page_index0, d.kind, d.field)
            for d in oracle.extraction_diffs)
        assert prod_triples == ora_triples, (
            f"{case_id}: production extraction diffs {prod_triples} != "
            f"oracle {ora_triples}")
        # The bundle-side (downstream) hash values must also agree.
        prod_down = sorted(
            (d.pdf_page_index0, d.downstream_value) for d in production)
        ora_down = sorted(
            (d.pdf_page_index0, d.downstream_value)
            for d in oracle.extraction_diffs)
        assert prod_down == ora_down, (
            f"{case_id}: downstream extraction values differ: "
            f"{prod_down} != {ora_down}")
        if prod_triples:
            differing[case_id] = prod_triples
    assert set(differing) == {
        "mm-ext-01", "mm-ext-02", "mm-ext-03",
        "po-ext-01", "po-ext-02", "po-ext-03",
    }


def test_parity_matches_golden():
    """Both sides agree with the Golden file on every fault and
    control citation (the Golden file is the Oracle's own output,
    cross-checked against spec.expected — see the audit evidence)."""
    golden = load_golden()
    assert len(golden["cases"]) == 48
    for entry in golden["cases"]:
        case_id = entry["case_id"]
        bundle = load_bundle(case_id)
        production, _ = _production_results(case_id, bundle)
        oracle = analyze_case(
            str(FIXTURES / "pdfs" / entry["pdf_file_name"]), bundle, case_id)
        prod_by_id = {v.citation_id: v for v in production}
        for citation_id, golden_entry in (
                ("cite-fault", entry["fault"]),
                ("cite-control", entry["control"])):
            prod = prod_by_id[citation_id]
            ora = oracle.by_citation_id(citation_id)
            for field_name in ("verdict", "fault_type",
                               "first_fault_stage",
                               "expected_source_pages0",
                               "observed_page_value"):
                assert getattr(prod, field_name) == golden_entry[field_name], (
                    f"{case_id}/{citation_id} production {field_name} != "
                    "golden")
                assert getattr(ora, field_name) == golden_entry[field_name], (
                    f"{case_id}/{citation_id} oracle {field_name} != golden")
            if citation_id == "cite-fault" and \
                    golden_entry["fault_type"] == "UNLOCATABLE":
                assert prod.reason == golden_entry["unlocatable_reason"], (
                    f"{case_id} production reason != golden")
                assert ora.reason == golden_entry["unlocatable_reason"], (
                    f"{case_id} oracle reason != golden")


def test_missing_stage_reason_agrees_across_implementations():
    """T013 P2-05: with a stage snapshot missing, production and the
    Oracle both report verdict UNKNOWN_TRACE_MISSING with reason
    TRACE_MISSING (the Oracle used to leave reason null). Reason is
    not an S0 parity field; this pins the cross-implementation value
    directly instead."""
    import copy

    bundle = load_bundle("po-chk-05")
    bundle = copy.deepcopy(bundle)
    bundle["stages"]["missing_stages"] = ["chunking"]
    bundle["stages"]["chunking"] = None
    production, _ = _production_results("po-chk-05", bundle)
    oracle = analyze_case(
        str(FIXTURES / "pdfs" / "po-chk-05.pdf"), bundle, "po-chk-05")
    for citation_id in ("cite-fault", "cite-control"):
        prod = next(v for v in production if v.citation_id == citation_id)
        ora = oracle.by_citation_id(citation_id)
        assert prod.verdict == "UNKNOWN_TRACE_MISSING", citation_id
        assert ora.verdict == "UNKNOWN_TRACE_MISSING", citation_id
        assert prod.reason == "TRACE_MISSING", citation_id
        assert ora.reason == "TRACE_MISSING", citation_id
