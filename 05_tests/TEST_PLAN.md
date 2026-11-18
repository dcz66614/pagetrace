# P026 PageTrace — 测试计划（T011）

> 规格 v1.0.0 已冻结（`01_project_book/PROJECT_BOOK.md`）。本计划只描述
> 如何验证，不改规格、不改 Golden、不改生产代码。发现缺陷另派 FIX 任务。

## 1. 范围

| 层 | 位置 | 内容 |
|---|---|---|
| 单元 | `04_source/source/tests/unit/` | bundle 解析、抽取、定位、页码语义、verdicts（T001–T006、T010） |
| Oracle | `04_source/source/tests/oracle/` + `tests/integration/test_oracle_parity.py` | 独立实现与生产 parity（T006） |
| 集成 CLI | `tests/integration/test_cli.py` | analyze/validate/s0/clean 与退出码（T009） |
| 集成 HTML | `tests/integration/test_html_report.py` | 四栏报告渲染、离线、确定性（T008） |
| **集成 E2E** | **`tests/e2e/test_e2e.py`（T011 新增，13 测试）** | 见 §3 |
| **隐私回归** | **`tests/privacy/test_privacy.py`（T011 新增，12 测试）** | 见 §4 |
| S0 门禁 | `tests/s0/test_run_s0.py` + `tools/run_s0.py` | 48 组冻结套件，100 次重放唯一 hash（T007） |

## 2. 如何运行（PACKAGE_ROOT = `04_source/source/`）

```bash
cd 04_source/source
export PYTHONPATH=$PWD/src PYTHONSAFEPATH=1   # 双包问题，见 §6
mkdir -p .tmp
TMPDIR=$PWD/.tmp .venv/bin/python -m pytest -q
```

全量约含 S0 repeat=2 的端到端用例（单次约 10 s），其余均为秒级。
S0 全量 100 次重放是独立的验收命令，不在 pytest 内：

```bash
PYTHONPATH=$PWD/src PYTHONSAFEPATH=1 TMPDIR=$PWD/.tmp \
  .venv/bin/python -m pagetrace.cli s0 --suite fixtures --repeat 100 \
  --out 05_tests/s0-final
# --out 相对仓库根解析；约 7 分钟；退出 0 = 全部门禁通过
```

## 3. E2E 断言（`tests/e2e/test_e2e.py`）

完整链路 PDF + trace → `report.json` + `report.html`，真实子进程
调用 CLI，不用 mock：

- **四类故障各一例**：`po-ext-01`（FAIL_PAGE_OFFSET / PAGE_OFFSET /
  extraction）、`mm-ext-01`（FAIL_METADATA_MISSING /
  PAGE_METADATA_MISSING / extraction）、`du-chk-01`（FAIL_AMBIGUOUS /
  DUPLICATE_TEXT_AMBIGUITY / chunking）、`un-ext-01`（FAIL_UNLOCATABLE /
  UNLOCATABLE / extraction）。每例 `analyze` 退出 1，`report.json`
  为合法 `pagetrace.report/v1`，fault/control 两条结果与预期一致，
  HTML + assets 齐全，源 PDF **不**复制进输出目录。
- **四栏字段齐全**：嵌入 `#report-data` JSON 中每条 entry 含
  `truth_pages` / `extraction` / `chunk` / `index_record` /
  `display` / `stage_diffs` / `verdict` / `fault_type` /
  `first_fault_stage` / `observed_page_value` /
  `correct_pdf_page_number1` / `correct_viewer_page1` 等全部字段；
  页面含 ①②③④ 栏标题与“对照表：错误页码 → 首错阶段 →
  正确来源位置”。
- **对照包退出 0**：仅 `cite-control` 的 bundle 分析退出 0，
  PASS 1 / FAIL 0。
- **确定性**：同一用例跑两次，`normalized_result_sha256` 相同，
  `report.json` 与 `report.html` 字节一致。
- **退出码矩阵**（§12.2）：hash 不符退出 2（`INPUT_HASH_MISMATCH`，
  不写报告）；PDF / trace 缺失退出 2；与分析 FAIL（1）严格区分。
- **断网渲染**：headless shell 以
  `--host-resolver-rules=MAP * ~NOTFOUND`（注意必须用 `=` 形式，
  空格形式会被旧版 shell 当成第二个目标）渲染 `file://` 报告，
  退出 0，四栏与 `po-ext-01/cite-fault` 均在 DOM 中，DOM 无
  `http://` / `https://`。
- **S0 基线不变**：冻结报告 `05_tests/s0/S0_REPORT.json` 仍为
  PASS：检出 48/48、首错阶段 48/48、控制误报 0、parity 96/96、
  重放唯一 hash 1 个 =
  `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`。
  任何出入先停下来核查，**不得改 Golden 或 runner 去“修”数字**；
  完整 100 次重放复核见 `05_tests/s0-final/`（验收命令产物）。

## 4. 隐私回归断言（`tests/privacy/test_privacy.py`，§13）

扫描**真实产物**，不是只断言配置：

- **全文引文**：JSON 报告永不含 `quote_text`（只有
  `quote_sha256`），无论是否 `--include-snippets`；HTML 默认只含
  前 40 字摘要 + `…`，全文仅 `--include-snippets` 时出现。
  证明用长引文 bundle 变体（> 40 字唯一 sentinel）：冻结夹具的
  引文均 ≤ 40 字，默认摘要即全文是摘要规则本身，不是泄漏，
  测试中对此有显式断言。
- **绝对路径 / 主机名 / 时间戳**：扫描 `report.json`、
  `report.html`、assets、S0 报告与 `replay-hashes.txt`，不得含
  `/home/`、家目录、主机名或 `YYYY-MM-DDTHH:MM` 形式时间戳；
  `report.json` 不得含 `generated_at`。另有一例以**相对路径**
  调用 CLI，断言其 stdout/stderr 同样无泄漏。
- **无网络 / 不上传**：静态扫描生产源码不得含 `socket` /
  `urllib` / `requests` / `httpx` / `http.client` 等网络调用；
  报告 HTML/CSS/JS 不得含 `http://`、`https://`、`fetch(`、
  `XMLHttpRequest` 或外部 `<script src>`（本地相对
  `assets/report.js` 除外）；输出目录不得含 PDF 副本，
  `document` 只记文件名 + SHA-256。
- **S0 报告**：基线 `S0_REPORT.json` 与 `replay-hashes.txt`
  同样无上述泄漏；`05_tests/s0-final/` 由验收命令生成后，
  以同一规则做离线扫描（见 `07_evidence/runtime_logs/t011-privacy-scan.log`）。

## 5. 证据

- 全量 pytest 日志：`07_evidence/runtime_logs/t011-pytest-full.log`
  （另存摘要于 `05_tests/test-results/t011-pytest.log`）。
- S0 final：`05_tests/s0-final/S0_REPORT.json` +
  `05_tests/s0-final/replay-hashes.txt`，及运行日志
  `07_evidence/runtime_logs/t011-s0-final.log`。
- 隐私扫描日志：`07_evidence/runtime_logs/t011-privacy-scan.log`。
- UI 截图：`07_evidence/screenshots/t011-report-desktop.png`
  （1280×900）、`t011-report-narrow.png`（390×844），浏览器
  Google Chrome for Testing 158.0.8127.18（headless shell 同版本）；
  `/opt/meta-chromium/chrome` 无法独立启动，不用它。
- 集成证据汇总：`07_evidence/runtime_logs/t011-evidence.log`。

## 6. 已知问题（不阻塞 T011，均已有归属）

- **P2 双包问题（T013 已修复）**：旧布局顶层 `pagetrace/` stub 与
  `src/pagetrace/` 并存，`python -m pagetrace.cli` 须用
  `PYTHONPATH=$PWD/src PYTHONSAFEPATH=1`。T013（P2-08）已改为单一
  `src` 打包布局并删除 stub；安装后无需 `PYTHONPATH`（源码检出下
  仍可用作后备）。注意：共享 venv 的 editable 安装仍指向旧布局，
  合并后须在 venv 里重跑 `pip install -e ".[dev]"`。
- **S0 不演练不确定类 verdict（T012 P2-07，T013 已记录）**：冻结
  48 组只含故障 verdict（`FAIL_*`）与 `PASS`，无 `AMBIGUOUS` /
  `UNKNOWN_*` / `NEEDS_MANUAL_REVIEW`；不确定路径只由单元/集成
  测试覆盖。另 Oracle 三元组探针（`tests/oracle/locate.py`
  `_triple_spans`）是生产穷举 `_spans_triple` 的有界子集（只试
  `prefix_max-3..prefix_max` × `suffix_max-3..suffix_max` 切分）；
  冻结套件无 3 页跨页样本（`split_pages0` 长度只为 0 或 2），故无
  S0 影响。不得为此加 fixture——套件已冻结。另见
  `docs/LIMITATIONS.md`。
- **headless shell 1248**：空格形式的 `--host-resolver-rules "MAP *
  ~NOTFOUND"` 会被当成第二个目标而报错；须用 `=` 形式，且优先用
  最新的 1254 shell。T011 测试已按此实现。
- **T008/T009/T010 已 PASS 并合并**：本任务只做集成验证，不重做
  它们的单项断言；集成失败则回退到对应任务派修。
