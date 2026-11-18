# T012 审查包 02 — 复核证据（实测数据）

- 项目：P026 PageTrace 引文落页镜；任务：T012 独立只读代码审查
- 基线：`2e7d0f8`；审查者：独立会话 `d470301b-fe7f-4398-a72b-170af3572a20`，模型 Muse Spark
- 本包所列数字均为本次审查亲自跑出的结果，不是转述施工汇报。命令均在 worktree `~/workspace/p026-pagetrace-t012` 内执行，Python 为 `04_source/source/.venv/bin/python`（指向主仓库 venv 的符号链接）。

## §1 全量 pytest 复现：639 passed

命令（后台执行，`TMPDIR=$PWD/.tmp`，因 `/tmp` 为 512M tmpfs）：

```bash
cd 04_source/source
TMPDIR=$PWD/.tmp .venv/bin/python -m pytest -q
```

结果：`639 passed in 162.13s (0:02:42)`，退出码 0。逐文件计数（`pytest --collect-only -q` 实测，与总数 639 一致）：

| 测试文件 | 数量 |
|---|---:|
| `tests/unit/test_bundle.py` | 291 |
| `tests/unit/test_verdicts.py` | 156 |
| `tests/unit/test_page_semantics.py` | 47 |
| `tests/unit/test_extract.py` | 19 |
| `tests/unit/test_locate.py` | 15 |
| `tests/unit/test_fixture_manifest.py` | 7 |
| `tests/integration/test_cli.py` | 22 |
| `tests/integration/test_html_report.py` | 14 |
| `tests/integration/test_oracle_parity.py` | 3 |
| `tests/e2e/test_e2e.py` | 14 |
| `tests/oracle/test_oracle.py` | 21 |
| `tests/privacy/test_privacy.py` | 11 |
| `tests/prototypes/test_prototype.py` | 10 |
| `tests/s0/test_run_s0.py` | 9 |

## §2 S0 双报告核对：一致，全部 PASS

`05_tests/s0/S0_REPORT.json`（`base_commit 5095c37e…`）与 `05_tests/s0-final/S0_REPORT.json`（`base_commit a6bc9c8f…`）除 `base_commit` 外逐项一致：

| 门禁 | 结果 |
|---|---|
| `s0_result` | PASS / PASS |
| 检出 detection | 48/48（PAGE_OFFSET 12、PAGE_METADATA_MISSING 12、DUPLICATE_TEXT_AMBIGUITY 12、UNLOCATABLE 12） |
| `first_fault_stage` | 48/48 |
| 控制误报 `control_false_positives` | 0 |
| parity | 96/96 引用一致，0 失配 |
| Golden 一致 | 0 失配（96 条引用） |
| 不确定误判 `uncertainty_violations` | 0 |
| 重放 replay | 100 次，1 个唯一哈希 |

重放哈希（两份报告 + 两份 `replay-hashes.txt` 均为 100 行同一值）：

```text
5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8
```

逐用例复核：48 组生产 fault verdict 分布为 `FAIL_AMBIGUOUS 12 / FAIL_METADATA_MISSING 12 / FAIL_PAGE_OFFSET 12 / FAIL_UNLOCATABLE 12`；48 组控制引用全部 PASS；`parity_mismatches` 合计 0。

Golden 独立核对（`fixtures/golden/expected.json`，48 组）：UN fault 原因 `IMAGE_ONLY 4 / EMPTY 4 / NO_EXACT_MATCH 4`；Golden verdict 全集为 `FAIL_AMBIGUOUS / FAIL_METADATA_MISSING / FAIL_PAGE_OFFSET / FAIL_UNLOCATABLE / PASS`——无 `AMBIGUOUS` / `UNKNOWN_*` / `NEEDS_MANUAL_REVIEW`（见 PACK_01 P2-07）。`un-ext-12` 的 spec 确认 8 页全为 `kind: "text"`（其余 11 组 UN 均含 image 或 blank 页），其 fault 为 `near-miss-quote`、`NO_EXACT_MATCH`（PACK_01 P2-11）。

## §3 参考实现差分比对：250 输入，1 处类型差异

方法：直接 import `tests/unit/test_page_semantics.py` 的参考实现与 `src/pagetrace/contracts.py` 的生产实现，对 `to_number1` / `to_index0` / `to_viewer1` / `viewer_to_index0`（值 × 页数）、`label_to_index0`（label × 映射）、`resolve_citation_to_index0`（值 × basis × label_map）、`validate_source_pages0`（14 种集合输入）逐项比对返回值与异常类型。

结果：250 组，值/类型差异 1 处：

```text
resolve(None, "PDF_LABEL", 6, label_map=None)
  参考实现：UnresolvableLabelError("no PDF label map available")
  生产实现：PageSemanticsError("citation_page_value is null for basis PDF_LABEL: ...")
```

另有 7 处仅消息不同（None 值 + 各 basis / BOGUS basis 的报错措辞与检查顺序），值与异常类型均一致。详见 PACK_01 P2-03。

## §4 Oracle 独立性证据

grep + 全文件通读（`tests/oracle/*.py` 共 1,192 行）：

```text
tests/oracle/api.py:       from .attribute / .locate / .pdfread（相对模块）
tests/oracle/attribute.py: from .locate / .pdfread / .textnorm（相对模块）
tests/oracle/locate.py:    from .textnorm（相对模块）
tests/oracle/pdfread.py:   from pdfminer.high_level / .layout / .pdfdocument / .pdfpage / .pdftypes
tests/oracle/textnorm.py:  import hashlib / re / unicodedata（stdlib）
```

`pagetrace` / `pypdf` 在 `tests/oracle/` 的代码 import 中出现 0 次（仅 docstring 提及）；生产 `src/pagetrace/` 的 PDF 读取只用 `pypdf`（`extract.py:32`、`pdf_input.py:26`）。两者交汇仅在 harness 层（`tools/run_s0.py`、parity 测试）。

归一化等价：`textnorm.collapse_text`（NFC → CRLF/CR→LF → `\s+` 折叠 → strip）与 `normalize.normalize_text` 逐行同义；fixture 生成器 `tools/generate_fixtures.py` 的 `norm_text` 亦同款三行。定位算法独立（Oracle 最长前后缀覆盖 + 二分 vs 生产切分点枚举），成对跨页判定已证等价（PACK_01 §2.3）。

## §5 许可证实测

已安装发行版元数据（`.venv`，`importlib.metadata` 实测）：

```text
Pillow:      MIT-CMU
pypdf:       BSD-3-Clause
reportlab:   BSD license (see license.txt for details)
pdfminer.six: MIT
jsonschema:  MIT
```

Pillow 13.0.0 自带 `licenses/LICENSE` 原文（节选，逐字）：

```text
Like PIL, Pillow is licensed under the open source MIT-CMU License:
```

Pillow 13.0.0 官方文档 About 页与 13.0.0 发布说明同样表述为 MIT-CMU；旧版（9.x/10.x/11.x）LICENSE 称 HPND——同一许可文本的不同名称。结论：lock 的 MIT-CMU 对 13.0.0 正确，计划 §10.2 的 HPND 措辞已过时（PACK_01 §2.9）。

## §6 隐私实测（均为本次 live 运行）

1. `clean` 绝对路径打印（PACK_01 P2-01）：

```bash
# 相对路径调用，工作目录 /tmp/t012-clean-test
.venv/bin/python -m pagetrace.cli clean --dry-run out1
# 输出：
TARGET: /tmp/t012-clean-test/out1
contains 3 entries: assets, report.html, report.json
DRY RUN: nothing deleted
```

相对路径调用仍打印解析后的绝对路径；`tests/integration/test_cli.py:292,301` 甚至断言该行为（`TARGET: {out.resolve()}`）。`analyze` 的相对路径输出经 `test_privacy.py:175-196` 锁定为无绝对路径，`clean` 无对应覆盖。

2. 报告内容：`report.json` 无 quote 原文、无时间戳字段（`test_privacy.py` 11 测试通过，含于 639）；T011 隐私扫描日志（`07_evidence/runtime_logs/t011-privacy-scan.log`）扫描 10 个人工件 `TOTAL LEAKS: 0`；本次审查另对 `src/` 做网络 import 扫描：无 `socket`/`urllib`/`requests`/`http.client`。

## §7 健壮性探针（未校验输入，均本次实测）

以 `du-chk-01.pdf` + 对应 bundle，改动全部 chunk/index 记录后调 `analyze_bundle`：

```text
chunk source_page_indices0 = 5 (int)   -> TypeError: 'int' object is not iterable
chunk source_page_indices0 = None      -> TypeError: 'NoneType' object is not iterable
index source_page_indices0 = 3 (int)   -> TypeError: 'int' object is not iterable
chunk source_page_indices0 = [0.5]     -> OK, FAIL_PAGE_OFFSET（正常降级）
display viewer_page1 = "x"             -> OK, FAIL_PAGE_OFFSET
display value True + PDF_INDEX_0       -> OK, NEEDS_MANUAL_REVIEW（control）
```

（PACK_01 P2-02。注：首轮以 `po-ext-01` 探针时被 extraction 首错掩盖，改用 `du-chk-01` 并改动全部记录后复现。）

原因字段分歧探针（`po-ext-01.pdf`，本次实测）：

```text
缺失 chunking 快照：  生产 reason=TRACE_MISSING / Oracle reason=None（verdict 同为 UNKNOWN_TRACE_MISSING）
display PDF_NUMBER_1 值 0：生产与 Oracle 同为 NEEDS_MANUAL_REVIEW / reason=VALUE_BASIS_TYPE_MISMATCH
仅 display 具名页的 UNLOCATABLE（un-ext-01）：生产与 Oracle 同为 expected=None / reason=NO_TEXT_LAYER
```

（PACK_01 P2-04、P2-05、P2-06。）

0 引用 bundle 的 `normalized_result_sha256`（`_build_report_document` 实测）：

```text
total: 0  normalized sha: a35f8d5ba56f8a422191c488abfb1698d245463d57fee2400bd1819b74867e73
```

——非 null，与 `PAGE_SEMANTICS.md` §1.3 的“无可规范化结果时为 null”不符（PACK_01 P2-12b）。

## §8 Schema 核对（本次实测）

以 JSON 遍历统计：bundle schema 11 个对象 schema、`report` schema 6 个对象 schema 的 `additionalProperties` 均为 `false`（仅 `display_record` 的 `if`/`then` 子 schema 无此键，属正常）；`$schema` 均为 `https://json-schema.org/draft/2020-12/schema`；UNKNOWN→`viewer_page1` null 由 `display_record` 的 `if`/`then` 强制（`then.properties.viewer_page1.const: null`）。裸 `page` 字段无独立字段名扫描（grep 0 命中，PACK_01 P2-12a）。

## §9 审查期间工作树状态

审查开始与结束时 `git status --short` 均仅显示预先存在的 untracked 项：

```text
?? 04_source/source/.venv
```

无任何生产文件被修改；本次提交只含任务卡 FILE_OWNERSHIP 内的文件 + `REVIEW_PACK_SHA256SUMS.txt`（见 REVIEW_INDEX.md）。
