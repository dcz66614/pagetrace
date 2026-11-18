# T013 fix record — 13 × P2 from the T012 independent review

- Task: P026-T013 (defect fixes, docs, licences, packaging)
- Base commit: 9bd5270 (master, T012 merged); branch: task/t013
- Worktree: ~/workspace/p026-pagetrace-t013
- Review sources: 06_reviews/TASK_REVIEWS/T012_REVIEW.md,
  07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md §3
- P0/P1 in this batch: 0 (nothing to fix)

## Per-item disposition

| # | Disposition | Change |
|---|---|---|
| P2-01 | FIXED (code + tests) | `cli.py` clean prints `args.target` verbatim for TARGET:/REMOVED: and both refusal messages; resolved path only for internal checks. `test_cli.py:292,301` updated; new relative-target test asserts no absolute path on stdout. Commit c155a75. |
| P2-02 | FIXED (code + tests) | `_check_source_stage` + `_trace_anchor_pages` treat a non-list (or non-integer-membered) `source_page_indices0` as `PAGE_METADATA_MISSING`, never a raw `TypeError`. CLI path unaffected (schema rejects first). Regression tests via `analyze_bundle` (int/null/string/non-int member) + direct anchor probe. Commit 5ca538f. |
| P2-03 | FIXED (code + tests) | `contracts.resolve_citation_to_index0`: the `PDF_LABEL` + `label_map is None` check now precedes the None guard, so `(None, PDF_LABEL, no map)` raises `UnresolvableLabelError`, matching the T001 reference (the 1 type difference in the 250-input differential). Docstring updated. Regression test pins production + reference. Commit dbe3b13. |
| P2-04 | FIXED production only (code + tests) | New reason `VALUE_OUT_OF_RANGE` (`verdicts.py`); `_check_display` splits the shared branch — out-of-range gets it, type mismatch keeps `VALUE_BASIS_TYPE_MISMATCH`; verdict stays `NEEDS_MANUAL_REVIEW`. Oracle NOT changed (see divergences below). Regression tests for both branches. Commit 84048ea. |
| P2-05 | FIXED (Oracle + tests) | Oracle `attribute.py` missing-snapshot branch now sets `reason="TRACE_MISSING"`, matching production. Reason is not an S0 parity field. Synthetic Oracle test + new production↔Oracle parity test. Commit d6233bd. |
| P2-06 | FIXED (docstring) | `_trace_anchor_pages` docstring no longer claims a display fallback; it checks chunk, then index, only. Commit d6c0c7e. |
| P2-07 | RECORDED (comment + docs) | Oracle `_triple_spans` docstring now states it is a bounded subset probe of production's exhaustive `_spans_triple`, names the theoretical divergence, and notes the frozen suite has no 3-page span. Coverage gap recorded in `docs/LIMITATIONS.md` AND in the test plan (`05_tests/TEST_PLAN.md` §6). NO fixture or Golden change (suite frozen). Commit d6c0c7e (+ test-plan note in the final commit). |
| P2-08 | FIXED (packaging + tests) | Single src layout: pyproject installs `src/pagetrace/` (+ `assets/*`, `schemas/*.json`), top-level stub deleted, `license = "MIT"` (SPDX string). Verification exposed a real gap: `contracts.py` loaded schemas from `<PACKAGE_ROOT>/contracts/`, absent in a wheel — fixed by shipping byte-identical copies at `src/pagetrace/schemas/` (hashes match the T012 review pack), packaged-first with repo fallback, pinned by 2 new tests. Installed-wheel check passed (see below). Commit 34c929d. |
| P2-09 | FIXED (packaging) | Pillow/reportlab moved from runtime `dependencies` to the `[fixtures]` extra; runtime deps are now pypdf / pdfminer.six / jsonschema only. `requirements.lock` comment-only update; all pinned versions unchanged. Both fixture tools still run (`--help` verified). Commit ef17561. |
| P2-10 | RECORD ONLY — no action | `fixtures build` remains unimplemented; recorded in `docs/LIMITATIONS.md` and `docs/CLI.md` (already). No new implementation (task card requires 4 commands only). |
| P2-11 | RECORD ONLY — no action | UN §8.1 wording deviation (un-ext-12, all-text pages) recorded in `docs/LIMITATIONS.md`; frozen spec NOT edited (DECISIONS.md already holds the entry). |
| P2-12 | FIXED (docs only) | `PAGE_SEMANTICS.md`: (a) §5 — no extra bare-field-name scan exists; the only defence is schema `additionalProperties: false`; (b) §1.4 — `normalized_result_sha256` is always computed, never null. No code behaviour changed. Commit 941f503. |
| P2-13 | FIXED (code + tests) | `stage_diffs_for_bundle` gives `NEEDS_MANUAL_REVIEW` its own kind `needs_review` instead of `offset`; `StageDiff` docstring updated. Regression test asserts the display diffs are exactly `{'needs_review'}`. Commit 554faaf. |
| Pillow licence | CLOSED, recorded | MIT-CMU verified against the installed 13.0.0 LICENSE file (line 10: "Like PIL, Pillow is licensed under the open source MIT-CMU License:") + METADATA License-Expression. Recorded in `NOTICE`, `requirements.lock` header, `README.md`/`docs/LIMITATIONS.md` pointers. Frozen spec files NOT touched; `requirements.lock` versions unchanged. |

## Known divergences left deliberately

- P2-04: Oracle still maps out-of-range to `VALUE_BASIS_TYPE_MISMATCH`
  (`tests/oracle/attribute.py:579-586`) while production reports
  `VALUE_OUT_OF_RANGE`. Verdict agrees; reason is not a parity field.
  The Oracle is independent and is not silently edited to match
  production. Recorded in `docs/LIMITATIONS.md`.
- O-1/O-2/O-3 observations from the review pack §4: not filed as
  defects, no action taken.

## Verification (evidence in this directory unless noted)

- Full pytest: see `pytest-t013.log` (baseline 639 + 13 new regression
  tests = 652 expected; the real count is recorded in the final
  report, not assumed here).
- S0 full run: `05_tests/s0-r13` in the worktree (repo root);
  expected replay hash
  `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`.
- Wheel: `wheel-build-1.log` (pre-fix layout, superseded),
  `wheel-build-2.log` / `wheel-build-3.log` (two builds, contents
  identical, only dist-info timestamps differ). Final wheel
  `wheel-final.whl` (sha
  `a674d565a98c4d4a598d24be3112567419929e7278ebbbf179366edbaa669924`,
  58 KB-class): rebuilt after P2-09, so its METADATA lists only the 3
  runtime deps (+ `fixtures` / `dev` extras) and ships LICENSE +
  NOTICE as license files. Two `SOURCE_DATE_EPOCH=1792000000` builds
  of the final code are byte-identical (same sha); without it only
  the dist-info timestamps differ.
- Installed-wheel check: `wheel-installed-analyze.log` (isolated venv,
  no PYTHONPATH, neutral cwd: `analyze` on po-ext-01 exits 1 with the
  correct FAIL/PASS verdicts, report.json + report.html + assets).
- License scan: `license_scan.py` + `license-report.txt` (19/19 lock
  entries at pinned versions, 0 problems; Pillow MIT-CMU PASS).

## Follow-ups for the coordinator (not done in T013)

- After merging task/t013, re-run `pip install -e ".[dev]"` in the
  shared venv: its editable install still maps `pagetrace` to the
  pre-T013 layout (top-level stub, now deleted). All T013 verification
  ran via src-first sys.path or the wheel, so this did not affect
  results — but a stale editable install would break
  `python -m pagetrace.cli` without PYTHONPATH in the main repo.
- The installed CLI's `s0` subcommand needs a source checkout
  (`tools/` + `fixtures/` + Oracle are not shipped in the wheel);
  documented in README.md / docs/LIMITATIONS.md.
