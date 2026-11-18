# P026 T010 — 字段映射表（Field Mapping）与未知字段策略

来源：T001 冻结的 `contracts/pagetrace.bundle.v1.schema.json`（`pagetrace.bundle/v1`，
Draft 2020-12）与 `docs/PAGE_SEMANTICS.md`（R-01–R-10）。实现：
`src/pagetrace/contracts.py`（`FIELD_MAPPING`、`UNKNOWN_FIELD_POLICY`）、
`src/pagetrace/trace_bundle.py`（`TraceBundle`）。测试：
`tests/unit/test_bundle.py`（291 项通过，见 `T010-pytest.log`）。

## 1. 核心规则

- 规范页身份只有一个：`pdf_page_index0`（0-based）。其余一切页码都是它的
  派生、展示或外部原始观测；任何字段不得只叫 `page`。
- 唯一允许的转换：`pdf_page_number1 = pdf_page_index0 + 1`（R-01）、
  `viewer_page1 = pdf_page_index0 + 1`（R-01）、逆向 `-1`（R-02）。
  解析器本身**不做任何隐式转换**：原始值原样保留，转换只通过
  `contracts.to_number1 / to_index0 / to_viewer1 / viewer_to_index0 /
  resolve_citation_to_index0` 显式调用。
- 缺失 ≠ 空 ≠ 零（R-07）：字段缺失（unknown）、`[]`（verified empty）、
  数值 `0`（合法首物理页）是三种不同状态，不得互相默认。整阶段缺失
  必须显式列在 `stages.missing_stages` 里；空数组阶段记入
  `TraceBundle.empty_stages`，绝不冒充“已检查无问题”。

## 2. 字段映射表（bundle `pagetrace.bundle/v1`）

| 字段 | 类型 | 基准 | 含义 / 处理 |
|---|---|---|---|
| `schema` | string（const） | — | 精确为 `pagetrace.bundle/v1`；版本错（v2、v1.0、report）拒绝 |
| `case_id` | string 1–128 | — | 案例标识，`^[A-Za-z0-9][A-Za-z0-9._-]*$` |
| `document.file_name` | string | — | PDF 文件名（仅名，不含目录与绝对路径） |
| `document.sha256` | 64 位小写 hex | — | 精确 PDF 字节的 SHA-256；与实测不一致 → `INPUT_HASH_MISMATCH`（`verify_document_hash`） |
| `document.page_count` | int 1–500 | — | 物理页数；所有索引/页号的上界 |
| `page_semantics.canonical_field` | const | — | 恒为 `pdf_page_index0` |
| `page_semantics.index_base` | const | — | 恒为 0 |
| `page_semantics.viewer_base` | const | — | 恒为 1 |
| `stages.extraction[].pdf_page_index0` | int | 0-based | 规范物理页；越界/重复/乱序拒绝（R-05） |
| `stages.extraction[].pdf_page_label` | string \| null | 不转换 | PDF page label；只查表，永不算术（R-03） |
| `stages.extraction[].text_state` | enum | — | TEXT / EMPTY / IMAGE_ONLY / ERROR |
| `stages.extraction[].text_sha256` | 64-hex \| null | — | 规范化抽取文本的哈希；非 TEXT 时可为 null |
| `stages.chunking[].chunk_id` | string | — | chunk 标识；重复拒绝 |
| `stages.chunking[].source_page_indices0` | int[] | 0-based | 必须升序、去重、非负、不越界；`[]` = 已验证为空集 |
| `stages.chunking[].text_sha256` | 64-hex \| null | — | chunk 文本哈希或 null |
| `stages.indexing[].record_id` | string | — | index 记录标识；重复拒绝 |
| `stages.indexing[].source_page_indices0` | int[] | 0-based | 同 chunking |
| `stages.indexing[].pdf_page_label` | string \| null | 不转换 | label，只查表 |
| `stages.display[].citation_id` | string | — | 引用标识；同一 bundle 内重复拒绝 |
| `stages.display[].citation_page_value` | int \| string \| null | 随 basis | 外部原始值，**原样保留**；null = 来源未给出页码值，不得补 0/补 1 |
| `stages.display[].citation_page_basis` | enum | — | PDF_INDEX_0 / PDF_NUMBER_1 / PDF_LABEL / UNKNOWN |
| `stages.display[].viewer_page1` | int \| null | 1-based | 传给 viewer 的页号；0 永非法；越界拒绝；UNKNOWN basis 时必须为 null（R-04）；null = 缺失信号 |
| `stages.missing_stages` | enum[] | — | 无快照的阶段；缺失必须显式列出，谎报（列出却存在 / 缺失却不列）拒绝 |
| `citations[].citation_id` | string | — | 引用标识；重复拒绝 |
| `citations[].quote_text` | string ≥1 | — | 原文引用文本，原样保留 |
| `citations[].chunk_id` | string \| null | — | 引用来源 chunk；悬空引用是故障数据，解析器接受并记入 `unresolved_chunk_refs` |
| `citations[].index_record_id` | string \| null | — | 引用来源 index 记录；悬空同上（`unresolved_index_refs`） |

## 3. `citation_page_value` / `citation_page_basis`（R-04、R-08）

| basis | 值类型（非 null 时） | 解析 | 越界 |
|---|---|---|---|
| `PDF_INDEX_0` | int | 值即 `pdf_page_index0` | `< 0` 或 `>= page_count` 拒绝 |
| `PDF_NUMBER_1` | int | `pdf_page_index0 = 值 - 1` | `0` 或 `> page_count` 拒绝 |
| `PDF_LABEL` | string | 查 extraction 的 label 映射；无映射 → `UnresolvableLabelError`，不得猜页 | 不适用（label 不做算术） |
| `UNKNOWN` | int / string / null | **永不转换**；`viewer_page1` 必须为 null；原始值原样保留 | 不适用 |

类型不符（字符串配数字 basis、数字配 label basis、布尔/浮点冒充页码）
是语义无效，拒绝；不得静默转型（不得把 `"7"` 当作数字 7）。

## 4. 未知字段策略（已固定）

**默认 = 拒绝（`UNKNOWN_FIELD_POLICY = "reject"`），无宽松模式、无开关。**
两份冻结 schema 的每个对象都设 `additionalProperties: false`，且裸字段
`page` 不在任何属性表内，因此任何未知字段——裸 `page`、`pageNo`、
`page_no`、拼写错误、未来新增字段——都会使 schema 校验失败。外部系统
新增字段必须走新 schema 版本（`pagetrace.bundle/v2`），不得在此静默接受。
测试 `test_unknown_field_policy_is_fixed_reject` 遍历 schema 断言每个
`type: object` 节点都有 `additionalProperties: false`。

## 5. 故障数据 vs 结构损坏（解析器边界）

解析器**接受**以下故障数据（供 T004 分析器归咎阶段），只暴露、不拒绝：

- display 值错位（如 `po-dsp-10`：INDEX_0 值 1 却交给 viewer 1，正确应为 2）
- label 字符串与数字混淆（如 `po-dsp-12`：label `"7"`，viewer 7）
- 记录缺失：`mm-chk-05` 悬空 `chunk_id`、`mm-idx-08` 悬空 `index_record_id`、
  `mm-dsp-10` 缺 display 记录、`mm-ext-03` 缺第 4 页抽取记录
- 值缺失信号：`mm-dsp-11` 值与 viewer 同为 null、`mm-dsp-12` 仅 viewer 为 null

解析器**拒绝**结构损坏：schema 校验失败、版本错、未知字段、重复 id、
越界页/未排序来源页集合、值/基准类型不一致、谎报 `missing_stages`、
文档哈希与实测 PDF 字节不符（`INPUT_HASH_MISMATCH`）。

## 6. 证据

- 合法样本：48 份 T002 bundle（`fixtures/bundles/*.trace.json`）全部解析通过，
  且每份的 `document.sha256` 与真实 PDF 字节一致。
- 合法变体：9 份 `tests/unit/fixtures_bundle/valid-*.json`（缺失阶段、UNKNOWN
  basis、label 引用、跨页集合、空来源集、首物理页、空阶段数组、null display 值）。
- 非法样本：44 份 `tests/unit/fixtures_bundle/inv-*.json`（见上表各类），全部被拒绝，
  且每个错误都带非空 `.errors` 列表。
- 测试日志：`07_evidence/runtime_logs/T010-pytest.log`（291 项通过）与
  `07_evidence/runtime_logs/T010-pytest-full-unit.log`（全量单元 535 项通过）。
