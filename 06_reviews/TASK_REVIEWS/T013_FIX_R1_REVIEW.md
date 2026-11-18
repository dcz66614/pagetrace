# P026 PageTrace — T013 风格独立内部重审：FIX-R1（R1 返修后重冻结）

- 重审员：独立内部重审（T013 风格），只审不改
- 重审时间：2026-11-17 ~05:13–05:25 UTC
- 审查对象：代码冻结 `d0aa21f` + 文档修正 `8cfd7dc`；当前 master `04cefb3`（已合并 `task/fix-r1`）；工作树干净（重审前后 `git status` 均为空）
- 发布包：`04_source/source-release.zip`，255 文件、1,148,388 B、SHA-256 `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b`；manifest SHA `b6db053e…fcc33f`
- 对照：GPT 终审 R1 全文 `~/workspace/P026_FINAL_REVIEW_R1.md`（FINAL_VERDICT: FAIL，P0=0，P1=5，P2=6）；冻结报告 `00_control/FIX_R1_FREEZE_REPORT.md`；审查包 `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_03.md`、`REVIEW_PACK_RELEASE_04.md`；证据索引 `07_evidence/REVIEW_PACKS/RELEASE_REVIEW_INDEX.md`（FIX-R1 定稿节）
- 方法：全部 5 项 P1 均按 R1 报告的复现步骤亲手复现（不用测试文件里的现成夹具做唯一证据，另写独立复现脚本 `~/workspace/tmp-p026-rereview/repro.py`）；全量 pytest 与 S0 `--repeat 100` 亲自重跑；clean-copy 从 ZIP 全新 venv 重做；ZIP 与冻结 git 树逐文件比对并重建一次；Drive 25 文件全部元数据核对 + 5 文件下载核对。测试缓存与输出目录均用持久磁盘 `~/workspace/tmp-p026-rereview`（TMPDIR 同指该处），未用 `/tmp`。
- 本次重审未做：未改任何源码/测试/文档，未 commit，未写 Drive，未提交 GPT 终审，未上传 GitHub。本报告是仓库内唯一新增文件。

## 总体 verdict：FAIL（4/5 项 P1 CLOSED，1 项 PARTIAL）

| 项 | verdict |
|---|---|
| P1-R1-01 PDF TOCTOU | **CLOSED** |
| P1-R1-02 UNLOCATABLE 错归因 | **CLOSED** |
| P1-R1-03 clean 误删无关目录 | **CLOSED** |
| P1-R1-04 报告泄露绝对路径 | **CLOSED** |
| P1-R1-05 证据不完整 | **PARTIAL** — FIX-R1 自身证据已齐且 25/25 核对通过；但 R1 点名的 3 份 T014 原始日志与 T014 的 git-diff 证据仍不在 Drive 上（本地存在，未上传；索引 §3 自认“仍待协调员决定是否补传”） |
| P2 SMOKE_PASS / 图像枚举 ERROR / lock 安装 | 全部 **CLOSED** |
| 独立重跑门禁 | pytest **754/754**；S0 `--repeat 100` **PASS**（哈希 `a06b87fc…`，与冻结报告逐字段一致，仅 `base_commit` 不同，见 §7 注） |
| ZIP ↔ 冻结树 / 确定性 | **0 不匹配**（仅 `.gitignore` 未打包）；重建 SHA 与发布包**完全相同** |

按任务格式：任一 P1 非 CLOSED 即总体 FAIL。本次唯一的未闭合项是 P1-R1-05 的历史证据缺口，且补救极小——把本地已有的 5 个文件补传到 Drive 并更新索引即可关闭（见 §5 末“关闭条件”）。4 项代码类 P1 均已亲手复现确认修复，无新代码缺陷发现。

---

## 1. P1-R1-01 PDF TOCTOU — CLOSED

**修复机制（读码确认）。** `src/pagetrace/pdf_input.py`：`load_pdf` 把校验过的精确字节带在 `PdfDocumentInfo.pdf_bytes` 里；`src/pagetrace/extract.py:126` `extract_pages` 只解析 `info.pdf_bytes`，且先复核其 SHA 与 `info.sha256` 一致（不一致报 `CORRUPT`）；无携带字节的旧式 info 才重读路径，且 SHA 不符报 `SHA_MISMATCH`（`extract.py:140–180`）。`extract.py:187` `_require_disk_matches` 在 `extract_pdf(pdf_bytes=…, expected_sha256=…)` 时复核磁盘文件仍与期望哈希一致。`src/pagetrace/cli.py:230` `cmd_analyze` 只读一次 PDF 字节（`_read_pdf_bytes`），先 `bundle.verify_document_hash(pdf_bytes)`，再把同一份字节传给 `extract_pdf`（cli.py:245–258）——验证与抽取之间不存在无复核重开路径的窗口。

**亲手复现（独立脚本，非测试夹具）。** 用 pypdf 自建两个 2 页 PDF：标记 `AAAAAAAA` 与 `BBBBBBBB`，同字节数、同页数、SHA 不同：

- 校验后换文件再 `extract_pages(info)`：返回的仍是 `AAAAAAAA` 文本，`BBBBBBBB` 零出现，`info.sha256` 仍为原 PDF 的 SHA（`84a7571d…`）。报告 SHA 与实际抽取字节一致。
- 去掉携带字节的 info（`dataclasses.replace(info, pdf_bytes=None)`）再抽取：拒收，`PdfInputError`，`reason == "SHA_MISMATCH"`。
- CLI 层（在 `cli.extract_pdf` 入口处注入换文件，复现 R1 的“验证后替换”窗口）：`analyze` 返回码 2，`INPUT ERROR: [SHA_MISMATCH] PDF changed between verification and extraction…`，且 `report.json` 未写出。
- 无换文件对照：`analyze` 返回码 0，`report.json` 的 `document.sha256` 等于原 PDF 的 SHA。

**回归测试。** `tests/integration/test_toctou.py` 9 测试已读：含 `test_cli_rejects_swapped_pdf_same_size_same_pages`（正是 GPT 的同尺寸同页调换复现）、`test_extract_pages_uses_verified_bytes_after_swap`、`test_extract_pages_without_carried_bytes_rejects_swapped_file`；全量 pytest 754/754 中包含它们（见 §7）。

---

## 2. P1-R1-02 UNLOCATABLE 错归因 — CLOSED

**修复机制（读码确认）。** `src/pagetrace/compare_stages.py:434–480`：引用在文本层找不到时，先由 `_unlocatable_reason`（compare_stages.py:961 起）定原因；仅 `IMAGE_ONLY` / `EMPTY`（锚点页确实无文本层）才归因 extraction；`NO_EXACT_MATCH` / `NO_TEXT_LAYER` 时，只有当 bundle 的抽取记录与诚实抽取**可证不同**才归因 extraction，否则 `first_fault_stage = None`、`expected_source_pages0 = None`，并在 notes 中明言锚点页不是已确认来源页。`tests/oracle/attribute.py:20–26` 的 Oracle 规则已同步改写（近似引用 `first_fault_stage` 为 `None`，注释注明 FIX-R1 P1-R1-02），不再与生产共用错误规则。

**夹具核对（un-ext-09..12）。** 4 份 spec 的 `expected` 与顶层 `first_fault_stage` 均为 `null`，`expected_source_pages0` 为 `null`，`fault_citation.claimed_page0` 为 `null`；Golden（`fixtures/golden/expected.json` 的 `cases[]` 与 S0 报告的 `golden_fault`）与 Oracle（S0 报告的 `oracle_fault`）三方一致：`first_fault_stage: null`，`reason: NO_EXACT_MATCH`。12 个 UN 案例的 reason 仍为 4/4/4（IMAGE_ONLY ×4：un-ext-01..04；EMPTY ×4：un-ext-05..08；NO_EXACT_MATCH ×4：un-ext-09..12）。

**冻结规格 §8.1 核对（`01_project_book/PROJECT_BOOK.md:325`：12 组 UN“均含扫描件式图像页或无文本层页面”）。** 逐组查 spec 的 `pages[].kind`：

| 案例 | 页数 | 非 TEXT 页 | 备注 |
|---|---|---|---|
| un-ext-09 | 5 | p0 blank | 控制引用在 p4，未触碰 |
| un-ext-10 | 6 | p2 image | 控制引用在 p4–p5，未触碰 |
| un-ext-11 | 7 | p1 blank | 控制引用在 p0，未触碰 |
| un-ext-12 | 8 | p6 blank | 控制引用在 p0–p1，未触碰 |

12 组 UN 现全部符合 §8.1 字面要求——R1 指出 un-ext-12 原为“8 页全 TEXT”是本轮再生时修正的（旧版 8 页全 TEXT，新版 p6 为 blank）。4 组近似引用的锚点页（fault `true_source_pages0`：09→p2、10→p1、11→p5、12→p5）均为 TEXT 页，符合“近似引用不在无文本页上”的设计。

**48/48 首错阶段是真实定位还是仅与 Golden 一致——抽查 2 组手工定位（只用 pypdf 原始抽取 + 归一化，不用生产定位代码）：**

- **un-ext-09**：PDF SHA 与 spec 一致；5 页中仅 p0 无文本；fault 引用在全部单页及全文拼接中**无精确匹配**；p2 上的近似句与 fault 引用仅 1 字不同（`正文` vs `原文`，位置 26，`difflib` opcodes 为单字 replace，相似度 0.9655）；控制引用精确匹配仅在 p4。结论：`FAIL_UNLOCATABLE` + `first_fault_stage null` + `NO_EXACT_MATCH` 属实，p2 不是已确认来源页。
- **un-ext-12**：PDF SHA 与 spec 一致；8 页中仅 p6 无文本；fault 引用在全部单页及全文拼接中无精确匹配；p5 上的近似句同样仅 1 字不同（`正文` vs `原文`，位置 26）；控制引用为跨页长句，前半句在 p0、后半句在 p1（两半拼接后与控制引用逐字相等；直接拼接失败是因为两半之间隔着页脚“第 1 页 / 共 8 页”，定位器处理跨页时去页脚——S0 控制 PASS 与此一致）。结论同上属实。

因此 S0 的 48/48 不是空洞的“与 Golden 一致”：Golden 本身按 PROJECT_BOOK §8.2 由独立审查从 spec 手工核对（非生产生成），Oracle 用独立的 pdfminer 路径复核（parity 96/96），再加上本次 2 组手工定位抽查均独立证实了语义。剩余 10 组 UN 的 IMAGE_ONLY/EMPTY 归因是可证的（锚点页确实无文本层，见上表及 S0 报告 `oracle_fault.reason`），未再逐组手工抽查——如实记录抽查范围。

**回归测试。** `tests/unit/test_unlocatable_attribution.py` 19 测试已读：含 `test_un_ext_12_reproduces_gpt_findings`、`test_near_miss_cases_have_no_attributable_stage[un-ext-09..12]`、`test_unlocatable_reasons_still_split_4_4_4`、`test_tampered_anchor_extraction_still_blames_extraction`（锚点抽取记录被篡改时仍归因 extraction，证明新规则不是“一律不归因”）。

---

## 3. P1-R1-03 clean 误删无关目录 — CLOSED

**修复机制（读码确认）。** `src/pagetrace/cli.py:585` `_is_pagetrace_output_dir` 现要求**自洽的工具自写输出**二者居其一：`_is_verified_report_output`（cli.py:374 起）要求 `report.json` 的派生统计与 `summary` 一致、内嵌 `report.html` 的 `<script id="report-data">` 与 `report.json` 的 `schema`/`tool`/`case_id`/`document.file_name` 逐项一致、且 `assets/report.css` 与 `assets/report.js` 存在；`_is_verified_s0_output`（cli.py:504 起）要求 `S0_REPORT.json` 的 `format`/`project`/`s0_result`/`suite.case_count == 48`、全部 `counts` 与 `gates` 对应值相等、`replay.hashes` 为 64-hex 且长度等于 `suite.repeat`、唯一哈希计数一致，且 `replay-hashes.txt` 逐行等于这些哈希。裸 `report.html`、任意 `S0_REPORT.json`、仅 schema 的 `report.json` 均不通过。`cmd_clean`（cli.py:598 起）先打印目标、再做受保护路径检查、再做 marker 检查，不通过即 `INPUT ERROR … refusing to clean …`，不删除。

**亲手复现（按 R1 步骤）。** 新建无关目录 `unrelated-report-folder`，内含 `keep.txt`（内容 `do not delete`）+ 仿冒 `report.html` + 仿冒 `S0_REPORT.json`（`{"format": "pagetrace.s0-report/v1", "fake": true}`），执行 `clean`：

- 返回码 2，输出 `INPUT ERROR: refusing to clean …: not a verified PageTrace output directory (no self-consistent report.json + report.html with matching normalized_result_sha256, and no self-consistent S0_REPORT.json + replay-hashes.txt; …)`；
- 目录与三个文件**完整保留**，`keep.txt` 内容逐字不变。
- 正向对照：真实 `analyze` 输出目录先 `--dry-run`（返回码 0，仅预览不删除），再 `clean`（返回码 0，目录已删除）。标记能防误删，也未把真输出锁死。

**回归测试。** `tests/integration/test_cli.py` 中 13 个 clean 相关测试（冻结报告所称，含 `test_clean_refuses_unrelated_report_html_directory`、`test_clean_refuses_arbitrary_s0_report_json`、`test_clean_refuses_schema_only_report_json`、`test_clean_refuses_tampered_report_json/hash`）随全量 pytest 通过。

已知残留（非新发现）：clean 标记无签名，只能防误删，不能防故意伪造——冻结报告 §4 已如实记录。

---

## 4. P1-R1-04 报告泄露绝对路径 — CLOSED

**修复机制（读码确认，双层）。** Schema 层：`contracts/pagetrace.bundle.v1.schema.json` 的 `document.file_name` 现有 `pattern: ^(?![A-Za-z]:)(?!\.{1,2}$)[^/\\]+$`（拒绝 `/`、`\`、盘符开头、`..`/`.`）。Runtime 层：`src/pagetrace/trace_bundle.py:115` `is_bare_file_name`（同规则 + 拒绝空串、非字符串、控制字符）+ `TraceBundle.__init__` 的 R-11 预检（trace_bundle.py:158–172，在 schema 层之前拒绝）+ `_runtime_errors` 的二次检查（trace_bundle.py:205–217）；错误信息只写规则不回显原值，且 `_redact_file_name`（trace_bundle.py:129–137）会把 schema 错误文本里可能出现的原值替换为 `[redacted file_name]`。

**亲手复现。** 取真实 bundle `fixtures/bundles/un-ext-12.trace.json`，只改 `document.file_name`，跑 `validate`，7 种形式全部返回码 2 且输出中**不含原路径字符串**：

| 形式 | 值 | 结果 |
|---|---|---|
| POSIX（R1 复现原值） | `/home/alice/private/contracts/secret.pdf` | 拒收，exit 2，无回显 |
| Windows 盘符反斜杠 | `C:\x\y.pdf` | 拒收，exit 2，无回显 |
| Windows 盘符正斜杠 | `C:/x/y.pdf` | 拒收，exit 2，无回显 |
| UNC 反斜杠 | `\\server\share\secret.pdf` | 拒收，exit 2，无回显 |
| UNC 正斜杠 | `//server/share/secret.pdf` | 拒收，exit 2，无回显 |
| 相对目录 | `sub/secret.pdf` | 拒收，exit 2，无回显 |
| 父目录 | `../secret.pdf` | 拒收，exit 2，无回显 |

错误文本均为 `INPUT ERROR: …: document.file_name must be a bare file name (no directory, no absolute path)`。正向对照：裸名 `un-ext-12.pdf` 的同一 bundle `validate` 返回码 0（VALID）。

**回归测试。** `tests/unit/test_file_name_paths.py` 66 测试已读：15 种路径形式 × 3 层（裸名判定、bundle 解析、schema 层），另含 `test_cli_validate_gpt_repro_without_leak`（正是 R1 的 `/home/alice/…` 复现）与 `test_cli_analyze_rejects_absolute_path_without_leak`。

---

## 5. P1-R1-05 证据不完整 — PARTIAL

**已补齐并核实的部分（Drive 文件夹 `FIX_R1_2026-11-17_d0aa21f`，id `16nQDtKj04UC_qHsXzr16BYMq6YfV2U5N`）。** Drive `files list` 返回 25 文件，与索引 FIX-R1 清单逐名一致；我用本地文件逐个算 MD5+大小与 Drive 元数据比对，**25/25 匹配**（含 `S0_REPORT.json` 172,664 B / MD5 `11b0cba6e0f830b89ef86e14d48ce2dc`——该 JSON 用 `files get` 下载会写 0 字节，系 CLI 侧行为，已用 size+md5Checksum 元数据核对代替，与冻结报告所述一致）。另抽查下载 5 文件逐字节核对 MD5：`source-release.zip`、`pytest-fixr1.log`、`license-report.txt`、`REVIEW_PACK_RELEASE_04.md`、`git-diff-011f523-d0aa21f-stat.txt`——**5/5 匹配**。本地 `sha256sum -c 07_evidence/REVIEW_PACKS/RELEASE_REVIEW_SHA256SUMS.txt`：**23/23 OK**。索引本身与校验表本身不自列（避免自指），其 Drive id 与本地哈希在索引末节已注明；索引文件本地 MD5 与 Drive 一致。

逐项核对 R1 列出的缺失项：

| R1 缺失项 | 现在状态 |
|---|---|
| `pytest-t014.log`（831 B） | ❌ **仍不在 Drive**（见下） |
| `s0-release.log`（438 B） | ❌ **仍不在 Drive** |
| `clean-copy-t014.log`（2,743 B） | ❌ **仍不在 Drive** |
| `T013_FIX_RECORD.md` | ✅ 在 Drive（7,168 B，MD5 核对通过） |
| T012 审查报告及审查包（`T012_REVIEW.md` + `REVIEW_PACK_01/02.md`） | ✅ 在 Drive（MD5 核对通过） |
| `license-report.txt` | ✅ 在 Drive（3,447 B，MD5 核对通过） |
| `RELEASE_REVIEW_SHA256SUMS.txt` | ✅ 在 Drive（2,486 B，23 文件，本地复核 23/23 OK） |
| T013 基线与 T014 的实际 git-diff 输出 | ⚠️ **部分**：已上传 `git-diff-011f523-d0aa21f`（T014 master → FIX-R1，48 文件 +4645/−475，`diff --git` 行数 48）与 `git-diff-cfc8b94-d0aa21f-frozen-source`（T013 冻结源码 → FIX-R1 冻结源码，35 文件 +1962/−268，`diff --git` 行数 35），stat 尾行与冻结报告一致；但 **T014 本步的 `git-diff-cfc8b94-011f523`（含冻结源码版）未上传**（见下） |
| FIX-R1 新证据（pytest-fixr1.log / s0-fixr1.log / clean-copy-fixr1-release.log） | ✅ 在 Drive（MD5 核对通过）；三份日志内容与本次独立重跑结果一致（754 passed；S0 PASS；clean-copy validate 0 / analyze 1 / SMOKE_PASS） |

**仍缺的证据（新发现，即本次 PARTIAL 的唯一依据）。** Drive 全盘按名检索 `pytest-t014.log` / `s0-release.log` / `clean-copy-t014.log` 返回 0 命中；`04_release` 根目录（id `1Yg5I1ZlMj7297duZcjgEiTMmtX3o44Jz`）清点 13 项（12 个 T014 文件 + FIX_R1 子文件夹），其中无上述 3 份日志、无 T014 git-diff。本地这 5 个文件**确实存在**且内容与 T014 索引所列一致：`07_evidence/runtime_logs/pytest-t014.log`（831 B，`754 passed` 之外的 T014 日志，首行即 pytest 进度）、`s0-release.log`（438 B）、`clean-copy-t014.log`（2,743 B）、`git-diff-cfc8b94-011f523.txt`（301,613 B）及 `-stat.txt`。索引 `RELEASE_REVIEW_INDEX.md` §3 已自认：“草稿曾列入上传清单的三份 T014 日志与 T014 的 git-diff 文件**不在本次上传清单内**（发布任务的上传清单未包含它们），仍待协调员决定是否补传；本次上传的是 FIX-R1 的新日志与新 git-diff 证据。”——因此这不是审查包的疏漏未察，而是上传清单有意未含、决定未下。

**定级说明。** 定为 PARTIAL 而非 OPEN：FIX-R1 当次发布的全部证据（新日志、新 git-diff、T012/T013 记录、license、SHA256SUMS）已齐且 25/25 核对通过；缺的是**历史审计链**——R1 要求用 T014 原始日志与 T014 本步 diff 证明“T014 的 652 测试确实通过、T014 未改 T013 冻结源码”。严格说，已上传的 `cfc8b94..d0aa21f` 冻结源码 diff 在数学上包含了 T014 的改动（T013 基线 → FIX-R1），但它把 T014 与 FIX-R1 的改动混在一起，不能单独证明 T014 本步未动冻结源码；`011f523..d0aa21f` 也只能证明 FIX-R1 相对 T014 master 的改动。GPT R2 极可能沿用 R1 的同一清单追问这 5 个文件。

**关闭条件（建议，不代执行）。** 将本地已有的 5 个文件补传到 Drive（`FIX_R1_2026-11-17_d0aa21f` 子文件夹或 `04_release` 根目录均可，需在索引中注明位置）：`07_evidence/runtime_logs/pytest-t014.log`、`s0-release.log`、`clean-copy-t014.log`、`git-diff-cfc8b94-011f523.txt`、`git-diff-cfc8b94-011f523-frozen-source-stat.txt`（与同名 `-stat` 的 T014 版；本地另有 `git-diff-cfc8b94-011f523-stat.txt`，补传时以本地实际文件为准并在索引中列明字节与 SHA）；随后更新 `RELEASE_REVIEW_INDEX.md` 与 `RELEASE_REVIEW_SHA256SUMS.txt` 并重算校验表。补传后 P1-R1-05 可判 CLOSED。本重审未补传（任务限定只审不改、且不写 Drive）。

---

## 6. 三项 P2 — 全部 CLOSED

- **P2：`run_s0.py` repeat<100 误报 PASS。** `tools/run_s0.py:123` `S0_FULL_REPEAT = 100`，`:135` `return "PASS" if repeat >= S0_FULL_REPEAT else "SMOKE_PASS"`。亲手实测 `--repeat 1`：输出 `S0_RESULT: SMOKE_PASS` + 注明 `smoke run only (1 replay(s)); formal S0 PASS requires --repeat 100`，其余门禁数字仍为 48/48、0 误报、96/96 parity、重放哈希 `a06b87fc…`，退出码 0。clean-copy 中 `--repeat 1` 同样为 SMOKE_PASS（见 §7）。
- **P2：`extract.py` 图片枚举异常误报 EMPTY。** `src/pagetrace/extract.py:60–71` `_page_has_images` 枚举失败返回 `None`（与“无图” `False` 严格区分）；`_extract_one_page` 在空白文本 + 枚举失败时返回 `text_state="ERROR"`（`extracted_text`/`text_sha256` 均为 `None`），不再报 EMPTY。回归测试 `test_image_enum_failure_is_error_not_empty`、`test_image_enum_failure_does_not_mask_real_text`、`test_image_enum_controls_still_classify` 随全量 pytest 通过。
- **P2：clean-copy 不按 lock 安装。** `08_release/HOW_TO_REPRODUCE.md` §4（行 135–142）已改用 `./venv/bin/pip install -r pkg/requirements.lock`，并注明 6 个直接依赖 pin 与 `pyproject.toml` 一致；§4 正文已修正为持久磁盘路径 `~/workspace/tmp-p026-clean-release`（8,139 B，SHA `23caf863…`，与任务所述一致）。本次 clean-copy 即按此步骤安装（见 §7）：`pip install` 退出 0，版本 `pypdf 7.1.0`、`pdfminer.six 20260107`、`jsonschema 4.26.0`、`pytest 9.2.0` 与锁文件一致。

---

## 7. 独立重跑门禁与 clean-copy（亲自执行）

环境：`04_source/source` 现有 `.venv`，Python 3.12.3，`PYTHONPATH=src`，`TMPDIR=~/workspace/tmp-p026-rereview`。工作树未改动（重跑前后 `git status` 为空）。

| 门禁 | 本次实测结果 | 与冻结报告对照 |
|---|---|---|
| 全量 pytest | **754 passed，0 failed，136.25 s，退出 0**（日志 `~/workspace/tmp-p026-rereview/pytest-rereview.log`） | 与冻结报告 754/754 一致（首轮 99.95 s、F2 106.09 s；本次 136.25 s 为机器负载差异，非失败） |
| S0 `--repeat 100` | **PASS，退出 0**：检出 48/48（四类各 12），首错阶段 48/48，控制误报 0，parity 96/96，100 次重放 1 个唯一哈希 `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`，Golden 0 不匹配，golden_sha256 `9db9b16e…`（日志 `s0-repeat100.log`，报告 `s0-repeat100/S0_REPORT.json`） | 与冻结 `05_tests/s0-release/S0_REPORT.json` 逐字段比对：`counts`、`gates`、`replay`、`suite`、`per_case`、`input_hashes` 全部相同；`replay-hashes.txt` 100 行逐字节相同。唯一差异是 `base_commit`：本次为 `04cefb3…`（我在已合并的 master 工作树上跑），冻结版为 `8cfd7dc…`——内容相同，此差异是运行位置所致，不构成 findings。本次重跑消除了已知残留“S0 --repeat 100 本轮由协调员重跑、F2 未独立重跑”。 |
| S0 `--repeat 1`（P2 验证） | **SMOKE_PASS**，退出 0，同一重放哈希 `a06b87fc…` | 见 §6 |
| clean-copy（全新目录 + fresh venv + lock 安装） | `unzip` 255 条目；`pip install -r pkg/requirements.lock` 退出 0；`pip install -e ./pkg --no-deps` 退出 0；`validate` 退出 0（`document hash: MATCH`）；`analyze` 退出 1（预期，verdicts `FAIL_PAGE_OFFSET` + `PASS`）；`s0 --repeat 1` **SMOKE_PASS**，退出 0，同一重放哈希 `a06b87fc…`（目录 `~/workspace/tmp-p026-rereview/clean-copy`） | 与冻结报告及 HOWTO §4 预期输出逐项一致 |

---

## 8. ZIP ↔ 冻结 git 树一致性与确定性 — 均通过

- **ZIP ↔ manifest**：发布包与 `04_source/SOURCE_MANIFEST.csv` 逐文件 SHA + 大小 255/255 一致（冻结报告已核，本次下载的 ZIP 与本地 MD5 一致，见 §5）。
- **ZIP ↔ 冻结 git 树（`8cfd7dc`）**：逐文件比对（`git hash-object` 对照 blob SHA）：**0 内容不匹配，0 多余条目**；唯一缺失为 `.gitignore`（构建脚本明确排除，git 树 256 文件 vs ZIP 255 文件）；全部条目时间戳 1980-01-01、权限 0o644；无 `__pycache__` / `*.pyc` / `.venv` / `egg-info` 条目。
- **确定性重建**：用 `git archive 8cfd7dc 04_source/source` 解到全新目录，跑构建脚本 `07_evidence/runtime_logs/fixr1-build-release.py`（脚本本身只读源树、只写重建目录，未碰发布文件）：重建包 **255 文件、1,148,388 B、SHA-256 `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b`**，manifest SHA `b6db053e…fcc33f`——与发布包**字节级完全相同**。
- **两步冻结核对**：`git diff d0aa21f..8cfd7dc --stat` 仅 4 文件（冻结源码内只改 `04_source/source/README.md` 一行重放哈希 `5195fc9a…` → `a06b87fc…`，其余为 `08_release/` 三文档）；`5195fc9a` 在 `README.md` 与 `08_release/` 三文档中零命中，`a06b87fc` 出现次数为 1/1/1/2，与冻结报告一致。

---

## 9. 新发现（除 §5 外）与已知残留确认

**新发现（按分级）：**

- **P1（未闭合项，即 §5 的内容，不另立项）：** P1-R1-05 PARTIAL——3 份 T014 日志 + T014 本步 git-diff 仍不在 Drive。关闭条件见 §5 末。
- **P0：无。P2：无。** 4 项代码类 P1 的亲手复现均通过，未发现新代码缺陷；3 项 P2 均已验证关闭。
- **观察（不构成 finding）：** 本次 S0 重跑报告的 `base_commit` 为 `04cefb3`（master 合并提交）而非冻结 `8cfd7dc`，因我在已合并的工作树上运行；除该字段外报告与冻结版逐字段相同、重放哈希文件逐字节相同，不影响结论。

**已知残留逐项确认（任务所列，如实记录，非新发现）：**

- S0 `--repeat 100` 本轮 F2 未独立重跑——**已由本次亲自重跑消除**（§7）。
- Windows / macOS **NOT_TESTED**（仅 Linux x86_64 + CPython 3.12.3 实测）。
- S0 只覆盖 48 个冻结合成夹具，不证明真实 PDF 流水线。
- clean 标记无签名，只能防误删不能防故意伪造。
- HOWTO §4 正文已修正为持久磁盘路径；旧路径 `/tmp/fixr1-clean` 仅出现在**未上传的旧日志** `07_evidence/runtime_logs/clean-copy-fixr1.log`（第 2、43–44、75 行，2026-11-17 ~03:50–03:52 UTC 的历史记录）中，发布版 `clean-copy-fixr1-release.log` 内无此路径——与任务所述一致，日志是历史记录，不改。

---

## 10. 亲自跑过的命令与结果摘要

（工作目录 `~/workspace/p026-pagetrace`；源码操作目录 `04_source/source`；`.venv` Python 3.12.3；`TMPDIR=~/workspace/tmp-p026-rereview`）

1. `git log --oneline -8` / `git status --short`：master `04cefb3`，工作树干净（重跑前后均为空）。
2. 全量 pytest：`TMPDIR=… PYTHONPATH=src .venv/bin/python -m pytest -q` → **754 passed，136.25 s，退出 0**。
3. 独立复现脚本 `~/workspace/tmp-p026-rereview/repro.py`（自建同尺寸同页 PDF、仿冒 clean 目录、7 种 `file_name` 形式）：P1-01 换文件后抽取仍为原内容、去字节 info 报 `SHA_MISMATCH`、CLI 换文件 `analyze` 退出 2 且无报告、干净对照退出 0 且 SHA 一致；P1-03 仿冒目录 `clean` 退出 2 且三文件完整保留、真输出目录 `--dry-run` 0 / `clean` 0 且删除；P1-04 七种路径 `validate` 全部退出 2 且无原值回显、裸名对照退出 0。脚本退出 0。
4. UN 手工抽查（pypdf 原始抽取 + `difflib`）：un-ext-09 / un-ext-12 的 fault 引用全文档无精确匹配、近似句仅 1 字不同（`正文` vs `原文`，位置 26）、控制引用定位正确（09 在 p4；12 前半在 p0、后半在 p1）；12 组 UN 的非 TEXT 页与 §8.1 逐组核对通过；Golden/Oracle/S0 三方 `first_fault_stage null` + `NO_EXACT_MATCH` 一致。
5. S0：`tools/run_s0.py --repeat 100` → **PASS，退出 0**，100 次重放 1 哈希 `a06b87fc…`，与冻结报告逐字段一致（仅 `base_commit` 不同）；`--repeat 1` → **SMOKE_PASS**。
6. Clean-copy：`unzip` ZIP → `python3 -m venv` → `pip install -r pkg/requirements.lock`（退出 0；pypdf 7.1.0 / pdfminer.six 20260107 / jsonschema 4.26.0 / pytest 9.2.0）→ `validate` 退出 0（MATCH）→ `analyze` 退出 1（`FAIL_PAGE_OFFSET` + `PASS`）→ `s0 --repeat 1` SMOKE_PASS，同一哈希。
7. ZIP 一致性：ZIP 内 255 文件与 `8cfd7dc` git 树逐文件 SHA 比对 **0 不匹配**（仅 `.gitignore` 未打包）；`git archive 8cfd7dc` 重建 SHA **与发布包完全相同**（`7526f511…`）；`sha256sum -c 07_evidence/REVIEW_PACKS/RELEASE_REVIEW_SHA256SUMS.txt` **23/23 OK**。
8. Drive：`hatch_gws_cli drive files list`（FIX_R1 文件夹）25 文件；本地 MD5+大小与 Drive 元数据 **25/25 匹配**；下载抽查 5 文件 **5/5 字节+MD5 匹配**（另确认 `S0_REPORT.json` 下载写 0 字节为 CLI 已知行为，已用元数据核对）；全盘按名检索 3 份 T014 日志 **0 命中**；`04_release` 根目录清点 13 项，无 T014 日志与 T014 git-diff。

---

## 结论与建议

FIX-R1 的代码修复是实的：4 项代码类 P1 我按 GPT 的复现步骤亲手重做了一遍，全部拒绝/拦截如预期，回归测试齐全；3 项 P2 全部验证关闭；门禁（754 测试、S0 100 次重放）与发布包（ZIP 一致性、确定性重建）我独立重跑重建了一遍，与冻结报告逐项相符。**唯一的未闭合项是 P1-R1-05 的历史证据缺口**：3 份 T014 原始日志与 T014 本步 git-diff 仍不在 Drive 上——文件本地都有，索引也自认未上传、待协调员决定。建议协调员把这 5 个本地文件补传到 Drive 并更新索引与校验表，之后 P1-R1-05 可判 CLOSED、总体可转 PASS，再提交 GPT R2。除此之外，本次重审未发现任何应阻止提交 R2 的新问题。
