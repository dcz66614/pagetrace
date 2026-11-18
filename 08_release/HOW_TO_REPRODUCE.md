# PageTrace — How to Reproduce (P026, v0.1.0, FIX-R1)

Every number in `08_release/README.md` was produced with the commands
below. Nothing here needs a network connection except the one
`pip install` step (downloading the pinned dependencies); all gates
run fully offline afterwards.

## 0. Environment used by FIX-R1

- OS: Linux x86_64, `Linux-7.0.0-44-generic` (glibc 2.39)
- Python: CPython **3.12.3** (`python3 --version`)
- Dependencies (pinned in `requirements.lock`, verified installed):
  `pypdf==7.1.0`, `pdfminer.six==20260107`, `jsonschema==4.26.0`,
  `pytest==9.2.0` (+ fixture extra `reportlab==5.1.0`,
  `Pillow==13.0.0`, only needed to (re)generate fixtures)
- Worktree: `~/workspace/p026-pagetrace`, branch `task/fix-r1`,
  base commit `d0aa21f`; `PACKAGE_ROOT = 04_source/source/`
- `/tmp` on this VM is a 512M tmpfs: **all test runs must set
  `TMPDIR=$PWD/.tmp`** or the suite can run out of disk mid-run.

Other platforms (Windows, macOS, other Python versions) are
**NOT_TESTED** — see `README.md`.

## 1. Verify the release package

From the repository root:

```bash
sha256sum -c 04_source/SHA256SUMS.txt
# expected: both lines OK
#   04_source/source-release.zip: OK
#   04_source/SOURCE_MANIFEST.csv: OK

python3 - <<'EOF'
import csv, hashlib, zipfile
zf = zipfile.ZipFile('04_source/source-release.zip')
rows = list(csv.DictReader(open('04_source/SOURCE_MANIFEST.csv')))
assert zf.namelist() == [r['path'] for r in rows]          # 255 entries
assert all(hashlib.sha256(zf.read(r['path'])).hexdigest() == r['sha256']
           and zf.getinfo(r['path']).file_size == int(r['bytes'])
           for r in rows)
print('ZIP <-> manifest: consistent,', len(rows), 'files, 0 mismatches')
EOF
```

Expected ZIP facts: **255 files, 1,148,388 bytes**,
SHA-256 `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b`.
Rebuilding the ZIP from the same frozen tree (build script:
`07_evidence/runtime_logs/fixr1-build-release.py`) reproduces the
identical hash — fixed file order, fixed 1980-01-01 timestamps, fixed
permissions.

## 2. Full test suite (754 tests)

In `PACKAGE_ROOT` (`04_source/source/`):

```bash
cd 04_source/source
PYTHONPATH=$PWD/src TMPDIR=$PWD/.tmp .venv/bin/python -m pytest -q
```

Expected: `754 passed` (exit 0). Log:
`07_evidence/runtime_logs/pytest-fixr1.log`.

Per-file counts (from `pytest --collect-only -q`): `test_bundle.py`
291, `test_verdicts.py` 164, `test_file_name_paths.py` 66,
`test_page_semantics.py` 50, `test_cli.py` 30, `test_oracle.py` 21,
`test_unlocatable_attribution.py` 19, `test_extract.py` 19,
`test_locate.py` 15, `test_html_report.py` 14, `test_e2e.py` 14,
`test_privacy.py` 11, `test_run_s0.py` 10, `test_prototype.py` 10,
`test_toctou.py` 9, `test_fixture_manifest.py` 7,
`test_oracle_parity.py` 4.
Total 754 = 652 (T014 baseline) + 102 new FIX-R1 regression tests
(TOCTOU 9, UNLOCATABLE 19, file-name 66, clean 7, S0-threshold 1).

> **Why `PYTHONPATH=$PWD/src`?** The worktree's `.venv` is a symlink
> to the main repository's venv, whose editable install points at the
> *main* repository's `src/`. Without `PYTHONPATH`, `python -m
> pagetrace.cli` (and pytest's production imports) resolve to the main
> checkout's code — T014 caught this when the first S0 run wrote its
> report to the main repo's `05_tests/s0-release/` instead of the
> worktree's. The two trees are byte-identical at `cfc8b94`, so the
> first run's numbers were still correct, but the committed evidence
> is the `PYTHONPATH`-pinned re-run, which provably imports
> `.../p026-pagetrace-t014/04_source/source/src/pagetrace/__init__.py`
> (verified with `python -c "import pagetrace; print(...)"` before
> each gate). The stray output directory in the main repo was removed;
> the main repo is clean. `PYTHONPATH=$PWD/src` is also the documented
> source-checkout fallback in `docs/CLI.md` and `05_tests/TEST_PLAN.md`
> §2.

## 3. S0 gate (100 replays)

In `PACKAGE_ROOT`:

```bash
cd 04_source/source
PYTHONPATH=$PWD/src TMPDIR=$PWD/.tmp .venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 100 --out 05_tests/s0-release
```

Expected output (exit 0):

```text
S0_RESULT: PASS
detection: 48/48 (by type: {'DUPLICATE_TEXT_AMBIGUITY': 12, 'PAGE_METADATA_MISSING': 12, 'PAGE_OFFSET': 12, 'UNLOCATABLE': 12})
first_fault_stage: 48/48
control_false_positives: 0
parity: 96/96 citations matching, 0 field mismatches
replay: 1 unique hash(es) over 100 replays
uncertainty_not_pass violations: 0
golden_agreement mismatches: 0
golden_sha256: 9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353
```

`--out` is resolved against the repository root, so the report lands
in `<repo>/05_tests/s0-release/` (`S0_REPORT.json` +
`replay-hashes.txt`). `replay-hashes.txt` must contain 100 identical
lines: `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`.
Runtime: ~6–7 minutes. Log: `07_evidence/runtime_logs/s0-fixr1.log`.

## 4. Clean-copy reproduction (ZIP only, fresh venv)

Proves the delivered ZIP — not the worktree — reproduces the core
commands. FIX-R1 used `~/workspace/tmp-p026-clean-release` (persistent
disk; /tmp on this VM is a 512M tmpfs and a fresh venv does not fit
there; logs kept in the repo):

```bash
rm -rf ~/workspace/tmp-p026-clean-release && mkdir -p ~/workspace/tmp-p026-clean-release
cd ~/workspace/tmp-p026-clean-release
unzip -q ~/workspace/p026-pagetrace/04_source/source-release.zip -d pkg
python3 -m venv venv
# FIX-R1 (GPT R1 §4): install from the actual lock file, not from
# pyproject.toml. `requirements.lock` pins every direct dependency
# (pypdf==7.1.0, pdfminer.six==20260107, jsonschema==4.26.0,
# pytest==9.2.0, reportlab==5.1.0, Pillow==13.0.0) and every
# transitive dependency to the exact versions pip resolved at the
# T001 freeze; the 6 direct pins were verified identical to
# pyproject.toml. Only this step needs network.
./venv/bin/pip install -r pkg/requirements.lock
./venv/bin/pip install -e ./pkg --no-deps   # pagetrace itself, no re-resolution
./venv/bin/python -c "import importlib.metadata as m; print('pypdf', m.version('pypdf')); print('pdfminer.six', m.version('pdfminer.six')); print('jsonschema', m.version('jsonschema')); print('pytest', m.version('pytest'))"
# expected: pypdf 7.1.0, pdfminer.six 20260107, jsonschema 4.26.0, pytest 9.2.0
cd pkg
./../venv/bin/python -m pagetrace.cli --help                            # exit 0
./../venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf                                     # exit 0, VALID
./../venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out ~/workspace/tmp-p026-clean-release/out-po-ext-01                 # exit 1 (expected)
TMPDIR=$PWD/.tmp ./../venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 1 --out ~/workspace/tmp-p026-clean-release/s0-clean  # exit 0, SMOKE_PASS
```

Expected: `validate` VALID with `document hash: MATCH`; `analyze`
writes `report.json` (`pagetrace.report/v1`, verdicts
`FAIL_PAGE_OFFSET` + `PASS`) and `report.html`, exiting 1 because a
FAIL citation is present; `s0 --repeat 1` prints
`S0_RESULT: SMOKE_PASS` (exit 0) with replay hash `a06b87fc…632a3` —
the same hash as the 100-replay gate. A single replay is only a
smoke run (FIX-R1): it proves the gates pass once, not the §8.4
100-replay determinism, so it must never be quoted as a formal
S0 PASS; only `--repeat 100` returns `S0_RESULT: PASS`. (Use an absolute `--out` for `s0` here: outside a git worktree
the relative path would resolve against the ZIP's parent directory.)
Full log: `07_evidence/runtime_logs/clean-copy-fixr1-release.log`.

## 5. What is NOT reproduced here

- The GPT final review (run separately by the coordinator from
  `06_reviews/GPT_FINAL_REVIEW.md`; this task only prepares its
  template and evidence).
- Any real-world PDF pipeline: all gates use the 48 frozen synthetic
  fixtures. A pass is evidence about the tool on those fixtures, not
  about any real system.
- Windows / macOS runs: not attempted (NOT_TESTED).
