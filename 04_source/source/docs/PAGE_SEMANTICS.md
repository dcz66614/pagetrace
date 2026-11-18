# PageTrace 页码语义（P026 · T001 冻结）

> 来源：`PROJECT_BOOK.md` v1.0.0 §4（权威契约）、§5、§6。机器可校验形式见
> `contracts/pagetrace.bundle.v1.schema.json` 与 `contracts/pagetrace.report.v1.schema.json`
>（JSON Schema Draft 2020-12）。本文档是人可读的同一契约；两者冲突时以 schema 为准，
>并按 `IMPLEMENTATION_PLAN.md` §11 登记为缺陷，不得自行取舍。
> 冻结 commit：见任务 T001 汇报。版本：`pagetrace.bundle/v1` / `pagetrace.report/v1`。

## 0. 一句话规则

**物理页的身份只有一个：`pdf_page_index0`（0-based）。其余一切页码都是它的派生、
展示或外部原始观测；任何字段都不得只叫 `page`。**

## 1. 字段表（全部字段：名称 / 类型 / 基准 / 缺省语义）

### 1.1 规范内部页身份（bundle 与 report 共用）

| 字段 | 类型 | 基准 | 定义 | 缺省 / 空值语义 |
|---|---|---|---|---|
| `pdf_page_index0` | integer | 0-based | PDF 物理页序号 | 无缺省；必填；必须满足 `0 <= v <= page_count-1`，越界拒绝（R-05） |
| `pdf_page_number1` | integer | 1-based | 人类按物理顺序数的页号 | 无缺省；恒等于 `pdf_page_index0 + 1`（R-01），不得独立输入 |
| `viewer_page1` | integer 或 null | 1-based | 传给 PDF viewer 的物理页号 | 恒等于 `pdf_page_index0 + 1`（R-01）；basis 为 `UNKNOWN` 时必须为 null（R-04）；其余情况必填，不得缺省为 0 |
| `pdf_page_label` | string 或 null | **不转换** | PDF page label，如 `i`、`iv`、`A-3` | PDF 未定义 label 时为 null；null 表示“无标签”，不是第 0 页 |
| `printed_page_number` | string 或 null | **不转换** | 页面视觉内容中印刷的页码 | MVP 不负责可靠识别、不推断；未知时为 null，不得由物理页号反推 |
| `source_page_indices0` | integer[] | 0-based | chunk / index 记录覆盖的物理页集合 | 必须排序升序、去重、非负、不越界；空数组 `[]` 表示“记录的集合为空”（与“字段缺失”不同，见 R-07）；不得缺省 |

### 1.2 外部引用原始观测（bundle `stages.display` 与 report 各 citation）

| 字段 | 类型 | 基准 | 定义 | 缺省 / 空值语义 |
|---|---|---|---|---|
| `citation_page_value` | integer / string / null | 随 `citation_page_basis` | 外部系统原始输出，原样保留 | null 表示“来源未给出页码值”；不得补 0、补 1 或猜测 |
| `citation_page_basis` | enum | — | `citation_page_value` 的语义 | 必填；未知时为 `UNKNOWN`（R-04） |
| `citation_page_basis` 取值 | — | — | `PDF_INDEX_0`：值是 0-based 物理索引；`PDF_NUMBER_1`：值是 1-based 物理页号；`PDF_LABEL`：值是 page label 字符串；`UNKNOWN`：来源未说明基准 | — |

### 1.3 报告派生字段（`pagetrace.report/v1` 每个 citation）

| 字段 | 类型 | 基准 | 定义 | 缺省 / 空值语义 |
|---|---|---|---|---|
| `candidate_source_pages0` | integer[] | 0-based | 规范化 quote 实际出现的全部物理页 | 找不到时为 `[]`（不是 null）；不得缩减为单页（R-09） |
| `expected_source_pages0` | integer[] 或 null | 0-based | trace 宣称的权威来源页集合 | trace 未给出可用来源集合时为 null（“未知”，不是“无来源”）；近似引用 UNLOCATABLE 无可证实抽取失败时亦为 null（FIX-R1 P1-R1-02），声称页不作已确认来源 |
| `observed_page_value` | integer / string / null | 随 basis | 展示层实际出示/传给 viewer 的页码值，原样保留 | 同 `citation_page_value` |
| `correct_pdf_page_number1` | integer[] 或 null | 1-based | 真实来源页对应的正确 1-based 页号（可多页，跨页引用） | 无法确定正确页时为 null |
| `correct_viewer_page1` | integer[] 或 null | 1-based | 正确的 viewer 目标页号 | 与 `correct_pdf_page_number1` 逐项相等；后者为 null 时必为 null |
| `verdict` | enum | — | 见 §4 | 必填，无缺省 |
| `fault_type` | enum 或 null | — | `PAGE_OFFSET` / `PAGE_METADATA_MISSING` / `DUPLICATE_TEXT_AMBIGUITY` / `UNLOCATABLE` | `verdict == PASS` 时必须为 null；不确定类 verdict（`UNKNOWN_*` / `AMBIGUOUS` / `NEEDS_MANUAL_REVIEW`）无故障类时也为 null |
| `first_fault_stage` | enum 或 null | — | `extraction` / `chunking` / `indexing` / `display` | `verdict == PASS` 时必须为 null；阶段快照缺失导致无法归咎时为 null 并出 `UNKNOWN_TRACE_MISSING`；近似引用 UNLOCATABLE（`NO_EXACT_MATCH`，锚页为 TEXT 且抽取与诚实抽取一致、无可证实抽取失败）时亦为 null（FIX-R1 P1-R1-02），此时 `expected_source_pages0` 亦为 null，trace 声称页不作已确认来源 |
| `quote_sha256` | string（64 位小写 hex） | — | 规范化 quote 文本的 SHA-256（§4.2 规范化） | 必填；报告默认不存 quote 原文 |
| `evidence[]` | object[] | — | 阶段差异证据：`stage`、`field`、可选 `upstream_value` / `downstream_value` / `note` | 至少 `stage` + `field`；值缺失时字段可省，不得填 0 占位 |

### 1.4 Bundle / Report 共有结构字段

| 字段 | 类型 | 定义 | 缺省语义 |
|---|---|---|---|
| `schema` | string | 精确为 `pagetrace.bundle/v1` 或 `pagetrace.report/v1`；未知主版本拒绝 | 无缺省 |
| `case_id` | string | 匹配 `^[A-Za-z0-9][A-Za-z0-9._-]*$`，1–128 字符 | 必填 |
| `document.file_name` | string | PDF 文件名（仅名，不含目录与绝对路径） | 必填；只允许纯文件名：不得含 `/` 或 `\`、不得以 Windows 盘符开头（如 `C:`）、不得为 UNC 路径、不得为 `.` 或 `..`、不得含 `..` 目录段；违反者 schema 与运行时双双拒绝（R-11，FIX-R1 P1-R1-04），且错误信息不得回显该路径值 |
| `document.sha256` | string（64 位小写 hex） | PDF 精确字节的 SHA-256；与实测不一致返回 `INPUT_HASH_MISMATCH` | 必填 |
| `document.page_count` | integer | 物理页数，1–500（500 为 §13 默认拒收阈值）；必须与真实 PDF 一致 | 必填 |
| `page_semantics.canonical_field` | string | 恒为 `pdf_page_index0` | 必填 |
| `page_semantics.index_base` | integer | 恒为 0 | 必填 |
| `page_semantics.viewer_base` | integer | 恒为 1 | 必填 |
| `stages.missing_stages` | string[] | 无快照的阶段，取自 `extraction` / `chunking` / `indexing` / `display` | 必填；四阶段齐全时为 `[]`；缺失必须显式列出，不得用空数组冒充“已检查无问题” |
| `summary.*`（report） | integer / string | `total_citations` / `pass_count` / `fail_count` / `unknown_count` / `ambiguous_count` / `normalized_result_sha256` | 计数由 `results` 导出；`normalized_result_sha256` 恒计算：即使 0 引用也为规范化空结果的真实 SHA-256，永不为 null（`cli._build_report_document` 恒计算；T013 P2-12 修正，旧文“无可规范化结果时为 null”不实） |
| `tool.name` / `tool.version`（report） | string | 恒为 `pagetrace` / 工具 semver | 必填 |
| `generated_at`（report，可选） | string（RFC 3339 date-time） | 报告生成时间 | 可省；**不计入规范化结果哈希**（§6.4） |

## 2. 转换规则（硬断言，R-01–R-10）

```text
pdf_page_number1 = pdf_page_index0 + 1        (R-01, 唯一允许的 0-based -> 1-based 转换)
viewer_page1     = pdf_page_index0 + 1        (R-01)
pdf_page_index0  = viewer_page1 - 1            (R-02, 唯一允许的 1-based -> 0-based 转换)
```

- **R-01** 0-based → 1-based 只允许 `+1`。不存在 `+0`、`+2` 或任何“看起来差不多”的偏移。
  任何其它偏移一律是 `PAGE_OFFSET` 故障。
- **R-02** 1-based → 0-based 只允许 `-1`。`viewer_page1 == 0` 非法（viewer 是 1-based，
  0 不对应任何物理页），拒绝。
- **R-03** `pdf_page_label` 与 `printed_page_number` **不得做算术转换**。label 只能查表
  （PDF 的 label→物理页映射）；没有映射时不得把 label 当数字解析，更不得 `int(label) ± 1`。
  例：label `iv` 不是数字 4，也不是物理页 4；label `A-3` 不是第 3 页。
- **R-04** `citation_page_basis == UNKNOWN` 时**不得转换**：`viewer_page1` 必须为 null，
  报告 verdict 为 `UNKNOWN_PAGE_BASIS`（或上游更早的 `UNKNOWN_TRACE_MISSING`），
  并保留原始 `citation_page_value` 原样。禁止以“值看起来像从 1 开始”推断基准。
- **R-05** 越界拒绝：任何 `pdf_page_index0 < 0` 或 `>= page_count`、任何
  `viewer_page1 < 1` 或 `> page_count`、任何 `source_page_indices0` 元素越界，
  均拒绝（bundle 校验失败 / 分析退出码 2），不得钳制（clamp）到边界。
- **R-06** viewer 目标只能是 1-based：传给 viewer 的必须是 `viewer_page1`；
  0-based 值直接传给 viewer 是 Display 阶段 `PAGE_OFFSET` 故障
  （§6.2 例：`citation_page_value == 6`（`PDF_INDEX_0`）时正确 `viewer_page1` 是 7，
  出示 6 即错）。
- **R-07** 缺失 ≠ 空 ≠ 零：字段缺失（unknown）、空集合 `[]`（verified empty）、数值 0
  是三种不同状态，不得互相默认。`source_page_indices0` 缺失是
  `PAGE_METADATA_MISSING` 的候选信号；`[]` 是“记录的集合为空”；0 是合法的第一个物理页。
- **R-08** 值/基准类型一致：`PDF_INDEX_0` 与 `PDF_NUMBER_1` 的 `citation_page_value`
  必须是 integer；`PDF_LABEL` 的必须是 string；`UNKNOWN` 的可为 integer / string / null。
  类型不符是语义无效（退出码 2），不得静默转型（例如不得把字符串 `"7"` 当作数字 7）。
- **R-09** 多候选不得压成单页：同一规范化 quote 出现在多个物理页时，
  `candidate_source_pages0` 必须列出**全部**候选页；只有阶段 trace 中有可验证的来源页
  身份/范围才能消歧；否则 verdict 为 `AMBIGUOUS`（或 `FAIL_AMBIGUOUS`，见 §4），不得猜一页。
- **R-10** 跨页引用是集合：引用横跨第 n、n+1 页（1-based）时，权威来源集合为
  `[n-1, n]`（0-based），`correct_viewer_page1` 为 `[n, n+1]`；展示必须明确页范围，
  不得伪装成单页引用。
- **R-11** `document.file_name` 只允许纯文件名（FIX-R1，P1-R1-04）：
  不得含 `/` 或 `\`；不得以 Windows 盘符开头（`C:\...`、`C:/...`、盘符相对路径
  `C:...`）；不得为 UNC 路径（`\\server\share\...`、`//server/share/...`）；
  不得为相对目录形式（`sub/file.pdf`、`../file.pdf`、`..\file.pdf`）；不得为裸目录引用
  `.` 或 `..`。schema（`file_name.pattern`）与运行时（`trace_bundle.is_bare_file_name`
  / `TraceBundle._runtime_errors`）双层拒绝，违反者整个 bundle 校验失败（退出码 2），
  分析不运行、报告不写。拒绝时的错误信息只说明规则，**不得回显该路径值**（路径最小化，
  §13）：`TraceBundle` 在 schema 校验前先行拦截，`jsonschema` 的报错文本不得成为泄漏通道。

## 3. 可复算示例（独立审查者按此复算）

约定：示例 PDF 共 8 页（`page_count == 8`），物理页 0-based 为 0–7。

### 例 A（§6.2 原例：Display 阶段错位）

输入：`citation_page_value == 6`，`citation_page_basis == PDF_INDEX_0`，
展示层 `viewer_page1 == 6`。

复算：

```text
pdf_page_index0 = 6                       (basis PDF_INDEX_0, 值即索引)
pdf_page_number1 = 6 + 1 = 7              (R-01)
correct viewer_page1 = 7                  (R-01)
observed viewer_page1 = 6 ≠ 7             → PAGE_OFFSET, 首错阶段 display
```

结论：`verdict == FAIL_PAGE_OFFSET`，`first_fault_stage == display`，
`correct_pdf_page_number1 == [7]`，`correct_viewer_page1 == [7]`。

### 例 B（首物理页）

`pdf_page_index0 == 0` → `pdf_page_number1 == 1`，`viewer_page1 == 1`。
0 是合法索引（R-07：0 不是“缺失”），`viewer_page1 == 0` 非法（R-02）。

### 例 C（末物理页）

`pdf_page_index0 == 7`（8 页 PDF）→ `pdf_page_number1 == 8`，`viewer_page1 == 8`。
`pdf_page_index0 == 8` 越界，拒绝（R-05）；`viewer_page1 == 9` 越界，拒绝。

### 例 D（罗马数字 label，不做算术）

PDF label 映射：`{"i": 0, "ii": 1, "iii": 2, "iv": 3}`。
`citation_page_value == "iv"`，`citation_page_basis == PDF_LABEL` →
查表得 `pdf_page_index0 == 3`，`viewer_page1 == 4`。
**禁止**：`int("iv")`、把 `iv` 当作 4 再 `+1`、或把 label 当作 1-based 页号。
若 label 不在映射中（如 `"ix"`），结果为“无法解析 label”，不得猜页。

### 例 E（label 与物理页号混淆）

某 PDF 第 1 页（`pdf_page_index0 == 0`）的 label 是 `"7"`（印刷页码 7 的那一页恰好是
PDF 第一页）。`citation_page_value == "7"`，`basis == PDF_LABEL` → 查 label 映射得
`pdf_page_index0 == 0`，`viewer_page1 == 1`。
**禁止**：把字符串 `"7"` 当作 1-based 页号 7（`viewer_page1 == 7` 是错的），
或当作 0-based 索引 7（越界/错页）。字符串 `"7"` 与数字 `7` 是不同的观测值（R-08）。

### 例 F（UNKNOWN basis，不得转换）

`citation_page_value == 6`，`citation_page_basis == UNKNOWN` →
保留原值 6，`viewer_page1` 必须为 null，`verdict == UNKNOWN_PAGE_BASIS`。
即使 6“看起来像 0-based 索引”也不得推断（R-04）。

### 例 G（跨页引用）

Quote 横跨 1-based 第 7、8 页 → 权威来源集合 `expected_source_pages0 == [6, 7]`，
`correct_pdf_page_number1 == [7, 8]`，`correct_viewer_page1 == [7, 8]`（R-10）。
只报一页（如只报 7）是错误的确定化。

### 例 H（重复文本歧义）

规范化 quote 同时出现在 `pdf_page_index0` 2 与 5，trace 无消歧锚点 →
`candidate_source_pages0 == [2, 5]`，`verdict == AMBIGUOUS`（或 trace 曾错误缩减为
单页时 `FAIL_AMBIGUOUS`，首错阶段为首次缩减的阶段），不得猜一页（R-09）。

## 4. Verdict 与故障类型（PROJECT_BOOK §5）

| verdict | fault_type | 含义 |
|---|---|---|
| `PASS` | null | 引用页与真实来源一致，无故障 |
| `FAIL_PAGE_OFFSET` | `PAGE_OFFSET` | 某阶段物理页索引/页号与 canonical page identity 不一致（0/1 基准混用或 ±1 偏移） |
| `FAIL_METADATA_MISSING` | `PAGE_METADATA_MISSING` | 上游有来源页身份，下游某阶段缺失/清空 `source_page_indices0`、页标签或必要映射 |
| `FAIL_AMBIGUOUS` | `DUPLICATE_TEXT_AMBIGUITY` | 多候选页被错误缩减/强制选页 |
| `FAIL_UNLOCATABLE` | `UNLOCATABLE` | quote 在可抽取文本中找不到 |
| `UNKNOWN_TRACE_MISSING` | null | 阶段快照缺失，无法归咎具体阶段；须列出缺失快照 |
| `UNKNOWN_PAGE_BASIS` | null | 引用基准未知，不得转换（R-04） |
| `AMBIGUOUS` | null | 多候选、无消歧信息，诚实报告不确定（不是故障 verdict，是不确定状态） |
| `NEEDS_MANUAL_REVIEW` | null | 精确匹配失败，工具拒绝猜页，需人工复核 |

首错阶段判定：按 Extraction → Chunking → Indexing → Display 顺序，首个可证明的
差异为 `first_fault_stage`（§4.3）。阶段快照缺失时不得跳过未知环节归咎某阶段，
输出 `UNKNOWN_TRACE_MISSING` 并列出缺失快照。

`FAIL_UNLOCATABLE` 近似引用（FIX-R1 P1-R1-02）：quote 与 TEXT 锚页上的句子仅一字之差
（`NO_EXACT_MATCH`），且抽取 trace 与诚实抽取一致、无可证实抽取失败时，
`first_fault_stage` 与 `expected_source_pages0` 均为 null——无阶段可归咎，trace 声称页
只作为证据文本记录，不冒充已确认来源页。只有锚页诚实状态为 `IMAGE_ONLY` / `EMPTY`
（无文本层可抽取），或锚页抽取记录可证与诚实抽取不同时，才归因 `extraction`。

## 5. Schema 强制 vs 运行时强制

| 规则 | schema 强制 | 运行时强制（分析器 / T003、T010） |
|---|---|---|
| 无含糊裸 `page` | 是（全对象 `additionalProperties: false`，`page` 不在属性表） | 否——无额外字段名扫描；实际防线只有 schema 的 `additionalProperties: false`（见 `contracts.py` 的 `UNKNOWN_FIELD_POLICY`；T013 P2-12 修正，旧文“另做字段名扫描”不实） |
| `schema` 精确值 | 是（`const`） | 是 |
| `sha256` 64 位小写 hex | 是（`pattern`） | 与真实 PDF 字节比对 |
| `pdf_page_index0 >= 0`、`viewer_page1 >= 1` | 是（`minimum`） | 是 |
| `pdf_page_index0 < page_count`、`viewer_page1 <= page_count` | 否（schema 无法跨字段比较） | 是（R-05） |
| `source_page_indices0` 排序、去重 | 去重部分是（`uniqueItems`）；排序否 | 是（R-07；未排序/重复拒绝） |
| `UNKNOWN` basis → `viewer_page1 == null` | 是（display record 的 `if`/`then`） | 是（R-04） |
| 值/基准类型一致（R-08） | 否（basis 依赖） | 是 |
| `+1` / `-1` 唯一转换（R-01/R-02） | 否（算术不在 schema 表达范围） | 是（单元测试锁定，见 §6） |
| `document.file_name` 为纯文件名（R-11） | 是（`file_name.pattern`：禁 `/`、`\`、盘符、`.`/`..`） | 是（`is_bare_file_name` + `_runtime_errors`；拒绝前拦截，错误信息不回显路径值） |
| label 不做算术（R-03） | 否 | 是（查表；无映射拒绝猜测） |
| verdict PASS → fault/stage 为 null | 否 | 是 |
| `correct_viewer_page1 == correct_pdf_page_number1` | 否 | 是 |

## 6. 边界 Fixture 清单（测试 `tests/unit/test_page_semantics.py`）

测试文件内含冻结的纯函数参考实现（`to_number1` / `to_index0` / `to_viewer1` /
`resolve_citation_to_index0` / `label_to_index0` / `validate_source_pages0`），
后续任务（T003 起）将其移入正式源码包时，语义不得变。至少 12 个边界 fixture：

| # | Fixture | 预期 |
|---|---|---|
| F-01 | 0-based `page=0`（首物理页） | `number1 == 1`，`viewer == 1` |
| F-02 | 0-based `page=6`（8 页 PDF，§6.2 例） | `number1 == 7`，`viewer == 7`；出示 6 即错 |
| F-03 | 末页 `index0 == 7`（8 页） | `number1 == 8`；`index0 == 8` 拒绝 |
| F-04 | `index0 == -1` | 拒绝（越界） |
| F-05 | `viewer_page1 == 0` | 拒绝（viewer 只接受 1-based） |
| F-06 | `viewer_page1 == 9`（8 页 PDF） | 拒绝（越界） |
| F-07 | `viewer_page1 == 1` → `index0 == 0` | 逆向 `-1` 唯一转换 |
| F-08 | 罗马数字 label `"iv"` | 查表 → `index0 == 3`，`viewer == 4`；禁止算术 |
| F-09 | label `"A-3"` | 查表命中才转换；无映射拒绝猜测 |
| F-10 | label `"7"` 与数字 `7` 混淆 | 字符串 label 查表（本例 `index0 == 0`）；不得当作数字 7 |
| F-11 | `basis == UNKNOWN`，值 `6` | 不转换，`viewer_page1` 为 null，`UNKNOWN_PAGE_BASIS` |
| F-12 | `source_page_indices0 == [6, 7]` 跨页 | 合法集合；`correct_viewer_page1 == [7, 8]` |
| F-13 | `source_page_indices0 == [7, 6]` 未排序 / `[6, 6]` 重复 / `[-1]` / `[8]` | 均拒绝 |
| F-14 | 布尔 `True` / 浮点 `6.0` 冒充页码 | 拒绝（JSON `true` 在 Python 中是 `int` 子类，必须显式排除） |
| F-15 | `basis == PDF_NUMBER_1`，值 `0` | 拒绝（1-based 无 0） |
| F-16 | 裸 `page` 字段出现在 bundle / report 实例中 | schema 校验拒绝 |

## 7. 禁止模式（审查清单）

- 字段名 `page`、`pageNo`、`page_no`、`pagenum` 等含糊命名。
- `+0` / `+2` / `-0` / `-2` 的页码“修正”，以及“看起来像从 1 开始所以是 1-based”的推断。
- `int(label)`、`label + 1`、`label - 1`。
- 把 `viewer_page1` 缺省为 0，或把缺失值默认成 0 / 空列表。
- 用空数组冒充“阶段已检查且无问题”（必须走 `missing_stages`）。
- 把机器执行时间、绝对本地路径、临时目录名纳入规范化结果哈希。
- 把绝对路径或目录路径放进 `document.file_name`（R-11）；拒绝时不得把该路径值回显到终端或错误信息中。
- 报告中存 quote 原文（默认只存 `quote_sha256`；短摘录仅在用户启用 `--include-snippets` 时保存本地）。

## 8. 变更纪律

- 本契约冻结于 T001；后续任务不得擅自改字段名、基准或 verdict 枚举。
  变更须经协调员派发新任务，并同步更新 schema、本文档与测试，且重跑 S0。
- 依赖版本冻结见 `requirements.lock`；升级依赖必须重跑完整 S0（PROJECT_BOOK §11）。
