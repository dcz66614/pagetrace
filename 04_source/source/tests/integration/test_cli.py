"""T009 — CLI integration tests.

Run from PACKAGE_ROOT, inside the venv::

    TMPDIR=$PWD/.tmp python -m pytest tests/integration/test_cli.py -q

The CLI is exercised as a real subprocess (``python -m
pagetrace.cli``) with the production import path (``PYTHONPATH=src``
+ ``PYTHONSAFEPATH=1``; T013 P2-08 made this a source-checkout fallback
— the installed package needs no PYTHONPATH — see
``src/pagetrace/cli.py`` module docstring).

Checks (PROJECT_BOOK §12, TASK-009 hard assertions):

* ``analyze`` / ``validate`` / ``s0`` / ``clean`` all exist with
  explicit parameters; ``analyze`` supports ``--include-snippets``;
* a fault case analyses to exit 1 with a schema-valid
  ``pagetrace.report/v1`` JSON + HTML report; a control-only
  bundle analyses to exit 0;
* a document-hash mismatch exits 2 (``INPUT_HASH_MISMATCH``);
* a bundle with a missing stage snapshot reports
  ``UNKNOWN_TRACE_MISSING`` with ``first_fault_stage`` null — the
  stage is never guessed — and exits 1;
* analysis FAIL (exit 1) and tool crash (exit 3) are distinct;
* ``clean`` prints the target path first, only deletes a directory
  carrying a PageTrace marker, and ``--dry-run`` deletes nothing;
* ``s0`` forwards to ``tools/run_s0.py`` (exit 0 on PASS).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PACKAGE_ROOT / "fixtures"
VENV_PYTHON = PACKAGE_ROOT / ".venv" / "bin" / "python"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.contracts import validate_report_schema  # noqa: E402

FAULT_TRACE = FIXTURES / "bundles" / "po-ext-01.trace.json"
FAULT_PDF = FIXTURES / "pdfs" / "po-ext-01.pdf"
OTHER_PDF = FIXTURES / "pdfs" / "po-ext-02.pdf"


def run_cli(*argv: str, cwd: Path = PACKAGE_ROOT) -> subprocess.CompletedProcess:
    """Run ``python -m pagetrace.cli`` as a subprocess; return the result."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    env["PYTHONSAFEPATH"] = "1"
    python = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    return subprocess.run(
        [python, "-m", "pagetrace.cli", *argv],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=300)


def _load_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_bundle(tmp_path: Path, bundle: dict, name: str = "case.trace.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# help / usage
# ---------------------------------------------------------------------------
def test_help_lists_all_commands():
    proc = run_cli("--help")
    assert proc.returncode == 0
    for command in ("analyze", "validate", "s0", "clean"):
        assert command in proc.stdout


def test_unknown_command_exits_2():
    proc = run_cli("frobnicate")
    assert proc.returncode == 2


def test_analyze_help_mentions_include_snippets():
    proc = run_cli("analyze", "--help")
    assert proc.returncode == 0
    assert "--include-snippets" in proc.stdout
    assert "--pdf" in proc.stdout
    assert "--trace" in proc.stdout
    assert "--out" in proc.stdout


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------
def test_analyze_fault_case_exits_1_with_json_and_html(tmp_path):
    out = tmp_path / "case-001"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(FAULT_TRACE), "--out", str(out))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAIL_PAGE_OFFSET" in proc.stdout
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    validate_report_schema(report)  # must be a valid report/v1 document
    assert report["schema"] == "pagetrace.report/v1"
    assert report["case_id"] == "po-ext-01"
    assert report["summary"] == {
        "total_citations": 2, "pass_count": 1, "fail_count": 1,
        "unknown_count": 0, "ambiguous_count": 0,
        "normalized_result_sha256": report["summary"][
            "normalized_result_sha256"],
    }
    fault, control = report["results"]
    assert (fault["citation_id"], fault["verdict"],
            fault["fault_type"], fault["first_fault_stage"]) == (
        "cite-fault", "FAIL_PAGE_OFFSET", "PAGE_OFFSET", "extraction")
    assert (control["citation_id"], control["verdict"]) == (
        "cite-control", "PASS")
    html_path = out / "report.html"
    assert html_path.is_file()
    assert (out / "assets" / "report.css").is_file()
    assert (out / "assets" / "report.js").is_file()
    assert "FAIL_PAGE_OFFSET" in html_path.read_text(encoding="utf-8")


def test_analyze_is_deterministic(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    for out in (out1, out2):
        proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                       str(FAULT_TRACE), "--out", str(out))
        assert proc.returncode == 1
    doc1 = json.loads((out1 / "report.json").read_text(encoding="utf-8"))
    doc2 = json.loads((out2 / "report.json").read_text(encoding="utf-8"))
    assert doc1["summary"]["normalized_result_sha256"] == \
        doc2["summary"]["normalized_result_sha256"]
    assert (out1 / "report.html").read_bytes() == \
        (out2 / "report.html").read_bytes()


def test_analyze_control_only_bundle_exits_0(tmp_path):
    bundle = _load_bundle(FAULT_TRACE)
    bundle["citations"] = [c for c in bundle["citations"]
                           if c["citation_id"] == "cite-control"]
    trace = _write_bundle(tmp_path, bundle)
    out = tmp_path / "control-only"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["summary"]["pass_count"] == 1
    assert report["summary"]["fail_count"] == 0
    assert report["results"][0]["verdict"] == "PASS"


def test_analyze_snippets_default_excerpt_vs_opt_in(tmp_path):
    # The frozen fixture quotes are short (23 chars), below the
    # 40-char excerpt threshold, so build a bundle variant with a
    # long quote: it becomes UNLOCATABLE (not found verbatim) but
    # the HTML entry still carries the bundle's quote text, which
    # is exactly what the snippet policy governs.
    bundle = _load_bundle(FAULT_TRACE)
    long_quote = "关键引文po-ext-01：" + "页码漂移误导定位，" * 10
    assert len(long_quote) > 40
    for citation in bundle["citations"]:
        if citation["citation_id"] == "cite-fault":
            citation["quote_text"] = long_quote
    trace = _write_bundle(tmp_path, bundle, "long-quote.trace.json")
    out_default = tmp_path / "default"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out_default))
    assert proc.returncode == 1
    html_default = (out_default / "report.html").read_text(encoding="utf-8")
    assert long_quote not in html_default
    assert long_quote[:40] in html_default  # excerpt present
    out_full = tmp_path / "full"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out_full),
                   "--include-snippets")
    assert proc.returncode == 1
    html_full = (out_full / "report.html").read_text(encoding="utf-8")
    assert long_quote in html_full
    # The JSON report never carries quote text, with or without the flag.
    for out in (out_default, out_full):
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        assert not any("quote_text" in r for r in report["results"])


def test_analyze_missing_stage_reports_unknown_without_guessing(tmp_path):
    bundle = _load_bundle(FAULT_TRACE)
    del bundle["stages"]["display"]
    bundle["stages"]["missing_stages"] = ["display"]
    trace = _write_bundle(tmp_path, bundle)
    out = tmp_path / "no-display"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out))
    # Analysis completed (not a crash): exit 1, UNKNOWN verdict,
    # first_fault_stage stays null — no stage is guessed.
    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    validate_report_schema(report)
    assert report["summary"]["unknown_count"] == 2
    for result in report["results"]:
        assert result["verdict"] == "UNKNOWN_TRACE_MISSING"
        assert result["first_fault_stage"] is None
        assert result["fault_type"] is None
    assert "first_fault_stage=None (UNKNOWN, not guessed)" in proc.stdout


def test_analyze_hash_mismatch_exits_2(tmp_path):
    out = tmp_path / "mismatch"
    proc = run_cli("analyze", "--pdf", str(OTHER_PDF), "--trace",
                   str(FAULT_TRACE), "--out", str(out))
    assert proc.returncode == 2
    assert "INPUT_HASH_MISMATCH" in proc.stderr
    assert not (out / "report.json").exists()


def test_analyze_missing_pdf_exits_2(tmp_path):
    proc = run_cli("analyze", "--pdf", str(tmp_path / "nope.pdf"),
                   "--trace", str(FAULT_TRACE),
                   "--out", str(tmp_path / "out"))
    assert proc.returncode == 2


def test_analyze_crash_is_distinct_from_analysis_fail(tmp_path):
    # --out pointing at an existing *file* breaks report writing:
    # an internal error, exit 3 — never confused with the analysis
    # FAIL exit code 1.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(FAULT_TRACE), "--out", str(blocker))
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "Traceback" in proc.stderr


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def test_validate_ok_with_hash(tmp_path):
    proc = run_cli("validate", "--trace", str(FAULT_TRACE),
                   "--pdf", str(FAULT_PDF))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VALID" in proc.stdout
    assert "document hash: MATCH" in proc.stdout


def test_validate_without_pdf_skips_hash_check():
    proc = run_cli("validate", "--trace", str(FAULT_TRACE))
    assert proc.returncode == 0
    assert "document hash" not in proc.stdout


def test_validate_hash_mismatch_exits_2():
    proc = run_cli("validate", "--trace", str(FAULT_TRACE),
                   "--pdf", str(OTHER_PDF))
    assert proc.returncode == 2
    assert "INPUT_HASH_MISMATCH" in proc.stderr


def test_validate_malformed_bundle_exits_2(tmp_path):
    bad = tmp_path / "bad.trace.json"
    bad.write_text("{not json", encoding="utf-8")
    proc = run_cli("validate", "--trace", str(bad))
    assert proc.returncode == 2


def test_validate_missing_trace_exits_2(tmp_path):
    proc = run_cli("validate", "--trace", str(tmp_path / "nope.json"))
    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------
def _make_output_dir(tmp_path: Path, name: str = "case-001") -> Path:
    out = tmp_path / name
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(FAULT_TRACE), "--out", str(out))
    assert proc.returncode == 1
    return out


def test_clean_dry_run_shows_target_and_deletes_nothing(tmp_path):
    out = _make_output_dir(tmp_path)
    proc = run_cli("clean", "--dry-run", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # T013 P2-01: clean echoes the target exactly as given, never the
    # resolved absolute path.
    assert f"TARGET: {out}" in proc.stdout
    assert "DRY RUN: nothing deleted" in proc.stdout
    assert out.is_dir()  # still there


def test_clean_relative_target_prints_verbatim_not_absolute(tmp_path):
    """T013 P2-01: with a relative target, stdout must contain the
    verbatim relative path and no resolved absolute path (§13)."""
    out = _make_output_dir(tmp_path)
    proc = run_cli("clean", "--dry-run", "case-001", cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "TARGET: case-001" in proc.stdout
    assert str(out.resolve()) not in proc.stdout
    assert out.is_dir()  # still there


def test_clean_removes_marker_directory(tmp_path):
    out = _make_output_dir(tmp_path)
    proc = run_cli("clean", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"TARGET: {out}" in proc.stdout
    assert f"REMOVED: {out}" in proc.stdout
    assert not out.exists()


def test_clean_refuses_non_marker_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "notes.txt").write_text("not a pagetrace output",
                                     encoding="utf-8")
    proc = run_cli("clean", str(plain))
    assert proc.returncode == 2
    assert "not a verified PageTrace output directory" in proc.stderr
    assert plain.is_dir()  # untouched


def test_clean_refuses_protected_paths():
    proc = run_cli("clean", "--dry-run", str(FIXTURES))
    assert proc.returncode == 2
    assert "protected path" in proc.stderr
    proc = run_cli("clean", "--dry-run", str(PACKAGE_ROOT))
    assert proc.returncode == 2
    assert "protected path" in proc.stderr


def test_clean_missing_directory_exits_2(tmp_path):
    proc = run_cli("clean", str(tmp_path / "nope"))
    assert proc.returncode == 2


def test_clean_refuses_unrelated_report_html_directory(tmp_path):
    """FIX-R1 (P1-R1-03, GPT repro): an unrelated directory that merely
    contains a generic report.html must NOT be deleted."""
    unrelated = tmp_path / "unrelated-report-folder"
    unrelated.mkdir()
    (unrelated / "report.html").write_text(
        "<html><body>unrelated</body></html>", encoding="utf-8")
    (unrelated / "keep.txt").write_text("do not delete me",
                                        encoding="utf-8")
    proc = run_cli("clean", str(unrelated))
    assert proc.returncode == 2
    assert "not a verified PageTrace output directory" in proc.stderr
    assert (unrelated / "report.html").is_file()
    assert (unrelated / "keep.txt").read_text(
        encoding="utf-8") == "do not delete me"


def test_clean_dry_run_refuses_unrelated_directory(tmp_path):
    unrelated = tmp_path / "unrelated-report-folder"
    unrelated.mkdir()
    (unrelated / "report.html").write_text("unrelated", encoding="utf-8")
    (unrelated / "S0_REPORT.json").write_text(
        json.dumps({"format": "pagetrace.s0-report/v1"}),
        encoding="utf-8")
    proc = run_cli("clean", "--dry-run", str(unrelated))
    assert proc.returncode == 2
    assert unrelated.is_dir()
    assert (unrelated / "report.html").is_file()
    assert (unrelated / "S0_REPORT.json").is_file()


def test_clean_refuses_arbitrary_s0_report_json(tmp_path):
    """FIX-R1 (P1-R1-03): any S0_REPORT.json is not a marker — the
    format/project/gates/counts/replay cross-checks must all hold."""
    fake = tmp_path / "fake-s0"
    fake.mkdir()
    (fake / "S0_REPORT.json").write_text(json.dumps({
        "format": "pagetrace.s0-report/v1",
        "project": "P026 PageTrace",
        "s0_result": "PASS",
        "suite": {"case_count": 48, "repeat": 1},
        "counts": {"detection": 48},
        "gates": {},
        "replay": {"hashes": ["a" * 64], "unique_hashes": ["a" * 64],
                   "unique_hash_count": 1},
    }), encoding="utf-8")
    (fake / "keep.txt").write_text("do not delete me", encoding="utf-8")
    proc = run_cli("clean", str(fake))
    assert proc.returncode == 2
    assert "not a verified PageTrace output directory" in proc.stderr
    assert fake.is_dir()
    assert (fake / "keep.txt").is_file()


def test_clean_refuses_schema_only_report_json(tmp_path):
    """FIX-R1 (P1-R1-03): a report.json that only carries the right
    schema string (no tool identity, no recomputable normalised
    hash, no report.html) is not a marker."""
    fake = tmp_path / "fake-report"
    fake.mkdir()
    (fake / "report.json").write_text(json.dumps({
        "schema": "pagetrace.report/v1",
        "case_id": "fake-case",
        "document": {"file_name": "fake.pdf",
                     "sha256": "a" * 64, "page_count": 1},
        "tool": {"name": "pagetrace", "version": "0.1.0"},
        "results": [],
        "summary": {"total_citations": 0, "pass_count": 0,
                    "fail_count": 0, "unknown_count": 0,
                    "ambiguous_count": 0,
                    "normalized_result_sha256": "b" * 64},
    }), encoding="utf-8")
    (fake / "keep.txt").write_text("do not delete me", encoding="utf-8")
    proc = run_cli("clean", str(fake))
    assert proc.returncode == 2
    assert fake.is_dir()
    assert (fake / "keep.txt").is_file()


def test_clean_refuses_tampered_report_json(tmp_path):
    """FIX-R1 (P1-R1-03): a real analyze output whose report.json was
    tampered with afterwards (summary counts no longer derived from
    the results) is refused, untouched."""
    out = _make_output_dir(tmp_path)
    report_path = out / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["summary"]["pass_count"] += 1  # no longer derived from results
    report_path.write_text(json.dumps(report, ensure_ascii=False,
                                     sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    proc = run_cli("clean", str(out))
    assert proc.returncode == 2
    assert "not a verified PageTrace output directory" in proc.stderr
    assert out.is_dir()
    assert report_path.is_file()


def test_clean_refuses_tampered_report_hash(tmp_path):
    """FIX-R1 (P1-R1-03): a real analyze output whose results were
    edited (normalised hash no longer recomputes) is refused."""
    out = _make_output_dir(tmp_path)
    report_path = out / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["results"][0]["verdict"] = "PASS"
    report_path.write_text(json.dumps(report, ensure_ascii=False,
                                     sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    proc = run_cli("clean", str(out))
    assert proc.returncode == 2
    assert out.is_dir()
    assert report_path.is_file()


def test_clean_removes_verified_s0_output(tmp_path):
    """FIX-R1 (P1-R1-03): a real S0 output directory (self-consistent
    S0_REPORT.json + matching replay-hashes.txt) is still cleanable."""
    out = tmp_path / "s0"
    proc = run_cli("s0", "--suite", str(FIXTURES), "--repeat", "1",
                   "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "S0_REPORT.json").is_file()
    assert (out / "replay-hashes.txt").is_file()
    proc = run_cli("clean", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"REMOVED: {out}" in proc.stdout
    assert not out.exists()


# ---------------------------------------------------------------------------
# s0
# ---------------------------------------------------------------------------
def test_s0_repeat_1_smoke_pass(tmp_path):
    """FIX-R1 (GPT R1 §4): --repeat 1 passes the gates but is only a
    smoke run — S0_RESULT is SMOKE_PASS, exit 0, never formal PASS."""
    out = tmp_path / "s0"
    proc = run_cli("s0", "--suite", str(FIXTURES), "--repeat", "1",
                   "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "S0_RESULT: SMOKE_PASS" in proc.stdout
    report = json.loads((out / "S0_REPORT.json").read_text(encoding="utf-8"))
    assert report["s0_result"] == "SMOKE_PASS"
    assert report["counts"]["detection"] == 48
