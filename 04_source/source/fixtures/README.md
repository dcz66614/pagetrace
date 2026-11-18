# PageTrace Fixtures — 48 组确定性合成案例（T002）

生成器：`tools/generate_fixtures.py`（`GENERATOR_VERSION = t002-1.0.0`）。
规格依据：`PROJECT_BOOK.md` v1.0.0 §8.1；页码语义以 T001 冻结的
`contracts/pagetrace.bundle.v1.schema.json` 与 `docs/PAGE_SEMANTICS.md` 为准。

## 目录

| 路径 | 内容 |
|---|---|
| `fixtures/pdfs/` | 48 份 PDF（`pdfs/<case_id>.pdf`） |
| `fixtures/specs/` | 48 份 fixture spec（`specs/<case_id>.json`） |
| `fixtures/bundles/` | 48 份 trace bundle（`bundles/<case_id>.trace.json`，`pagetrace.bundle/v1`） |
| `fixtures/manifest.json` | 全部案例清单：页数、SHA-256、引用、覆盖统计 |
| `fixtures/sha256sums.txt` | 48 份 PDF 的 SHA-256 清单 |

## 样本矩阵（§8.1）

| 故障类别 | 数量 | 首错阶段分布 |
|---|---:|---|
| `PAGE_OFFSET` | 12 | Extraction 3 / Chunking 3 / Indexing 3 / Display 3 |
| `PAGE_METADATA_MISSING` | 12 | Extraction 3 / Chunking 3 / Indexing 3 / Display 3 |
| `DUPLICATE_TEXT_AMBIGUITY` | 12 | Chunking 4 / Indexing 4 / Display 4 |
| `UNLOCATABLE` | 12 | Extraction 12（图像页 4 / 空白页 4 / 近似引用 4） |

结构覆盖（见 `manifest.json` 的 `coverage`）：中文段落 48/48 份、
空白页 24 份、图像式无文本页 16 份、跨页断句 18 份、重复句子 24 份；
页标签方案 5 种（decimal / roman / roman-decimal / alpha-prefix / label-7，
其中 label-7 复现 `PAGE_SEMANTICS.md` 例 E：物理页 0 的 label 为 `"7"`）。
每份 PDF 至少含 1 条正常引用控制项，控制引用共 48 条。

## 故障植入模型

**PDF 本身永远是真值；故障只植入 trace（bundle 的阶段快照），绝不手工
修改 PDF 二进制。** 下游阶段如实沿用上游的错误值（真实流水线不会自行
修复上游错误），因此 `first_fault_stage` 是首个出现可证明差异的阶段：

- `PAGE_OFFSET`：某阶段的页身份偏离 canonical `pdf_page_index0`。
  Extraction 是抽取记录附上了邻页文本哈希；Chunking/Indexing 是来源页
  集合 ±1 或把 label 当数字读；Display 是把 0-based 值直接交给 1-based
  viewer、或多加 1、或把 label `"7"` 当作 viewer 页 7。
- `PAGE_METADATA_MISSING`：上游已有来源页身份，下游某阶段缺失/清空。
  表现为记录状态 `ERROR`、字段缺失（`text_sha256` / `pdf_page_label`）、
  记录缺失、`source_page_indices0 == []`、display 值或 viewer 为 null。
  注意：缺失的是**单条记录**，整个阶段从不整体缺失（`missing_stages`
  恒为 `[]`），因此每份 PDF 的控制引用仍可被完整验证为 PASS。
- `DUPLICATE_TEXT_AMBIGUITY`：同一句话出现在 2–3 页，某阶段把候选页
  集合错误缩减为单页（取首/末/中间出现位置）；上游正确的集合保留在
  更早的阶段快照中。
- `UNLOCATABLE`：引用在可抽取文本中找不到。图像页的引用文字只存在于
  栅格图像中（无文本层，不启用 OCR）；空白页的引用无处可寻；近似引用
  与页上句子差一个字，精确匹配失败。`first_fault_stage` 均为 extraction。

## Spec 格式（`specs/<case_id>.json`）

```json
{
  "spec_format_version": "pagetrace.fixture-spec/v1",
  "case_id": "po-ext-01",
  "fault_type": "PAGE_OFFSET",
  "first_fault_stage": "extraction",
  "variant": "plus-one-shift",
  "fault_description": "……（中文/英文说明）",
  "pdf_file_name": "po-ext-01.pdf",
  "pdf_sha256": "<64 位小写 hex>",
  "page_count": 6,
  "label_scheme": "decimal",
  "pages": [
    {"pdf_page_index0": 0, "pdf_page_label": "1", "kind": "text",
     "lines": ["……（每行即抽取后的一行）"], "image_visible_text": null}
  ],
  "fault_citation": {
    "citation_id": "cite-fault",
    "quote_text": "……",
    "true_source_pages0": [3],
    "claimed_page0": 4,
    "candidate_source_pages0": [3]
  },
  "control_citation": {
    "citation_id": "cite-control",
    "quote_text": "……",
    "true_source_pages0": [5],
    "note": "……"
  },
  "duplicate_occurrence_pages0": [],
  "extra_duplicate_pages0": [],
  "split_pages0": [],
  "expected": {
    "verdict": "FAIL_PAGE_OFFSET",
    "fault_type": "PAGE_OFFSET",
    "first_fault_stage": "extraction",
    "expected_source_pages0": [3],
    "candidate_source_pages0": [3]
  }
}
```

字段说明：

- `pages[].kind`：`text`（有文本层）/ `blank`（空白页，无任何内容）/
  `image`（扫描件式图像页，无文本层；`image_visible_text` 是图像中
  肉眼可见的文字，仅供人工核对，不可用于文本匹配）。
- `pages[].lines`：该页实际绘制的文本行（按绘制顺序）；`text` 页的
  每一行在 §4.2 规范化（NFC、LF、空白折叠）后都必须能在 pypdf 抽取
  结果中找到原文。页脚 `第 N 页 / 共 M 页` 也计入行内。
- `fault_citation.claimed_page0`：故障 trace 宣称的单页（`PAGE_OFFSET`
  与 `DUPLICATE_TEXT_AMBIGUITY` 有值；`PAGE_METADATA_MISSING` /
  `UNLOCATABLE` 为 `null`，因为故障是缺失/无法定位而非错页）。
- `expected.candidate_source_pages0`：规范化 quote 实际出现的全部物理页；
  `UNLOCATABLE` 为 `[]`（文本层中找不到）；`expected_source_pages0`
  是 trace 宣称的权威来源页集合（供分析器比对）。
- `split_pages0` 非空时，控制引用是跨页引用（R-10）：`control_citation`
  的 `quote_text` 是两页各半句拼接的完整句子，`true_source_pages0`
  为两页。

## 生成方法

```bash
cd 04_source/source
python tools/generate_fixtures.py --out fixtures
```

- 文本页用 ReportLab 绘制：中文用内置 CID 字体 `STSong-Light`（不嵌入
  字体文件、不下载任何字体），英文用内置 Helvetica。图像页用 Pillow
  生成栅格 PNG（系统 Noto Sans CJK 字体仅用于栅格渲染）后嵌入 PDF。
- 页标签用 pypdf `set_page_label` 写入；元数据固定为
  `CreationDate = ModDate = D:20260101000000Z`，Title/Creator/Producer
  固定字符串；最终字节由 pypdf 写出。
- 生成器在写入前自校验：每行文本可抽取、空白/图像页无抽取文本、PDF
  内实际 label 与 spec 一致、每份 bundle 通过
  `pagetrace.bundle/v1` schema 校验（`jsonschema`）。任一失败即报错停下。
- 不依赖外部数据与网络；不使用随机数（内容只由案例序号派生）。

## 确定性（两次运行字节一致）

固定元数据 + 固定对象顺序 + 无随机源。验证方法：

```bash
python tools/generate_fixtures.py --out fixtures
python tools/generate_fixtures.py --out /tmp/regen-check
diff <(cd fixtures && sha256sum pdfs/*.pdf specs/*.json bundles/*.json manifest.json sha256sums.txt | sort -k2) \
     <(cd /tmp/regen-check && sha256sum pdfs/*.pdf specs/*.json bundles/*.json manifest.json sha256sums.txt | sort -k2)
```

两次运行的 146 个文件 SHA-256 应完全相同（T002 证据日志中有实测记录）。

## 验收

```bash
cd 04_source/source
python tools/generate_fixtures.py --out fixtures
python -m pytest tests/unit/test_fixture_manifest.py -q
```

`test_fixture_manifest.py` 校验：48 例、每类 12 例、控制引用 48 条、
manifest 页数与 SHA-256 与实际 PDF 一致、spec label 与 PDF 内 label
一致、控制/故障引用按 spec 定位（UNLOCATABLE 引用在任何可抽取页中
都不存在）、全部 bundle 通过 schema 校验、重生成字节确定。
