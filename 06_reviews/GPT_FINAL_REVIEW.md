# GPT Final Review — Submission Template (P026 PageTrace)

> **This file is the submission template, not the review itself.**
> The coordinator sends the contents below (plus the review packs) to
> GPT for the final review. Do **not** fill in a verdict here — the
> verdict comes from GPT's reply. Model + thinking for the review:
> GPT-6 + Extra High (factory rule: all reviews use 极高). Every
> message to GPT ends with: “请使用谷歌云盘以及任何需要的插件，如果有了的话就算了。”

## 1. What is submitted for review

- **Project:** P026 PageTrace 引文落页镜 — PDF citation page-drift
  detector (PDF truth → Extraction → Chunking → Indexing → Display).
- **Spec:** v1.0.0 (frozen; `~/workspace/p026-specs/`, do not edit).
- **Freeze commit:** `cfc8b94` — "P026: T013 PASS control — merged
  b99a77b, 13× P2 closed, venv reinstalled, T014 dispatched"
  (T001–T013 all PASS; worktree `~/workspace/p026-pagetrace-t014`,
  branch `task/t014`).
- **Source release:** `04_source/source-release.zip` — 252 files,
  1,125,629 bytes,
  SHA-256 `ec4ceae6ccf96dbe03bd85c3009eeff96c95b21195ede684f59bf896bf01b215`.
  Manifest: `04_source/SOURCE_MANIFEST.csv` (SHA-256
  `e118da2c301a6d43da76fa95e88885924b54dc38d6d54c0b8f9f05c8a3c2e5c0`),
  verified with `sha256sum -c 04_source/SHA256SUMS.txt` (both OK).
  The ZIP is deterministic (two builds → identical hash).
- **Review packs (this freeze):**
  `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_01.md` (frozen-tree
  inventory: all 252 files with SHA-256, plus gate evidence) and
  `REVIEW_PACK_RELEASE_02.md` (independent reproduction evidence:
  ZIP↔manifest checks, clean-copy run, venv-resolution finding).
  Index: `07_evidence/REVIEW_PACKS/RELEASE_REVIEW_INDEX.md`.
- **Prior review:** T012 independent review (0 P0, 0 P1, 13 P2) in
  `06_reviews/TASK_REVIEWS/T012_REVIEW.md` and
  `07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md` /
  `REVIEW_PACK_02.md` (untouched by T014). All 13 P2 were closed by
  T013 (10 fixed, 3 recorded); the fix record is
  `07_evidence/runtime_logs/T013_FIX_RECORD.md`.
- **Release docs:** `08_release/README.md`, `08_release/USER_GUIDE.md`,
  `08_release/HOW_TO_REPRODUCE.md`.

## 2. Claimed gate results (all re-run by T014 from the clean worktree)

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | **652 passed**, 0 failed (~90 s) | `07_evidence/runtime_logs/pytest-t014.log`; per-file counts in `08_release/HOW_TO_REPRODUCE.md` §2 |
| S0 gate, repeat 100 | **PASS** — detection 48/48, first-fault stage 48/48, control false positives 0, parity 96/96, 100 replays → 1 unique hash `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`, Golden mismatches 0 | `05_tests/s0-release/S0_REPORT.json`, `07_evidence/runtime_logs/s0-release.log` |
| Clean-copy reproduction (fresh venv, ZIP contents only) | `validate` exit 0; `analyze` exit 1 (expected, one FAIL present); `s0 --repeat 1` **PASS**, same replay hash | `07_evidence/runtime_logs/clean-copy-t014.log` |
| License scan (T013) | 19/19 dependencies OK | `07_evidence/runtime_logs/license-report.txt`, `NOTICE` |
| ZIP ↔ manifest | 252 entries, 0 hash/size mismatches; no venv / `__pycache__` / `.pyc` / user PDF / key / absolute-path entries; rebuild byte-identical | `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_02.md` |

## 3. What the reviewer must check

1. **Frozen-tree integrity:** does every file in the release match
   `SOURCE_MANIFEST.csv`, and is anything in the ZIP that should not
   be there (user PDF, secret, cache, absolute path, venv)?
2. **Gate honesty:** are the pytest / S0 / clean-copy numbers real
   and reproducible from `HOW_TO_REPRODUCE.md`? Does any gate hide a
   skipped, loosened, or deleted check?
3. **Docs ↔ implementation consistency:** do `README.md`,
   `USER_GUIDE.md`, `HOW_TO_REPRODUCE.md` and `docs/LIMITATIONS.md`
   describe what the code actually does — in particular, is there any
   claim of OCR, semantic fact-checking, or a real system having
   passed? (There must be none.)
4. **Known limitations:** are the carried items stated honestly and
   completely — P2-04 (Oracle `reason` divergence), P2-07 (Oracle
   triple-span probe is a subset), P2-10 (`fixtures build` not
   implemented), P2-11 (`un-ext-12` wording deviation), S0 covering
   only fault verdicts (no `AMBIGUOUS` / `UNKNOWN_*` /
   `NEEDS_MANUAL_REVIEW` citation in the frozen suite)?
5. **Scope of any PASS:** a PASS covers engineering fixes, offline
   acceptance on the 48 frozen synthetic fixtures, and delivery
   integrity only. It is **not** evidence of superiority,
   non-inferiority, or that any real-world PDF pipeline has passed,
   and it does not cover Windows / macOS (NOT_TESTED).

## 4. Hard assertions the review must not waive

- ZIP contents == manifest (hash + size, every file); `SHA256SUMS.txt`
  fully passes.
- S0 and full pytest genuinely pass on the frozen tree; replay hash
  matches the baseline `5195fc9a…f33f8`.
- No user PDF, key, cache, venv, or absolute path in the package.
- `REVIEW_INDEX` covers every file submitted for review.
- No frozen source / Golden / dependency-lock change after T013
  (T014 changed only release metadata, manifests, docs, and review
  packs — verify with `git diff cfc8b94 --stat`).

## 5. Verdict format (for GPT's reply)

```text
FINAL_VERDICT: PASS | FAIL | EVIDENCE_INCOMPLETE
P0: <n>  P1: <n>  P2: <n>
Findings: [P<level>-R<round>-<nn>: <one line each, with file + line evidence>]
Coverage: <files read / files submitted>
```

Delivery requires an explicit `FINAL_VERDICT: PASS`. If the verdict
is FAIL or EVIDENCE_INCOMPLETE, list every blocker with file + line
evidence so a fix task can be dispatched.

请使用谷歌云盘以及任何需要的插件，如果有了的话就算了。
