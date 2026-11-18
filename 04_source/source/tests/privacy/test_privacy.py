"""T011 — privacy regression tests (PROJECT_BOOK §13).

Run from PACKAGE_ROOT, inside the venv::

    TMPDIR=$PWD/.tmp .venv/bin/python -m pytest tests/privacy/test_privacy.py -q

These tests scan the *real artefacts* the pipeline writes —
``report.json``, ``report.html`` + assets, CLI stdout/stderr and
the S0 report — for the things §13 forbids by default.  They do
not merely assert a configuration flag.

Forbidden by default (§13):

* full quote text in any report: JSON never carries ``quote_text``
  (only ``quote_sha256``); HTML carries at most a 40-character
  excerpt unless ``--include-snippets`` is given explicitly;
* absolute paths, hostnames, usernames or timestamps in reports,
  logs or CLI output;
* any network request, and any copy/upload of the user's PDF.

Note on the frozen fixtures: their quotes are short (<= 40 chars),
so for them the default excerpt *is* the whole short quote — that
is the excerpt rule working as specified, not a leak.  The
truncation proof therefore uses a long-quote bundle variant (the
same construction T009 uses): only a > 40-char quote can show
that the tail is withheld by default and released only on opt-in.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PACKAGE_ROOT.parents[1]
FIXTURES = PACKAGE_ROOT / "fixtures"
SRC = PACKAGE_ROOT / "src" / "pagetrace"
VENV_PYTHON = PACKAGE_ROOT / ".venv" / "bin" / "python"
S0_BASELINE = REPO_ROOT / "05_tests" / "s0" / "S0_REPORT.json"

sys.path.insert(0, str(PACKAGE_ROOT / "src"))

FAULT_TRACE = FIXTURES / "bundles" / "po-ext-01.trace.json"
FAULT_PDF = FIXTURES / "pdfs" / "po-ext-01.pdf"

HOSTNAME = socket.gethostname()
HOME = str(Path.home())
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")

# A long, unique quote: head (first 40 chars, allowed as excerpt),
# tail (must never appear by default) and the full string.
LONG_QUOTE = (
    "T011-PRIVACY-SENTINEL-甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
    "页码漂移误导定位，重复文本造成歧义，元数据缺失无法确认页码。"
    "T011-PRIVACY-SENTINEL-TAIL-0123456789abcdef"
)
assert len(LONG_QUOTE) > 40
QUOTE_TAIL = LONG_QUOTE[60:]


def run_cli(*argv: str, cwd: Path = PACKAGE_ROOT) -> subprocess.CompletedProcess:
    """Run ``python -m pagetrace.cli`` as a subprocess."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    env["PYTHONSAFEPATH"] = "1"
    python = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    return subprocess.run(
        [python, "-m", "pagetrace.cli", *argv],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=300)


def long_quote_trace(tmp_path: Path) -> Path:
    """po-ext-01 bundle with the fault citation's quote replaced by
    a long sentinel quote (> 40 chars).  The quote becomes
    UNLOCATABLE in the PDF text layer, but the HTML entry still
    carries the bundle's quote text — which is exactly what the
    snippet policy governs (same construction as T009)."""
    bundle = json.loads(FAULT_TRACE.read_text(encoding="utf-8"))
    for citation in bundle["citations"]:
        if citation["citation_id"] == "cite-fault":
            citation["quote_text"] = LONG_QUOTE
    trace = tmp_path / "long-quote.trace.json"
    trace.write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return trace


def analyze_long_quote(tmp_path: Path, *extra: str):
    trace = long_quote_trace(tmp_path)
    out = tmp_path / ("out-" + ("optin" if extra else "default"))
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out), *extra)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    return out, proc


def assert_no_leaks(text: str, where: str) -> None:
    assert "/home/" not in text, f"{where} leaks an absolute path"
    assert HOME not in text, f"{where} leaks the home directory"
    assert HOSTNAME not in text, f"{where} leaks the hostname"
    assert TIMESTAMP_RE.search(text) is None, (
        f"{where} leaks a timestamp")


# ---------------------------------------------------------------------------
# full quote text: JSON never, HTML only on explicit opt-in
# ---------------------------------------------------------------------------
def test_privacy_json_never_carries_quote_text(tmp_path):
    for extra in ((), ("--include-snippets",)):
        out, _ = analyze_long_quote(tmp_path, *extra)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        raw = (out / "report.json").read_text(encoding="utf-8")
        assert "quote_text" not in raw
        assert LONG_QUOTE not in raw
        assert QUOTE_TAIL not in raw
        assert not any("quote_text" in r for r in report["results"])
        assert all(r.get("quote_sha256") for r in report["results"])


def test_privacy_default_html_excerpt_only(tmp_path):
    out, _ = analyze_long_quote(tmp_path)
    html_text = (out / "report.html").read_text(encoding="utf-8")
    assert LONG_QUOTE not in html_text, "default HTML leaks the full quote"
    assert QUOTE_TAIL not in html_text, "default HTML leaks the quote tail"
    assert LONG_QUOTE[:40] in html_text, "40-char excerpt must be present"
    assert "…" in html_text, "excerpt must be marked with an ellipsis"


def test_privacy_opt_in_html_full_but_json_still_clean(tmp_path):
    out, _ = analyze_long_quote(tmp_path, "--include-snippets")
    html_text = (out / "report.html").read_text(encoding="utf-8")
    assert LONG_QUOTE in html_text, "--include-snippets must show full quote"
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert "quote_text" not in json.dumps(report, ensure_ascii=False)


def test_privacy_frozen_fixture_quotes_are_short_by_design():
    """Frozen quotes are <= 40 chars, so their default excerpt is
    the whole quote by the excerpt rule itself — not a leak.  The
    long-quote tests above are the real truncation proof."""
    bundle = json.loads(FAULT_TRACE.read_text(encoding="utf-8"))
    for citation in bundle["citations"]:
        assert len(citation["quote_text"]) <= 40, (
            f"{citation['citation_id']} quote longer than the excerpt "
            "limit; the truncation proof would be vacuous")


# ---------------------------------------------------------------------------
# absolute paths / hostname / timestamps in real artefacts
# ---------------------------------------------------------------------------
def test_privacy_no_leaks_in_report_artifacts(tmp_path):
    out, proc = analyze_long_quote(tmp_path)
    for name in ("report.json", "report.html"):
        assert_no_leaks((out / name).read_text(encoding="utf-8"), name)
    for asset in ("report.css", "report.js"):
        assert_no_leaks(
            (out / "assets" / asset).read_text(encoding="utf-8"),
            f"assets/{asset}")
    # CLI stdout/stderr of this run used absolute tmp paths as
    # arguments, so it legitimately echoes them; the *artefacts*
    # above must not.  The relative-path CLI output is covered by
    # the next test.
    assert LONG_QUOTE not in proc.stdout
    assert QUOTE_TAIL not in proc.stdout


def test_privacy_cli_output_with_relative_paths_has_no_leaks(tmp_path):
    """Invoked with relative paths (the documented usage), CLI
    stdout/stderr must contain no absolute path or hostname."""
    out_dir = PACKAGE_ROOT / "out-t011-privacy"
    try:
        proc = run_cli("analyze", "--pdf",
                       "fixtures/pdfs/po-ext-01.pdf",
                       "--trace", "fixtures/bundles/po-ext-01.trace.json",
                       "--out", "out-t011-privacy")
        assert proc.returncode == 1, proc.stdout + proc.stderr
        combined = proc.stdout + proc.stderr
        assert "/home/" not in combined
        assert HOME not in combined
        assert HOSTNAME not in combined
        assert TIMESTAMP_RE.search(combined) is None
        assert_no_leaks(
            (out_dir / "report.json").read_text(encoding="utf-8"),
            "relative-path report.json")
        assert_no_leaks(
            (out_dir / "report.html").read_text(encoding="utf-8"),
            "relative-path report.html")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_privacy_s0_baseline_report_has_no_leaks():
    assert S0_BASELINE.is_file()
    raw = S0_BASELINE.read_text(encoding="utf-8")
    assert_no_leaks(raw, "S0_REPORT.json")
    assert "generated_at" not in raw
    hashes = (S0_BASELINE.parent / "replay-hashes.txt").read_text(
        encoding="utf-8")
    assert_no_leaks(hashes, "replay-hashes.txt")
    assert set(hashes.split()) == {
        "a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3"}


def test_privacy_report_json_has_no_timestamp_field(tmp_path):
    out, _ = analyze_long_quote(tmp_path)
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert "generated_at" not in report
    assert TIMESTAMP_RE.search(
        json.dumps(report, ensure_ascii=False)) is None


# ---------------------------------------------------------------------------
# no network, no upload, no PDF copy (§13 / §14 privacy gate)
# ---------------------------------------------------------------------------
def test_privacy_no_network_code_in_production_source():
    forbidden = ("import socket", "import urllib", "import requests",
                 "import httpx", "http.client", "socketserver",
                 "urlopen", "requests.get", "requests.post")
    for path in sorted(SRC.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token!r}"


def test_privacy_report_has_no_external_requests(tmp_path):
    out, _ = analyze_long_quote(tmp_path)
    for name in ("report.html",):
        html_text = (out / name).read_text(encoding="utf-8")
        assert "http://" not in html_text
        assert "https://" not in html_text
        assert "fetch(" not in html_text
        assert "XMLHttpRequest" not in html_text
        # Only the local relative asset is referenced; no external
        # script source.
        assert '<script src="http' not in html_text
        assert '<script src="https' not in html_text
        assert '<script src="//' not in html_text
    for asset in ("report.css", "report.js"):
        text = (out / "assets" / asset).read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, asset
        assert "fetch(" not in text and "XMLHttpRequest" not in text, asset


def test_privacy_pdf_not_copied_or_uploaded(tmp_path):
    out, _ = analyze_long_quote(tmp_path)
    assert not list(out.rglob("*.pdf")), "source PDF copied into output"
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    document = report["document"]
    assert document["file_name"] == "po-ext-01.pdf"
    assert "/" not in document["file_name"]
    assert document["sha256"] == (
        "97d1f68a573e09c9b6fc519dde6d37ee25158ee4f6673488770e2debef7cb9cf")
