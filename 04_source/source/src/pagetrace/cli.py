"""P026 T009 — ``pagetrace`` command line interface.

Thin wrapper over the production modules; it implements no
locating / attribution logic of its own (PROJECT_BOOK §12):

* ``analyze`` — one PDF + one ``pagetrace.bundle/v1`` trace ->
  ``report.json`` (``pagetrace.report/v1``) + ``report.html``
  (T008 renderer) in an output directory.
* ``validate`` — bundle schema + runtime validation (T010), and,
  with ``--pdf``, the document-hash check against the real PDF.
  No analysis is run.
* ``s0`` — the frozen 48-case S0 gate (``tools/run_s0.py``);
  the CLI only forwards arguments and its exit code.
* ``clean`` — delete one explicitly named PageTrace output
  directory, after printing the target path. A directory is only
  deleted when it carries a *verified* PageTrace output marker (a
  self-consistent ``report.json`` whose normalised-result hash
  recomputes, corroborated by its ``report.html`` embedding and
  assets — or a self-consistent ``S0_REPORT.json`` whose counts
  match its gates and whose replay hashes match
  ``replay-hashes.txt``); a bare ``report.html``, a bare
  ``S0_REPORT.json``, or a schema-only ``report.json`` is refused,
  untouched (FIX-R1, P1-R1-03).

Exit codes (PROJECT_BOOK §12.2):

* 0 — command succeeded; for ``analyze`` that means every
  citation is PASS, for ``s0`` that means every S0 gate passed.
* 1 — the command ran to completion but the *analysis* contains
  FAIL / UNKNOWN / AMBIGUOUS / NEEDS_MANUAL_REVIEW results.
  This is a completed analysis, not a tool crash: it is
  deliberately different from exit 3.
* 2 — invalid input: unreadable / malformed bundle, schema or
  runtime validation failure, PDF unreadable / oversize /
  encrypted, or a document-hash mismatch
  (``INPUT_HASH_MISMATCH``). Also argparse usage errors.
* 3 — internal error / uncaught exception (tool crash).
* 4 — S0 gate failed (``s0`` only).

Uncertainty is never converted to PASS: a citation whose trace
is missing (``UNKNOWN_TRACE_MISSING``) is reported with
``first_fault_stage`` null and the analysis exits 1; no stage
is ever guessed.

Packaging (T013 P2-08): single src layout. ``pyproject.toml`` installs
``src/pagetrace/`` (with its report assets), so after ``pip install .``
the CLI runs from any directory with no ``PYTHONPATH``::

    .venv/bin/python -m pagetrace.cli --help

The ``sys.path.insert(0, "src")`` below is kept as a source-checkout
fallback, so running from PACKAGE_ROOT without installing still works.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import traceback
from pathlib import Path

# PACKAGE_ROOT is the parent of src/ (this file is src/pagetrace/cli.py).
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

# Import-path rule (see module docstring): src/ first as a
# source-checkout fallback (the installed package already wins
# once `pip install .` has run; T013 P2-08).
if str(PACKAGE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pagetrace.compare_stages import analyze_bundle, compare_extraction  # noqa: E402
from pagetrace.contracts import (  # noqa: E402
    BundleValidationError,
    PageSemanticsError,
    validate_report_schema,
)
from pagetrace.extract import extract_pdf  # noqa: E402
from pagetrace.pdf_input import PdfInputError  # noqa: E402
from pagetrace.report_html import TOOL_VERSION, build_view_entry, write_report  # noqa: E402
from pagetrace.trace_bundle import load_bundle_file  # noqa: E402
from pagetrace.verdicts import FAIL_VERDICTS  # noqa: E402

__all__ = [
    "EXIT_OK",
    "EXIT_ANALYSIS_FAIL",
    "EXIT_INPUT",
    "EXIT_INTERNAL",
    "EXIT_S0_FAIL",
    "InputError",
    "main",
]

#: PROJECT_BOOK §12.2.
EXIT_OK = 0
EXIT_ANALYSIS_FAIL = 1
EXIT_INPUT = 2
EXIT_INTERNAL = 3
EXIT_S0_FAIL = 4

REPORT_SCHEMA = "pagetrace.report/v1"

#: Default excerpt length for quote text in the HTML report when
#: --include-snippets is off (PROJECT_BOOK §13: only a short
#: excerpt by default; the full text only on explicit opt-in).
SNIPPET_EXCERPT_CHARS = 40


class InputError(Exception):
    """Invalid user input / frozen input (exit 2)."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _read_pdf_bytes(pdf_path: Path) -> bytes:
    """Read a PDF file; missing / unreadable files are input errors."""
    try:
        return pdf_path.read_bytes()
    except OSError as exc:
        raise InputError(f"cannot read PDF {pdf_path}: {exc}") from exc


def _load_bundle(trace_path: Path):
    """Load + validate a bundle file; any failure is an input error."""
    try:
        return load_bundle_file(trace_path)
    except (BundleValidationError, PageSemanticsError) as exc:
        raise InputError(str(exc)) from exc


def _verify_hash(bundle, pdf_path: Path) -> None:
    """Check the bundle's document hash against the real PDF bytes.

    A mismatch is an input error (exit 2), never a crash and never
    silently ignored: analysing the wrong PDF would attribute
    faults to the wrong document.
    """
    pdf_bytes = _read_pdf_bytes(pdf_path)
    try:
        bundle.verify_document_hash(pdf_bytes)
    except BundleValidationError as exc:
        raise InputError(str(exc)) from exc


def _excerpt(quote_text: str) -> str:
    """Short excerpt shown in the HTML report by default (§13)."""
    if len(quote_text) <= SNIPPET_EXCERPT_CHARS:
        return quote_text
    return quote_text[:SNIPPET_EXCERPT_CHARS] + "…"


def _canonical_json(obj: object) -> bytes:
    """Canonical JSON (§8.4): UTF-8, sorted keys, no extra spaces."""
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _build_report_document(bundle, verdicts: list) -> dict:
    """A ``pagetrace.report/v1`` document for *verdicts*.

    ``results`` are the verdict dicts in bundle citation order;
    the summary counts are derived from them. ``generated_at`` is
    deliberately omitted: the normalised hash must be stable
    across runs (§8.4) and no timestamp is evidence.
    """
    results = [verdict.to_dict() for verdict in verdicts]
    normalized = {
        "case_id": bundle.case_id,
        "document": bundle.document,
        "results": results,
    }
    summary = {
        "total_citations": len(results),
        "pass_count": sum(1 for r in results if r["verdict"] == "PASS"),
        "fail_count": sum(
            1 for r in results if r["verdict"] in FAIL_VERDICTS),
        "unknown_count": sum(
            1 for r in results if r["verdict"].startswith("UNKNOWN")),
        "ambiguous_count": sum(
            1 for r in results if r["verdict"] == "AMBIGUOUS"),
        "normalized_result_sha256": hashlib.sha256(
            _canonical_json(normalized)).hexdigest(),
    }
    document = {
        "schema": REPORT_SCHEMA,
        "case_id": bundle.case_id,
        "document": bundle.document,
        "tool": {"name": "pagetrace", "version": TOOL_VERSION},
        "results": results,
        "summary": summary,
    }
    try:
        validate_report_schema(document)
    except PageSemanticsError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"internal error: generated report fails its own schema: "
            f"{exc}") from exc
    return document


def _print_report_summary(report: dict) -> None:
    summary = report["summary"]
    print(f"case_id: {report['case_id']}")
    print(f"document: {report['document']['file_name']} "
          f"({report['document']['page_count']} pages, "
          f"sha256 {report['document']['sha256'][:16]}…)")
    print(f"citations: {summary['total_citations']} "
          f"(PASS {summary['pass_count']}, "
          f"FAIL {summary['fail_count']}, "
          f"UNKNOWN {summary['unknown_count']}, "
          f"AMBIGUOUS {summary['ambiguous_count']})")
    for result in report["results"]:
        stage = result["first_fault_stage"]
        print(f"  {result['citation_id']}: {result['verdict']}"
              + (f" fault={result['fault_type']}" if result["fault_type"]
                 else "")
              + (f" first_fault_stage={stage}" if stage else "")
              + (" first_fault_stage=None (UNKNOWN, not guessed)"
                 if result["verdict"].startswith("UNKNOWN") else ""))


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------
def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyse one PDF + trace bundle; write JSON + HTML report."""
    pdf_path = Path(args.pdf)
    trace_path = Path(args.trace)
    out_dir = Path(args.out)
    if not pdf_path.is_file():
        raise InputError(f"PDF not found: {args.pdf}")
    if not trace_path.is_file():
        raise InputError(f"trace bundle not found: {args.trace}")

    bundle = _load_bundle(trace_path)
    # TOCTOU (P1-R1-01): read the PDF bytes once, verify the bundle
    # hash against those exact bytes, and carry the verified bytes
    # through extraction — extraction must never silently re-open a
    # path that may have been swapped after verification.
    # extract_pdf additionally rejects if the file on disk no longer
    # matches the verified hash.
    pdf_bytes = _read_pdf_bytes(pdf_path)
    try:
        bundle.verify_document_hash(pdf_bytes)
    except BundleValidationError as exc:
        raise InputError(str(exc)) from exc
    try:
        _, honest_records = extract_pdf(
            str(pdf_path), pdf_bytes=pdf_bytes,
            expected_sha256=bundle.document_sha256)
    except PdfInputError as exc:
        raise InputError(str(exc)) from exc
    verdicts = analyze_bundle(bundle.to_dict(), honest_records)

    # HTML view entries (T008 renderer): truth column from the
    # honest extraction, extraction/chunk/index/display columns
    # from the bundle verbatim; never re-derived here.
    extraction_diffs = [
        diff.to_dict()
        for diff in compare_extraction(
            honest_records, bundle.stages.get("extraction"))
    ]
    entries = []
    for verdict in verdicts:
        entry = build_view_entry(
            case_id=bundle.case_id, result=verdict.to_dict(),
            bundle=bundle.to_dict(), honest_records=honest_records,
            extraction_diffs=extraction_diffs)
        if not args.include_snippets:
            # §13: full quote text only on explicit opt-in.
            entry["quote_text"] = _excerpt(entry.get("quote_text", ""))
        entries.append(entry)

    report = _build_report_document(bundle, verdicts)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True,
                   indent=2) + "\n", encoding="utf-8")
    written = write_report(out_dir, entries)
    print(f"report.json: {report_path}")
    print(f"report.html: {written['report_html']} "
          f"({written['report_html_bytes']} bytes)")
    print(f"report assets: {', '.join(sorted(written['assets']))}")
    if args.include_snippets:
        snippet_note = "full quote text included (--include-snippets)"
    else:
        snippet_note = ("short excerpts only (default; use "
                        "--include-snippets for full quote text)")
    print(f"snippets: {snippet_note}")
    _print_report_summary(report)
    if report["summary"]["fail_count"] or report["summary"]["unknown_count"]:
        print("RESULT: FAIL/UNKNOWN present — analysis completed, "
              "exit 1 (not a tool crash)")
        return EXIT_ANALYSIS_FAIL
    if (report["summary"]["ambiguous_count"]
            or any(r["verdict"] == "NEEDS_MANUAL_REVIEW"
                   for r in report["results"])):
        print("RESULT: uncertainty present (AMBIGUOUS / "
              "NEEDS_MANUAL_REVIEW) — analysis completed, exit 1")
        return EXIT_ANALYSIS_FAIL
    print("RESULT: PASS — all citations PASS")
    return EXIT_OK


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a bundle (schema + runtime rules); no analysis."""
    trace_path = Path(args.trace)
    if not trace_path.is_file():
        raise InputError(f"trace bundle not found: {args.trace}")
    bundle = _load_bundle(trace_path)
    print(f"bundle: {trace_path}")
    print(f"schema: {bundle.schema}")
    print(f"case_id: {bundle.case_id}")
    print(f"document: {bundle.file_name} "
          f"({bundle.page_count} pages, sha256 {bundle.document_sha256})")
    print(f"citations: {len(bundle.citations)}")
    print(f"stages present: {', '.join(bundle.present_stages) or '(none)'}")
    print(f"stages missing: {', '.join(bundle.missing_stages) or '(none)'}")
    print(f"stages empty: {', '.join(bundle.empty_stages) or '(none)'}")
    if bundle.unresolved_chunk_refs or bundle.unresolved_index_refs \
            or bundle.citations_without_display:
        print("note: dangling references are fault data for the "
              "analyser, not a validation failure: "
              f"unresolved chunks {bundle.unresolved_chunk_refs}, "
              f"unresolved index records {bundle.unresolved_index_refs}, "
              f"citations without display "
              f"{bundle.citations_without_display}")
    if args.pdf is not None:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_file():
            raise InputError(f"PDF not found: {args.pdf}")
        _verify_hash(bundle, pdf_path)
        print(f"document hash: MATCH ({pdf_path})")
    print("VALID: bundle is a well-formed pagetrace.bundle/v1 document")
    return EXIT_OK


# ---------------------------------------------------------------------------
# s0
# ---------------------------------------------------------------------------
def cmd_s0(args: argparse.Namespace) -> int:
    """Run the frozen S0 gate via tools/run_s0.py (thin forward)."""
    tools_dir = PACKAGE_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    try:
        import run_s0  # noqa: PLC0415 - imported only for this command
    except ImportError as exc:
        raise RuntimeError(
            f"internal error: cannot import tools/run_s0.py: {exc}") from exc
    forwarded = ["--suite", args.suite, "--repeat", str(args.repeat),
                 "--out", args.out]
    return run_s0.main(forwarded)


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------
def _is_hex64(value: object) -> bool:
    """True iff *value* is a 64-char lowercase hex string (a SHA-256)."""
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _is_verified_report_output(target: Path) -> bool:
    """True iff *target* holds a self-consistent PageTrace analyze output.

    Marker scheme (FIX-R1, P1-R1-03) — every check must pass; the
    marker is the tool's own output, verified rather than trusted by
    file name:

    * ``report.json`` is a schema-valid ``pagetrace.report/v1``
      document whose ``tool`` is exactly ``pagetrace`` /
      ``TOOL_VERSION`` (the identity ``_build_report_document``
      stamps on every report it writes);
    * ``summary.normalized_result_sha256`` recomputes from the
      document's own ``case_id`` / ``document`` / ``results`` via the
      same canonical JSON (``_canonical_json``) the writer used — a
      hand-made schema-only ``report.json`` cannot pass without
      deliberately recomputing that binding over matching contents;
    * ``report.html`` exists and its embedded ``report-data`` JSON
      agrees with ``report.json`` (same schema, same tool identity,
      every entry's ``case_id`` and ``document.file_name`` match);
    * ``assets/report.css`` and ``assets/report.js`` exist (both are
      written next to ``report.html`` by every real analyze run).

    A lone ``report.html`` or a lone / forged ``report.json`` fails.
    No secret is involved: a file that deliberately reproduces a
    complete, internally consistent PageTrace report is, by
    construction, indistinguishable from a real output — the gate
    exists to stop *accidental* deletion of unrelated directories
    (the GPT R1 repro: an unrelated dir with a generic
    ``report.html``), not to authenticate against a determined
    forger. Directories that fail any check are refused, untouched.
    """
    report_json = target / "report.json"
    if not report_json.is_file():
        return False
    try:
        doc = json.loads(report_json.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    if not isinstance(doc, dict):
        return False
    if doc.get("schema") != REPORT_SCHEMA:
        return False
    if doc.get("tool") != {"name": "pagetrace", "version": TOOL_VERSION}:
        return False
    try:
        validate_report_schema(doc)
    except PageSemanticsError:
        return False
    summary = doc.get("summary")
    if not isinstance(summary, dict):
        return False
    try:
        normalized = {
            "case_id": doc["case_id"],
            "document": doc["document"],
            "results": doc["results"],
        }
        expected = hashlib.sha256(
            _canonical_json(normalized)).hexdigest()
    except (KeyError, TypeError, ValueError):
        return False
    if summary.get("normalized_result_sha256") != expected:
        return False
    # The summary counts must be derived from the results themselves
    # (a report whose counts disagree with its results is not a
    # report this tool wrote).
    try:
        results = doc["results"]
        derived = {
            "total_citations": len(results),
            "pass_count": sum(1 for r in results
                              if r["verdict"] == "PASS"),
            "fail_count": sum(1 for r in results
                              if r["verdict"].startswith("FAIL")),
            "unknown_count": sum(1 for r in results
                                 if r["verdict"].startswith("UNKNOWN")),
            "ambiguous_count": sum(1 for r in results
                                   if r["verdict"] == "AMBIGUOUS"),
        }
        for key, value in derived.items():
            if summary.get(key) != value:
                return False
    except (KeyError, TypeError, AttributeError):
        return False
    html_path = target / "report.html"
    if not html_path.is_file():
        return False
    if not (target / "assets" / "report.css").is_file():
        return False
    if not (target / "assets" / "report.js").is_file():
        return False
    try:
        html_text = html_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    marker = '<script id="report-data" type="application/json">'
    start = html_text.find(marker)
    if start < 0:
        return False
    start += len(marker)
    end = html_text.find("</script>", start)
    if end < 0:
        return False
    try:
        embedded = json.loads(html_text[start:end])
    except ValueError:
        return False
    if not isinstance(embedded, dict):
        return False
    if embedded.get("schema") != REPORT_SCHEMA:
        return False
    if embedded.get("tool") != {"name": "pagetrace",
                                "version": TOOL_VERSION}:
        return False
    entries = embedded.get("entries")
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        if entry.get("case_id") != doc["case_id"]:
            return False
        entry_doc = entry.get("document")
        if not isinstance(entry_doc, dict):
            return False
        if entry_doc.get("file_name") != doc["document"].get("file_name"):
            return False
    return True


def _is_verified_s0_output(target: Path) -> bool:
    """True iff *target* holds a self-consistent S0 gate output.

    Marker scheme (FIX-R1, P1-R1-03): ``S0_REPORT.json`` must carry
    ``format == "pagetrace.s0-report/v1"`` and
    ``project == "P026 PageTrace"``, ``s0_result`` must be one of
    ``PASS`` / ``FAIL`` / ``SMOKE_PASS``, ``suite.case_count`` must
    be 48, every ``counts`` entry must equal the corresponding
    ``gates`` figure, and the ``replay`` hashes must be 64-hex,
    ``len(hashes) == suite.repeat``, with
    ``unique_hash_count == len(set(hashes))`` — and
    ``replay-hashes.txt`` must list exactly those hashes, in order.
    A bare or hand-made ``S0_REPORT.json`` fails; a real
    ``tools/run_s0.py`` output passes all of it.
    """
    s0_path = target / "S0_REPORT.json"
    if not s0_path.is_file():
        return False
    try:
        doc = json.loads(s0_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    if not isinstance(doc, dict):
        return False
    if doc.get("format") != "pagetrace.s0-report/v1":
        return False
    if doc.get("project") != "P026 PageTrace":
        return False
    if doc.get("s0_result") not in ("PASS", "FAIL", "SMOKE_PASS"):
        return False
    suite = doc.get("suite")
    gates = doc.get("gates")
    counts = doc.get("counts")
    replay = doc.get("replay")
    if not all(isinstance(x, dict)
               for x in (suite, gates, counts, replay)):
        return False
    if suite.get("case_count") != 48:
        return False
    try:
        checks = (
            ("detection", gates["detection"]["actual"]),
            ("first_fault_stage", gates["first_fault_stage"]["actual"]),
            ("control_false_positives",
             gates["control_false_positives"]["actual"]),
            ("parity_mismatches", gates["parity"]["actual_mismatches"]),
            ("parity_citations_matching",
             gates["parity"]["actual_citations_matching"]),
            ("replay_unique_hashes", gates["replay"]["actual_unique_hashes"]),
            ("golden_mismatches",
             gates["golden_agreement"]["actual_mismatches"]),
            ("uncertainty_violations",
             gates["uncertainty_not_pass"]["actual"]),
        )
        for name, actual in checks:
            if counts.get(name) != actual:
                return False
        hashes = replay["hashes"]
        if (not isinstance(hashes, list) or not hashes
                or len(hashes) != suite.get("repeat")):
            return False
        if any(not _is_hex64(h) for h in hashes):
            return False
        unique = replay["unique_hashes"]
        if (not isinstance(unique, list)
                or sorted(set(hashes)) != sorted(unique)
                or replay.get("unique_hash_count") != len(set(hashes))
                or counts.get("replay_unique_hashes") != len(set(hashes))):
            return False
    except (KeyError, TypeError):
        return False
    txt_path = target / "replay-hashes.txt"
    if not txt_path.is_file():
        return False
    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    return lines == hashes


def _is_pagetrace_output_dir(target: Path) -> bool:
    """True iff *target* carries a *verified* PageTrace output marker.

    Either a verified analyze output (see
    :func:`_is_verified_report_output`) or a verified S0 output (see
    :func:`_is_verified_s0_output`). A generic ``report.html``, an
    arbitrary ``S0_REPORT.json``, or a schema-only ``report.json``
    is NOT a marker and the directory is refused.
    """
    return (_is_verified_report_output(target)
            or _is_verified_s0_output(target))


def cmd_clean(args: argparse.Namespace) -> int:
    """Delete one explicitly named PageTrace output directory.

    The target path is always printed first, before any check or
    deletion, so the user sees exactly what would be removed.
    """
    target = Path(args.target)
    resolved = target.resolve()
    # T013 P2-01: print the target exactly as the user gave it. The
    # resolved absolute path is used only for internal checks (protected
    # paths, marker lookup); stdout must not leak it (§13).
    print(f"TARGET: {args.target}")
    if not target.exists():
        raise InputError(f"nothing to clean: {args.target} does not exist")
    if not target.is_dir():
        raise InputError(f"not a directory: {args.target}")
    # Never delete the workspace itself, the frozen fixtures, the
    # current working directory, the filesystem root, or any
    # ancestor of the package (which would contain the workspace).
    pkg = PACKAGE_ROOT.resolve()
    protected = {pkg, (PACKAGE_ROOT / "fixtures").resolve(),
                 Path.cwd().resolve(), Path("/").resolve()}
    if resolved in protected or resolved in pkg.parents:
        raise InputError(
            f"refusing to clean protected path: {args.target}")
    if not _is_pagetrace_output_dir(target):
        raise InputError(
            f"refusing to clean {args.target}: not a verified "
            f"PageTrace output directory (no self-consistent "
            f"report.json + report.html with matching "
            f"normalized_result_sha256, and no self-consistent "
            f"S0_REPORT.json + replay-hashes.txt; a bare report.html, "
            f"an arbitrary S0_REPORT.json or a schema-only report.json "
            f"is not a marker)")
    entries = sorted(p.name for p in target.iterdir())
    print(f"contains {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}: "
          f"{', '.join(entries[:10])}"
          + (" …" if len(entries) > 10 else ""))
    if args.dry_run:
        print("DRY RUN: nothing deleted")
        return EXIT_OK
    shutil.rmtree(target)
    # T013 P2-01: echo the target as given, not the resolved path.
    print(f"REMOVED: {args.target}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pagetrace.cli",
        description="PageTrace (P026): PDF citation page-drift detector. "
                    "Exit codes (PROJECT_BOOK §12.2): 0 success, "
                    "1 analysis completed with FAIL/UNKNOWN, "
                    "2 invalid input, 3 internal error, 4 S0 gate failed.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser(
        "analyze",
        help="analyse one PDF + trace bundle; write report.json + "
             "report.html")
    p_analyze.add_argument("--pdf", required=True,
                           help="source PDF path")
    p_analyze.add_argument("--trace", required=True,
                           help="trace bundle JSON path "
                                "(pagetrace.bundle/v1)")
    p_analyze.add_argument("--out", required=True,
                           help="output directory (created if needed)")
    p_analyze.add_argument("--include-snippets", action="store_true",
                           help="include full quote text in report.html "
                                "(default: short excerpts only, §13)")
    p_analyze.set_defaults(func=cmd_analyze)

    p_validate = sub.add_parser(
        "validate",
        help="validate a trace bundle (schema + runtime rules); "
             "with --pdf also verify the document hash. No analysis.")
    p_validate.add_argument("--trace", required=True,
                            help="trace bundle JSON path")
    p_validate.add_argument("--pdf", default=None,
                            help="optional PDF path for the document-hash "
                                 "check")
    p_validate.set_defaults(func=cmd_validate)

    p_s0 = sub.add_parser(
        "s0",
        help="run the frozen 48-case S0 gate (exit 0 pass, 4 gate "
             "failed, 2 invalid input, 3 internal error)")
    p_s0.add_argument("--suite", default="fixtures",
                      help="fixture suite dir, relative to PACKAGE_ROOT "
                           "(default: fixtures)")
    p_s0.add_argument("--repeat", type=int, default=100,
                      help="normalised replay count (default: 100)")
    p_s0.add_argument("--out", default="05_tests/s0",
                      help="output dir; relative paths resolve against "
                           "the repository root (default: 05_tests/s0)")
    p_s0.set_defaults(func=cmd_s0)

    p_clean = sub.add_parser(
        "clean",
        help="delete one explicitly named PageTrace output directory "
             "(marker-checked; use --dry-run to preview)")
    p_clean.add_argument("target",
                         help="output directory to delete")
    p_clean.add_argument("--dry-run", action="store_true",
                         help="show the target path and contents; "
                              "delete nothing")
    p_clean.set_defaults(func=cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except Exception:  # noqa: BLE001 - internal error path, exit 3
        traceback.print_exc()
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
