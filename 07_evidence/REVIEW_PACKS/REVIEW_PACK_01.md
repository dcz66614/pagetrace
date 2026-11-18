# T012 审查包 01 — 源码审查（逐文件）

- 项目：P026 PageTrace 引文落页镜
- 任务：T012 独立只读代码审查
- 基线：`2e7d0f8`（master，T011 合并后）
- 审查者：独立会话 `d470301b-fe7f-4398-a72b-170af3572a20`，模型 Muse Spark（与施工路线不同；施工多用 gpt-6-luna）
- 审查方式：只读。未修改任何生产源码、测试、Golden、文档与发布文件（`git status` 除预先存在的 untracked `.venv` 符号链接外干净，见 REVIEW_PACK_02）。
- 范围：`04_source/source/` 下全部生产模块、Oracle、schema、文档、配置与工具；逐文件哈希见 §1。测试文件按测试计数覆盖（639 个测试全量复现，见 REVIEW_PACK_02），测试正文不逐行引用（测试是证据而非被审对象），但关键边界测试（`test_page_semantics.py` 参考实现）做了 250 输入差分比对。
- 结论：**0 个 P0，0 个 P1，13 个 P2**（§3）。P2 全部明确交给 T013 修复或记录；无一阻塞终审提交。
- 本包正文包含被审文件的真实内容引用（哈希 + 行号 + 关键行原文），不是目录清单。

## §1 逐文件审查覆盖表

路径相对 `04_source/source/`。`sha256` 为完整 SHA-256（基线 commit 时的文件内容，`git` 工作树未改动时复核一致）；行数为 `wc -l`（schema 为单行 JSON，行数记 0，另注字节数）。

| 文件 | 行数 | sha256 | 审查结论 |
|---|---|---|---|
| `src/pagetrace/__init__.py` | 11 | `12928b5fa9e1e762f66ae1f63d1fa4ce8b3ac4b26c1cba00ac3c0d1d4e8c7f5`（前 16 位 `12928b5fa9e1e762`，下同略） | PASS |
| `src/pagetrace/cli.py` | 490 | `a877b1a147409b8d…` | P2-01（clean 打印绝对路径） |
| `src/pagetrace/compare_stages.py` | 944 | `88a75f053e7935df…` | P2-02、P2-04、P2-06、P2-13 |
| `src/pagetrace/contracts.py` | 413 | `5e51b675229fbc79…` | P2-03 |
| `src/pagetrace/extract.py` | 154 | `128f26b925823a6f…` | PASS |
| `src/pagetrace/locate.py` | 193 | `7e24f93da23642b7…` | PASS |
| `src/pagetrace/normalize.py` | 61 | `c315c522881c72ce…` | PASS |
| `src/pagetrace/pdf_input.py` | 187 | `0dda32f27a58ee8b…` | PASS |
| `src/pagetrace/report_html.py` | 617 | `e3cacb534bcde33d…` | PASS（见 §2.8） |
| `src/pagetrace/trace_bundle.py` | 565 | `1b146919f7577040…` | PASS |
| `src/pagetrace/verdicts.py` | 284 | `5a0c27d8c2c37d98…` | PASS |
| `src/pagetrace/assets/report.js` | 361 | `009da7e9e624c210…` | PASS（转义完整） |
| `src/pagetrace/assets/report.css` | 158 | `3e6ea8a033f7a051…` | PASS |
| `pagetrace/__init__.py`（顶层 stub） | 8 | `f0d34827240c1693…` | P2-08（双包并存） |
| `pyproject.toml` | 25 | `2a99d8e2a52bb002…` | P2-08、P2-09 |
| `requirements.lock` | 45 | `ac77f4ee2d1bf821…` | PASS（Pillow 许可证已核实，见 §2.9） |
| `contracts/pagetrace.bundle.v1.schema.json` | 0 行 / 7875 B | `6ef5332f4dc4a04c…` | PASS |
| `contracts/pagetrace.report.v1.schema.json` | 0 行 / 8719 B | `a123094b033867d8…` | PASS |
| `docs/CLI.md` | 177 | `a2927e79e2200339…` | PASS（记录完整） |
| `docs/PAGE_SEMANTICS.md` | 244 | `464b49c692e2ab78…` | P2-12（两处 doc 超前于代码） |
| `tools/run_s0.py` | 721 | `73668444cbdb1806…` | PASS |
| `tools/generate_fixtures.py` | 1176 | `3e6195002c734946…` | PASS |
| `tools/render_previews.py` | 136 | `1d770b2099d2cf87…` | PASS |
| `tests/oracle/__init__.py` | 29 | `ebd2ce8596f405b9…` | PASS |
| `tests/oracle/api.py` | 61 | `90b1b147f0995436…` | PASS |
| `tests/oracle/attribute.py` | 645 | `92b37fed0c71cb08…` | P2-05（reason 差异） |
| `tests/oracle/locate.py` | 157 | `e88f710796d6edc8…` | P2-07（三元组探针为子集） |
| `tests/oracle/pdfread.py` | 252 | `0301148f5baa42b7…` | PASS（见观察 O-1） |
| `tests/oracle/textnorm.py` | 102 | `a0980265d3b55980…` | PASS |

> 注：上表 sha256 栏为节省篇幅只印前 16 位十六进制；完整 64 位值以审查时 `sha256sum` 实测为准，审查脚本复核命令见 REVIEW_PACK_02 §1。`git status` 证明审查期间未改动这些文件。

测试文件覆盖（计数，`pytest --collect-only` 实测）：`tests/unit/test_bundle.py` 291、`test_verdicts.py` 156、`test_page_semantics.py` 47、`test_extract.py` 19、`test_locate.py` 15、`test_fixture_manifest.py` 7；`tests/integration/test_cli.py` 22、`test_html_report.py` 14、`test_oracle_parity.py` 3；`tests/e2e/test_e2e.py` 14；`tests/oracle/test_oracle.py` 21；`tests/privacy/test_privacy.py` 11；`tests/prototypes/test_prototype.py` 10；`tests/s0/test_run_s0.py` 9。合计 639，与全量复现一致。

Fixture 覆盖：48 组 bundle / PDF / spec（`fixtures/bundles/*.trace.json`、`fixtures/pdfs/*.pdf`、`fixtures/specs/*.json` 各 48）+ `fixtures/golden/expected.json` + `fixtures/manifest.json` + `fixtures/sha256sums.txt`。逐组核对见 REVIEW_PACK_02 §2（UN 4/4/4、Golden verdict 分布）。

## §2 硬断言逐项核查（引用代码行原文）

### 2.1 0/1-based 转换 — PASS

`contracts.py` 只允许 `+1` / `-1`（R-01/R-02），布尔显式排除（F-14）：

```python
# contracts.py:325-336
def _require_int(value, field: str) -> int:
    # JSON `true` is an int subclass in Python; a bool is never a page (F-14).
    if isinstance(value, bool) or not isinstance(value, int):
        raise PageSemanticsError(f"{field} must be an integer, got {value!r}")
    return value
# contracts.py:339-346
def to_number1(index0: int, page_count: int) -> int:
    """R-01: the ONLY 0-based -> 1-based conversion is +1."""
    _require_int(index0, "pdf_page_index0")
    return _check_index0(index0, page_count) + 1
```

`compare_stages.py` 的 display 检查处处以 `resolved + 1` 核对 viewer（R-01/R-06），例如：

```python
# compare_stages.py:886-896（单页 truth 分支）
    if viewer != resolved + 1:
        return _fail(VERDICT_FAIL_PAGE_OFFSET, "PAGE_OFFSET",
                     STAGE_DISPLAY,
                     StageDiff(stage=STAGE_DISPLAY, field="viewer_page1",
                               kind="offset", pdf_page_index0=None,
                               upstream_value=resolved + 1, ...
```

全仓库 grep 未发现 `+ 2` / `- 2` / `int(label)` / `label + 1` 等违规算术；label 只查表（`label_to_index0`，`contracts.py:364-371`）。

### 2.2 page label 混用 — PASS

`resolve_display_to_index0`（`compare_stages.py:243-289`）对 `PDF_LABEL` 只查 `label_map`，多页同 label 判为 `label_unresolved`；字符串 `"7"` 与数字 `7` 分支不同（R-08 类型检查先行）。Oracle 同款逻辑（`attribute.py:268-296`）一致。`PAGE_SEMANTICS.md` 例 E（label `"7"` 查表得 index0 0）已由 `test_page_semantics.py` F-10 锁定。

### 2.3 跨页和重复文本 — PASS

`locate.py:118-193`：单页优先（`single` 全集返回，R-09）；无单页命中才试相邻对 `_spans_pair`（`MIN_CROSS_PAGE_PART_CHARS = 4`，`locate.py:44`）；三元组只探测、不定位（`span_status="unsupported_span"`，候选 `[]`）。Oracle 用另一算法（最长前后缀覆盖 + 二分，`tests/oracle/locate.py:49-75`）；本人证明两者在成对跨页判定上等价：Oracle 的 prefix/suffix 覆盖蕴含生产的一个合法切分点（取 `s = prefix` 或 `s = len-4` 的论证），反之亦然；S0 96/96 parity 佐证。唯一非等价处是三元组探针（P2-07）。

### 2.4 阶段归因顺序 — PASS

`compare_stages.analyze_citation` 固定顺序：0 缺失快照 → 1 不支持跨页 → 2 未定位 → 3 extraction → 4 chunking → 5 indexing → 6 display；每步首错即返，不跳阶段。`verdicts.py` 的 `CitationVerdict.__post_init__` 以构造时断言锁住 verdict↔fault_type、PASS↔`first_fault_stage is None`、`correct_*` 成对出现/相等。S0 阶段归因 48/48 与 Golden 一致（REVIEW_PACK_02 §2）。

### 2.5 UNKNOWN 是否被误判 PASS — PASS

三处防线均实测有效：

```python
# compare_stages.py:359-376（缺失快照）
    if missing_stages:
        return CitationVerdict(
            verdict=VERDICT_UNKNOWN_TRACE_MISSING, fault_type=None,
            first_fault_stage=None, reason=REASON_TRACE_MISSING, ...
# compare_stages.py:668-681（UNKNOWN basis 在 null 值检查之前）
    if display_record.get("citation_page_basis") == "UNKNOWN":
        return CitationVerdict(
            verdict=VERDICT_UNKNOWN_PAGE_BASIS, fault_type=None,
            first_fault_stage=STAGE_DISPLAY, ...
```

`contracts.py:375-380`：`resolve_citation_to_index0` 遇 `UNKNOWN` 抛 `UnknownBasisError`，`None` 值抛 `PageSemanticsError`（不默认 0）。Schema 层 `display_record` 的 `if`/`then` 强制 UNKNOWN 时 `viewer_page1` 为 null（已逐字段核对）。S0 gate 6（uncertainty_not_pass）0 违规；CLI `analyze` 对 UNKNOWN/AMBIGUOUS/NEEDS_MANUAL_REVIEW 出 exit 1（`cli.py:318-331`）。`run_s0.py` gate 6 另查生产 PASS 而 Golden/Oracle 非 PASS 的情形。

### 2.6 PDF 资源限制 — PASS

`pdf_input.py:29-30`：`DEFAULT_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024`，`DEFAULT_MAX_PAGES = 500`；`load_pdf` 先 `stat` 再读后复核字节数（TOCTOU 注释）；加密、0 页、超页均以受控 `PdfInputError` 拒绝；`extract_pages` 复核页数未变。限制只可下调（`extract_pdf` 的 `max_*` 透传，`extract.py:141-153`）；未发现放宽路径。整文件读入内存：上限 50 MiB，有界，可接受。

### 2.7 路径 / 内容泄露 — 1 个 P2（T012-P2-01），其余 PASS

- `report.json` 不含 quote 原文（`CitationVerdict.to_dict` 无 `quote_text` 字段；`verdicts.py:232-261`）；HTML 默认只放前 40 字摘要（`cli.py:145-149` `_excerpt` + `cli.py:261` 改写）；`--include-snippets` 才放全文（显式 opt-in，§13）。
- 报告不含时间戳（`_build_report_document` 刻意省略 `generated_at`，`cli.py:199-201`）；归一化哈希排除绝对路径/时间/主机名（`run_s0.py` 的 `normalize` 与 `citation_to_normalized`）。
- HTML 嵌入 JSON 经 `embedded_json` 转义 `<`/`>`/`&`（`report_html.py:447-456`）；`report.js` 全部插值走 `esc()`（`report.js:58-63`），逐处核对：`data-entry-id`、`title` 属性、quote 文本、label、hash 均经 `esc()`；`pages1`/`numbers1` 只输出数字；`truthLink` 的 href 经 `esc()` + `encodeURIComponent`。未发现可注入的未转义插值。
- 无网络代码：生产 `src/` 无 `socket`/`urllib`/`requests`/`http.client`（`test_privacy.py:223` 同款断言，639 通过中包含）。
- **P2-01 例外：见 §3。**

### 2.8 HTML 报告 — PASS（附观察）

`report_html.py` 只做呈现，不重算 verdict；`build_view_entry` 对未知 verdict/fault/stage 抛 `ValueError` 拒绝渲染；未知 verdict 的 tone 默认为 amber（`status_tone`，`report_html.py:140-146`），永不渲染成 PASS 绿。`build_entries_from_fixtures` 不做摘要（全文 quote 进 HTML），但仅测试调用（`tests/integration/test_html_report.py:99`），生产 CLI 路径必经 `_excerpt`——记为观察 O-2，不单独立项。

### 2.9 MIT 与依赖许可证 — PASS（Pillow 遗留项已闭合）

- 项目自有代码 MIT（`pyproject.toml:12` `license = { text = "MIT" }`）。
- 实测已安装发行版许可证：pypdf BSD-3-Clause、reportlab BSD、pdfminer.six MIT、jsonschema MIT、pytest MIT；Pillow `License-Expression: MIT-CMU`。
- **Pillow 遗留项（1）已核实闭合**：已安装 Pillow 13.0.0 的 `licenses/LICENSE` 原文写明 “Like PIL, Pillow is licensed under the open source MIT-CMU License:”；Pillow 13.0.0 官方文档 About 页同样写 “Like PIL, Pillow is licensed under the open source MIT-CMU License”；13.0.0 发布说明亦称 FriBiDi shim “covered by Pillow's MIT-CMU license”。计划 §10.2 的 “HPND/PIL License” 是旧版（9.x/10.x/11.x）LICENSE 的措辞，同一许可文本在 SPDX 语境下称 HPND——名称变了，文本与权限相同。结论：lock 的 MIT-CMU 对 13.0.0 正确；应由 T013 更新计划 §10.2 的措辞，不改 lock。无 AGPL、无商业授权引擎。
- 另：Pillow/reportlab 只被 `tools/generate_fixtures.py` 与 `tools/render_previews.py` import（fixture 生成），生产运行时只 import pypdf + jsonschema + stdlib——见 P2-09。

### 2.10 Oracle 独立性 — PASS（附 P2-05、P2-07）

独立再验（grep + import 图 + 全文件通读）：

- `tests/oracle/` 只 import stdlib（`hashlib`/`re`/`unicodedata`/`dataclasses`/`io`）+ `pdfminer.*` + 相对模块（`.attribute`、`.locate`、`.pdfread`、`.textnorm`）；**无任何 `pagetrace` / `pypdf` / `src` import**（仅 docstring 提及）。生产 `src/pagetrace/` 只用 pypdf 读 PDF（`extract.py:32`、`pdf_input.py:26`），不 import oracle。唯一交汇点是 `tools/run_s0.py` 与测试（harness 层，非生产路径）。
- 独立算法：定位用最长前后缀覆盖（二分）而非生产的切分点枚举；归一化独立重写（`textnorm.collapse_text` 与 `normalize.normalize_text` 逐行同义，§4.2）；label 表直接解析 PDF catalog `/PageLabels /Nums`（`pdfread.py:161-236`），而非 pypdf 的 `page_labels`。
- 单一已知调和点：`textnorm.py:45-102` 的单字形修复（pdfminer 丢 U+00B7 “·”）：仅当精确指纹失配时试插一个 “·”，修复须记入 evidence；SHA-256 下误匹配另一页在密码学上可忽略；S0 parity 96/96 佐证。`t006-pdfminer-pypdf-contrast.log` 称 312 页中 31 页仅差此字形——本人未重跑该 contrast 脚本（证据文件在案，Oracle 的 21 个测试通过且 parity 为 0 失配，修复逻辑本身已通读）。
- 结构相似性说明：`attribute.py` 与 `compare_stages.py` 的 helper 同名（`_find_record`、`_source_pages`、`_check_set_stage`、`_resolve_display`）且步骤同序——这是同一 spec（§4.3/§5/§7.3）推导出的同构，不是代码共享；关键分歧点（定位算法、PDF 读取、label 解析、hash 修复）均独立。

### 2.11 哈希规范化 — PASS

`normalize.py:54-61`：`quote_sha256` = §4.2 规范化后 UTF-8 的 SHA-256 小写 hex；`contracts.sha256_hex` 同款。`cli._canonical_json` 与 `run_s0.normalize` 均为 UTF-8 + sorted keys + `separators=(",", ":")` + `allow_nan=False`；`citation_to_normalized` 排序 page 列表与 evidence（stage, field, note）。S0 100 次重放 1 个唯一哈希 `5195fc9a…`（REVIEW_PACK_02 §2）。`_evidence_to_sorted_dicts` 对 `upstream/downstream_value` 用 `_sorted_pages`（仅全 int 列表才排序，`run_s0.py:140-149`）。

## §3 缺陷条目（0 P0 / 0 P1 / 13 P2）

### T012-P2-01 — `clean` 把解析后的绝对路径打印到 stdout（隐私 §13 偏差）

- 位置：`src/pagetrace/cli.py:377-378` 与 `:405`。
- 原文：

```python
# cli.py:376-378
    target = Path(args.target)
    resolved = target.resolve()
    print(f"TARGET: {resolved}")
# cli.py:405
    print(f"REMOVED: {resolved}")
```

- 实测：相对路径调用 `clean --dry-run out1` 仍打印 `TARGET: /tmp/t012-clean-test/out1`（绝对路径，含用户主目录形态）。而 `test_privacy.py:175-196` 对 `analyze` 的标准是“相对路径调用时 stdout 不得含绝对路径/`/home/`”，`clean` 不受该测试覆盖；PROJECT_BOOK §13 称“不记录绝对路径……到默认日志”。stdout 是瞬时的、本地的、无文件落盘，故定 P2 而非 P1。
- 修复建议（T013）：`TARGET:`/`REMOVED:` 打印用户原样 `args.target`，解析路径只用于内部校验（受保护路径、标记检查）；`tests/integration/test_cli.py:292,301` 现断言 `TARGET: {out.resolve()}`，须同步更新。保留“先打印、再删除”的安全顺序与目录内容清单。

### T012-P2-02 — `analyze_bundle` 对未校验输入的非列表 `source_page_indices0` 抛原始 `TypeError`

- 位置：`src/pagetrace/compare_stages.py:577`（`pages = sorted(pages)`）及 `:852`/`:857`（`_trace_anchor_pages` 内）。
- 实测（`du-chk-01.pdf` + 全 chunk/index 的 `source_page_indices0` 改为 `5` 或 `None`）：`TypeError: 'int' object is not iterable` / `'NoneType' object is not iterable`，直接从 `analyze_bundle` 抛出。CLI 路径受 `TraceBundle` 校验保护（schema 要求 array → exit 2），S0 用冻结合法 fixture，故用户侧无影响；直接调 API 时本应得受控错误/FAIL 归因。定 P2。
- 修复建议（T013）：在 `_check_source_stage`/`_trace_anchor_pages` 入口对非 list 的 `source_page_indices0` 按缺失处理（`PAGE_METADATA_MISSING`），或在 `analyze_bundle` 文档中明确“仅接受已校验 bundle”。

### T012-P2-03 — `resolve_citation_to_index0` 的 None 守卫改变了一个边界输入的异常类型

- 位置：`src/pagetrace/contracts.py:375-380`；对照 `tests/unit/test_page_semantics.py:113-136`。
- 差分比对（250 输入组合，值 + 异常类型逐项比）：仅 1 处值/类型差异——`resolve(None, "PDF_LABEL", 6, label_map=None)`：参考实现抛 `UnresolvableLabelError("no PDF label map available")`，生产实现抛基类 `PageSemanticsError`（None 守卫先行）。其余 None 输入仅消息不同（例如 `None + PDF_INDEX_0`：参考实现 “must be an integer, got None”，生产实现 “is null … missing must not be defaulted to 0 (R-07)”；`None + BOGUS basis`：参考实现先报未知 basis，生产实现先报 null 值）。
- 影响：只影响精确捕获 `UnresolvableLabelError` 的调用方；`PageSemanticsError` 的捕获行为不变（子类关系）。协调员“不改变任何输入结果，仅消息不同”的说法不精确——异常类型在该边界输入上变了。定 P2。修复建议：None 守卫在 `PDF_LABEL` 且 `label_map is None` 时仍抛 `UnresolvableLabelError`，或在 `contracts.py` 注释中写明该类型差异。

### T012-P2-04 — 越界 display 值的原因标签误标为 `VALUE_BASIS_TYPE_MISMATCH`

- 位置：`src/pagetrace/compare_stages.py:737-751`：`kind in ("type_mismatch", "out_of_range")` 统一以 `reason=REASON_VALUE_BASIS_TYPE_MISMATCH` 返回 `NEEDS_MANUAL_REVIEW`。
- 实测：`PDF_NUMBER_1` 值 `0`（越界，非类型错）→ verdict `NEEDS_MANUAL_REVIEW`、reason `VALUE_BASIS_TYPE_MISMATCH`；Oracle `attribute.py:579-586` 完全相同的映射（双方一致，parity 不受影响）。verdict 正确，机器可读原因误导。定 P2。修复建议：为 `out_of_range` 增加原因值（如 `VALUE_OUT_OF_RANGE`）或在 notes 中写明越界。

### T012-P2-05 — 生产与 Oracle 在 `UNKNOWN_TRACE_MISSING` 的 `reason` 上不一致

- 实测（删 chunking 快照并列入 `missing_stages`）：生产 `reason="TRACE_MISSING"`，Oracle `reason=None`；verdict 均为 `UNKNOWN_TRACE_MISSING`。`reason` 不在 S0 parity 的 6 字段与 Golden 比对的 6 字段内，故门禁不受影响；但归一化哈希包含 `reason`，跨实现比对时该字段不可比。定 P2。修复建议：Oracle 补 `reason="TRACE_MISSING"`，或把 `reason` 纳入 parity 字段。

### T012-P2-06 — `_trace_anchor_pages` 的 docstring 宣称了不存在的 display 回退

- 位置：`src/pagetrace/compare_stages.py:842-847`：docstring 称 “Chunk first, then index, then the display value resolved through its basis”，但实现只查 chunk、index，无 display 分支。
- 实测（`un-ext-01` 的 chunk/index 来源集清空、仅 display 有值）：生产与 Oracle 均返回 `expected_source_pages0=None`、`reason=NO_TEXT_LAYER`——行为一致且与 Oracle 相同，错的是 docstring。定 P2（文档）。

### T012-P2-07 — Oracle 三元组探针是生产穷举的子集；S0 从未演练不确定类 verdict

- `tests/oracle/locate.py:92-115` 的 `_triple_spans` 只试 `prefix_max-3..prefix_max` × `suffix_max-3..suffix_max` 的切分，而生产 `_spans_triple`（`locate.py:88-109`）穷举全部切分点。理论上存在生产检出 `unsupported_span` 而 Oracle 漏检的输入（此时 verdict 分歧：`NEEDS_MANUAL_REVIEW` vs `FAIL_UNLOCATABLE`）。
- 冻结套件中无此情形：48 组 spec 的 `split_pages0` 长度只有 0 或 2（无 3 页跨页）；Golden 96 条引用的 verdict 只有 `FAIL_*` 4 类 + `PASS`，无 `AMBIGUOUS` / `UNKNOWN_*` / `NEEDS_MANUAL_REVIEW`。即 S0 只演练故障 verdict 与 PASS，不确定路径只由单元/集成测试覆盖（`grep` 得 14 处引用）。定 P2（覆盖缺口 + Oracle 探针收窄），建议 T013 在 Oracle 探针处加注释说明子集性质，或补一组 3 页跨页 fixture（需协调员决定是否动冻结套件）。

### T012-P2-08 — 双包 import 路径（已知，T013 负责修）

- 顶层 `pagetrace/__init__.py`（8 行 stub，仅 `__version__`）与 `src/pagetrace/`（生产包）并存；`pyproject.toml:25` 仍写 `packages = ["pagetrace"]`，装的是 stub。`python -m pagetrace.cli` 不加 `PYTHONPATH=src PYTHONSAFEPATH=1` 即报 `No module named pagetrace.cli`；`cli.py:33-36`、`run_s0.py:37-43` 与测试均靠 `sys.path.insert(0, "src")` 绕过。已在 `docs/CLI.md` 与两处模块 docstring 如实记录为已知 P2。定 P2，T013 修打包布局（改动须重跑 S0）。

### T012-P2-09 — Pillow / reportlab 被列为运行时依赖，实际只用于 fixture 生成

- `pyproject.toml:16-17` 列 `reportlab==5.1.0`、`Pillow==13.0.0` 为运行时依赖；grep 证明生产 `src/` 从不 import 它们，只有 `tools/generate_fixtures.py` 与 `tools/render_previews.py` 使用（Pillow 画图、reportlab 生成 PDF）。安装包会多拉两个重依赖。定 P2，T013 打包时移入 fixture 生成的 extra 或文档说明。

### T012-P2-10 — `fixtures build` 命令未实现（§12.1 有示例）

- PROJECT_BOOK §12.1 示例含 `python -m pagetrace.cli fixtures build --out fixtures/generated`；CLI 只有 analyze/validate/s0/clean 4 个子命令。`docs/CLI.md` “未实现：`fixtures build`”一节已如实记录原因（48 组 fixture 是 T002 冻结产物，不由 CLI 生成；如需先立项）。任务卡只要求 4 命令。定 P2（记录项，无修复动作；T013 无需实现）。

### T012-P2-11 — UN 4/4/4 与 un-ext-12 的 1 组措辞偏差（已知，行为正确）

- PROJECT_BOOK §8.1 称 UN 12 组“均含扫描件式图像页或无文本层页面”；实测 `un-ext-12` 的 8 页全为 `kind: "text"`（其余 11 组均含 image 或 blank 页），其 fault 为 near-miss（`NO_EXACT_MATCH`）。Golden 仍记 `IMAGE_ONLY 4 / EMPTY 4 / NO_EXACT_MATCH 4`，S0 全通，行为正确。`00_control/DECISIONS.md`（2026-11-17 ~00:26 GMT）已登记该偏差。定 P2（spec 措辞，冻结 spec 不擅自改；T013 记录即可）。

### T012-P2-12 — `PAGE_SEMANTICS.md` 两处表述超前于代码

- （a）§5 表格称裸 `page` 字段“另做字段名扫描（防御）”——全仓库 grep 无此扫描；实际防线只有 schema 的 `additionalProperties: false`（已逐对象核对：bundle 11 个对象 schema、report 6 个，`if`/`then` 子 schema 除外，均设 false；裸 `page` 被拒的测试 F-16 通过）。行为正确，文档多写了一道防线。
- （b）§1.3 称 `summary.normalized_result_sha256`“无可规范化结果时为 null”——实测 0 引用 bundle 仍得真实哈希 `a35f8d5ba56f8a422191c488abfb1698d245463d57fee2400bd1819b74867e73`（`_build_report_document` 恒计算）。行为无害，文档与代码不一致。
- 定 P2（文档），T013 二选一：补扫描/补 null 分支，或修正文档措辞。

### T012-P2-13 — `stage_diffs_for_bundle` 把 `NEEDS_MANUAL_REVIEW` 标为 `kind="offset"`

- 位置：`src/pagetrace/compare_stages.py:927-939` 的 kind 映射：`FAIL_AMBIGUOUS`→`reduced`，`FAIL_METADATA_MISSING`/`UNKNOWN_TRACE_MISSING`→`missing`，`FAIL_UNLOCATABLE`→`not_found`，其余（含 `NEEDS_MANUAL_REVIEW` 与 `AMBIGUOUS`）落入 else → `"offset"`。该函数仅测试调用（`tests/unit/test_verdicts.py:168`），不进入生产报告路径。定 P2（低）。

## §4 观察（不立项）

- O-1：Oracle `_labels_from_catalog`（`pdfread.py:161-236`）对未知 label 样式回退为十进制字符串，且假定 `Nums` 已按 start 排序；fixture PDF 由生成器产出，排序成立，S0 无影响。
- O-2：`report_html.build_entries_from_fixtures` 不做 quote 摘要（全文进 HTML）；仅测试调用，生产 CLI 路径必经 `_excerpt`。
- O-3：Oracle `audit_extraction` 对越界 extraction 记录记 kind `"hash_mismatch"`，生产记 `"offset"`；verdict 只取 truth 页内的 diff，parity 字段不含 kind，故无影响。

## §5 审查者声明

本人与 T001–T011 施工为不同会话（本会话 `d470301b-fe7f-4398-a72b-170af3572a20`），模型路线为 Muse Spark；审查期间只读生产源码，所有结论均由本人亲自复核（全量 pytest 639 通过、S0 双报告核对、250 输入差分、Oracle import 图、许可证实测、隐私实测），未采信施工结论原文。未写任何源码；本次提交只含审查报告、审查包与只读校验脚本。
