"""T011 — end-to-end integration tests (PDF + trace -> JSON/HTML report).

Run from PACKAGE_ROOT, inside the venv::

    TMPDIR=$PWD/.tmp .venv/bin/python -m pytest tests/e2e/test_e2e.py -q

The CLI is exercised as a real subprocess (``python -m
pagetrace.cli``) with the production import path (``PYTHONPATH=src``
+ ``PYTHONSAFEPATH=1``; see ``docs/CLI.md``).  Nothing here is a
mock: every report is produced by the production pipeline over the
frozen fixtures.

Checks (PROJECT_BOOK §9/§12/§14, TASK-011 hard assertions):

* full chain, one case per fault class (PAGE_OFFSET,
  PAGE_METADATA_MISSING, DUPLICATE_TEXT_AMBIGUITY, UNLOCATABLE):
  ``analyze`` exits 1, ``report.json`` is a schema-valid
  ``pagetrace.report/v1`` document with the expected verdict /
  fault type / first-fault stage, and ``report.html`` carries the
  four columns with every field present;
* a control-only bundle analyses to exit 0;
* the chain is deterministic: two runs give the same normalised
  result hash and byte-identical HTML;
* exit-code matrix: hash mismatch / missing PDF / missing trace
  all exit 2 (input invalid), distinct from analysis FAIL (1)
  and tool crash (3);
* DNS-blocked browser render: the report renders from ``file://``
  with every DNS lookup refused, four columns present, no
  external URL in the rendered DOM;
* S0 baseline invariance: the frozen ``05_tests/s0/S0_REPORT.json``
  still shows 48/48 detection, 48/48 first-fault stages, 0 control
  false positives, 96/96 parity and the single frozen replay hash
  (the full 100-replay re-run is the acceptance command, run
  separately into ``05_tests/s0-final``).
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PACKAGE_ROOT.parents[1]
FIXTURES = PACKAGE_ROOT / "fixtures"
VENV_PYTHON = PACKAGE_ROOT / ".venv" / "bin" / "python"
S0_BASELINE = REPO_ROOT / "05_tests" / "s0" / "S0_REPORT.json"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.contracts import validate_report_schema  # noqa: E402

# case_id -> (expected verdict, fault type, first-fault stage)
FAULT_CASES = {
    "po-ext-01": ("FAIL_PAGE_OFFSET", "PAGE_OFFSET", "extraction"),
    "mm-ext-01": ("FAIL_METADATA_MISSING", "PAGE_METADATA_MISSING",
                  "extraction"),
    "du-chk-01": ("FAIL_AMBIGUOUS", "DUPLICATE_TEXT_AMBIGUITY",
                  "chunking"),
    "un-ext-01": ("FAIL_UNLOCATABLE", "UNLOCATABLE", "extraction"),
}

FOUR_COLUMN_HEADINGS = (
    "① PDF 真值", "② 抽取", "③ 分片与索引", "④ 最终引用",
)

# Every field the four columns + comparison table need (§9.2).
ENTRY_FIELDS = (
    "entry_id", "case_id", "citation_id", "quote_text",
    "quote_sha256", "verdict", "fault_type", "first_fault_stage",
    "observed_page_value", "citation_page_basis",
    "correct_pdf_page_number1", "correct_viewer_page1",
    "candidate_source_pages0", "expected_source_pages0",
    "document", "truth_pages", "extraction", "chunk",
    "index_record", "display", "stage_diffs", "extraction_diffs",
)

EXPECTED_REPLAY_HASH = (
    "a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3"
)


def run_cli(*argv: str, cwd: Path = PACKAGE_ROOT) -> subprocess.CompletedProcess:
    """Run ``python -m pagetrace.cli`` as a subprocess."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    env["PYTHONSAFEPATH"] = "1"
    python = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    return subprocess.run(
        [python, "-m", "pagetrace.cli", *argv],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=300)


def analyze(case_id: str, out: Path) -> subprocess.CompletedProcess:
    return run_cli(
        "analyze",
        "--pdf", str(FIXTURES / "pdfs" / f"{case_id}.pdf"),
        "--trace", str(FIXTURES / "bundles" / f"{case_id}.trace.json"),
        "--out", str(out))


def load_report(out: Path) -> dict:
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    validate_report_schema(report)
    return report


def embedded_document(html_text: str) -> dict:
    match = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>',
        html_text, re.DOTALL)
    assert match, "embedded #report-data block missing"
    return json.loads(match.group(1))


def headless_shell() -> Path | None:
    # Newest cached shell first: the older 1248 build mishandles
    # extra flags (it reads a space-separated flag value as a
    # second target); 1254 handles --host-resolver-rules correctly.
    candidates = sorted(Path.home().glob(
        ".cache/ms-playwright/chromium_headless_shell-*/"
        "chrome-headless-shell-linux64/chrome-headless-shell"),
        reverse=True)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# full chain, one case per fault class
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case_id,expected", sorted(FAULT_CASES.items()))
def test_e2e_fault_case_full_chain(case_id, expected, tmp_path):
    verdict, fault_type, first_stage = expected
    out = tmp_path / case_id
    proc = analyze(case_id, out)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = load_report(out)
    assert report["schema"] == "pagetrace.report/v1"
    assert report["case_id"] == case_id
    assert report["summary"]["total_citations"] == 2
    fault, control = report["results"]
    assert (fault["citation_id"], fault["verdict"], fault["fault_type"],
            fault["first_fault_stage"]) == (
                "cite-fault", verdict, fault_type, first_stage)
    assert (control["citation_id"], control["verdict"]) == (
        "cite-control", "PASS")
    assert fault["quote_sha256"] and control["quote_sha256"]
    # HTML report exists with its assets; no PDF copied into the output.
    html_path = out / "report.html"
    assert html_path.is_file()
    assert (out / "assets" / "report.css").is_file()
    assert (out / "assets" / "report.js").is_file()
    assert not list(out.rglob("*.pdf")), "source PDF must not be copied"
    assert verdict in html_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("case_id,expected", sorted(FAULT_CASES.items()))
def test_e2e_four_columns_fields_complete(case_id, expected, tmp_path):
    """Every four-column field is present in the embedded report data."""
    out = tmp_path / case_id
    proc = analyze(case_id, out)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    html_text = (out / "report.html").read_text(encoding="utf-8")
    for heading in FOUR_COLUMN_HEADINGS:
        assert heading in html_text, f"column heading {heading!r} missing"
    assert "对照表：错误页码 → 首错阶段 → 正确来源位置" in html_text
    document = embedded_document(html_text)
    assert document["schema"] == "pagetrace.report/v1"
    assert len(document["entries"]) == 2
    by_id = {e["citation_id"]: e for e in document["entries"]}
    fault = by_id["cite-fault"]
    for field in ENTRY_FIELDS:
        assert field in fault, f"entry field {field!r} missing"
    # Truth column is the honest extraction; extraction column keeps
    # the observed (faulty) records; chunk/index/display are separate.
    assert fault["truth_pages"], "truth column empty"
    assert fault["extraction"], "extraction column empty"
    assert fault["chunk"] is not None, "chunk column missing"
    assert fault["index_record"] is not None, "index column missing"
    assert fault["display"] is not None, "display column missing"
    assert fault["stage_diffs"], "comparison evidence empty"
    assert fault["document"]["file_name"] == f"{case_id}.pdf"
    assert "/" not in fault["document"]["file_name"]
    # The comparison table carries wrong page + first-fault stage +
    # correct source location together for the fault entry.
    assert fault["observed_page_value"] is not None
    assert fault["first_fault_stage"] == expected[2]
    summary = document["summary"]
    assert summary["total_citations"] == 2
    assert summary["pass_count"] == 1 and summary["fail_count"] == 1


def test_e2e_control_only_bundle_exits_0(tmp_path):
    bundle = json.loads(
        (FIXTURES / "bundles" / "po-ext-01.trace.json").read_text(
            encoding="utf-8"))
    bundle["citations"] = [c for c in bundle["citations"]
                           if c["citation_id"] == "cite-control"]
    trace = tmp_path / "control-only.trace.json"
    trace.write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    out = tmp_path / "control-only"
    proc = run_cli("analyze", "--pdf",
                   str(FIXTURES / "pdfs" / "po-ext-01.pdf"),
                   "--trace", str(trace), "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = load_report(out)
    assert report["summary"] == {
        "total_citations": 1, "pass_count": 1, "fail_count": 0,
        "unknown_count": 0, "ambiguous_count": 0,
        "normalized_result_sha256": report["summary"][
            "normalized_result_sha256"],
    }


def test_e2e_deterministic_across_runs(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    for out in (out1, out2):
        proc = analyze("po-ext-01", out)
        assert proc.returncode == 1, proc.stdout + proc.stderr
    doc1, doc2 = load_report(out1), load_report(out2)
    assert doc1["summary"]["normalized_result_sha256"] == \
        doc2["summary"]["normalized_result_sha256"]
    assert doc1 == doc2
    assert (out1 / "report.html").read_bytes() == \
        (out2 / "report.html").read_bytes()


# ---------------------------------------------------------------------------
# exit-code matrix (§12.2)
# ---------------------------------------------------------------------------
def test_e2e_hash_mismatch_exits_2(tmp_path):
    out = tmp_path / "mismatch"
    proc = run_cli("analyze", "--pdf",
                   str(FIXTURES / "pdfs" / "po-ext-02.pdf"),
                   "--trace",
                   str(FIXTURES / "bundles" / "po-ext-01.trace.json"),
                   "--out", str(out))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "INPUT_HASH_MISMATCH" in proc.stdout + proc.stderr
    assert not (out / "report.json").exists()


def test_e2e_missing_inputs_exit_2(tmp_path):
    out = tmp_path / "missing"
    proc = run_cli("analyze", "--pdf",
                   str(FIXTURES / "pdfs" / "no-such.pdf"),
                   "--trace",
                   str(FIXTURES / "bundles" / "po-ext-01.trace.json"),
                   "--out", str(out))
    assert proc.returncode == 2
    proc = run_cli("analyze", "--pdf",
                   str(FIXTURES / "pdfs" / "po-ext-01.pdf"),
                   "--trace", str(FIXTURES / "bundles" / "no-such.json"),
                   "--out", str(out))
    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# DNS-blocked browser render (offline proof, not just a static scan)
# ---------------------------------------------------------------------------
def test_e2e_dns_blocked_browser_renders_four_columns(tmp_path):
    binary = headless_shell()
    if binary is None:
        pytest.skip("no cached headless shell available")
    out = tmp_path / "po-ext-01"
    proc = analyze("po-ext-01", out)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    url = (out / "report.html").as_uri()
    result = subprocess.run(
        [str(binary), "--headless", "--disable-gpu", "--no-sandbox",
         # NOTE: the "=" form is required: with a space-separated
         # value the headless shell reads "MAP * ~NOTFOUND" as a
         # second target ("Multiple targets are not supported").
         "--host-resolver-rules=MAP * ~NOTFOUND",
         "--virtual-time-budget=5000", "--dump-dom", url],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[:2000]
    dom = result.stdout
    for fragment in FOUR_COLUMN_HEADINGS + (
            "po-ext-01/cite-fault", "FAIL — 页码偏移",
            "错误页码", "正确来源位置"):
        assert fragment in dom, f"DNS-blocked DOM missing {fragment!r}"
    assert "http://" not in dom and "https://" not in dom, (
        "rendered DOM contains an external URL")


# ---------------------------------------------------------------------------
# S0 baseline invariance (full 100-replay re-run is the acceptance
# command, executed separately into 05_tests/s0-final)
# ---------------------------------------------------------------------------
def test_e2e_s0_baseline_unchanged():
    assert S0_BASELINE.is_file(), "frozen S0 baseline report missing"
    baseline = json.loads(S0_BASELINE.read_text(encoding="utf-8"))
    assert baseline["s0_result"] == "PASS"
    assert baseline["counts"] == {
        "control_false_positives": 0,
        "detection": 48,
        "first_fault_stage": 48,
        "golden_mismatches": 0,
        "parity_citations_matching": 96,
        "parity_mismatches": 0,
        "replay_unique_hashes": 1,
        "uncertainty_violations": 0,
    }
    assert baseline["replay"]["unique_hashes"] == [EXPECTED_REPLAY_HASH]
    raw = S0_BASELINE.read_text(encoding="utf-8")
    assert "/home/" not in raw
    assert socket.gethostname() not in raw
