# PageTrace — User Guide (P026, v0.1.0)

PageTrace checks whether a cited page number still points at the true
source page of a quotation after it has travelled through a PDF
pipeline: **PDF truth → Extraction → Chunking → Indexing → Display**.
It never guesses a page: when the evidence is insufficient, it says so
(`UNKNOWN_*`, `AMBIGUOUS`, `NEEDS_MANUAL_REVIEW`).

## 1. Install

Requires **Python ≥ 3.12**. No network access is needed at run time;
only installation downloads the pinned dependencies.

```bash
unzip 04_source/source-release.zip -d pagetrace-0.1.0
cd pagetrace-0.1.0
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"        # runtime deps + pytest
# Fixture (re)generation only — not needed for normal use:
.venv/bin/pip install -e ".[fixtures]"   # adds Pillow + reportlab
.venv/bin/python -m pagetrace.cli --help
```

Installed from a wheel (`pip install pagetrace-0.1.0-py3-none-any.whl`)
the same commands work from any directory — no `PYTHONPATH` is
needed. From a source checkout without installing, the CLI inserts
`src/` on `sys.path` itself; if you use the shared-venv layout of the
project worktree, run with `PYTHONPATH=$PWD/src` so the checkout's own
code is used (see `HOW_TO_REPRODUCE.md` §5 — the shared venv's
editable install otherwise resolves to a different checkout).

## 2. Inputs

- **PDF** — the source document (the ground truth). Default limits:
  50 MiB / 500 pages; limits can only be lowered, never raised.
- **Trace bundle** — a `pagetrace.bundle/v1` JSON file describing what
  each pipeline stage recorded for each citation: the PDF it came from
  (SHA-256), the extraction / chunking / indexing / display snapshots,
  and the page values each stage observed. Schemas:
  `contracts/pagetrace.bundle.v1.schema.json` and
  `contracts/pagetrace.report.v1.schema.json` (JSON Schema Draft
  2020-12). Page identity is always `pdf_page_index0` (0-based); see
  `docs/PAGE_SEMANTICS.md` for the full page contract.

The 48 synthetic fixtures in `fixtures/` (`bundles/`, `pdfs/`,
`specs/`) are ready-made examples: every PDF has a matching bundle
with the same `case_id`.

## 3. Commands

### `validate` — check a bundle without analysing it

```bash
.venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf
```

Checks the schema and the runtime rules; with `--pdf` it also verifies
the document hash. Exit **0** = valid, **2** = invalid. It performs no
analysis and writes no report.

### `analyze` — analyse one PDF + bundle

```bash
.venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out out/case-001
```

Writes `report.json` + `report.html` (plus `report.css` /
`report.js` under `assets/`) into `--out`. Add
`--include-snippets` for full quote text; by default reports contain
short excerpts only.

Exit codes: **0** = every citation PASS; **1** = FAIL / UNKNOWN /
uncertainty present (the analysis completed — this is not a crash);
**2** = invalid input (e.g. document hash mismatch); **3** =
internal error.

### `s0` — run the frozen acceptance gate (source checkout only)

```bash
TMPDIR=$PWD/.tmp .venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 100 --out 05_tests/s0
```

Runs the 48 frozen cases, 100 deterministic replays, production↔
Oracle parity, and the Golden comparison. Exit **0** = gate passed,
**4** = gate failed, **2** = invalid input, **3** = internal error.
`--out` is resolved against the repository root; use an absolute path
when running outside the project worktree. The expected replay hash is
`a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`
(1 unique hash over 100 replays). `s0` needs a source checkout:
`tools/run_s0.py`, `fixtures/` and the Oracle are not shipped in the
wheel.

### `clean` — delete one PageTrace output directory

```bash
.venv/bin/python -m pagetrace.cli clean --dry-run out/case-001
.venv/bin/python -m pagetrace.cli clean out/case-001
```

Only deletes a directory that carries a PageTrace output marker; the
target path is printed exactly as you typed it. Exit **0** = done,
**2** = refused / missing.

## 4. Reading a report

`report.json` is a `pagetrace.report/v1` document. Each citation entry
carries, per stage, the observed page value and the canonical
`pdf_page_index0` it resolves to, plus:

| Field | Meaning |
|---|---|
| `verdict` | `PASS`, `FAIL_PAGE_OFFSET`, `FAIL_METADATA_MISSING`, `FAIL_AMBIGUOUS`, `FAIL_UNLOCATABLE`, `UNKNOWN_*`, `AMBIGUOUS`, `NEEDS_MANUAL_REVIEW` |
| `fault_type` | `PAGE_OFFSET`, `PAGE_METADATA_MISSING`, `DUPLICATE_TEXT_AMBIGUITY`, `UNLOCATABLE` (or none for PASS) |
| `first_fault_stage` | First stage where a provable difference appears (`extraction`, `chunking`, `indexing`, `display`, or none) |
| `correct_pdf_page_number1` / `correct_viewer_page1` | The correct 1-based page numbers for the true source page |
| `observed_page_value` | The page value the pipeline actually showed |
| `normalized_result_sha256` | Deterministic hash of the normalised result (same input → same hash) |

`report.html` shows the same data in four columns (truth /
extraction / chunk / index / display) with a comparison table
"wrong page → first-fault stage → correct source location". It is
fully offline (no network, no external assets) and deterministic:
running the same case twice produces byte-identical files.

Example (fixture `po-ext-01`): 2 citations — `cite-control` PASS,
`cite-fault` `FAIL_PAGE_OFFSET`, fault `PAGE_OFFSET`, first fault at
`extraction`. `analyze` exits 1 because a FAIL is present.

## 5. What it does NOT do

- **No OCR.** Text that exists only as a raster image is invisible to
  the tool; such quotes are `FAIL_UNLOCATABLE`, never "not in the
  document".
- **No semantic fact-checking.** PageTrace checks page *identity*, not
  whether the quoted words are true, complete, or fairly attributed.
- **Exact matching only.** A quote that differs by one character from
  the page text is a near miss (`NO_EXACT_MATCH`), not a match. There
  is no fuzzy matching.
- **Single-document, offline, local files only.** No network access,
  no fetching, no external service calls.
- **No claim about real systems.** A passing S0 gate means the tool
  behaves correctly on the 48 frozen synthetic fixtures — not that any
  real-world PDF pipeline has passed. The full boundary list is in
  `docs/LIMITATIONS.md`.

## 6. Troubleshooting

- `No module named pagetrace.cli` — install the package first
  (`pip install -e .`); in a bare checkout set `PYTHONPATH=$PWD/src`.
- `INPUT_HASH_MISMATCH` (exit 2) — the `--pdf` file's SHA-256 does not
  match the bundle's `document.sha256`; use the PDF the bundle was
  built from.
- `PDF is encrypted; no password support` — encrypted PDFs are
  rejected; decrypt outside the tool first.
- `s0` exit 4 — the gate failed; see the printed gate table and
  `S0_REPORT.json` in the `--out` directory for which gate failed.
- Out-of-disk errors in `/tmp` — the test suite writes temporary
  files; run with `TMPDIR=$PWD/.tmp` (see `HOW_TO_REPRODUCE.md`).
