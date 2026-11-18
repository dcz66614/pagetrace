# FIX-R1 P1-R1-02 — UNLOCATABLE 错误归因修复记录

- 日期：2026-11-17（GMT）
- 修复工：B（P1-R1-02）
- 终审依据：`~/workspace/P026_FINAL_REVIEW_R1.md` P1-R1-02（§一）与 P2-11（§四）
- 冻结规格：`~/workspace/p026-specs/PROJECT_BOOK.md` v1.0.0（§5、§7.2、§7.3、§8.1；规格本身未编辑）
- 工作目录：`~/workspace/p026-pagetrace/04_source/source`（main，未 commit；冻结源码 commit cfc8b94 未动）

## 1. 缺陷复现（修复前证据，实测）

用 `.venv`（Python 3.12.3）对 `un-ext-12` 及全部 12 个 UN 案例复现，GPT 的描述全部属实：

- `un-ext-12.pdf` 共 8 页，8 页全部是 `TEXT`（pypdf 诚实抽取），无图像页、无空白页。
- Extraction trace 与诚实抽取逐页一致：`compare_extraction` 差异 0 条（text_state 与 text_sha256 全部相符）。
- 故障引用 `近似句un-ext-12：引用页码漂移会误导读者定位正文。` 与第 6 页（index 5）句子 `……定位原文。` 仅在第 27 个字符不同（原文 vs 正文，两句各 29 字）；`locate_quote` 候选页 `[]`。
- 但生产代码、Oracle、Golden 三者都返回 `FAIL_UNLOCATABLE / UNLOCATABLE /
  first_fault_stage = "extraction"`，且 `expected_source_pages0 = [5]`，把 trace
  声称的第 6 页当作已确认的真实来源页。三者一致只是共同错误的自洽，不是正确性证明。
- 同一缺陷影响全部 4 个近似引用案例（`un-ext-09..12`，reason 均为
  `NO_EXACT_MATCH`，锚页全为 TEXT，extraction audit 差异均为 0）；另 8 个案例
  （`un-ext-01..04 IMAGE_ONLY`、`un-ext-05..08 EMPTY`）的 extraction 归因是可证实的，不受影响。

## 2. 修复规则（新正确语义）

**只有明确的 `IMAGE_ONLY` / `EMPTY` 或可证实的抽取失败，才归因 Extraction。**

- 锚页（trace 声称页，chunk 优先、其次 index）诚实状态全为 `IMAGE_ONLY` 或全为
  `EMPTY` → `first_fault_stage = "extraction"`，`expected_source_pages0 = 锚页`
  （该页没有文本层，抽取可证失败；规格 §5 明文）。
- 否则（`NO_EXACT_MATCH` / `NO_TEXT_LAYER`）：检查 bundle 的 extraction 记录在锚页上
  是否与诚实抽取可证不同（缺记录 / 状态不符 / hash 不符）。有可证差异 → 仍归因
  `extraction`（抽取确实错了）；无差异 → **`first_fault_stage = null`，
  `expected_source_pages0 = null`**，verdict 仍为 `FAIL_UNLOCATABLE`，reason 仍为
  `NO_EXACT_MATCH` / `NO_TEXT_LAYER`。trace 声称页只作为证据文本记录，不再冒充已确认来源页。
- `null` 的取值依据：报告 schema `pagetrace.report/v1` 的 `first_fault_stage` 字段
  本就允许 `null`，含义是“no stage can be blamed”；生产代码中 `PASS` /
  `UNKNOWN_TRACE_MISSING` / `AMBIGUOUS` / `NEEDS_MANUAL_REVIEW` 已用同一约定。
  规格 §7.3 要求“只有阶段输入齐全且来源真值唯一时，才能给出确定阶段”——近似引用
  在文本层无任何精确匹配、来源真值不存在，无法给出确定阶段；§5 要求“无法区分图像页
  与错误 quote 时，说明原因未知，不宣称原文不存在”；§7.2 要求非 `IMAGE_ONLY` /
  `EMPTY` 时“报告 UNLOCATABLE，原因未定”。不引入新的枚举值、不改 schema、不改规格。

## 3. 改了哪些文件（只改授权文件）

| 文件 | 改动 |
|---|---|
| `src/pagetrace/compare_stages.py` | 步骤 2（quote 未找到）分支：按上述规则决定 `first_fault_stage` / `expected_source_pages0`；证据 note 与 notes 说明“无阶段可归咎、声称页未确认”；模块 docstring 同步更新（含一处旧文案修正：anchor 只取 chunk/index，无 display 回退）。 |
| `tests/oracle/attribute.py` | 同一规则的独立镜像实现（用 `audit_extraction` / pdfminer 路径核查锚页可证差异）；模块 docstring 规则 2 同步更新。Oracle 仍不 import 生产模块。 |
| `fixtures/golden/expected.json` | `un-ext-09/10/11/12` 的 fault 项：`first_fault_stage: "extraction"` → `null`；`expected_source_pages0: [N]` → `null`；`evidence_note` 与 `basis` 删去“at stage extraction”的错误归因句，改为“无阶段可归咎、声称页未确认”。其余 44 个案例零改动（`git diff` 仅 16 行新增 / 24 行删除）。 |
| `fixtures/specs/un-ext-12.json` | `expected.first_fault_stage` → `null`；`expected.expected_source_pages0` → `null`；顶层 `first_fault_stage` → `null`；`fault_description` 澄清：第 5 页是设计上放置近似句的页面，不是已验证的引用来源；`fault_citation.true_source_pages0 [5]` 保留（它记录近似句被放置的位置，该事实本身为真，见说明）。spec 的 `pages` 内容与 `pdf_sha256` 未动（PDF 字节未动）。 |
| `fixtures/specs/un-ext-09.json`、`un-ext-10.json`、`un-ext-11.json`（授权范围外追加，见 §6 注） | 与 `un-ext-12.json` 完全相同的改法：顶层与 `expected` 的 `first_fault_stage` → `null`，`expected.expected_source_pages0` → `null`，`fault_description` 同样澄清。只改这三个文件是修复的必要延伸：生产代码按 reason 通用修复，4 案同错；若只改 `un-ext-12`，`test_fault_citation_matches_spec[un-ext-09/10/11]` 仍失败，且 spec 与 manifest 将互相矛盾。`pages` 与 `pdf_sha256` 未动。 |
| `fixtures/manifest.json`（授权范围外追加，见 §6 注） | 4 个近似案例条目的 `first_fault_stage` → `null`（其余 44 条零改动）。只改这 4 处是修复的必要延伸：manifest 是 HTML 报告管线比对首错阶段的期望来源，不改则报告渲染计数为 44/48；且 `test_specs_match_manifest` 要求 spec 顶层与 manifest 一致。`pdf_sha256` / 页数 / 覆盖统计未动；`test_regeneration_is_byte_deterministic` 只比对 SHA 与故障计数，不受影响。 |
| `docs/LIMITATIONS.md` | P2-11 条改写：记录修复内容、4 案范围、null 约定；并记录残留的 §8.1 组成措辞偏差（见 §5）。 |
| `tests/unit/test_unlocatable_attribution.py`（新增） | 独立回归测试 19 项（见 §4）。不改任何已有测试文件。 |
| 本文件（新增） | 变更原因与证据记录。 |

未碰：`tools/run_s0.py`（S0 门禁逻辑本身无需改动——它按“生产 == Golden”计分，null 与 null 相等即通过；§8.3 item 2 仍为 48/48）、冻结 commit cfc8b94、PDF 与 bundle 文件、GitHub/Drive（无上传）、`verdicts.py` 与 `docs/PAGE_SEMANTICS.md`（见 §6 待办）。

## 4. 验证（修复后证据）

- 复现脚本重跑（12 个 UN 案例，生产 + Oracle）：`un-ext-01..08` 不变
  （`IMAGE_ONLY`/`EMPTY` → `extraction`，锚页保留）；`un-ext-09..12` 变为
  `first_fault_stage = null`、`expected_source_pages0 = null`，reason 仍为
  `NO_EXACT_MATCH`，verdict 仍为 `FAIL_UNLOCATABLE`；控制引用全部 PASS。
- S0 `--repeat 1`（`tools/run_s0.py --out /tmp/s0-fix-r1-unloc`）：
  `S0_RESULT: SMOKE_PASS`（1 次重放，正式 PASS 需 100 次，在冻结阶段统一跑）。
  detection 48/48（UN 12/12）、**first_fault_stage 48/48**、控制误报 0、
  parity 96/96（0 字段不匹配）、golden 一致 0 不匹配、重放哈希 1 个唯一值：
  `2a324e9b21bea6247152c977886ff72e987e2257c6929c142747e93d44f276ac`
  （取代冻结基线 `5195fc9a…`；正式 100 次重放在冻结阶段确认该值）。
  此时 48/48 是生产、Oracle 与修正后 Golden 在新正确语义上的一致，不再是旧错误规则的自洽。
- 新回归测试 `tests/unit/test_unlocatable_attribution.py`：**19/19 通过**。覆盖：
  GPT 复现事实（8 页全 TEXT、extraction 零差异、一字之差位置 26）、4 个近似案例
  三方一致为 null、8 个图像/空白案例仍归因 extraction、reason 4/4/4 不变、
  合成篡改（锚页 hash 篡改 → 仍归因 extraction；无关页 hash 篡改 → 仍为 null；
  无 anchor → `NO_TEXT_LAYER` + null）、含 null 阶段的完整报告通过
  `pagetrace.report/v1` schema 校验。
- 相关已有测试（最终宽口径复核，`tests/unit + tests/oracle +
  test_oracle_parity + test_html_report + tests/s0`）：**676 通过 / 4 失败**，
  4 个失败全部是授权文件之外的旧钉（见 §6）：2 个旧规则断言
  （`test_verdicts.py::test_unlocatable_reasons_split_four_four_four`、
  `test_oracle.py::test_golden_unlocatable_reasons_are_4_4_4`）与 2 个冻结
  Golden SHA 钉（`test_run_s0.py` 两项；其余 S0 计数全部通过）。其中
  `tests/integration/test_oracle_parity.py` **4/4 通过**；
  `test_fault_citation_matches_spec` 48/48 通过；
  `test_specs_match_manifest` 通过；
  `test_real_pipeline_counts` 的 `first_fault_stage_correct` 为 **48/48**。

## 5. §8.1 合规说明与残留偏差（诚实记录）

- §8.1 的行为要求现已满足：近似引用不启用 OCR、报告为文本层无法确认、不宣称
  内容不存在、不虚构首错阶段、不冒充已确认来源页。
- §8.1 的组成措辞（“12 组均含扫描件式图像页或无文本层页面”）对 `un-ext-12`
  仍字面不成立：其 8 页全为 TEXT。原因是夹具生成器
  （`tools/generate_fixtures.py` `_build_case`）的结构规则：案例序号 47 为奇数且
  `47 % 3 == 2`，空白页与图像页两条结构规则均未触发；其余 11 案各含一页非文本页。
  本修复工未 hand-edit spec 的 `pages`（那会使 spec 与 PDF 字节及生成器三方脱节，
  且 S0 运行时根本不读 spec 文件），也未重新生成 PDF（`fixtures/pdfs/` 与
  `fixtures/bundles/` 不在授权文件内）。PDF 第 0 页页眉行
  （“故障类别 UNLOCATABLE · 首错阶段 extraction”）同样是已冻结的旧文案，随 PDF
  字节冻结，须随重新生成才改。
- 彻底解决需协调员另派任务：改生成器（近似引用 UN 案例保证含一页非文本页）→
  重新生成并验证其余 47 案字节不变 → 更新 spec `pdf_sha256` 与 bundle 抽取记录 →
  重新冻结（S0 100 次重放确立新基线哈希）。在该任务完成前，§8.1 组成措辞偏差
  以本记录 + `docs/LIMITATIONS.md` 为准，不再是归因错误。

## 6. 未完成 / 需协调员处理（本修复工无权改的文件）

以下失败与残留均非本修复引入的新缺陷，而是旧期望值在授权文件之外的副本；
修复工已核实每一条的根因，修复方法明确，待协调员派发或在重冻结时统一处理。
注：§3 所列 `fixtures/manifest.json` 与 `fixtures/specs/un-ext-09/10/11.json`
超出任务原定文件清单——超出原因是同一错误期望存在于这些生成器产物副本中，
只改授权文件会使套件自相矛盾（spec 与 manifest 不一致、HTML 渲染 44/48）。
四处改动均为同一规则的同值修改（null），与 `un-ext-12.json` 的已授权改法完全相同，
未碰 PDF/bundle/代码/测试；生成器本身仍编码旧规则（见下），请协调员确认该范围延伸。

1. **`tools/generate_fixtures.py`**（生成器，根源）：`_build_case` 对 UN 案例无条件写
   `"first_fault_stage": stage`（即 extraction）进 case dict、`expected` 与 manifest，
   且页面种类规则造成 §5 的组成偏差。修复：近似引用 UN 案例的期望阶段改为 null、
   期望来源页改为 null，并保证一页非文本页；随后重新生成并验证其余 47 案字节不变。
   在生成器修复前，任何一次重新生成都会把本修复的手改值（spec/manifest）打回旧值——
   重冻结前务必先修生成器，或重生成后重新应用本修复的期望值。
2. **旧断言测试（他人文件，须由其负责人按新规则更新）**：
   - `tests/unit/test_verdicts.py::test_unlocatable_reasons_split_four_four_four`
     断言 12 案全为 extraction；应改为 8 案 extraction + 4 案 null（reason 4/4/4 不变）。
   - `tests/oracle/test_oracle.py::test_golden_unlocatable_reasons_are_4_4_4`
     同上（Golden 已改，断言未改）。
3. **冻结哈希钉（重冻结时统一更新，非本修复工文件）**：Golden 文件 SHA 已变
   （新值 `70a76461338aa6ee47fe345b610dbe7a4f6ece6b9e13de662e35efbc1aac2451`，
   旧值 `417e3ed3…`），导致 `tests/s0/test_run_s0.py` 两项失败
   （`test_golden_sha_matches_frozen_value`、`test_run_s0_real_suite_repeat_2` 的
   SHA 断言；其余 S0 计数全部通过）；S0 重放基线哈希已变（新值见 §4，旧值
   `5195fc9a…`），`tests/e2e/test_e2e.py` 与 `tests/privacy/test_privacy.py`
   的 `EXPECTED_REPLAY_HASH` 钉须在 100 次重冻结后更新（本次未跑 e2e/privacy 全量）。
4. **文档不同步（非授权文件）**：`src/pagetrace/verdicts.py` 的
   `CitationVerdict.expected_source_pages0` docstring 仍写“UNLOCATABLE 用
   trace-claimed anchor pages”；`docs/PAGE_SEMANTICS.md` §1.3/§4 的
   `first_fault_stage` null 规则只列 PASS 与缺失快照，未提及近似引用 UNLOCATABLE
   （该文件正由 P1-R1-04 工人编辑 R-11 内容，改动须与其协调）。
   建议随上述任务同步更新（不影响行为与 S0）。

## 7. 收尾确认

- `git diff --stat`（本修复工的文件）：`src/pagetrace/compare_stages.py`、
  `tests/oracle/attribute.py`、`fixtures/specs/un-ext-09/10/11/12.json`、
  `fixtures/golden/expected.json`、`fixtures/manifest.json`、
  `docs/LIMITATIONS.md`，新增 `tests/unit/test_unlocatable_attribution.py` 与本文件；
  未 commit，未改 `tools/run_s0.py`，未动冻结 commit cfc8b94，未上传 GitHub/Drive。
  同工作区内其他 FIX-R1 工人的改动（cli/extract/pdf_input/trace_bundle、
  `tools/run_s0.py`、PAGE_SEMANTICS R-11 等）与本修复无关，未碰。
- 未能核实的事：正式 100 次 S0 重放（冻结阶段统一跑）；e2e / privacy 全量
  （仅知其哈希钉须更新，未实测）；§5 的生成器修复与重新生成（未授权、未执行）。

## 8. 收尾工 E：生成器修正与重生成记录（2026-11-17 GMT）

- 修复工：E（P1-R1-02 收尾）。本节接 §5–§6 的尾巴：生成器修正、§8.1 字面组成
  达标、过期断言/钉更新、文档同步。冻结规格 v1.0.0 未编辑；未 commit；未上传
  GitHub/Drive；正式 100 次 S0 重放留待冻结阶段。

### §8.1 任务前提的一个纠正（实测为准）

- 任务书称“un-ext-09..12 四个近似案例目前全是 TEXT 页”，实测不成立——B 的
  §5 记录正确：只有 `un-ext-12`（生成器序号 47，奇数且 `47 % 3 == 2`，空白页
  与图像页两条结构规则均未触发）8 页全 TEXT。实测重生成前各案非文本页：
  `un-ext-09` 第 0 页 blank、`un-ext-10` 第 2 页 image、`un-ext-11` 第 1 页
  blank。因此 §8.1 的字面缺口只有 `un-ext-12` 一案；09–11 本就达标，本次
  只因页眉文案（§8.2c）与 pdf_sha 联动而变字节，09 的 PDF 字节未变。

### §8.2 生成器改了什么（tools/generate_fixtures.py，只改此文件内的 4 处）

1. **近似引用期望阶段改为 null**（`_build_case`，`is_near_miss` 标志）：
   `case["first_fault_stage"]` 与 `expected.first_fault_stage` 由无条件
   `"extraction"` 改为近似引用时 `None`；`expected.expected_source_pages0`
   由 `[tp]` 改为近似引用时 `None`。其余 44 案（及 8 个图像/空白 UN 案）
   的期望值零改动。`GENERATOR_VERSION` 刻意未升（仍为 `t002-1.0.0`），使
   manifest diff 只含预期条目，不含版本噪音。
2. **§8.1 组成保证**（`_build_case`，kind 赋值后）：近似引用案例若尚无任何
   非文本页，则把最后一个空闲页（不在 `{tp, cp} ∪ occ ∪ split_pages`
   内，永不碰锚页与控制引用页）改为 blank。`un-ext-12` 命中：空闲页
   `[2, 3, 4, 6]`，末页取 index 6 改为 blank；09–11 已有非文本页，保证不触发。
3. **PDF 第 0 页页眉去旧文案**：近似引用案例的页眉由“首错阶段 extraction”
   改为“首错阶段 未定（无阶段可归咎）”。09 的第 0 页本就是 blank（不绘文），
   故其 PDF 字节不变，仅 spec `pages[0].lines` 的记录文本同步更新。
4. **`fault_description` 参数化澄清**：近似引用的 `fault_description` 改为
   按 `true_page0` 生成 B 手写澄清的同款文本（锚页是“设计上放置近似句的
   页面，不是已验证的引用来源；无阶段可归咎”），使重生成不再丢 B 的手改
   文案；`FAULT_DESCRIPTIONS` 里的短条目保留但注明已被本分支取代。

### §8.3 重生成与比对（全量重生成到临时目录，两次运行字节一致）

- `python tools/generate_fixtures.py --out /tmp/regen-fixr1-e`（.venv，
  Python 3.12.3），第二次重生成到 `/tmp/regen-fixr1-f`，两次输出 `diff -rq`
  零差异，确定性成立。逐文件比对结论：其余 44 组 PDF/spec/bundle **字节
  零差异**；差异只在下表。合入方式：只从临时目录拷回 09..12 的
  pdf/spec/bundle + `manifest.json` + `sha256sums.txt`（见 §8.6 范围说明）。

| 文件 | 旧 SHA-256（前 12 位） | 新 SHA-256（前 12 位） | 变化原因 |
|---|---|---|---|
| fixtures/pdfs/un-ext-09.pdf | be632f97afa2（不变） | be632f97afa2 | 无变化：PDF 字节未动 |
| fixtures/pdfs/un-ext-10.pdf | 19e175385e7a | 866399d47a2a | 页眉文案改 |
| fixtures/pdfs/un-ext-11.pdf | 5c26f3613c33 | f65caccf698a | 页眉文案改 |
| fixtures/pdfs/un-ext-12.pdf | f4bb6a31c691 | 6bb8eb975bfb | 页眉文案改 + 第 6 页改 blank |
| fixtures/specs/un-ext-09.json | cc3e200aa5b2 | 8211cb6ea70e | 仅页眉记录文本改 |
| fixtures/specs/un-ext-10.json | 70f01d65b9bf | dc876134a8cb | 页眉记录文本 + pdf_sha256 |
| fixtures/specs/un-ext-11.json | 44d9a1850714 | ae8cef445067 | 页眉记录文本 + pdf_sha256 |
| fixtures/specs/un-ext-12.json | 108ee268ea93 | a0088ab652c8 | 页眉记录文本 + 第 6 页 kind blank/lines [] + pdf_sha256 |
| fixtures/bundles/un-ext-09.trace.json | 4729fadc687e（不变） | 4729fadc687e | 无变化 |
| fixtures/bundles/un-ext-10.trace.json | 681dd82f389f | cf5544329f41 | document sha + 第 0 页抽取 hash（页眉改） |
| fixtures/bundles/un-ext-11.trace.json | 903e278aac99 | 3ec1e1a19735 | 同上 |
| fixtures/bundles/un-ext-12.trace.json | e9813d9a6740 | 1bfe56aed14f | document sha + 第 0 页抽取 hash + 第 6 页 TEXT→EMPTY |
| fixtures/manifest.json | fa4dc08a0192 | 25fcf8b77a98 | 10/11/12 三条 pdf_sha256 + coverage `pdfs_with_blank_page` 24→25 |
| fixtures/sha256sums.txt | 74bbfd6efa23 | b79ef2c1a7c1 | 10/11/12 三行 pdf sha |
| fixtures/golden/expected.json | 70a76461338a（B 改后） | 9db9b16e1fd8 | 仅 10/11/12 三条按案 `pdf_sha256`（见 §8.4） |

- Golden 全 SHA 新值 `9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353`
  已写入 `tests/s0/test_run_s0.py` 的 `GOLDEN_SHA256` 钉。未动任何重放哈希钉
  （`EXPECTED_REPLAY_HASH` 未碰）。

### §8.4 Golden 必须同步的原因（重生成确实需要，§8.3 表中最后一行）

- `tools/run_s0.py`（另一 FIX-R1 工人现行版）`load_suite_inputs` 会逐案核对
  PDF 实测 SHA 与 Golden 各案 `pdf_sha256`；只改 PDF 不改 Golden 时，
  S0 及 7 项依赖测试报 `InputError: PDF hash mismatch for un-ext-10:
  file 866399… != Golden 19e175…`。Golden 各案 `extraction_audit` 只有
  `{"diffs": [], "summary": ...}`，无逐页 hash——4 案抽取差异重验仍为 0，
  故 audit 内容无需改，只更新 3 条 `pdf_sha256`（纯字符串替换，git diff
  只多 3 行改动，其余 Golden 内容零动）。

### §8.5 §8.1 达标证据（重生成后实测）

- 12 个 UN 案例每案至少 1 个非文本页：01–04 image、05–08 blank、
  09 blank（p0）、10 image（p2）、11 blank（p1）、12 blank（p6，新增）。
  `un-ext-12` 新页状态：`['TEXT','TEXT','TEXT','TEXT','TEXT','TEXT',
  'EMPTY','TEXT']`——锚页 index 5 仍为 TEXT，控制引用跨页 0–1 未动，
  第 7 页（旧单页控制页位，已被 split 取代）未动。
- 4 个近似案例设计保持（逐案实测）：引用与锚页 TEXT 句仅第 26 字不同
  （原文 vs 正文）、`locate_quote` 候选页 `[]`、控制引用 PASS、抽取
  trace 与诚实抽取差异 0、`first_fault_stage` null、
  `expected_source_pages0` null、verdict 仍为 `FAIL_UNLOCATABLE` /
  reason `NO_EXACT_MATCH`、Golden 三方一致为 null。

### §8.6 断言、钉与文档同步

- `tests/unit/test_verdicts.py::test_unlocatable_reasons_split_four_four_four`：
  改为 8 案 extraction + 4 案 null（并断言近似案 `expected_source_pages0`
  为 null、其余 8 案非 null）；reason 4/4/4 不变。
- `tests/oracle/test_oracle.py::test_golden_unlocatable_reasons_are_4_4_4`：
  同上（Golden 侧）。
- `tests/s0/test_run_s0.py`：`GOLDEN_SHA256` 由 B 记录的
  `70a76461…` 更新为 `9db9b16e…`（§8.3 表）。未动 `EXPECTED_REPLAY_HASH`。
- `src/pagetrace/verdicts.py`（仅 docstring）：模块 docstring 的
  `first_fault_stage` 段补 null 规则（近似引用无可证实抽取失败时为 null，
  只有 `IMAGE_ONLY`/`EMPTY` 或可证抽取记录错误才归因 extraction）；
  `CitationVerdict.expected_source_pages0` 说明同步（UNLOCATABLE 锚页仅在
  诚实无文本层或记录可证不同时才作来源，否则 null）。无代码改动。
- `docs/PAGE_SEMANTICS.md`（仅追加 null 规则段落，未碰 R-11 文本）：
  §1.3 `first_fault_stage` 与 `expected_source_pages0` 两行补近似引用
  null 语义；§4“首错阶段判定”段后追加 FIX-R1 P1-R1-02 段落（与 B 的规则
  表述一致）。
- 范围说明（与 B 的 §6 同类）：`fixtures/bundles/un-ext-10/11/12.trace.json`
  与 `fixtures/sha256sums.txt` 不在任务书文件清单内，但为生成器直接产物、
  且不改则测试失败（`test_bundles_validate_against_schema` 要求 bundle
  `document.sha256 == manifest pdf_sha256`；`test_pdfs_match_manifest`
  要求 `sha256sums.txt == manifest`）。只改这 4 个文件内与本次重生成直接
  相关的行（10/11/12 的 bundle、3 行 sha），其余 44 案零动；请协调员确认
  该范围延伸。

### §8.7 验证结果

- 全量 pytest（.venv，Python 3.12.3，`TMPDIR=~/workspace/tmp-p026-pytest`）：
  **753 通过 / 1 失败**（115 秒）。唯一失败见 §8.8。
- S0 `--repeat 1`（`tools/run_s0.py --out /tmp/s0-fixr1-e --repeat 1`）：
  **`S0_RESULT: SMOKE_PASS`**，detection **48/48**（四类各 12/12）、
  first_fault_stage **48/48**、控制误报 **0**、parity **96/96**（0 字段
  不匹配）、golden 一致 0 不匹配、重放哈希 1 个唯一值
  `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`
  （取代 B 的 `2a324e9b…`；正式 100 次重放在冻结阶段确认该值）。
- 重生成确定性：两次全量重生成输出 `diff -rq` 零差异。

### §8.8 未完成 / 需协调员处理（本收尾工无权改的文件）

1. **`tests/unit/test_unlocatable_attribution.py::test_un_ext_12_reproduces_gpt_findings`
   （B 的文件，全量唯一失败）**：该测试把 GPT 复现事实钉为“8 页全 TEXT”
   （`assert [r.text_state …] == ["TEXT"] * 8`），而 §8.1 修复本身要求
   `un-ext-12` 含一页非文本页——两者互斥，该断言在修复后必然失败
   （现为第 6 页 `'EMPTY' != 'TEXT'`）。其余 18 项（含近似案三方 null、
   4/4/4、篡改合成、无锚点、schema 校验）全部通过。建议由 B 或协调员把该
   测试改为历史复现记录（锚页 index 5 仍为 TEXT、一字之差仍在位置 26、
   抽取零差异仍成立），或把“8 页全 TEXT”改为“除新增 §8.1 空白页外全 TEXT”。
   本收尾工未碰该文件。
2. **`docs/LIMITATIONS.md` §5 的 P2-11 残留偏差段**（B 的文件）：仍写
   “§8.1 组成措辞对 un-ext-12 字面不成立……彻底解决需另派任务”，现已解决，
   该段已过期，建议随冻结同步更新。本收尾工未碰该文件。
3. **正式 100 次 S0 重放**（冻结阶段统一跑）：本次只跑 `--repeat 1`
   验证，重放基线哈希 `a06b87fc…` 待 100 次确认；`EXPECTED_REPLAY_HASH`
   钉（e2e/privacy）须在该阶段更新，本次未跑 e2e/privacy 全量。
4. **其他 FIX-R1 工人的在途改动**（`tools/run_s0.py`、`tests/integration/test_cli.py`
   等）与本收尾无关，未碰；本次全量 753 通过已含其现行改动。

### §8.9 收尾确认

- `git diff --stat`（本收尾工的文件）：`tools/generate_fixtures.py`、
  `fixtures/specs/un-ext-09/10/11/12.json`、`fixtures/pdfs/un-ext-10/11/12.pdf`、
  `fixtures/bundles/un-ext-10/11/12.trace.json`、`fixtures/manifest.json`、
  `fixtures/sha256sums.txt`、`fixtures/golden/expected.json`（仅 3 行
  pdf_sha256；另含 B 的 null 改动）、`tests/unit/test_verdicts.py`、
  `tests/oracle/test_oracle.py`、`tests/s0/test_run_s0.py`、
  `src/pagetrace/verdicts.py`（仅 docstring）、`docs/PAGE_SEMANTICS.md`
  （仅 null 规则段落）、本文件 §8。未 commit，未动冻结 commit cfc8b94，
  未上传 GitHub/Drive；`fixtures/pdfs/un-ext-09.pdf` 与
  `fixtures/bundles/un-ext-09.trace.json` 字节未变（未列入 git 改动）。
