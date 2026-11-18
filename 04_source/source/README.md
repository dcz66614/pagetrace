# PageTrace (P026) — PDF citation page-drift detector

PageTrace checks whether a cited page number still points at the true
source page of a quotation after the quotation has travelled through a
PDF pipeline: **PDF truth → Extraction → Chunking → Indexing →
Display**. For each citation it reports a verdict (`PASS`,
`FAIL_PAGE_OFFSET`, `FAIL_METADATA_MISSING`, `FAIL_AMBIGUOUS`,
`FAIL_UNLOCATABLE`, `UNKNOWN_*`, `AMBIGUOUS`, `NEEDS_MANUAL_REVIEW`),
the fault type, and the first stage where a provable difference
appears. It never guesses a page: uncertainty is reported as
uncertainty, never converted to PASS.

The page contract is frozen (v1.0.0): the canonical page identity is
always `pdf_page_index0` (0-based); everything else is a derivation, a
display value, or a verbatim external observation. See
`docs/PAGE_SEMANTICS.md` and `contracts/` (JSON Schema Draft 2020-12).

## What it does NOT do

- **No OCR.** A quote that only exists as raster/image text is reported
  `FAIL_UNLOCATABLE` (reason `IMAGE_ONLY` / `EMPTY` / `NO_EXACT_MATCH`),
  with a note that this does *not* establish the quoted text is absent
  from the document.
- **No semantic fact-checking.** PageTrace verifies *page identity*
  (does the cited page match the page where the normalised quote was
  actually found?), not whether the quoted claim is true.
- **No claim about real systems.** The S0 gate runs 48 frozen synthetic
  fixtures (see below); a pass means the tool behaves correctly on
  those fixtures. It is not evidence that any real-world PDF pipeline
  has passed. See `docs/LIMITATIONS.md` for the full boundary list.

## Install and run

Requires Python ≥ 3.12.

```bash
# From a source checkout (PACKAGE_ROOT = 04_source/source/):
pip install -e .[dev]          # runtime deps + pytest
pip install -e ".[dev,fixtures]"  # also Pillow/reportlab, only needed
                               # to (re)generate fixtures (T013 P2-09)
python -m pagetrace.cli --help

# Or install the wheel (no PYTHONPATH needed after install):
pip install dist/pagetrace-0.1.0-py3-none-any.whl
python -m pagetrace.cli --help
```

In a source checkout without installing, the CLI still works — it
inserts `src/` on `sys.path` itself (or set `PYTHONPATH=$PWD/src`).
See `docs/CLI.md` for the full command reference.

## Commands

| Command | Purpose | Exit codes |
|---|---|---|
| `analyze --pdf P --trace T --out DIR` | Analyse one PDF + trace bundle; writes `report.json` + `report.html` | 0 all PASS · 1 FAIL/UNKNOWN/uncertainty present · 2 invalid input · 3 internal error |
| `validate --trace T [--pdf P]` | Bundle schema + runtime validation (no analysis); with `--pdf` also verifies the document hash | 0 valid · 2 invalid |
| `s0 --suite fixtures --repeat 100 --out 05_tests/s0` | Run the frozen 48-case S0 gate (source checkout only — see below) | 0 gate passed · 4 gate failed · 2 invalid input · 3 internal error |
| `clean [--dry-run] DIR` | Delete one explicitly named PageTrace output directory (marker-checked; prints the target as given, then deletes) | 0 done · 2 refused / missing |

Full details, including the exit-code table and the unimplemented
`fixtures build` command, are in `docs/CLI.md`.

## Tests and the S0 gate

```bash
TMPDIR=$PWD/.tmp .venv/bin/python -m pytest -q
TMPDIR=$PWD/.tmp .venv/bin/python -m pagetrace.cli s0 --suite fixtures \
    --repeat 100 --out 05_tests/s0-r13
```

The S0 gate is the frozen acceptance check: 48 fixture cases
(4 fault classes × 12), stage attribution, 0 control false alarms,
production↔independent-Oracle parity (96 citations), Golden match,
and 100 deterministic replays producing a single normalised hash.
The expected replay hash is
`a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`.

The `s0` subcommand needs a source checkout: `tools/run_s0.py`,
`fixtures/` and the Oracle (`tests/oracle/`) are not shipped in the
wheel. `analyze` / `validate` / `clean` work from an installed wheel.

## Layout

- `src/pagetrace/` — production package (single src layout since T013).
  The frozen JSON Schemas ship inside the package as
  `src/pagetrace/schemas/` (byte-identical to `contracts/`; the repo
  copy remains the frozen authority).
- `contracts/` — frozen `pagetrace.bundle/v1` + `pagetrace.report/v1`
  schemas (T001; do not edit without a new task).
- `fixtures/` — the 48 frozen fixture cases + Golden file (T002; frozen).
- `tests/` — unit / integration / e2e / privacy / S0 tests, plus the
  independent Oracle (`tests/oracle/`, stdlib + pdfminer.six only).
- `tools/` — S0 runner, fixture generator, preview renderer.
- `docs/` — `CLI.md`, `PAGE_SEMANTICS.md`, `LIMITATIONS.md`.

## Reproducible wheel

`python -m pip wheel . --no-deps` builds `pagetrace-0.1.0-py3-none-any.whl`.
Without `SOURCE_DATE_EPOCH` two builds differ only in the
`dist-info` timestamps (all file contents identical); with
`SOURCE_DATE_EPOCH` set the two builds are byte-identical. Build logs
are kept under `07_evidence/runtime_logs/` in the project worktree.

## License

MIT — see `LICENSE`. Third-party licences and versions: see `NOTICE`
(verified offline by T013; report in
`07_evidence/runtime_logs/license-report.txt`). Dependency versions are
pinned in `requirements.lock` (T001 freeze; upgrade only with a full
S0 re-run).
