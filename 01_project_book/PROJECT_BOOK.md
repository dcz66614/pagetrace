---
project_id: P026
slug: pagetrace
name: 引文落页镜
spec_version: 1.0.0
document: PROJECT_BOOK
status: SPECIFICATION_DRAFT / WAITING_OWNER_REVIEW / NO_GO / NO_CODE_BUILT
created_utc: 2026-11-16
license: MIT
human_participants: 0
---

# P026 引文落页镜（PageTrace）项目书

**副标题：PDF 引用页码漂移检测与来源位置回归测试**  
**PROJECT_ID：** P026  
**SLUG：** `pagetrace`  
**规格版本：** v1.0.0  
**状态：** `SPECIFICATION_DRAFT / WAITING_OWNER_REVIEW / NO_GO / NO_CODE_BUILT`  
**许可证：** MIT  
**计划规模：** 单人 88 小时；约两周日历时间  
**真人参与者：** 0；全部验证使用合成 PDF、Golden Fixtures、独立 Oracle 与自动化断言  
**运行边界：** 本地离线、CPU-only；不需要 GPU、数据库服务、收费 API 或运行时 LLM

> 本文件是产品和算法的权威规格，不是软件已实现或已通过测试的声明。所有测试结果在真实执行前均为 `NOT_VERIFIED`。本轮仅编写规格并等待项目方核对；不宣布 GO、不启动施工。

## 0. 一页摘要

### 0.1 一句话价值

**AI 引用写第 6 页，原文其实在第 7 页——点引用跳错页，甚至没有页码。PageTrace 把 PDF 的真实页序与 RAG 管线各阶段的页码记录逐项对账，找出页码在哪一环节偏移、丢失或变得不可唯一定位。**

### 0.2 产品是什么

PageTrace 是一个本地离线的 PDF 引用位置回归测试工具。它读取 PDF 和一份标准化的管线追踪包，按冻结的页码字段语义核对四个阶段：

1. **抽取（Extraction）**：PDF 每个物理页抽出的文本及页身份。
2. **分片（Chunking）**：每个 chunk 的原始来源页集合。
3. **索引（Indexing）**：向量/文档索引记录保留的页码元数据。
4. **展示（Display）**：最终 citation payload 与 PDF viewer 实际打开的页码。

它对每条引用给出可复核结论：`PAGE_OFFSET`、`PAGE_METADATA_MISSING`、`DUPLICATE_TEXT_AMBIGUITY`、`UNLOCATABLE`，或明确的 `PASS / UNKNOWN`；并输出“错误页码 → 首个出错环节 → 正确来源位置”的对照。

### 0.3 核心承诺与诚实边界

- 首版只证明**来源位置是否落在正确 PDF 物理页**，并在有完整阶段追踪数据时定位页码首次丢失/偏移的环节。
- 首版不判断引用内容的事实真假、论证是否充分、回答是否忠实；不得宣传为通用引文事实核验器。
- 仅给 PDF 和最终引用文本、没有抽取/分片/索引/展示阶段快照时，PageTrace 可以验证文本候选页与最终页码是否一致，但**不能凭空知道错误发生在哪个内部环节**；此时必须输出 `UNKNOWN_TRACE_MISSING`，不能猜测。
- 首版 S0 用 48 组合成 PDF 故障案例与独立真值验收。合成数据成绩不能被宣传成 Open WebUI、RAGFlow 或任何真实 RAG 系统的端到端成绩。真实系统集成需要后续单独验证。
- 扫描件式无文本页不做 OCR。工具只报告“当前文本抽取路径无法定位”，不宣称扫描页上不存在该内容。

## 1. 用户、场景与问题定义

### 1.1 目标用户

- 使用 Open WebUI、RAGFlow 或同类 RAG / 文档问答系统构建 PDF 知识库的开发者与团队。
- 维护文档抽取、chunking、索引重建、citation payload 或 PDF viewer 的工程师。
- 为 RAG 系统编写文档处理回归测试的 QA / 测试工程师。
- 在升级 Docling、MinerU、pypdf 或自研解析/分片逻辑后，需要确认来源页码没有回归的开源项目维护者。

### 1.2 典型使用场景

团队把 PDF 上传到知识库后，文档经过抽取、分片、索引和展示四道环节。AI 回答“合同第 7 页规定了什么”时，引用卡片显示第 6 页；用户点击引用，PDF viewer 也打开第 6 页。另一种情况是重新建索引后，正文仍能检索，但 citation 不再携带页码；还有一种情况是同一句话在 PDF 多页重复出现，系统只凭文本无法知道用户引用的是哪一处。

PageTrace 在解析器升级、索引重建、RAG 管线变更或发布前运行一套固定样本，把页码字段从原始 PDF 到最终展示逐段对账。

### 1.3 痛点与证据边界

| 痛点 | 公开案例 | 对产品的启示 | 证据边界 |
|---|---|---|---|
| 0-based 与 1-based 页码混用，viewer 打开前一页 | Open WebUI #33603 | 必须区分内部物理页索引与 viewer 页码，不允许字段都叫 `page` 却不标计数基准 | 该 issue 已于 2026-11-03 标记完成；证明曾出现此类问题，不证明当前版本仍有缺陷 |
| 小 PDF 走全文传输后，引用与模型输入丢失页码 | Open WebUI #33810 | 全文传输和检索分片路径都必须保留页身份 | 该 issue 于 2026-11-08 以 `not planned` 关闭；这是特定行为决策，不应写成未修复漏洞 |
| 重建索引后 PDF 页元数据丢失 | Open WebUI #33909 | 索引重建必须纳入页元数据回归测试 | issue 说明 Docling 初次处理有页元数据、重建后丢失；本规格不推断其当前修复状态 |
| 中文 PDF chunk 缩略图与原文位置映射不一致 | RAGFlow #12309 | 中文 PDF 的 chunk 与原页映射值得独立测试 | issue 报告的是 RAGFlow 0.23.0 + MinerU 2.6.6 的历史回归，不能泛化为所有版本 |

这些案例证明“PDF 来源页码会在不同处理边界发生偏移、丢失或歧义”是具体存在过的工程问题；它们不证明所有 RAG 产品都存在相同缺陷，也不构成市场规模或购买意愿调查。

### 1.4 目标用户当前 workaround

- 手工打开 PDF 搜索引用句子，再数页确认。
- 在 Open WebUI / RAGFlow 管理界面删除文件并重新上传或重建索引。
- 临时把页码加一/减一，或在 prompt 中要求模型换算。
- 对比索引前后的 metadata JSON。

这些办法能处理单次问题，但不能系统覆盖抽取、chunk、索引、展示四段，也难以在依赖升级或索引重建前自动阻断回归。

## 2. 产品目标与非目标

### 2.1 MVP 目标

1. 冻结所有页码字段的语义、计数基准与转换规则。
2. 对 PDF 逐页抽取文本，保留每页物理页身份及文本状态。
3. 根据 citation quote 在逐页文本中定位候选页，支持跨页引用与重复文本候选集合。
4. 接收 `pagetrace.bundle/v1` 标准化追踪数据，比较 extraction、chunking、indexing、display 阶段的页身份。
5. 准确检测四类指定故障，并定位首次发生偏差的阶段；信息不足时返回 `UNKNOWN`，不编造归因。
6. 生成 JSON 机器报告与无需联网的本地 HTML 交互报告。
7. 用 48 组合成 PDF 案例、Golden Fixtures、独立 Oracle 和 100 次规范化重放完成 S0 自动门禁。

### 2.2 非目标

- 不判断引用语义、事实正确性、推理有效性或答案完整性。
- 不实现 RAG、向量数据库、OCR、embedding、reranker、LLM 或 PDF 问答。
- 不连接真实 Open WebUI / RAGFlow 数据库，不自动登录或调用它们的私有 API。
- 不自动修复第三方索引、不改写 citation、不重建知识库。
- 不提供扫描 PDF OCR；图像页仅能被标记为无可抽取文本。
- 不做字符级/版面坐标级定位、表格结构恢复、跨文档实体解析或通用 PDF 解析质量认证。
- 不把合成 S0 通过率解释成真实 RAG 产品的线上准确率。

## 3. 与既有项目及开源先例的差异

### 3.1 历史项目去重边界

| 项目 | 已有核心机制 | PageTrace 不重复的原因 |
|---|---|---|
| P020 CheckPath | 静态分析 GitHub Actions workflow 的 required-checks 门禁路径 | PageTrace 检查 PDF 内容来源页与 RAG 阶段元数据，不分析 CI YAML |
| P021 ViewportShift | 模拟移动浏览器软键盘造成的视口变化与遮挡 | PageTrace 不模拟视口或布局事件 |
| P022 LocatorStress | 对浏览器 DOM 定位器做确定性变异压力测试 | PageTrace 不测试 DOM locator，不涉及浏览器自动化定位器 |
| P023 SkillScope | 技能文件来源归属、符号链接与策略作用域静态审计 | PageTrace 不扫描技能文件或宿主权限 |
| P025 GuidancePulse | Coding Agent 指导读取凭证与运行时 Hook 约束 | PageTrace 不管理指导文件、Hook 或读取租约 |
| P024 RepoMapVerify | 静态 import 图与 Agent 仓库地图逐项核对 | PageTrace 不分析源码依赖图 |
| P014 FormulaWitness | 用户自填公式及典型错误变异体的结果验收 | PageTrace 的对象是 PDF 页身份与 RAG 阶段来源元数据，不验证计算公式 |

### 3.2 与通用 AI 引文事实核验器的区别

通用引文核验器需要判断引用内容本身是否支持回答、语义是否被曲解、是否遗漏上下文，涉及开放式语义判断与模型评测，范围不可控。PageTrace 只回答可测的来源位置问题：引用是否落在正确的 PDF 物理页、页码在哪个处理阶段偏移或丢失、文本是否有多个候选页或无法从文本层定位。**不判定引用内容真假。**

### 3.3 与 ReviewReceipt 的关系

ReviewReceipt 已降为备选，不是本项目的前提。open-code-review issue #367 与 PR #520 已形成并合并 `RunManifest` 逐文件覆盖契约。因此 PageTrace 不以“AI 评审器没有覆盖回执”为立项依据，也不实现代码评审覆盖功能。两者对象和数据链完全不同。

### 3.4 最接近的 PDF/RAG 先例

- Open WebUI：公开 issue #33603、#33810、#33909 分别记录页码基准不一致、小 PDF 全文路径丢页码、索引重建丢失 PDF 页元数据。
- RAGFlow：#12309 记录特定版本组合下中文 PDF chunk 缩略图与原文位置映射不准确。
- Docling 的 provenance / page 相关能力与 PDF 抽取工具是来源定位基础设施先例。PageTrace 不重新实现抽取器，而是把阶段输出变成可回归验证的契约。

差异化不在“又一个 PDF parser”，而在于**页码语义冻结 + 多阶段 trace 对账 + 首个偏差阶段定位 + 独立真值门禁**的组合。

## 4. 核心机制与页码语义（权威契约）

### 4.1 永不使用含糊的 `page` 字段

所有内部与接口字段必须显式标注语义。禁止把不同计数基准的值都命名为 `page`。

| 字段 | 类型 | 计数规则 | 定义 | 是否权威 |
|---|---|---|---|---|
| `pdf_page_index0` | integer | 0-based | PDF 文件中的物理页序号，范围 `0..page_count-1` | **规范内部页身份** |
| `pdf_page_number1` | integer | 1-based | 人类按 PDF 物理顺序数的页号，严格等于 `pdf_page_index0 + 1` | 派生值 |
| `viewer_page1` | integer | 1-based | 传给 PDF viewer 的物理页号，严格等于 `pdf_page_index0 + 1` | 展示接口值 |
| `pdf_page_label` | string 或 null | 不转换 | PDF page label 字符串，例如 `i`、`iv`、`A-3`；若 PDF 没有定义则为 null | 辅助标签，不可代替物理页身份 |
| `printed_page_number` | string 或 null | 不转换 | 页面视觉内容中印刷的页码；MVP 不负责可靠识别 | 非权威、MVP 不推断 |
| `source_page_indices0` | integer[] | 0-based | chunk / index 记录所覆盖的物理 PDF 页集合，排序、去重 | 来源集合 |
| `citation_page_value` | number / string / null | 必须伴随 `citation_page_basis` | 外部系统原始输出，不做隐式猜测 | 原始观测值 |
| `citation_page_basis` | enum | `PDF_INDEX_0` / `PDF_NUMBER_1` / `PDF_LABEL` / `UNKNOWN` | 明确 `citation_page_value` 的语义 | 必填；未知时为 `UNKNOWN` |

**转换规则：**

```text
pdf_page_number1 = pdf_page_index0 + 1
viewer_page1     = pdf_page_index0 + 1
pdf_page_index0  = viewer_page1 - 1
```

`pdf_page_label` 与 `printed_page_number` 不能直接加一或减一。若来源系统只给出含糊的 `page` 字段、未说明计数基准，必须保留原值并标记 `UNKNOWN_PAGE_BASIS`，不得通过“看起来像从 1 开始”推断。

### 4.2 文本匹配规范

- 保存原始逐页抽取文本；匹配副本使用 Unicode NFC、统一 CRLF/CR 为 LF、把连续空白折叠为一个空格。
- 保留标点、大小写、全角/半角差异；不做语义相似度、模糊匹配、拼写纠错或自动翻译。
- 默认先精确匹配规范化 quote；不匹配时报告 `UNLOCATABLE` 或 `NEEDS_MANUAL_REVIEW`，不降低阈值“猜一个最像的页”。
- 同一规范化 quote 出现在多个物理页时，返回完整候选集合。只有阶段 trace 中有可验证的来源页身份/范围才能消除歧义。
- 跨页引用可以有多个来源页；若引用横跨第 n、n+1 页，权威来源集合为 `[n-1, n]`（0-based），展示应明确页范围，不把它伪装成单页引用。

### 4.3 四阶段首个偏差定位

PageTrace 按下列顺序比较，首个可证明的差异为 `first_fault_stage`：

1. **Extraction**：PDF 物理页与抽取记录是否一一对应；抽取文本是否来自对应页；空白/图像页是否诚实标记。
2. **Chunking**：chunk 的 `source_page_indices0` 是否覆盖 quote 的真实候选页/跨页范围；不得丢失或错误偏移。
3. **Indexing**：索引记录是否保留 chunk 的来源页集合和 `pdf_page_label`；重建索引不得静默丢弃来源元数据。
4. **Display**：最终引用页码是否按 `citation_page_basis` 转换成 `viewer_page1`；展示层不得把 0-based 值直接传给 1-based viewer。

阶段快照缺失时，不能跳过未知环节并把后续差异归咎于某个具体阶段；输出 `UNKNOWN_TRACE_MISSING` 并列出缺失快照。

## 5. 四类故障定义与判定

| 故障类型 | 触发条件 | 正确 verdict | 首个故障环节定位规则 |
|---|---|---|---|
| `PAGE_OFFSET` 页码错位 | 某阶段物理页索引/页号与 canonical page identity 不一致，常见为 0/1 基准混用或 +1/-1 偏移 | `FAIL_PAGE_OFFSET` | 从 Extraction → Chunking → Indexing → Display 顺序找第一处值偏离 |
| `PAGE_METADATA_MISSING` 元数据缺失 | 已有上游来源页身份，但下游某阶段缺失/清空 `source_page_indices0`、页标签或必要映射 | `FAIL_METADATA_MISSING` | 找到第一次从存在变为缺失的阶段；索引重建前后需分别记录 |
| `DUPLICATE_TEXT_AMBIGUITY` 重复文本歧义 | 同一 quote 在多个物理页出现，阶段数据没有可靠锚点却将其压成一个确定页 | `FAIL_AMBIGUOUS` | 找到候选页集合首次被错误缩减/强制选页的阶段；若始终没有消歧信息，则报告 `AMBIGUOUS` 而不猜页 |
| `UNLOCATABLE` 无法定位 | quote 在可抽取文本中找不到；页面可能是扫描图像、无文本层或抽取失败 | `FAIL_UNLOCATABLE` | 若页面状态明确为 `IMAGE_ONLY` / `EMPTY`，定位 Extraction；无法区分图像页与错误 quote 时，说明原因未知，不宣称原文不存在 |

**特别说明：** `DUPLICATE_TEXT_AMBIGUITY` 与 `UNLOCATABLE` 都不是简单的页码加减错误。正确结果可能是“多个候选页”或“当前文本层无法确认”，而不是强行选出一个页号。系统不得为了让报告看起来确定而消除不确定性。

## 6. 输入、数据结构与接口

### 6.1 输入文件

一个 Case Bundle 包含：

```text
case-<case_id>/
├── source.pdf                  # 用户自带 PDF 或合成 PDF
├── trace.json                  # pagetrace.bundle/v1 阶段快照与引用记录
└── expected.json               # 仅测试夹具使用；真实用户输入不得要求此文件
```

真实使用时 `expected.json` 不存在；它只属于测试目录，不参与生产判断。

### 6.2 `pagetrace.bundle/v1` 最小结构

```json
{
  "schema": "pagetrace.bundle/v1",
  "case_id": "sample-offset-display-001",
  "document": {
    "file_name": "sample.pdf",
    "sha256": "<64-hex>",
    "page_count": 8
  },
  "page_semantics": {
    "canonical_field": "pdf_page_index0",
    "index_base": 0,
    "viewer_base": 1
  },
  "stages": {
    "extraction": [
      {"pdf_page_index0": 6, "text_state": "TEXT", "text_sha256": "<64-hex>"}
    ],
    "chunking": [
      {"chunk_id": "c-17", "source_page_indices0": [6], "text_sha256": "<64-hex>"}
    ],
    "indexing": [
      {"record_id": "v-17", "source_page_indices0": [6], "pdf_page_label": "7"}
    ],
    "display": [
      {"citation_id": "cite-17", "citation_page_value": 6, "citation_page_basis": "PDF_INDEX_0", "viewer_page1": 6}
    ]
  },
  "citations": [
    {"citation_id": "cite-17", "quote_text": "引用中的原文片段", "chunk_id": "c-17", "index_record_id": "v-17"}
  ]
}
```

上例的展示层错误：`citation_page_value=6` 是 0-based 物理索引；正确 `viewer_page1` 应为 7，而不是 6。

### 6.3 结构约束

- `schema` 必须精确为 `pagetrace.bundle/v1`；未知主版本拒绝处理。
- `document.sha256` 必须与实际 PDF 字节一致；不一致返回 `INPUT_HASH_MISMATCH`。
- `page_count` 必须与实际 PDF 页数一致。
- 每个 `pdf_page_index0` 必须在 `[0, page_count-1]` 范围内。
- `citation_page_basis=UNKNOWN` 时不得转换成 viewer 页码。
- `source_page_indices0` 允许多页，但必须非负、排序、去重、且不越界。
- 阶段数组可缺失，但缺失必须显式体现在 `missing_stages`；不得把空数组伪装成“阶段已检查且无问题”。
- `trace.json` 默认不携带完整文档正文；文本摘要和哈希优先。只有用户明确启用 `include_snippets` 才在本地报告中保存短摘录。

### 6.4 输出数据

`pagetrace.report/v1` 至少包含：

- 输入 PDF SHA-256、页数、工具版本、schema 版本。
- 每条 citation 的 quote hash、原始页码值、页码基准、真实候选页集合。
- `verdict`、`fault_type`、`first_fault_stage`、`expected_source_pages0`、`observed_page_value`、`correct_pdf_page_number1`、`correct_viewer_page1`。
- 阶段差异证据：上游值、下游值、首次差异位置、缺失字段。
- `UNKNOWN_TRACE_MISSING`、`UNKNOWN_PAGE_BASIS`、`AMBIGUOUS` 等不确定状态。
- 不把机器执行时间、绝对本地路径、临时目录名纳入规范化结果哈希。

## 7. 核心算法与数据假设

### 7.1 处理流程

1. 读取 PDF 字节并计算 SHA-256；验证文件大小、页数、加密状态和可解析性。
2. 使用生产抽取器逐页提取文本；记录物理页索引、页标签（若存在）、文本状态与文本哈希。
3. 规范化 citation quote 与逐页文本；生成候选页集合和跨页匹配集合。
4. 对每条 citation 关联 trace 中的 chunk、index、display 记录。
5. 以 canonical `pdf_page_index0` 为基准，按阶段顺序比较来源页集合与转换值。
6. 根据第 5 节规则给出 verdict、首个偏差阶段及证据链。
7. 输出 JSON 与本地 HTML 报告；任何缺少必要观测的情况返回 `UNKNOWN`，而非推断。

### 7.2 候选页定位

令 PDF 的规范化逐页文本为 `T_i`，引用文本为 `q`。单页候选集合：

\[
C(q)=\{i\mid q\text{ 是 }T_i\text{ 的精确子串}\}
\]

跨页候选通过相邻页文本拼接并保留边界标记计算；匹配结果记录完整页集合，例如 `[4,5]`。不跨越超过 2 个物理页；超过时标记 `UNSUPPORTED_SPAN`，不尝试无界组合。

- `|C(q)| = 1`：有唯一文本页候选。
- `|C(q)| > 1`：重复文本歧义；除非阶段 trace 提供可验证的页级来源锚点，否则不能选单页。
- `|C(q)| = 0`：若 trace 指向 `IMAGE_ONLY` / `EMPTY` 页，则报告文本层无法定位；否则报告 `UNLOCATABLE`，原因未定。

### 7.3 首个差异定位

设真实来源页集合为 `S0`，各阶段观测集合为 `S_extract`、`S_chunk`、`S_index`，最终 viewer 页为 `V_display`。逐边比较：

```text
PDF truth -> Extraction -> Chunking -> Indexing -> Display
```

若某阶段的页集合与其上游来源集合首次不同，则该阶段为 `first_fault_stage`。Display 阶段将 canonical 0-based 页集合转换为 1-based viewer 页；如果 viewer 页不等于 `index0 + 1`，归因为 `DISPLAY`。只有阶段输入齐全且来源真值唯一时，才能给出确定阶段；否则返回 `UNKNOWN` / `AMBIGUOUS`。

### 7.4 复杂度与边界

- PDF 抽取：与 PDF 内容流大小和页数相关；MVP 对页数与字节数设上限。
- 精确 quote 搜索：采用逐页字符串搜索；不使用 embedding 或语义模型。
- 跨页组合只检查相邻页，避免组合爆炸。
- 不提供 OCR、模糊搜索、字符坐标和布局恢复；遇到这些需求时给出明确 unsupported 原因。

## 8. S0 硬门与 Golden 验收

### 8.1 48 组故障样本

建立 **48 组故障型合成 PDF 案例**，四类故障各 12 组：

| 故障类别 | 数量 | 样本构成与首错阶段覆盖 |
|---|---:|---|
| 页码错位 `PAGE_OFFSET` | 12 | Extraction / Chunking / Indexing / Display 各 3 组；包含 0/1 基准混用、+1、-1、页标签与物理页号混淆 |
| 元数据缺失 `PAGE_METADATA_MISSING` | 12 | 四个阶段各 3 组；包含 chunk 丢页集合、重建索引丢 label/页索引、display payload 缺字段 |
| 重复文本歧义 `DUPLICATE_TEXT_AMBIGUITY` | 12 | Chunking / Indexing / Display 各 4 组；同一句话在 2–3 页出现，丢失页级消歧后错误地输出单页 |
| 无法定位 `UNLOCATABLE` | 12 | 12 组均含扫描件式图像页或无文本层页面；不启用 OCR，必须报告无法从文本层确认，不能假称内容不存在 |

每组 PDF 必须覆盖多样化结构：中文段落、空白页、重复句子、跨页断句、不同 PDF page label、扫描件式无文本页；每个故障 PDF 还必须至少含 **1 条正常引用控制项**。因此控制引用至少 48 条，确保 `0` 误报有真实分母。

### 8.2 独立 Oracle 与 Golden Fixtures

- `fixtures/specs/`：48 份人工定义的 fixture spec，描述 PDF 页内容、植入故障阶段、预期页身份与控制引用。
- `fixtures/pdfs/`：由固定版本合成器生成的 PDF；生成时固定元数据和对象顺序，避免时间戳导致字节漂移。
- `fixtures/golden/expected.json`：由独立审查者按 fixture spec 手工核对的预期 verdict、fault type、first fault stage、candidate pages 与正常控制结果；不得由生产实现自动生成后直接当真值。
- `tests/oracle/`：独立 Python Oracle，不导入 `pagetrace` 生产模块；使用独立 PDF 文本读取路径（pdfminer.six）检查页文本与 Golden 结果，和生产 pypdf 路径分离。
- Oracle 与生产实现不得共用规范化、定位、阶段归因或 verdict 函数；仅共享 JSON schema 与固定输入文件。

### 8.3 S0 通过门槛（全部必须通过）

1. 四类故障各 `12/12` 检出，总计 `48/48`。
2. `first_fault_stage` 对 48 组均与 Golden 预期一致：`48/48`。
3. 每个 PDF 中的正常控制引用均为 PASS，**误报数 0**。
4. 生产实现与独立 Oracle 在全部 48 组故障样本的 `fault_type / verdict / first_fault_stage / expected_source_pages0 / observed_page_value` 上完全一致；正常控制项也必须一致。
5. 对完整 S0 套件执行 100 次规范化重放，规范化结果 SHA-256 只有 **1 个唯一值**。
6. 不得将 `UNKNOWN_TRACE_MISSING`、`UNKNOWN_PAGE_BASIS`、`AMBIGUOUS` 或 `UNLOCATABLE` 偷换成 PASS；不确定样本必须保持不确定。
7. 固定 fixture 输入文件哈希、Golden 文件哈希、依赖 lock 与运行环境信息全部写入 S0 报告。

### 8.4 100 次规范化重放

规范化 JSON 使用 UTF-8、键排序、固定数组排序规则和无多余空格序列化。哈希覆盖 verdict、故障类别、阶段、候选页、页码转换和证据字段；排除墙钟时间、运行耗时、绝对路径、临时目录、主机名和随机 UUID。重放 100 次应得到一个且仅一个规范化 SHA-256。该测试证明同一冻结输入的计算结果确定，不证明不同模型或真实系统的行为一致。

## 9. UI 与交互设计

### 9.1 主界面

本地 Web 报告为单页离线 HTML，默认桌面宽屏布局；无 CDN、远程字体、分析脚本或外部 API。页面顶部显示 PDF 文件名、SHA-256、页数、bundle schema、运行版本与整体状态。

### 9.2 四栏联动视图

1. **PDF 真值栏**：物理页索引 0-based、页号 1-based、page label、该页抽取状态与可点击的本地 PDF `#page=<viewer_page1>` 链接。
2. **抽取栏**：逐页文本状态、文本 hash、引用 quote 命中位置/候选页；图像页显示 `IMAGE_ONLY / NO_TEXT_LAYER`。
3. **分片与索引栏**：chunk id、source page 集合、index record id、索引中保留的页元数据；分别显示 chunk 与 index 差异，不把两阶段合并归因。
4. **最终引用栏**：模型/应用输出的原始 page value、page basis、最终 viewer page、实际应打开的页与 verdict。

选中一条引用时四栏同步高亮；选择一项故障后显示“错误页码 → 首个出错环节 → 正确来源位置”对照表。可按故障类型、阶段、状态过滤；支持展开原始观测 JSON、复制单条 JSON 证据、下载完整 `report.json`。

### 9.3 颜色与状态

- PASS：中性绿色标记。
- FAIL：红色，必须显示差异值。
- AMBIGUOUS / UNLOCATABLE / UNKNOWN：琥珀色，强调“未能确认”，不可使用绿色。
- SKIPPED：灰色，显示跳过原因。

### 9.4 可访问性

键盘可操作；状态不能只靠颜色表达；页码同时显示字段名和基准；长路径与中文文件名换行；表格可横向滚动；报告在 1280px 宽度可读，窄屏降为分栏卡片。

## 10. 技术架构与模块划分

### 10.1 固定架构

```text
PDF + pagetrace.bundle/v1
        |
        v
Input Validator ---- PDF SHA / page count / size / encryption
        |
        v
Page Extractor (pypdf) ---- per-page text + page identity
        |
        v
Quote Locator ------------ exact normalized matches / candidate pages
        |
        v
Stage Comparator --------- Extraction -> Chunking -> Indexing -> Display
        |
        v
Verdict Engine ----------- four fault classes + UNKNOWN states
        |
        +------> report.json
        +------> offline report.html (vanilla JS)

S0 tests: Golden Fixtures + independent Oracle (pdfminer.six) + 100 replays
```

### 10.2 建议源码目录

```text
pagetrace/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── src/pagetrace/
│   ├── __init__.py
│   ├── cli.py
│   ├── contracts.py
│   ├── pdf_input.py
│   ├── extract.py
│   ├── normalize.py
│   ├── locate.py
│   ├── trace_bundle.py
│   ├── compare_stages.py
│   ├── verdicts.py
│   ├── report_json.py
│   ├── report_html.py
│   └── assets/report.css
├── fixtures/
│   ├── specs/
│   ├── pdfs/
│   ├── bundles/
│   └── golden/expected.json
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── privacy/
│   ├── oracle/                 # 独立实现，不 import src/pagetrace
│   └── s0/
└── docs/
    ├── PAGE_SEMANTICS.md
    ├── BUNDLE_SCHEMA.md
    ├── PRIVACY.md
    └── LIMITATIONS.md
```

## 11. 技术栈与版本策略

| 层 | 技术 | 用途与约束 |
|---|---|---|
| 语言 | Python 3.12.x | CLI、PDF 逐页处理、确定性报告 |
| 生产 PDF 抽取 | pypdf | 逐页 `extract_text()`；不执行 OCR |
| 合成 PDF | ReportLab | 固定元数据生成文本页、空白页与页标签样本 |
| 图像页夹具 | Pillow | 生成扫描件式图像页；图像中可画可见文本，但 PDF 不含文本层 |
| 独立 Oracle PDF 路径 | pdfminer.six | 与生产 pypdf 分离的文本页读取，用于独立核对 Golden Fixtures |
| 数据契约 | JSON Schema Draft 2020-12 + Python dataclass / 校验器 | bundle 与 report 版本化 |
| UI | 原生 HTML / CSS / JavaScript | 静态离线报告，无 CDN、无构建服务依赖 |
| 测试 | pytest + Python 标准库 | 单元、集成、Golden、Oracle、100 次重放 |
| 打包 | Python `venv` / pip / wheel | 不依赖 GPU、数据库或收费服务 |

**版本冻结原则：** T001 在实际 VM 上探测 Python、浏览器、CPU、内存与可用磁盘；从当时稳定版本中选取与 Python 3.12 兼容的依赖，精确写入 `requirements.lock` / lock 文件。不要在规格中伪称已经验证某个未来版本。依赖版本一旦通过 S0 后冻结，升级必须重跑完整 S0。

## 12. CLI 与运行接口

### 12.1 命令

```bash
# 建立环境
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"

# 生成合成夹具
python -m pagetrace.cli fixtures build --out fixtures/generated

# 对单份 PDF + 标准化 trace 运行
python -m pagetrace.cli analyze --pdf path/to/source.pdf --trace path/to/trace.json --out out/case-001 [--include-snippets]

# 预览并清理指定的 PageTrace 输出目录
python -m pagetrace.cli clean --dry-run out/case-001
python -m pagetrace.cli clean out/case-001

# 运行 S0 全部 48 组与正常控制引用
python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out out/s0

# 校验 bundle，不运行分析
python -m pagetrace.cli validate --trace path/to/trace.json --pdf path/to/source.pdf
```

命令名和参数以 T009 实际冻结的 CLI contract 为准；任何变更必须同步 README、测试和计划书交接记录。

### 12.2 退出码

| 退出码 | 意义 |
|---:|---|
| 0 | 命令成功；S0 所有阻断门通过 |
| 1 | 输入可读但分析结果包含 FAIL / UNKNOWN（分析完成，不等于工具崩溃） |
| 2 | 输入、schema、hash 或页码语义无效 |
| 3 | 内部错误或未捕获异常 |
| 4 | S0 门禁失败 |

## 13. 隐私、安全与许可证

- 默认本地处理；运行时不发起任何网络请求，不上传 PDF、quote、trace、报告或日志。
- 不需要账号、密钥、收费 API、模型 token、数据库服务或 GPU。
- 默认报告只保存 quote hash 与短摘录；完整文本仅在用户明确启用 `--include-snippets` 时保存在本地。
- 原始 PDF 默认不复制进输出目录，只记录文件名与 SHA-256；用户可选择将其作为本地报告相对链接目标。
- 临时文件放在每次运行独立临时目录；成功/失败均清理临时内容。提供 `pagetrace clean <case-dir>`，用户可查看、编辑、删除输入、bundle、报告和缓存。
- 不记录绝对路径、用户名、环境变量、网络地址或文档正文到默认日志。
- 拒绝超限 PDF、加密且无法读取的 PDF、异常页数与损坏输入；限制默认 50 MiB、500 页，阈值可在本地配置中下调，不自动放宽。
- 项目自有代码使用 MIT。依赖须保留其原始许可证与 NOTICE；T013 做依赖许可证扫描。MVP 避免引入 AGPL 或需要商业授权的 PDF 引擎；生产抽取采用 pypdf，独立 Oracle 采用 pdfminer.six。
- 不提供法律、医疗、金融或其他高风险领域建议。

## 14. 验收指标与成功定义

| 指标 | MVP 门槛 | 测量方式 |
|---|---:|---|
| 四类故障检出 | 48/48；每类 12/12 | S0 Golden Fixtures |
| 首错阶段定位 | 48/48 与 Golden 一致 | 阶段快照逐边比较 |
| 正常引用误报 | 0 | 每份故障 PDF 至少 1 条正常控制引用 |
| 生产实现与 Oracle parity | 48/48 故障案例 + 全部控制项一致 | 独立 Oracle 报告 |
| 规范化重放 | 100 次结果 SHA-256 唯一值数 = 1 | 同一冻结套件重复执行 |
| 页码语义 | 0 个无基准隐式转换 | schema / unit tests |
| 隐私 | 0 网络请求；0 文档内容外传 | 离线网络拦截与本地日志审计 |
| 可复现性 | fixture、Golden、依赖锁与命令完整 | `HOW_TO_REPRODUCE.md` + SHA 清单 |

成功只意味着合成基准与本地契约达标。真实系统的 RAG pipeline integration、不同解析器的线上质量和用户价值仍需单独验证。

## 15. 样例输入与输出

### 15.1 页码偏移示例

- PDF 有 8 个物理页。
- quote 唯一出现在 `pdf_page_index0=6`，因此 `pdf_page_number1=7`。
- extraction、chunking、indexing 都记录 `[6]`。
- display 收到 `citation_page_value=6`、`citation_page_basis=PDF_INDEX_0`，却把 `viewer_page1` 设成 6。

预期报告：

| 错误页码 | 首个出错环节 | 正确来源位置 |
|---|---|---|
| viewer 第 6 页 | Display（把 0-based 值直接传给 1-based viewer） | `pdf_page_index0=6`；`pdf_page_number1=7`；`viewer_page1=7` |

### 15.2 索引重建丢元数据示例

- Extraction 与 Chunking 都记录 `source_page_indices0=[6]`。
- Indexing 重建后 `source_page_indices0=null`。
- Display 没有可靠页身份。

预期报告：`PAGE_METADATA_MISSING`，`first_fault_stage=INDEXING`；正确来源为物理第 7 页；不得将展示层缺页码当成首因。

### 15.3 重复文本示例

quote 在物理第 2 页与第 6 页各出现一次；chunk/index 仅保存 quote 文本，未保留来源页锚点。

预期报告：`DUPLICATE_TEXT_AMBIGUITY`，候选 `pdf_page_index0=[1,5]`，显示“无法唯一落页”；不得擅自挑第 2 页或第 6 页。

### 15.4 扫描件式页面示例

引用的可见文本只存在于 PDF 第 4 页的图片中，抽取文本为空，未启用 OCR。

预期报告：`UNLOCATABLE`，`first_fault_stage=EXTRACTION`，状态 `IMAGE_ONLY_OR_NO_TEXT_LAYER`；可以展示 trace 给出的候选物理页，但必须注明“文本层无法确认”，不得声称引用不存在。

## 16. 评分与商业假设（非实测）

本项目沿用立项确认分数：**22/25**（新颖性 3、可行性 5、数据 5、范围 5、影响 4）；GitHub 传播潜力 **4.7/5**；潜在收购价值 **4.3/5**。这些是产品规划评分，不是用户研究结果。

RICE 规划假设：`Reach=12`（千名潜在触达用户）、`Impact=2.5`、`Confidence=0.40`、`Effort=2.0` 人周，`RICE = 12 × 2.5 × 0.40 ÷ 2.0 = 6.00`。Reach、Impact、Confidence、Effort 均待验证；不得将 6.00 解释为市场测量或收入预测。

GitHub 传播路径假设：README 用一个 7 页 PDF 展示“引用第 6 页 → 正文第 7 页 → 自动定位 Display off-by-one”，随后展示四阶段 trace 与 S0 可复现命令。潜在产品化路径是作为 RAG / 文档处理系统的 CI 回归测试组件、解析器升级验收工具或企业知识库数据质量插件。收购潜力评分仅表示产品邻接性，不代表任何公司表达过兴趣。

## 17. 主要风险与处理

| 风险 | 影响 | 处理与边界 |
|---|---|---|
| 用户只提供 PDF 和最终 citation，没有阶段 trace | 无法确定是抽取、分片、索引还是展示丢页码 | 明确输出 `UNKNOWN_TRACE_MISSING`；要求导出四阶段快照，不猜测 |
| PDF 文本抽取格式与 quote 不一致 | 误报无法定位 | 严格 NFC/空白规范化；不做语义模糊匹配；记录 `UNLOCATABLE` 原因 |
| 重复文本本身无法唯一确定来源 | 可能错误地强行落页 | 保留候选集合，报告 `AMBIGUOUS`；除非有页级来源锚点，不判 PASS |
| 扫描 PDF 没有文本层 | 无法定位视觉文字 | 明确不做 OCR；标记 `IMAGE_ONLY / NO_TEXT_LAYER` |
| 第三方 trace schema 各不相同 | 接入成本较高 | 先冻结 `pagetrace.bundle/v1` 通用格式；真实 Open WebUI / RAGFlow adapter 不纳入 MVP |
| PDF 畸形或过大 | 资源耗尽或崩溃 | 50 MiB / 500 页默认上限、异常输入退出码、单文件隔离处理 |
| 合成数据过拟合 | S0 通过不能证明真实系统有效 | 48 个 Golden 必须手工定义；真实 RAG 集成明确列为后续独立验证 |

## 18. 参考来源（可核查）

### 真实工程案例

1. Open WebUI #33603 — Docling PDF 的 0-based `page` 与 1-based viewer 参数不一致，导致打开前一页：<https://github.com/open-webui/open-webui/issues/33603>
2. Open WebUI #33810 — 小 PDF 走全文传输路径后 citation / model 输入丢失页码；该 issue 关闭原因为 `not planned`：<https://github.com/open-webui/open-webui/issues/33810>
3. Open WebUI #33909 — 重建索引后 PDF page metadata 丢失：<https://github.com/open-webui/open-webui/issues/33909>
4. RAGFlow #12309 — RAGFlow 0.23.0 + MinerU 2.6.6 的中文 PDF chunk thumbnail / position 映射回归：<https://github.com/infiniflow/ragflow/issues/12309>
5. Open WebUI 文档：Docling 空白页可能造成引用页码漂移的排查说明：<https://github.com/open-webui/docs/blob/main/docs/features/chat-conversations/rag/document-extraction/docling.md>
6. ReviewReceipt 的去重边界：open-code-review #367 与已合并 PR #520 `RunManifest` 覆盖契约：<https://github.com/alibaba/open-code-review/issues/367>；<https://github.com/alibaba/open-code-review/pull/520>

### 官方技术资料

7. pypdf 文本抽取官方文档：<https://pypdf.readthedocs.io/en/stable/user/extract-text.html>
8. ReportLab 文档入口：<https://docs.reportlab.com/>
9. Python Unicode normalization：<https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize>
10. JSON Schema 2020-12：<https://json-schema.org/draft/2020-12>
11. pdfminer.six 文档：<https://pdfminersix.readthedocs.io/en/latest/>

### 仅作背景、不用于推导 PageTrace 需求规模的调查

- Stack Overflow Developer Survey 2026：14,304 名受访者中 949 人（6.6%）表示信任 AI 处理包括重要工作决策在内的工作。它反映 AI 信任具有条件性，不是 PDF 引用痛点频率或 PageTrace 购买意愿调查：<https://survey.stackoverflow.co/2026/ai/data/ai-trust>
- METR 2025 RCT 的 19% 结果仅适用于该研究的早期 2025 工具、16 名资深开源开发者和 246 项任务；它只可用于说明开发者自我预测与研究中实际测量结果可能不一致，不能写成“2026 年 AI 编程普遍慢 19%”，也不能推导 PageTrace 购买需求。METR 2026-02-24 后续说明新一轮实验存在参与者选择偏差，因此不用于 PageTrace 需求论证：<https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/>；<https://metr.org/blog/2026-02-24-uplift-update/>
- CodeRabbit 关于 AI 合著 PR 问题数的比较不作为 PageTrace 的需求、Reach 或评分依据；若后续背景材料引用该数字，必须注明它是供应商自有评审体系对 470 个 PR 的分析，并说明工具判定与样本选择限制。该研究与 PDF 引用页码问题没有直接关系。

---

**规格结论：** PageTrace 的 MVP 边界、字段语义、数据结构、故障分类和 S0 验收口径已冻结为本 v1.0.0 草案。项目方核对前保持 `WAITING_OWNER_REVIEW`；不宣布 GO，不启动代码施工。