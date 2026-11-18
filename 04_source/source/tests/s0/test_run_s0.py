"""Tests for the S0 gate runner (P026 T007, PROJECT_BOOK §8.3/§8.4).

Run from PACKAGE_ROOT, inside the venv::

    python -m pytest tests/s0 -q

The end-to-end tests run the real frozen suite (repeat=2, and a
repeat=1 run against a deliberately corrupted Golden copy); they
take ~10 s each because production + Oracle analyse all 48 cases
per replay.  The full 100-replay acceptance run is the runner CLI
itself (``python tools/run_s0.py --suite fixtures --repeat 100
--out 05_tests/s0``), not this pytest module.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import run_s0

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"

GOLDEN_SHA256 = (
    "9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353")


def test_normalize_is_canonical():
    """§8.4: sorted keys, no redundant whitespace, UTF-8 bytes."""
    payload = {"b": [2, 1], "a": {"z": 1, "y": "引文"}}
    first = run_s0.normalize(payload)
    assert first == run_s0.normalize(payload)
    assert first == b'{"a":{"y":"\xe5\xbc\x95\xe6\x96\x87","z":1},"b":[2,1]}'
    assert b" " not in first


def test_out_path_resolution():
    """Relative --out resolves against the repo root, not PACKAGE_ROOT."""
    assert run_s0.resolve_out_path("05_tests/s0") == \
        run_s0.REPO_ROOT / "05_tests" / "s0"
    absolute = Path("/tmp/s0-out")
    assert run_s0.resolve_out_path(str(absolute)) == absolute
    assert run_s0.resolve_suite_path("fixtures") == FIXTURES


def test_normalized_result_contains_no_absolute_paths():
    """§8.4: the hashed result must not embed absolute paths."""
    manifest, golden, golden_by_id = run_s0.load_suite_inputs(FIXTURES)
    result = run_s0.run_suite_once(FIXTURES, manifest, golden_by_id)
    blob = run_s0.normalize(result["normalized"])
    assert str(PACKAGE_ROOT).encode("utf-8") not in blob
    assert b"/home/" not in blob
    assert result["hash"] == run_s0.suite_hash(result["normalized"])


def test_golden_sha_matches_frozen_value():
    assert run_s0.sha256_file(FIXTURES / "golden" / "expected.json") \
        == GOLDEN_SHA256


def test_s0_result_threshold():
    """FIX-R1 (GPT R1 §4): < 100 replays can only be SMOKE_PASS."""
    assert run_s0.s0_result_for(True, 1) == "SMOKE_PASS"
    assert run_s0.s0_result_for(True, 99) == "SMOKE_PASS"
    assert run_s0.s0_result_for(True, 100) == "PASS"
    assert run_s0.s0_result_for(True, 101) == "PASS"
    assert run_s0.s0_result_for(False, 100) == "FAIL"
    assert run_s0.s0_result_for(False, 1) == "FAIL"


def test_run_s0_real_suite_repeat_2(tmp_path):
    """End to end on the frozen suite: all §8.3 gates pass, 1 hash.

    repeat=2 is a smoke run (FIX-R1): the gates pass but the result
    is SMOKE_PASS, not a formal S0 PASS (needs --repeat 100).
    """
    out_dir = tmp_path / "s0"
    report, exit_code = run_s0.run_s0(FIXTURES, 2, out_dir)
    assert exit_code == 0
    assert report["s0_result"] == "SMOKE_PASS"
    assert report["counts"]["detection"] == 48
    assert report["counts"]["first_fault_stage"] == 48
    assert report["counts"]["control_false_positives"] == 0
    assert report["counts"]["parity_citations_matching"] == 96
    assert report["counts"]["parity_mismatches"] == 0
    assert report["counts"]["replay_unique_hashes"] == 1
    assert report["counts"]["uncertainty_violations"] == 0
    assert report["counts"]["golden_mismatches"] == 0
    assert report["input_hashes"]["golden_sha256"] == GOLDEN_SHA256
    assert len(report["input_hashes"]["fixtures"]) >= 48 * 3 + 2
    assert report["input_hashes"]["requirements_lock_sha256"]
    assert report["environment"]["python_version"].startswith("3.12")
    assert "golden/expected.json" in \
        report["input_hashes"]["fixtures"]

    report_path = out_dir / "S0_REPORT.json"
    hashes_path = out_dir / "replay-hashes.txt"
    assert report_path.is_file() and hashes_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["s0_result"] \
        == "SMOKE_PASS"
    lines = hashes_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and len(set(lines)) == 1
    assert lines[0] == report["replay"]["unique_hashes"][0]
    # The report itself carries no wall-clock, hostname or abs path.
    raw = report_path.read_text(encoding="utf-8")
    assert str(PACKAGE_ROOT) not in raw
    assert "/home/" not in raw


def test_run_s0_corrupted_golden_fails_with_exit_4(tmp_path):
    """A Golden fault-type change must fail S0 (exit 4), not pass."""
    fixtures_copy = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures_copy)
    golden_path = fixtures_copy / "golden" / "expected.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    golden["cases"][0]["fault"]["fault_type"] = "PAGE_METADATA_MISSING"
    golden["cases"][0]["fault"]["verdict"] = "FAIL_METADATA_MISSING"
    golden_path.write_text(
        json.dumps(golden, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "s0"
    report, exit_code = run_s0.run_s0(fixtures_copy, 1, out_dir)
    assert exit_code == 4
    assert report["s0_result"] == "FAIL"
    assert report["counts"]["detection"] < 48
    assert report["gates"]["detection"]["passed"] is False


def test_cli_main_returns_4_on_gate_failure(tmp_path, monkeypatch):
    """CLI exit code 4 propagates through main() on a gate failure."""
    fixtures_copy = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures_copy)
    golden_path = fixtures_copy / "golden" / "expected.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    golden["cases"][0]["fault"]["first_fault_stage"] = "display"
    golden_path.write_text(
        json.dumps(golden, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(PACKAGE_ROOT)
    code = run_s0.main([
        "--suite", str(fixtures_copy), "--repeat", "1",
        "--out", str(tmp_path / "s0-cli")])
    assert code == 4


def test_cli_main_returns_2_on_missing_suite(tmp_path):
    code = run_s0.main([
        "--suite", "no-such-suite", "--repeat", "1",
        "--out", str(tmp_path / "s0-missing")])
    assert code == 2


def test_evaluate_gates_empty_replay_fails():
    """Gate scoring is honest: a split replay hash set fails the gate."""
    manifest, golden, golden_by_id = run_s0.load_suite_inputs(FIXTURES)
    result = run_s0.run_suite_once(FIXTURES, manifest, golden_by_id)
    gates = run_s0.evaluate_gates(
        result["per_case"], [result["hash"], "0" * 64])
    assert gates["replay"]["passed"] is False
    assert gates["replay"]["actual_unique_hashes"] == 2
    assert gates["s0_pass"] is False
