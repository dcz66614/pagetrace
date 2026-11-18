"""S0 gate runner for P026 PageTrace (T007).

Runs the whole S0 suite from PROJECT_BOOK.md v1.0.0 §8.3 / §8.4 as one
repeatable command::

    python tools/run_s0.py --suite fixtures --repeat 100 --out 05_tests/s0

from PACKAGE_ROOT (``04_source/source``).  It runs the production
implementation (pypdf path, ``src/pagetrace``) and the independent
Oracle (pdfminer.six path, ``tests/oracle``) over all 48 frozen
fixture cases, checks every §8.3 gate, then re-executes the full
suite ``--repeat`` times, hashing the normalised result each time
(§8.4: exactly one unique SHA-256 over 100 replays).

Outputs (``--out`` is resolved against the repository root, so the
acceptance command's ``05_tests/s0`` lands in
``<repo>/05_tests/s0``):

* ``S0_REPORT.json`` — full report: per-gate counts, per-case actual
  results (never expected values written as actuals), fixed input
  file hashes, Golden hash, dependency lock hash, environment info,
  and the replay hashes.
* ``replay-hashes.txt`` — one normalised SHA-256 per replay line
  (``--repeat`` lines).

Exit codes (PROJECT_BOOK §12.2): 0 = every S0 gate passed; 4 = any
S0 gate failed; 2 = invalid input (missing fixture, count != 48,
PDF hash mismatch against the frozen manifest/Golden); 3 = internal
error.

Result levels (FIX-R1, GPT final review R1 §4): a run with fewer
than 100 replays can only return ``SMOKE_PASS`` — it proves the
gates pass once, not the §8.4 100-replay determinism.  Only a run
with ``--repeat`` >= 100 that passes every gate returns the formal
``S0 PASS``.  A failed gate is ``FAIL`` at any repeat count, and
the exit code stays 4.  ``SMOKE_PASS`` still exits 0: the gates
passed; only the replay-count bar for a formal PASS was not met.

Import-path note (T013 P2-08): the package is a single src layout
(``pyproject.toml`` installs ``src/pagetrace/``); the top-level T001
stub is deleted.  Like the existing tests
(``tests/integration/test_oracle_parity.py``), this runner still inserts
``src/`` (then ``tests/`` for the Oracle) at the head of ``sys.path``
before importing ``pagetrace`` or ``oracle``, so running from a source
checkout without installing works too.

Determinism (§8.4): the normalised result hashed per replay is
canonical JSON — UTF-8, sorted keys, no redundant whitespace
(``separators=(",", ":")``), page lists sorted numerically, evidence
sorted by (stage, field, note) — and covers verdict, fault type,
first fault stage, candidate pages, page-number conversions and
evidence fields.  It excludes wall-clock time, run duration,
absolute paths, temporary directories, hostnames and random UUIDs:
only relative file names, content hashes and verdict data enter the
hash.  The report itself likewise carries no timestamps, durations,
absolute paths or hostnames.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths.  This file lives at <PACKAGE_ROOT>/tools/run_s0.py, so its
# parents give both roots without depending on the working directory.
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = TOOLS_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[1]

# Import-path rule (see module docstring): src/ first as a
# source-checkout fallback (T013 P2-08); tests/ next for the Oracle.
sys.path.insert(0, str(PACKAGE_ROOT / "tests"))
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.compare_stages import analyze_bundle  # noqa: E402
from pagetrace.extract import extract_pdf  # noqa: E402
from pagetrace.verdicts import FAIL_VERDICTS  # noqa: E402

from oracle.api import analyze_case  # noqa: E402

#: The five §8.3 item 4 parity fields, plus the candidate page set
#: (same set as tests/integration/test_oracle_parity.py).
PARITY_FIELDS = (
    "fault_type",
    "verdict",
    "first_fault_stage",
    "expected_source_pages0",
    "observed_page_value",
    "candidate_source_pages0",
)

#: Verdicts that count as honest uncertainty, never to be turned PASS.
UNCERTAINTY_VERDICTS = frozenset({
    "UNKNOWN_TRACE_MISSING",
    "UNKNOWN_PAGE_BASIS",
    "AMBIGUOUS",
})

GOLDEN_FIELDS = (
    "verdict",
    "fault_type",
    "first_fault_stage",
    "candidate_source_pages0",
    "expected_source_pages0",
    "observed_page_value",
)

EXPECTED_CASES = 48
EXPECTED_PER_FAULT_TYPE = 12

#: Minimum replay count for a formal S0 PASS (PROJECT_BOOK §8.4:
#: exactly one unique SHA-256 over 100 replays).  Fewer replays can
#: only return SMOKE_PASS (FIX-R1, GPT final review R1 §4).
S0_FULL_REPEAT = 100


def s0_result_for(s0_pass: bool, repeat: int) -> str:
    """Overall S0 result level for a run.

    ``FAIL`` when any §8.3 gate failed; ``PASS`` only when every
    gate passed *and* at least ``S0_FULL_REPEAT`` replays ran;
    ``SMOKE_PASS`` when every gate passed on fewer replays.
    """
    if not s0_pass:
        return "FAIL"
    return "PASS" if repeat >= S0_FULL_REPEAT else "SMOKE_PASS"


class InputError(Exception):
    """Invalid frozen input (exit 2)."""


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
def resolve_suite_path(suite_arg: str) -> Path:
    """``--suite``: relative paths are relative to PACKAGE_ROOT."""
    path = Path(suite_arg)
    if not path.is_absolute():
        path = PACKAGE_ROOT / path
    return path


def resolve_out_path(out_arg: str) -> Path:
    """``--out``: relative paths are relative to the repository root.

    The acceptance command is run from PACKAGE_ROOT with
    ``--out 05_tests/s0``; that directory lives at the repository
    root (``<repo>/05_tests/s0``), not under PACKAGE_ROOT, so a
    relative ``--out`` is resolved against REPO_ROOT.  Absolute
    paths are used as given.
    """
    path = Path(out_arg)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


# ---------------------------------------------------------------------------
# Hashing / normalisation (§8.4)
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sorted_pages(value):
    """Page lists in canonical order; anything else verbatim."""
    if isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool)
            for item in value):
        return sorted(value)
    return value


def _evidence_to_sorted_dicts(evidence) -> list[dict]:
    """Evidence items as plain dicts, in a fixed order."""
    items = []
    for item in evidence:
        if hasattr(item, "to_dict"):
            entry = item.to_dict()
        elif isinstance(item, dict):
            entry = dict(item)
        else:  # pragma: no cover - defensive, both sides use dataclasses
            entry = {"stage": str(item), "field": "", "note": ""}
        entry["upstream_value"] = _sorted_pages(entry.get("upstream_value"))
        entry["downstream_value"] = _sorted_pages(
            entry.get("downstream_value"))
        items.append(entry)
    items.sort(key=lambda e: (
        str(e.get("stage", "")),
        str(e.get("field", "")),
        str(e.get("note", "")),
        str(e.get("upstream_value")),
        str(e.get("downstream_value")),
    ))
    return items


def citation_to_normalized(result) -> dict:
    """One citation verdict as a deterministic plain dict.

    Only verdict data enters: no paths, no timestamps, no hostnames.
    """
    return {
        "citation_id": result.citation_id,
        "citation_page_basis": result.citation_page_basis,
        "citation_page_value": result.citation_page_value,
        "candidate_source_pages0": _sorted_pages(
            result.candidate_source_pages0),
        "correct_pdf_page_number1": _sorted_pages(
            result.correct_pdf_page_number1),
        "correct_viewer_page1": _sorted_pages(
            result.correct_viewer_page1),
        "evidence": _evidence_to_sorted_dicts(result.evidence),
        "expected_source_pages0": _sorted_pages(
            result.expected_source_pages0),
        "fault_type": result.fault_type,
        "first_fault_stage": result.first_fault_stage,
        "missing_stages": sorted(result.missing_stages or []),
        "notes": sorted(result.notes or []),
        "observed_page_value": result.observed_page_value,
        "quote_sha256": result.quote_sha256,
        "reason": getattr(result, "reason", None),
        "verdict": result.verdict,
    }


def normalize(obj: object) -> bytes:
    """Canonical JSON (§8.4): UTF-8, sorted keys, no extra spaces."""
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def suite_hash(normalized_suite: dict) -> str:
    return hashlib.sha256(normalize(normalized_suite)).hexdigest()


# ---------------------------------------------------------------------------
# Frozen-input loading and integrity checks
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read JSON {path.name}: {exc}") from exc


def collect_input_hashes(fixtures_dir: Path) -> dict[str, str]:
    """SHA-256 of every file under fixtures/, keyed by relative path."""
    hashes: dict[str, str] = {}
    for path in sorted(fixtures_dir.rglob("*")):
        if path.is_file():
            hashes[path.relative_to(fixtures_dir).as_posix()] = sha256_file(
                path)
    return hashes


def git_head_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    commit = proc.stdout.strip()
    return commit or None


def environment_info() -> dict:
    """Run environment (no timestamps, hostnames or absolute paths)."""
    versions: dict[str, str | None] = {}
    for dist in ("pypdf", "pdfminer.six", "reportlab", "Pillow",
                 "jsonschema", "pytest"):
        try:
            versions[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            versions[dist] = None
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "dependency_versions": versions,
    }


def load_suite_inputs(fixtures_dir: Path) -> tuple[dict, dict, dict]:
    """Load manifest + Golden and verify frozen-input integrity.

    Raises InputError (exit 2) when the suite is not exactly the
    frozen 48 cases, when a PDF/bundle/spec is missing, or when a
    PDF's hash disagrees with the manifest and the Golden file.
    """
    manifest_path = fixtures_dir / "manifest.json"
    golden_path = fixtures_dir / "golden" / "expected.json"
    if not manifest_path.is_file():
        raise InputError(f"missing manifest: {manifest_path.name}")
    if not golden_path.is_file():
        raise InputError(f"missing Golden file: {golden_path.name}")
    manifest = load_json(manifest_path)
    golden = load_json(golden_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASES:
        raise InputError(
            f"manifest case count is "
            f"{len(cases) if isinstance(cases, list) else 'not a list'}, "
            f"expected {EXPECTED_CASES}")
    golden_cases = golden.get("cases")
    if not isinstance(golden_cases, list) or len(golden_cases) != EXPECTED_CASES:
        raise InputError(
            f"Golden case count is "
            f"{len(golden_cases) if isinstance(golden_cases, list) else 'not a list'}, "
            f"expected {EXPECTED_CASES}")
    golden_by_id = {case["case_id"]: case for case in golden_cases}
    for case in cases:
        case_id = case["case_id"]
        if case_id not in golden_by_id:
            raise InputError(f"case {case_id} missing from Golden file")
        pdf_path = fixtures_dir / "pdfs" / case["pdf_file_name"]
        bundle_path = fixtures_dir / "bundles" / f"{case_id}.trace.json"
        spec_path = fixtures_dir / "specs" / f"{case_id}.json"
        for needed in (pdf_path, bundle_path, spec_path):
            if not needed.is_file():
                raise InputError(f"missing fixture file: {needed.name}")
        pdf_sha = sha256_file(pdf_path)
        if pdf_sha != case.get("pdf_sha256"):
            raise InputError(
                f"PDF hash mismatch for {case_id}: file {pdf_sha} != "
                f"manifest {case.get('pdf_sha256')}")
        if pdf_sha != golden_by_id[case_id].get("pdf_sha256"):
            raise InputError(
                f"PDF hash mismatch for {case_id}: file {pdf_sha} != "
                f"Golden {golden_by_id[case_id].get('pdf_sha256')}")
    return manifest, golden, golden_by_id


# ---------------------------------------------------------------------------
# One full suite execution (production + Oracle, all 48 cases)
# ---------------------------------------------------------------------------
def run_suite_once(fixtures_dir: Path, manifest: dict,
                   golden_by_id: dict) -> dict:
    """Run production + Oracle over all 48 cases; return detail + hash.

    ``normalized`` is the §8.4 hash input (verdict data only);
    ``per_case`` additionally carries the Golden expectations used to
    score the gates, kept separate so expectations never leak into
    the hashed result or pose as actuals.
    """
    per_case: list[dict] = []
    normalized_cases: list[dict] = []
    for case in sorted(manifest["cases"], key=lambda c: c["case_id"]):
        case_id = case["case_id"]
        pdf_path = fixtures_dir / "pdfs" / case["pdf_file_name"]
        bundle = load_json(
            fixtures_dir / "bundles" / f"{case_id}.trace.json")
        golden_case = golden_by_id[case_id]

        _, honest = extract_pdf(str(pdf_path))
        production = analyze_bundle(bundle, honest)
        oracle = analyze_case(str(pdf_path), bundle, case_id)

        prod_by_id = {v.citation_id: v for v in production}
        oracle_by_id = {v.citation_id: v for v in oracle.citations}
        if set(prod_by_id) != {"cite-fault", "cite-control"}:
            raise InputError(
                f"{case_id}: production returned citations "
                f"{sorted(prod_by_id)}, expected cite-fault/cite-control")
        if set(oracle_by_id) != {"cite-fault", "cite-control"}:
            raise InputError(
                f"{case_id}: Oracle returned citations "
                f"{sorted(oracle_by_id)}, expected cite-fault/cite-control")

        prod_fault = citation_to_normalized(prod_by_id["cite-fault"])
        prod_control = citation_to_normalized(prod_by_id["cite-control"])
        oracle_fault = citation_to_normalized(oracle_by_id["cite-fault"])
        oracle_control = citation_to_normalized(
            oracle_by_id["cite-control"])

        parity_mismatches: list[str] = []
        for citation_id, prod, ora in (
                ("cite-fault", prod_fault, oracle_fault),
                ("cite-control", prod_control, oracle_control)):
            for field_name in PARITY_FIELDS:
                if prod[field_name] != ora[field_name]:
                    parity_mismatches.append(
                        f"{case_id}/{citation_id} {field_name}: "
                        f"production={prod[field_name]!r} "
                        f"oracle={ora[field_name]!r}")

        per_case.append({
            "case_id": case_id,
            "pdf_file_name": case["pdf_file_name"],
            "pdf_sha256": case["pdf_sha256"],
            "fault_type_golden": golden_case["fault"]["fault_type"],
            "golden_fault": {
                field_name: golden_case["fault"][field_name]
                for field_name in GOLDEN_FIELDS},
            "golden_control": {
                field_name: golden_case["control"][field_name]
                for field_name in GOLDEN_FIELDS},
            "production_fault": prod_fault,
            "production_control": prod_control,
            "oracle_fault": oracle_fault,
            "oracle_control": oracle_control,
            "parity_mismatches": parity_mismatches,
        })
        normalized_cases.append({
            "case_id": case_id,
            "pdf_file_name": case["pdf_file_name"],
            "pdf_sha256": case["pdf_sha256"],
            "oracle_control": oracle_control,
            "oracle_fault": oracle_fault,
            "production_control": prod_control,
            "production_fault": prod_fault,
        })
    normalized = {"cases": normalized_cases}
    return {
        "normalized": normalized,
        "hash": suite_hash(normalized),
        "per_case": per_case,
    }


# ---------------------------------------------------------------------------
# Gate evaluation (§8.3)
# ---------------------------------------------------------------------------
def _golden_matches(result: dict, golden: dict) -> list[str]:
    """Golden-field mismatches between one actual result and Golden."""
    mismatches = []
    for field_name in GOLDEN_FIELDS:
        if result[field_name] != golden[field_name]:
            mismatches.append(
                f"{field_name}: actual={result[field_name]!r} "
                f"golden={golden[field_name]!r}")
    return mismatches


def evaluate_gates(per_case: list[dict], replay_hashes: list[str]) -> dict:
    """Score every §8.3 gate from one suite run + the replay hashes."""
    detection_by_type: dict[str, int] = {}
    detection_failures: list[str] = []
    stage_failures: list[str] = []
    control_false_positives: list[str] = []
    parity_mismatches: list[str] = []
    uncertainty_violations: list[str] = []
    golden_failures: list[str] = []
    detected = 0
    stages_correct = 0

    for entry in per_case:
        case_id = entry["case_id"]
        fault_type = entry["fault_type_golden"]
        prod_fault = entry["production_fault"]
        prod_control = entry["production_control"]
        oracle_fault = entry["oracle_fault"]
        oracle_control = entry["oracle_control"]

        # Gate 1 — detection: FAIL verdict with the Golden fault type.
        if (prod_fault["fault_type"] == fault_type
                and prod_fault["verdict"] in FAIL_VERDICTS):
            detected += 1
            detection_by_type[fault_type] = \
                detection_by_type.get(fault_type, 0) + 1
        else:
            detection_failures.append(
                f"{case_id}: fault_type={prod_fault['fault_type']!r} "
                f"verdict={prod_fault['verdict']!r} "
                f"(golden fault_type={fault_type!r})")

        # Gate 2 — first fault stage matches Golden.
        if (prod_fault["first_fault_stage"]
                == entry["golden_fault"]["first_fault_stage"]):
            stages_correct += 1
        else:
            stage_failures.append(
                f"{case_id}: first_fault_stage="
                f"{prod_fault['first_fault_stage']!r} (golden "
                f"{entry['golden_fault']['first_fault_stage']!r})")

        # Gate 3 — normal control citations must be PASS (0 false +).
        if prod_control["verdict"] != "PASS":
            control_false_positives.append(
                f"{case_id}: control verdict={prod_control['verdict']!r} "
                f"fault_type={prod_control['fault_type']!r}")

        # Gate 4 — production/Oracle parity (fault + control).
        parity_mismatches.extend(entry["parity_mismatches"])

        # Gate 6 — uncertainty is never converted to PASS.
        for label, prod, ora, gold in (
                ("cite-fault", prod_fault, oracle_fault,
                 entry["golden_fault"]),
                ("cite-control", prod_control, oracle_control,
                 entry["golden_control"])):
            if prod["verdict"] == "PASS" and (
                    gold["verdict"] != "PASS"
                    or ora["verdict"] != "PASS"):
                uncertainty_violations.append(
                    f"{case_id}/{label}: production PASS but golden "
                    f"verdict={gold['verdict']!r} oracle "
                    f"verdict={ora['verdict']!r}")
            if (prod["verdict"] == "PASS"
                    and ora["verdict"] in UNCERTAINTY_VERDICTS):
                uncertainty_violations.append(
                    f"{case_id}/{label}: production PASS but Oracle "
                    f"verdict={ora['verdict']!r} (uncertainty)")

        # Supporting check — full Golden agreement (fault + control).
        for label, prod, gold in (
                ("cite-fault", prod_fault, entry["golden_fault"]),
                ("cite-control", prod_control, entry["golden_control"])):
            for mismatch in _golden_matches(prod, gold):
                golden_failures.append(f"{case_id}/{label} {mismatch}")

    unique_replay = sorted(set(replay_hashes))
    gates = {
        "detection": {
            "spec": "§8.3 item 1",
            "description": "Four fault classes detected, 12/12 each",
            "expected": EXPECTED_CASES,
            "actual": detected,
            "by_fault_type": {
                fault_type: detection_by_type.get(fault_type, 0)
                for fault_type in sorted(
                    {e["fault_type_golden"] for e in per_case})},
            "expected_by_fault_type": EXPECTED_PER_FAULT_TYPE,
            "passed": detected == EXPECTED_CASES,
            "failures": detection_failures,
        },
        "first_fault_stage": {
            "spec": "§8.3 item 2",
            "description": "first_fault_stage matches Golden, 48/48",
            "expected": EXPECTED_CASES,
            "actual": stages_correct,
            "passed": stages_correct == EXPECTED_CASES,
            "failures": stage_failures,
        },
        "control_false_positives": {
            "spec": "§8.3 item 3",
            "description": "Normal control citations are PASS, 0 false +",
            "expected": 0,
            "actual": len(control_false_positives),
            "passed": not control_false_positives,
            "failures": control_false_positives,
        },
        "parity": {
            "spec": "§8.3 item 4",
            "description": "Production == Oracle on all 96 citations "
                           "(6 fields each)",
            "expected_citations": EXPECTED_CASES * 2,
            "actual_citations_matching": EXPECTED_CASES * 2 - len({
                mismatch.split(" ")[0] for mismatch in parity_mismatches}),
            "expected_mismatches": 0,
            "actual_mismatches": len(parity_mismatches),
            "passed": not parity_mismatches,
            "failures": parity_mismatches,
        },
        "replay": {
            "spec": "§8.3 item 5 / §8.4",
            "description": f"{len(replay_hashes)} normalised replay(s) "
                           f"give 1 unique SHA-256 "
                           f"(formal S0 PASS needs {S0_FULL_REPEAT})",
            "expected_unique_hashes": 1,
            "actual_unique_hashes": len(unique_replay),
            "replays": len(replay_hashes),
            "passed": len(unique_replay) == 1,
            "failures": [] if len(unique_replay) == 1 else [
                f"{len(unique_replay)} unique hashes over "
                f"{len(replay_hashes)} replays"],
        },
        "uncertainty_not_pass": {
            "spec": "§8.3 item 6",
            "description": "UNKNOWN/AMBIGUOUS/UNLOCATABLE never become PASS",
            "expected": 0,
            "actual": len(uncertainty_violations),
            "passed": not uncertainty_violations,
            "failures": uncertainty_violations,
        },
        "golden_agreement": {
            "spec": "§8.3 items 1-2 (supporting: full Golden fields)",
            "description": "Production matches Golden on verdict / "
                           "fault_type / first_fault_stage / candidate / "
                           "expected / observed for all 96 citations",
            "expected_citations": EXPECTED_CASES * 2,
            "actual_mismatches": len(golden_failures),
            "passed": not golden_failures,
            "failures": golden_failures,
        },
    }
    gates["s0_pass"] = all(gate["passed"] for gate in gates.values()
                           if isinstance(gate, dict))
    return gates


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_s0(fixtures_dir: Path, repeat: int, out_dir: Path) -> dict:
    """Execute the S0 gate end to end; returns (report, exit_code)."""
    if repeat < 1:
        raise InputError(f"--repeat must be >= 1, got {repeat}")
    manifest, golden, golden_by_id = load_suite_inputs(fixtures_dir)
    input_hashes = collect_input_hashes(fixtures_dir)
    golden_sha = sha256_file(fixtures_dir / "golden" / "expected.json")

    replay_hashes: list[str] = []
    first_run = None
    for _ in range(repeat):
        result = run_suite_once(fixtures_dir, manifest, golden_by_id)
        replay_hashes.append(result["hash"])
        if first_run is None:
            first_run = result
    assert first_run is not None  # repeat >= 1

    gates = evaluate_gates(first_run["per_case"], replay_hashes)
    s0_pass = bool(gates["s0_pass"])

    lock_path = PACKAGE_ROOT / "requirements.lock"
    pyproject_path = PACKAGE_ROOT / "pyproject.toml"
    report = {
        "format": "pagetrace.s0-report/v1",
        "project": "P026 PageTrace",
        "spec_version": "PROJECT_BOOK.md v1.0.0 (§8.3, §8.4)",
        "base_commit": git_head_commit(),
        "s0_result": s0_result_for(s0_pass, repeat),
        "suite": {
            "case_count": EXPECTED_CASES,
            "repeat": repeat,
            "fixtures_dir": "fixtures",
        },
        "gates": gates,
        "counts": {
            "detection": gates["detection"]["actual"],
            "first_fault_stage": gates["first_fault_stage"]["actual"],
            "control_false_positives":
                gates["control_false_positives"]["actual"],
            "parity_mismatches": gates["parity"]["actual_mismatches"],
            "parity_citations_matching":
                gates["parity"]["actual_citations_matching"],
            "replay_unique_hashes":
                gates["replay"]["actual_unique_hashes"],
            "uncertainty_violations":
                gates["uncertainty_not_pass"]["actual"],
            "golden_mismatches":
                gates["golden_agreement"]["actual_mismatches"],
        },
        "per_case": first_run["per_case"],
        "input_hashes": {
            "fixtures": input_hashes,
            "golden_sha256": golden_sha,
            "requirements_lock_sha256": sha256_file(lock_path)
                if lock_path.is_file() else None,
            "pyproject_sha256": sha256_file(pyproject_path)
                if pyproject_path.is_file() else None,
        },
        "environment": environment_info(),
        "replay": {
            "repeat": repeat,
            "unique_hash_count": len(set(replay_hashes)),
            "unique_hashes": sorted(set(replay_hashes)),
            "hashes": replay_hashes,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "S0_REPORT.json").write_text(
        normalize(report).decode("utf-8") + "\n", encoding="utf-8")
    (out_dir / "replay-hashes.txt").write_text(
        "".join(f"{digest}\n" for digest in replay_hashes),
        encoding="utf-8")
    return report, 0 if s0_pass else 4


def print_summary(report: dict) -> None:
    gates = report["gates"]
    print(f"S0_RESULT: {report['s0_result']}")
    if report["s0_result"] == "SMOKE_PASS":
        print(f"note: smoke run only ({report['suite']['repeat']} "
              f"replay(s)); formal S0 PASS requires "
              f"--repeat {S0_FULL_REPEAT}")
    print(f"detection: {gates['detection']['actual']}/48 "
          f"(by type: {gates['detection']['by_fault_type']})")
    print(f"first_fault_stage: {gates['first_fault_stage']['actual']}/48")
    print(f"control_false_positives: "
          f"{gates['control_false_positives']['actual']}")
    print(f"parity: {gates['parity']['actual_citations_matching']}/96 "
          f"citations matching, "
          f"{gates['parity']['actual_mismatches']} field mismatches")
    print(f"replay: {gates['replay']['actual_unique_hashes']} unique "
          f"hash(es) over {gates['replay']['replays']} replays")
    print(f"uncertainty_not_pass violations: "
          f"{gates['uncertainty_not_pass']['actual']}")
    print(f"golden_agreement mismatches: "
          f"{gates['golden_agreement']['actual_mismatches']}")
    print(f"golden_sha256: {report['input_hashes']['golden_sha256']}")
    for name, gate in gates.items():
        if name == "s0_pass":
            continue
        if not gate["passed"]:
            print(f"GATE FAILED: {name} ({gate['spec']})")
            for failure in gate["failures"][:20]:
                print(f"  - {failure}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P026 S0 gate: 48 fixtures + Oracle parity + "
                    "100 normalised replays (PROJECT_BOOK §8.3/§8.4).")
    parser.add_argument("--suite", default="fixtures",
                        help="fixture suite dir, relative to PACKAGE_ROOT "
                             "(default: fixtures)")
    parser.add_argument("--repeat", type=int, default=100,
                        help="normalised replay count (default: 100). "
                             "Fewer than 100 replays can only return "
                             "SMOKE_PASS; formal S0 PASS requires 100.")
    parser.add_argument("--out", default="05_tests/s0",
                        help="output dir; relative paths resolve against "
                             "the repository root (default: 05_tests/s0)")
    args = parser.parse_args(argv)
    try:
        fixtures_dir = resolve_suite_path(args.suite)
        if not fixtures_dir.is_dir():
            raise InputError(f"suite dir not found: {args.suite}")
        report, exit_code = run_s0(
            fixtures_dir, args.repeat, resolve_out_path(args.out))
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - internal error path, exit 3
        traceback.print_exc()
        return 3
    print_summary(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
