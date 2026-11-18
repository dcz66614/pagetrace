# PageTrace CLI（T009）

`pagetrace.cli` 是 P026 PageTrace 的命令行入口（PROJECT_BOOK §12）。
它是核心模块的薄封装：定位与归因在 `compare_stages`，bundle 解析与
校验在 `trace_bundle` / `contracts`，HTML 渲染在 `report_html`，
S0 门禁在 `tools/run_s0.py`。CLI 本身不重写算法、不重算 verdict、
不猜测任何页码。

## 调用方式

在 PACKAGE_ROOT（`04_source/source/`）下运行，使用共享虚拟环境。
T013 起为单一 `src` 打包布局：安装后无需 `PYTHONPATH`，任意目录均可运行：

```bash
cd 04_source/source
.venv/bin/pip install -e .[dev]   # 或 pip install .
.venv/bin/python -m pagetrace.cli --help
```

未安装时在源码检出目录下运行仍可用（`cli.py` / `tools/run_s0.py` /
测试会把 `src/` 插到 `sys.path` 最前面作为后备）：

```bash
cd 04_source/source
export PYTHONPATH=$PWD/src PYTHONSAFEPATH=1
.venv/bin/python -m pagetrace.cli --help
```

> **历史说明（T013 P2-08 已修复）：** 旧布局中顶层 `pagetrace/` stub
> （T001 contracts）与生产包 `src/pagetrace/` 并存，而 pyproject 写
> `packages = ["pagetrace"]`，装的是 stub，导致不加 `PYTHONPATH=src`
> 即报 `No module named pagetrace.cli`。该 stub 已删除，pyproject 改为
> `src` 布局并打包 `assets/`；`PYTHONPATH=src` 现在只是后备做法。

## 命令

### `analyze` — 分析一份 PDF + trace bundle

```bash
.venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out out/case-001 [--include-snippets]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--pdf` | 是 | 源 PDF 路径（默认限制 50 MiB / 500 页，见 §13） |
| `--trace` | 是 | trace bundle JSON（`pagetrace.bundle/v1`） |
| `--out` | 是 | 输出目录，不存在则创建；相对路径按当前目录解析 |
| `--include-snippets` | 否 | 在 `report.html` 中写入完整引文，否则只写前 40 字摘要（§13） |

流程：校验 bundle（schema + 跨字段规则）→ 用真实 PDF 字节校验
`document.sha256`（不符即停，退出 2）→ 诚实抽取 PDF →
`analyze_bundle` 逐条引用归因 → 写出报告。

输出（`--out` 目录内）：

| 文件 | 内容 |
|---|---|
| `report.json` | `pagetrace.report/v1` 报告：`case_id`、`document`（文件名/页数/SHA-256）、`results`（逐条引用 verdict + 证据）、`summary`（计数 + `normalized_result_sha256`）。CLI 写出后会用 `validate_report_schema` 自检。`generated_at` 刻意省略：时间戳不是证据，且归一化 hash 必须跨运行稳定（§8.4） |
| `report.html` | T008 四栏联动离线报告（`write_report`） |
| `assets/report.css`、`assets/report.js` | 报告配套静态资源 |

`report.json` 从不包含引文原文（只有 `quote_sha256`）；引文原文
只出现在 `report.html` 的嵌入数据中，且默认只放前 40 字摘要，
`--include-snippets` 才放全文（PROJECT_BOOK §13）。

### `validate` — 只校验，不分析

```bash
.venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--trace` | 是 | trace bundle JSON |
| `--pdf` | 否 | 给出时额外校验 `document.sha256` 是否与真实 PDF 字节一致 |

打印 schema、case_id、文档信息、引用数、各阶段 present / missing /
empty 清单。悬空引用（chunk / index 记录缺失、引用无 display 记录）
会注明是“供分析器归因的故障数据”，不是校验失败——解析器接受
它们（T010 设计如此）。

### `s0` — S0 门禁（转发给 `tools/run_s0.py`）

```bash
.venv/bin/python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out out/s0
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--suite` | `fixtures` | fixture 套件目录，相对路径按 PACKAGE_ROOT 解析 |
| `--repeat` | `100` | 归一化重放次数（§8.4：100 次应得唯一 SHA-256） |
| `--out` | `05_tests/s0` | 输出目录；**相对路径按仓库根目录解析**（沿用 `tools/run_s0.py` 的既有行为，与 T007 验收命令一致），绝对路径按原样使用 |

CLI 只转发参数与退出码，门禁逻辑与报告格式完全由 `run_s0.py`
负责。输出 `S0_REPORT.json` 与 `replay-hashes.txt`。

### `clean` — 删除一个指定的 PageTrace 输出目录

```bash
.venv/bin/python -m pagetrace.cli clean --dry-run out/case-001
.venv/bin/python -m pagetrace.cli clean out/case-001
```

| 参数 | 说明 |
|---|---|
| `target`（位置参数） | 要删除的输出目录，必须明确指定 |
| `--dry-run` | 只显示目标路径与内容，不删除 |

安全规则（硬性）：

1. 无论是否 `--dry-run`，先打印 `TARGET: <绝对路径>`，再做任何判断。
2. 只删除带 PageTrace 标记的目录：含 `report.json`（且其 `schema`
   为 `pagetrace.report/v1`）、或 `report.html`、或 `S0_REPORT.json`。
   无标记的目录拒绝删除（退出 2），原样保留。
3. 拒绝删除受保护路径：PACKAGE_ROOT 本身、`fixtures/`、当前工作
   目录、文件系统根、以及 PACKAGE_ROOT 的任何祖先目录（退出 2）。
4. 目标不存在或不是目录 → 退出 2。

## 退出码（PROJECT_BOOK §12.2）

| 退出码 | 含义 | 例子 |
|---:|---|---|
| 0 | 命令成功 | `analyze` 全部引用 PASS；`validate` 通过；`s0` 全部门禁通过；`clean` 完成 |
| 1 | **分析已完成，但结果含 FAIL / UNKNOWN / AMBIGUOUS / NEEDS_MANUAL_REVIEW** | `analyze` 检出 `FAIL_PAGE_OFFSET`；trace 缺阶段快照得 `UNKNOWN_TRACE_MISSING`。这是完成的分析，**不是工具崩溃** |
| 2 | 输入无效 | bundle 不是合法 JSON / schema 或跨字段校验失败；PDF 不存在、不可读、超限、加密；`document.sha256` 与真实 PDF 不符（`INPUT_HASH_MISMATCH`）；`clean` 目标无标记或受保护；用法错误（argparse 同样退出 2） |
| 3 | 内部错误 / 未捕获异常（工具崩溃） | 写报告时 `--out` 指向既有文件等意外失败，打印 traceback。**与退出 1 严格区分**：1 是“分析跑完了，结果不好”，3 是“工具本身没跑完” |
| 4 | S0 门禁失败（仅 `s0`） | 任一 §8.3 门禁未通过 |

### 没有 trace 时输出 UNKNOWN，不臆测阶段

某阶段快照缺失（`missing_stages` 列出该阶段）时，分析器返回
`UNKNOWN_TRACE_MISSING`，`first_fault_stage` 为 `null`，报告如实
写入 `report.json` / `report.html`，`analyze` 退出 1。缺失的阶段
永远不会被猜成某个具体阶段，也永远不会被转成 PASS。

## 未实现：`fixtures build`

PROJECT_BOOK §12.1 示例中还有
`python -m pagetrace.cli fixtures build --out fixtures/generated`，
T009 未实现：仓库没有 fixture 生成器，48 组 fixture 是 T002 冻结
的产物，不由 CLI 生成。如未来需要，先在任务卡中立项，不要在
CLI 里临时拼一个生成器。

## 示例（真实 fixture）

```bash
cd 04_source/source
# 校验（应 exit 0）
.venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf
# 分析故障用例（cite-fault 为 FAIL_PAGE_OFFSET，应 exit 1）
.venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out out/case-001
# hash 不符（应 exit 2）
.venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-02.pdf
# 预览清理（不删除）
.venv/bin/python -m pagetrace.cli clean --dry-run out/case-001
```

## 测试

```bash
TMPDIR=$PWD/.tmp .venv/bin/python -m pytest tests/integration/test_cli.py -q
```

22 个测试覆盖：help 与参数、故障用例 exit 1 + JSON/HTML 输出、
确定性（两次运行归一化 hash 一致）、控制引用单包 exit 0、
`--include-snippets` 默认摘要 vs 全文、缺阶段快照 UNKNOWN 不猜测、
hash 不符 exit 2、缺失输入 exit 2、工具崩溃 exit 3 与分析 FAIL
exit 1 的区分、`validate` 的三种路径、`clean` 的 dry-run / 真删 /
拒删无标记目录 / 拒删受保护路径 / 目标缺失，以及 `s0 --repeat 1`
转发通过。
