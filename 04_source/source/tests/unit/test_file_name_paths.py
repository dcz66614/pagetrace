"""FIX-R1 (P1-R1-04, R-11) — ``document.file_name`` must be a bare file name.

Run from PACKAGE_ROOT, inside the venv::

    python -m pytest tests/unit/test_file_name_paths.py -q

Covers the GPT R1 repro and its variants at three layers:

* :func:`pagetrace.trace_bundle.is_bare_file_name` — the runtime
  predicate (POSIX absolute, Windows drive / drive-relative, UNC,
  relative-directory forms, and bare ``.`` / ``..`` all rejected;
  plain file names accepted);
* :func:`pagetrace.trace_bundle.parse_bundle` — schema + runtime
  dual rejection, and the rejection error never echoes the
  offending path back (path minimisation, §13);
* the CLI (``validate`` / ``analyze``) — the GPT repro step: a
  bundle whose ``file_name`` is
  ``/home/alice/private/contracts/secret.pdf`` exits 2, prints no
  absolute path on stdout/stderr, and writes no ``report.json``.

Note: a *direct* ``validate_bundle_schema`` call reports the
offending instance value inside jsonschema's own message text.
The CLI never takes that path — ``TraceBundle`` pre-checks
``file_name`` before the schema layer runs and redacts any schema
error that mentions it — so the no-leak assertions below are made
against ``parse_bundle`` and the CLI, not against the raw schema
validator.
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

from pagetrace.contracts import (  # noqa: E402
    PageSemanticsError,
    validate_bundle_schema,
)
from pagetrace.trace_bundle import (  # noqa: E402
    is_bare_file_name,
    parse_bundle,
)

FAULT_TRACE = FIXTURES / "bundles" / "po-ext-01.trace.json"
FAULT_PDF = FIXTURES / "pdfs" / "po-ext-01.pdf"

#: Every directory / absolute-path spelling R-11 must refuse.
REJECTED_FILE_NAMES = [
    "/home/alice/private/contracts/secret.pdf",  # GPT R1 repro (POSIX)
    "/secret.pdf",                               # POSIX root-absolute
    "C:\\Users\\alice\\secret.pdf",              # Windows drive, backslash
    "C:/Users/alice/secret.pdf",                # Windows drive, slash
    "D:secret.pdf",                              # Windows drive-relative
    "\\\\server\\share\\secret.pdf",             # UNC, backslashes
    "//server/share/secret.pdf",                # UNC, slashes
    "../secret.pdf",                             # relative parent dir
    "..\\secret.pdf",                            # relative parent dir (win)
    "sub/secret.pdf",                            # relative subdir
    "sub\\secret.pdf",                           # relative subdir (win)
    "a/b/../c.pdf",                              # embedded dot-dot segment
    ".",                                         # bare directory reference
    "..",                                        # bare parent reference
    "\\secret.pdf",                              # leading backslash
]

#: Plain file names R-11 must keep accepting.
ACCEPTED_FILE_NAMES = [
    "secret.pdf",
    "my report (final).pdf",
    "a.b.c.pdf",
    "x.pdf",
    "ab:c.pdf",  # colon after the first char is not a drive letter
]


def _bundle_with_file_name(file_name: str) -> dict:
    bundle = json.loads(FAULT_TRACE.read_text(encoding="utf-8"))
    bundle["document"]["file_name"] = file_name
    return bundle


def run_cli(*argv: str, cwd: Path = PACKAGE_ROOT) -> subprocess.CompletedProcess:
    """Run ``python -m pagetrace.cli`` as a subprocess; return the result."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    env["PYTHONSAFEPATH"] = "1"
    python = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable
    return subprocess.run(
        [python, "-m", "pagetrace.cli", *argv],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=300)


# ---------------------------------------------------------------------------
# Runtime predicate
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", REJECTED_FILE_NAMES)
def test_is_bare_file_name_rejects_paths(name):
    assert is_bare_file_name(name) is False


@pytest.mark.parametrize("name", ACCEPTED_FILE_NAMES)
def test_is_bare_file_name_accepts_plain_names(name):
    assert is_bare_file_name(name) is True


@pytest.mark.parametrize("name", [None, 42, "", "a/b"])
def test_is_bare_file_name_rejects_non_names(name):
    assert is_bare_file_name(name) is False


# ---------------------------------------------------------------------------
# Bundle parsing: schema + runtime dual rejection, no echo of the path
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", REJECTED_FILE_NAMES)
def test_parse_bundle_rejects_path_file_name(name):
    with pytest.raises(PageSemanticsError) as excinfo:
        parse_bundle(_bundle_with_file_name(name))
    # The rejection names the rule, never the offending value: a
    # private absolute path must not leak into the error text.
    # ("." / ".." are too short to assert on as substrings — the
    # message legitimately contains sentence periods.)
    if len(name) > 3:
        assert name not in str(excinfo.value)


@pytest.mark.parametrize("name", REJECTED_FILE_NAMES)
def test_schema_layer_rejects_path_file_name(name):
    # Schema layer alone (pattern) rejects every form too; the
    # runtime pre-check in TraceBundle is what keeps the value out
    # of the reported error (see module docstring).
    with pytest.raises(PageSemanticsError):
        validate_bundle_schema(_bundle_with_file_name(name))


@pytest.mark.parametrize("name", ACCEPTED_FILE_NAMES)
def test_parse_bundle_accepts_plain_file_name(name):
    bundle = parse_bundle(_bundle_with_file_name(name))
    assert bundle.file_name == name


# ---------------------------------------------------------------------------
# CLI: GPT R1 repro steps, end to end
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", [
    "/home/alice/private/contracts/secret.pdf",
    "C:\\Users\\alice\\secret.pdf",
    "\\\\server\\share\\secret.pdf",
    "../secret.pdf",
])
def test_cli_validate_rejects_path_file_name(tmp_path, name):
    trace = tmp_path / "abs.trace.json"
    trace.write_text(json.dumps(_bundle_with_file_name(name),
                                ensure_ascii=False, indent=2),
                     encoding="utf-8")
    proc = run_cli("validate", "--trace", str(trace), "--pdf",
                   str(FAULT_PDF))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert name not in proc.stdout
    assert name not in proc.stderr


def test_cli_validate_gpt_repro_without_leak(tmp_path):
    """GPT R1 repro verbatim: validate must exit 2 and print no
    absolute path anywhere."""
    trace = tmp_path / "abs.trace.json"
    trace.write_text(json.dumps(
        _bundle_with_file_name("/home/alice/private/contracts/secret.pdf"),
        ensure_ascii=False, indent=2), encoding="utf-8")
    proc = run_cli("validate", "--trace", str(trace), "--pdf",
                   str(FAULT_PDF))
    assert proc.returncode == 2
    assert "VALID" not in proc.stdout
    assert "/home/alice/private/contracts/secret.pdf" not in proc.stdout
    assert "/home/alice/private/contracts/secret.pdf" not in proc.stderr
    assert "bare file name" in proc.stderr


def test_cli_analyze_rejects_absolute_path_without_leak(tmp_path):
    """GPT R1 repro, analyze step: no run, no report, no leak."""
    trace = tmp_path / "abs.trace.json"
    trace.write_text(json.dumps(
        _bundle_with_file_name("/home/alice/private/contracts/secret.pdf"),
        ensure_ascii=False, indent=2), encoding="utf-8")
    out = tmp_path / "abs-out"
    proc = run_cli("analyze", "--pdf", str(FAULT_PDF), "--trace",
                   str(trace), "--out", str(out))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "/home/alice/private/contracts/secret.pdf" not in proc.stdout
    assert "/home/alice/private/contracts/secret.pdf" not in proc.stderr
    assert not (out / "report.json").exists()
    assert not (out / "report.html").exists()


def test_cli_validate_accepts_bare_file_name():
    proc = run_cli("validate", "--trace", str(FAULT_TRACE),
                   "--pdf", str(FAULT_PDF))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VALID" in proc.stdout
