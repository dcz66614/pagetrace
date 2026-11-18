# P026 FIX-R1 — 修复工 C 修复记录：P1-R1-03 + P1-R1-04

- 终审：GPT Final Review R1（`~/workspace/P026_FINAL_REVIEW_R1.md`），FINAL_VERDICT: FAIL
- 修复范围：仅 P1-R1-03（clean 错删无关目录）与 P1-R1-04（绝对路径泄漏）
- 冻结源码 commit cfc8b94 未动；修复在 main 工作副本上做；未 commit；未改冻结规格的语义（只把已有文字约束落成机器校验）；未上传 GitHub/Drive
- 负责人文件（只改了这些）：
  - `04_source/source/src/pagetrace/cli.py`（仅模块 docstring 的 clean 说明 + clean 区域约 348–560 行：`_is_pagetrace_output_dir` 族 + `cmd_clean` 拒绝文案；`cmd_analyze` 一行未动）
  - `04_source/source/src/pagetrace/trace_bundle.py`（`is_bare_file_name` + `TraceBundle` 预检/运行时校验 + 错误信息脱敏）
  - `04_source/source/contracts/pagetrace.bundle.v1.schema.json` 与 `04_source/source/src/pagetrace/schemas/pagetrace.bundle.v1.schema.json`（同一份 schema 的两份字节一致副本，同步改了 `document.file_name` 的 `pattern` + `description`；`contracts.py` 优先读 packaged 副本，且 `test_packaged_schemas_match_frozen_contracts` 钉死两份字节一致，只改一份会失效测试并使运行时校验落空）
  - `04_source/source/docs/PAGE_SEMANTICS.md`（§1.4、新增 R-11、§5 表、§7）
  - `04_source/source/tests/integration/test_cli.py`（仅 clean 区：新增 7 个测试，改 1 处旧断言措辞）
  - 新建 `04_source/source/tests/unit/test_file_name_paths.py`（66 个测试）
- 本记录：`~/workspace/p026-pagetrace/00_control/P026_FIX_R1_WORKER_C.md`

## 1. P1-R1-03 clean 错删 — 复现前证据（漏洞存在）

按 GPT 步骤复现（修复前）：

```text
$ mkdir /tmp/r1-repro/unrelated-report-folder   # 内含 report.html + keep.txt
$ PYTHONPATH=src .venv/bin/python -m pagetrace.cli clean /tmp/r1-repro/unrelated-report-folder
TARGET: /tmp/r1-repro/unrelated-report-folder
contains 2 entries: keep.txt, report.html
REMOVED: /tmp/r1-repro/unrelated-report-folder
EXIT=0
$ ls /tmp/r1-repro/unrelated-report-folder  → No such file or directory（整目录被删）
```

## 2. P1-R1-03 修复：可验证的输出标记方案

### 为什么不能只加一个标记文件 / 标记字段

`analyze` 的写出逻辑在 `cmd_analyze`（另一工人的区域）,`s0` 的写出逻辑在 `tools/run_s0.py`（不在本人负责文件内），本人无权改写出端，因此**无法新增**写出时落盘的专用标记文件或 `report.json` 新字段。本方案改为**校验工具已写出的现有产物之间的自洽性**——标记就是工具自身输出的、可重算的绑定关系，而不是文件名：

**A. analyze 输出目录（`_is_verified_report_output`），四项全过才认：**

1. `report.json` 是 schema 有效的 `pagetrace.report/v1`，且 `tool` 精确等于 `{"name": "pagetrace", "version": TOOL_VERSION}`（`_build_report_document` 给每份报告盖的身份）；
2. `summary.normalized_result_sha256` 能用同一规范 JSON（`_canonical_json`）从文档自身的 `case_id` / `document` / `results` 重算出来——只贴个 schema 字符串的仿冒 `report.json` 过不了这一项；
3. `summary` 的 5 项计数（total/pass/fail/unknown/ambiguous）必须由 `results` 导出，与之一致；
4. `report.html` 存在，其内嵌 `report-data` JSON 与 `report.json` 一致（同 schema、同 tool 身份、每条 entry 的 `case_id` 与 `document.file_name` 相符），且 `assets/report.css` 与 `assets/report.js` 均存在。

**B. S0 输出目录（`_is_verified_s0_output`），全过才认：**

`S0_REPORT.json` 的 `format == "pagetrace.s0-report/v1"`、`project == "P026 PageTrace"`、`s0_result ∈ {PASS, FAIL, SMOKE_PASS}`、`suite.case_count == 48`；`counts` 的 8 项逐项等于 `gates` 的对应数字；`replay.hashes` 全为 64 位小写 hex、条数等于 `suite.repeat`、`unique_hash_count == len(set(hashes))`；且 `replay-hashes.txt` 逐行等于 `replay.hashes`。

**拒绝逻辑：** 以上两类都不满足 → `cmd_clean` 报 `INPUT ERROR: refusing to clean …: not a verified PageTrace output directory …`，退出码 2，目录原样保留。裸 `report.html`、任意 `S0_REPORT.json`、只有 schema 的 `report.json`、被篡改过 `results`/`summary` 的报告一律拒绝。受保护路径拒绝逻辑（workspace、fixtures、cwd、根目录、包祖先）原样保留，未动。

**诚实说明（局限）：** 本方案不含密钥/签名——一个故意按同一规则完整伪造出自洽报告的人为文件无法被区分（它与真实输出在信息上等价）。本门禁防的是**误删无关目录**（GPT 复现的事故形态：通用文件名被当成删除授权），不是防有预谋的伪造。如需防伪造，需另立带密钥的标记设计（超出本次修复与冻结规格范围）。

### 复现后证据（同一复现步骤重跑）

```text
$ clean /tmp/r1-repro/unrelated-report-folder   # report.html + keep.txt
TARGET: /tmp/r1-repro/unrelated-report-folder
INPUT ERROR: refusing to clean …: not a verified PageTrace output directory …
CLEAN_UNRELATED_EXIT=2；目录完整保留，keep.txt 内容 "do not delete me" 不变
$ clean <真实 analyze 输出目录> → REMOVED，EXIT=0
$ clean <真实 s0 --repeat 1 输出目录> → REMOVED，EXIT=0
$ clean --dry-run <真实 analyze 输出目录> → DRY RUN，EXIT=0，目录保留
```

## 3. P1-R1-04 绝对路径泄漏 — 复现前证据（漏洞存在）

按 GPT 步骤复现（修复前）：合成 trace 的 `document.file_name` 改为 `/home/alice/private/contracts/secret.pdf`：

```text
$ validate --trace abs.trace.json --pdf po-ext-01.pdf
document: /home/alice/private/contracts/secret.pdf (5 pages, sha256 97d1f68a…)
VALID: bundle is a well-formed pagetrace.bundle/v1 document；VALIDATE_EXIT=0
$ analyze … --out abs-out
document: /home/alice/private/contracts/secret.pdf (5 pages, sha256 97d1f68a…)
ANALYZE_EXIT=1（分析照常跑完）；report.json 的 document.file_name 原样保存完整绝对路径
```

## 4. P1-R1-04 修复：`file_name` 拒绝规则（R-11）

**规则（只允许纯文件名）：** 不得含 `/` 或 `\`；不得以 Windows 盘符开头（`C:\…`、`C:/…`、盘符相对路径 `C:…`）；不得为 UNC 路径（`\\server\share\…`、`//server/share/…`）；不得为相对目录形式（`sub/file.pdf`、`../file.pdf`、`..\file.pdf`、含 `..` 目录段）；不得为裸目录引用 `.` / `..`；不得含控制字符。首字符后出现 `:`（如 `ab:c.pdf`）不是盘符，允许。

**双层落地：**

- Schema 层：`document.file_name` 新增 `pattern: ^(?![A-Za-z]:)(?!\.{1,2}$)[^/\\]+$` + 更新 `description`。两份副本同步改。
- Runtime 层：`trace_bundle.is_bare_file_name()`（与 schema 同一正则）+ `TraceBundle._runtime_errors()` 复核。

**防泄漏关键（只拦值不够，还要拦回显）：** `jsonschema` 的 pattern 报错文本会原样引用违规值；`TraceBundle.__init__` 因此在 schema 校验**之前**先行拦截非纯文件名并抛出不含该值的通用错误（`document.file_name must be a bare file name (no directory, no absolute path)`），另对 schema 报错做脱敏（把值替换为 `[redacted file_name]`）。`_load_bundle` 经此路径后，CLI 的 `validate`/`analyze` 在打印/写报告前即以退出码 2 拒绝。`report.json` / `report.html` 的 `document` 只来自已校验通过的 bundle，故不再含绝对路径。

**已知局限（已在测试注释中写明）：** 直接调用 `validate_bundle_schema()` 的报错文本仍会引用违规值（jsonschema 自身行为）；CLI 与 `TraceBundle` 均不走该裸路径，终端泄漏已堵住。调用方须经 `TraceBundle`。

### 复现后证据（同一复现步骤重跑）

```text
$ validate --trace abs.trace.json --pdf po-ext-01.pdf
INPUT ERROR: /tmp/r1-repro/abs.trace.json: document.file_name must be a bare file name (no directory, no absolute path)
VALIDATE_EXIT=2；stdout/stderr 中 "/home/alice" 出现 0 次
$ analyze … --out abs-out2 → ANALYZE_EXIT=2；stdout/stderr 中 "/home/alice" 出现 0 次；未创建输出目录与 report.json
```

四种路径形式验证（见测试）：POSIX（`/home/…`、`/secret.pdf`）、Windows（`C:\…`、`C:/…`、`D:…`）、UNC（`\\server\share\…`、`//server/share/…`）、相对目录（`sub/…`、`../…`、`..\…`、`a/b/../c.pdf`、`.`/`..`）均被拒绝；合法纯文件名（`secret.pdf`、`my report (final).pdf`、`a.b.c.pdf`、`x.pdf`）正常通过。

## 5. 新增测试

- `tests/integration/test_cli.py`（clean 区，新增 7 个）：
  - `test_clean_refuses_unrelated_report_html_directory`（GPT 复现 verbatim）
  - `test_clean_dry_run_refuses_unrelated_directory`（`report.html` + 任意 `S0_REPORT.json`，`--dry-run` 也拒绝）
  - `test_clean_refuses_arbitrary_s0_report_json`
  - `test_clean_refuses_schema_only_report_json`
  - `test_clean_refuses_tampered_report_json`（改 `summary` 计数）
  - `test_clean_refuses_tampered_report_hash`（改 `results`）
  - `test_clean_removes_verified_s0_output`（真实 `s0 --repeat 1` 输出仍可 clean）
  - 另改 1 处旧断言：`test_clean_refuses_non_marker_directory` 的措辞改成新拒绝文案。
- `tests/unit/test_file_name_paths.py`（新建，66 个）：`is_bare_file_name` 参数化（15 拒绝 + 5 接受 + 4 非法类型）、`parse_bundle` 双层拒绝 + 错误文本无泄漏（15 拒绝 + 5 接受）、schema 层拒绝（15）、CLI `validate`/`analyze`（4 种形式 + GPT 复现 verbatim + 合法通过）。

## 6. 相关测试结果

- 新测试 + `test_cli.py` + `test_bundle.py` + `test_page_semantics.py`：**437 passed**（含 66 个新建 `file_name` 测试与 7 个新建 clean 测试）。
- 全量 `pytest tests/`：**745 passed，9 failed**（351.89s）。9 个失败全部在 P1-R1-02 工人（UNLOCATABLE 归因）的在改文件中，与本人改动无关：`test_fixture_manifest.py::test_specs_match_manifest`（1）、`test_verdicts.py` 的 `un-ext-09/10/11` 与 `test_unlocatable_reasons_split_four_four_four`（4，`first_fault_stage` 由 `extraction` 变为 `None`，正是 R1-02 修复的行为）、`test_run_s0.py::test_golden_sha_matches_frozen_value` 与 `test_run_s0_real_suite_repeat_2`（2，golden 已被该工人改动）、`test_oracle.py::test_golden_unlocatable_reasons_are_4_4_4`（1）、`test_html_report.py::test_real_pipeline_counts`（1）。本人文件相关的测试（`test_cli.py`、`test_bundle.py`、`test_page_semantics.py`、新建 `test_file_name_paths.py`）在全量中全部通过；`test_bundle.py` 覆盖全部 48 个 fixture 与 44 个无效 fixture 的 bundle 解析，`file_name` 改动未造成任何回归。
- 一次性观察（未复现）：上述 437 测试的第一遍运行时，另一工人的 `test_s0_repeat_1_smoke_pass`（s0 区，非本人文件）失败 1 次（`S0_RESULT: SMOKE_PASS` 断言），随后两次全量重跑均通过（437 passed）。疑似负载抖动，非本人改动所致，已汇报给协调员复核。

## 7. 未能核实的事

- 冻结规格 `PROJECT_BOOK.md` / `IMPLEMENTATION_PLAN.md` 未改；`docs/PAGE_SEMANTICS.md` 的 R-11 与 schema/runtime 三方一致已自查，但未请终审复核。
- 未验证 `pip install .` 安装包形态下的行为（只在源码 checkout + `PYTHONPATH=src` 下验证）；`src/pagetrace/schemas/` 副本已同步，安装包读的是该副本，理论一致。
- 未做 GitHub/Drive 上传（任务明确不做）；未 commit。
