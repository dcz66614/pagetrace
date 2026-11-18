# 变更日志（CHANGELOG.md）

## 2026-11-16 ~23:40 GMT — 仓库初始化

- 新建 git 仓库 `~/workspace/p026-pagetrace/`，按 IMPLEMENTATION_PLAN.md §4 布局脚手架。
- 复制规格：`01_project_book/PROJECT_BOOK.md`（38,889 B，SHA-256 `735aa0b8…`）、`02_implementation_plan/IMPLEMENTATION_PLAN.md`（40,718 B，SHA-256 `2e5b16bb…`），与 Drive 下载副本一致。
- 生成任务卡 `03_tasks/TASK-001.md` … `TASK-014.md`。
- 控制文件：PROJECT_STATE.json、TASKBOARD.csv、DECISIONS.md、HANDOFF.md、ENVIRONMENT.md。
- 基线 commit：91002857021446030b86000068cde21fd3bc1ac4
- T001 已派发。

## 2026-11-16 ~23:52 GMT — T001 PASS（已合并）

- 任务 commit `a11836d`，合并 commit `809a624`（--no-ff，分支已删）。
- 协调员亲自核验：重跑三条验收命令（pytest 47 passed exit 0；两个 schema json.tool OK）；Draft 2020-12 check_schema 双通过；schema 功能探针：UNKNOWN+viewer→拒绝、viewer 0→拒绝、裸 page→拒绝；page_count 越界为文档化运行时强制（R-05，测试覆盖）；F-01–F-16、R-01–R-10、8 个可复算示例均在场；requirements.lock 精确锁定（pypdf 7.1.0、reportlab 5.1.0、Pillow 13.0.0、pdfminer.six 20260107、pytest 9.2.0、jsonschema 4.26.0）；diff 仅含允许路径 + 证据日志，无禁止路径改动。
- 遗留 P2：Pillow 许可证——已装包 METADATA 为 MIT-CMU，计划 §10.2 称 HPND/PIL License；lock 已如实记录，留待 T013 按上游 LICENSE 文件复核。
- 备注：子 agent 运行中有一条 exec 报 exit 128（原因未明，应为 git 侧小故障），交付物完整且已核验，无影响。
- T002 已派发。

## 2026-11-17 ~00:05 GMT — T002 PASS（已合并）

- 任务 commit `8308042`，合并 commit `10fd49e`（--no-ff，分支已删）。
- 协调员亲自核验：重跑生成器（exit 0），144 个文件与提交版字节一致（0 不匹配）；sha256sums.txt 48 行全对；pytest tests/unit/ 54 passed；48/48 bundle 独立 schema 校验通过；类别 12/12/12/12，阶段矩阵与 PROJECT_BOOK §8.1 完全一致；控制引用 48/48；expected verdict 各 12 且与 fault_type/stage 48/48 一致；覆盖：中文 48/48、空白页 24、图像页 16、跨页 18（split_pages0）、5 种 label 方案、重复句 ≥12（独立检查 43 份含跨页重复句，manifest 的 24 为较窄定义，要求已满足）。
- PDF 地面实况抽查（pypdf）：中文抽取正常、图像页抽取为空、空白页为空、page label 可读、控制引文可定位；36/36 可定位故障引文在其真值页上找到，12/12 UNLOCATABLE 引文正确地不在文本层中。
- mm-display 的"1/3"疑点已澄清：3 例用三种有文档记录的变体（record-absent / value-null / viewer-null），非缺陷；T004/T006 须覆盖全部三种。
- 备注：子 agent 运行中有一次 exec exit 1 与一次 SIGTERM kill（开发中途失败），最终态已核验干净，无影响。
- T003 已派发。

## 2026-11-17 ~00:12 GMT — T003 PASS（已合并）

- 任务 commit `5c195cb`，合并 commit `a6111f1`（--no-ff，分支已删）。
- 协调员亲自核验：重跑验收命令（test_extract + test_locate 34 passed；全量 tests/unit/ 88 passed）；证据：extraction 48 例/312 页记录，页数/hash 与 manifest 及 pypdf reader 48/48 一致；locate 故障 48/48、控制 48/48、跨页 18、UN 0 候选 12；9 种异常输入全部受控 PdfInputError；独立抽取复算（3 例）与证据一致，text_sha256 == 规范化文本 SHA-256（空页为 null）；定位器直调：du-chk-01 → [2,4]、un-ext-01 → []、控制 [4]，均与 spec 一致。
- 6 组 extraction 阶段故障 bundle 与诚实抽取的差异已独立证实（po-ext-01..03 各 2 页 hash 互换；mm-ext-01 第 2 页记 ERROR 且无 hash；mm-ext-02 第 1 页缺 hash；mm-ext-03 缺第 4 页记录）；其余 42 组 bundle 与诚实抽取 42/42 一致——正是 T004 要检测的差异。
- 遗留 P2（双包问题）：顶层 `pagetrace/`（T001 stub）与 `src/pagetrace/`（生产包）并存；pyproject 仍为 `packages = ["pagetrace"]`（装 stub），测试用 sys.path.insert(0, src) 导入生产包。S0 不阻塞（测试与证据均有效），但 T007 的 S0 runner 与 T009 的 CLI 必须面对导入路径问题；留待 T013 统一打包布局。
- 备注：子 agent 运行中有一次 exec exit 1（开发中途失败），最终态已核验干净，无影响。
- T004 已派发。

## 2026-11-17 ~00:26 GMT — T004 PASS（已合并）

- 任务 commit `48ed273`，合并 commit `a9c32d0`（--no-ff，分支已删）。
- 协调员亲自核验：重跑验收命令（test_verdicts 156 passed；全量 tests/unit/ 244 passed，无回归）；证据 t004-stage-diffs.json：四类 verdict 各 12、fault_type 与 spec 预期 48/48、first stage 48/48、控制 PASS 48/48；extraction_differing 恰为已知的 6 组（含 hash 互换的上下游值、ERROR 态、缺 hash、缺记录）；96 条 verdict dict 以完整报告文档形式通过 pagetrace.report/v1 schema 校验（0 无效）；设计裁决已写入 compare_stages.py docstring（重复文本无强制选页→AMBIGUOUS；跨页 display 值落在 span 内即接受；UNKNOWN basis 首错记 display）。
- P2 已确认（UNLOCATABLE 4/4/4）：子 agent 指出任务书措辞与夹具实测不符——核验属实：12 组 UN 为 image-only-page ×4 / blank-page ×4 / near-miss-quote ×4；实现按三者分别归因（IMAGE_ONLY / EMPTY / NO_EXACT_MATCH），first stage 均为 extraction，notes 明确"不代表原文不存在"，测试中断言 4/4/4。另注意：un-ext-12（near-miss，8 页全为 text）不含图像页或空白页，与 PROJECT_BOOK §8.1"12 组均含扫描件式图像页或无文本层页面"的字面表述有 1 组偏差；行为本身正确（文本层找不到该引文），不阻塞，T006 的 Golden 须按同一 4/4/4 记录。
- 备注：子 agent 回报中回退命令写 "git checkout main"，实际默认分支为 master，仅为文字笔误，无影响。
- T005 已派发。

## 2026-11-17 ~00:34 GMT — T005 PASS（已合并）

- 任务 commit `039eb93`，合并 commit `75e4c53`（--no-ff，分支已删）。
- 协调员亲自核验：重跑验收命令（tests/prototypes 10 passed；node --check OK）；grep 确认原型无外部网络引用；亲自目视 3 张截图（po-ext-01、un-ext-01、1280px）：四栏齐全、选中行联动高亮、错误页码+首错阶段+正确来源位置同时可见、对照表与 stage diffs 齐全；FAIL 红、FAIL_AMBIGUOUS/FAIL_UNLOCATABLE 琥珀（非绿）、PASS 绿；1280px 四栏仍可读；UNLOCATABLE 的正确来源页显示为琥珀"无可确认的正确来源页"。
- 嵌入数据与 T004 证据一致（4 例 verdict/首错阶段、mm-ext-01 的 ERROR、du-chk-01 候选 [2,4] 均在场）；build_prototype_data.py --check 重建字节一致（确定性）。
- 浏览器：Playwright 缓存 headless shell，Chrome for Testing 158.0.8127.18，真实截图；/opt/meta-chromium/chrome 无法独立启动（已知限制，已如实记录）。
- 施工中已修复 3 处呈现问题（窄表截断、UNLOCATABLE 误绿、差异 tag 截断）；1400px 下个别长表头换行属可接受原型形态。
- 备注：子 agent 运行中有一次 SIGTERM kill（应为清理截图/服务进程），最终态已核验干净，无影响。
- T006 已派发。

## 2026-11-17 ~00:47 GMT — T006 PASS（已合并）

- 任务 commit `08af05d`，合并 commit `b8b0587`（--no-ff，分支已删）。
- 协调员亲自核验：重跑验收命令（oracle + parity 24 passed；tests/unit 回归 244 passed）；grep + AST import 图确认 Oracle 只 import stdlib + pdfminer + 相对模块，无 pagetrace/pypdf/src；Golden SHA 与汇报一致（417e3ed3…）；**亲自运行 Oracle 全 48 组：与 Golden 0 差异、与 spec.expected 0 差异、与 T004 0 差异**；抽取差异恰为已知的 6 组，其余 0；UN 4/4/4 已记入 Golden（IMAGE_ONLY 4 / EMPTY 4 / NO_EXACT_MATCH 4），控制 PASS 48/48；审计表 spec_agrees 48/48、t004_production_agrees 48/48、discrepancies []。
- "·" 单字形修复已亲自读码核验：作用域仅限单次 U+00B7 插入/替换，先精确匹配、失败才尝试修复，每次使用均记录；对照日志证明 312 页中仅 31 页（全为页 0 标题行）因此差异、0 引文含 "·"；30 处修复均在审计表登记（全为页 0）；po-ext-02 页 0（真实换页）修复无法通过、仍被正确判定为抽取错位。属有文档记录的工具 quirks 处理，非缺陷。
- 定位算法确为独立实现：Oracle 用最大前缀/后缀二分覆盖，生产用枚举切分点。
- 备注：子 agent 运行中有 4 次 exec exit 1（开发中途发现并修复 2 个测试 bug：parity 误传 PdfDocumentInfo、triple 探针中段边界空格），最终态已核验干净，无影响。
- T007 已派发（S0 门禁）。

## 2026-11-17 ~01:11 GMT — T007 PASS（已合并）—— S0_RESULT: PASS

- 任务 commit `ed550d0`，合并 commit `7455ddf`（--no-ff，分支已删）。
- 交付：`04_source/source/tools/run_s0.py`（721 行，S0 runner：生产+Oracle 全 48 组、控制引用、8 门判定、100 次规范化重放、S0 报告与哈希清单生成；退出码 0/2/3/4）、`tests/s0/conftest.py` + `test_run_s0.py`（9 测试）、`05_tests/s0/S0_REPORT.json`（169,431 B）+ `replay-hashes.txt`（100 行，唯一 hash 5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8）、验收日志 2 份。
- S0 门：检出 48/48（每类 12/12）、first stage 48/48、控制误报 0、parity 96/96 引用（576/576 字段比较，0 不匹配）、重放 100 次 1 哈希、uncertainty 违规 0、Golden 全字段不匹配 0；另有支撑门 golden_agreement（已披露，更严非更松，接受）。
- 协调员亲自核验：diff 仅 7 个 T007 专属文件；报告逐项复算全符；148 fixture 哈希 + Golden SHA + lock SHA + 48 PDF SHA 全部重算一致；**亲自重跑完整验收**（tests/s0 9/9、全量 pytest 287/287、run_s0 --repeat 100 退出 0），重放 hash 与提交版相同；与提交版报告唯一差异为 base_commit 字段（子 agent 在 5095c37 上跑验收；我方在 ed550d0 上重跑），其余内容字节一致，已恢复提交版报告再合并。合入后 tests/s0 9/9 PASS。
- 规范化哈希覆盖生产与 Oracle 双臂的 verdict/故障类别/阶段/候选页/页码转换与证据字段，排除墙钟/耗时/绝对路径/主机名/UUID；报告不含时间戳与绝对路径（已核查无 /home/ 泄露）。
- 未修改生产算法、Golden、夹具、规格与冻结文件；未上传 GitHub、未对外发布。
- S1 已启动：T008 与 T010 并行派发（不同 worktree，基线 7455ddf）。

## 2026-11-17 ~01:25 GMT — T008 PASS（已合并）

- 任务 commit `09f6fc3`，合并 commit `1a5e0fb`（--no-ff，分支已删，worktree 已移除）。
- 交付：`src/pagetrace/report_html.py`（617 行：四栏视图模型构建器，读 pagetrace.report/v1 结果、不重算 verdict、不猜页码；确定性渲染器 render_html / write_report）、`src/pagetrace/assets/report.css`（158 行，§9.3 四色徽章，4→2→1 栏响应式）、`assets/report.js`（361 行，重写结构：四栏同步、点击同步高亮、故障类型/首错阶段/状态过滤、对照表、深链 #case=、下载/复制 JSON；零网络请求）、`tests/integration/test_html_report.py`（14 测试）。
- 证据：demo 报告 5 条引用（4 类故障各 1 例 + 1 控制）`07_evidence/t008-report/report.html`（20,781 B，sha 9f69974f…）；全量报告 96 条引用 `07_evidence/t008-report-full/report.html`（298,026 B，sha e65c2620…）；截图 3 张（桌面 1280x900、窄屏 390x844、深链 du-chk-01）；离线日志 `t008-netlog.json`（7 事件、0 URL）；DNS 全阻断重渲染 exit 0，深链仍正确选中。
- 协调员亲自核验：diff 仅 15 个 T008 专属文件（无禁区改动）；重跑验收 14/14、全量 pytest 301/301（287 基线 + 14 新增，零回归）；亲自目视桌面与窄屏截图（四栏齐全、FAIL 红/AMBIGUOUS 琥珀/PASS 绿、1280px 可读、窄屏堆叠可读）；netlog 7 事件 0 http URL、report.html 含 0 个 http；demo 5 条与 Golden 逐项核对 5/5 一致，全量 96 条 verdict 分布 48 PASS / 12×4 FAIL；读码确认渲染器只读 verdict、不重算、不猜页码；报告哈希与汇报一致。
- 更正：子 agent 交接中 NEXT_TASKS_READY 称“T009 依赖 T008”有误——按 TASKBOARD，T009 依赖 T010，与 T008 无关；不影响本次交付，已记录。另子 agent 执行中曾有 1 次 exec exit 1（中间步骤），最终态全绿，无影响。
- T010 仍在进行中（独立 worktree，分支 task/t010）。

## 2026-11-17 ~01:26 GMT — T010 PASS（已合并）

- 任务 commit `6780aa3`，合并 commit `d9934a2`（--no-ff，分支已删，worktree 已移除）。
- 交付：`src/pagetrace/contracts.py`（413 行：加载 T001 冻结 schema 原样不改语义；`validate_bundle_schema` / `validate_report_schema`；T001 冻结页码纯函数；`FIELD_MAPPING` 27 项；`UNKNOWN_FIELD_POLICY = "reject"`）、`src/pagetrace/trace_bundle.py`（565 行：`TraceBundle` 解析器，schema 层 + 运行时跨字段层两层校验，原始值深拷贝保留、永不隐式转换，`missing_stages`/`present_stages`/`empty_stages` 显式区分，`verify_document_hash(_file)` 比对真实 PDF 字节）、`tests/unit/test_bundle.py`（291 测试）、53 个 fixture（9 合法 + 44 非法）、字段映射表 `07_evidence/T010-field-mapping.md`。
- 协调员亲自核验：diff 仅 59 个 T010 专属文件（schema/docs 原封未动，无禁区改动）；重跑验收 291/291、全量单元 535/535、全量 tests 578/578（工作树内，287 基线 + 291 新增）；**独立抽查**：48/48 份 T002 bundle 解析通过且 document.sha256 与真实 PDF 字节一致；44/44 非法 fixture 被拒且带非空 `.errors`；9/9 合法变体通过；故障数据正确接受并暴露（mm-chk-05 悬空 chunk、mm-idx-08 悬空 index、mm-dsp-10 缺 display 记录、mm-ext-03 缺第 4 页抽取记录）；null 值原样保留（mm-dsp-11 display value null、po-dsp-10 错位值 1 原样保留，均未默认成 0）。
- T001 函数核验：6/7 字节一致；`resolve_citation_to_index0` 的 None 守卫已审查——不改变任何输入的结果（同抛错、同异常类），仅消息文本不同，接受（见 DECISIONS.md）。
- 合入后全量 pytest 592/592（301 + 291，T008 与 T010 无交互回归）。
- T009 已派发（CLI，依赖 T010 已满足）。

## 2026-11-17 ~01:40 GMT — T009 PASS（已合并）

- 任务 commit `3df5f6c`，合并 commit `a6bc9c8`（--no-ff，分支已删，worktree 已移除）。
- 交付：`src/pagetrace/cli.py`（490 行：analyze/validate/s0/clean 薄封装；退出码按 §12.2：0 成功、1 分析完成含 FAIL/UNKNOWN、2 输入无效、3 内部错误、4 S0 门禁失败；hash 校验走 T010；HTML 走 T008；`--include-snippets` 控制引文全文；缺阶段快照输出 UNKNOWN_TRACE_MISSING 且 first_fault_stage 为 null；clean 先打印 TARGET、仅删带标记目录、拒受保护路径）、`tests/integration/test_cli.py`（22 测试）、`docs/CLI.md`（177 行：调用方式、命令参数表、退出码表、输出清单、clean 安全规则、snippets 政策）。
- 协调员亲自核验：diff 仅 6 个 T009 专属文件（核心算法/UI/Golden/Oracle 未动）；重跑验收 test_cli 22/22、全量 tests 614/614（592 基线 + 22 新增）；**亲自跑 CLI**：help 0、validate 正常 0、hash 不符 2（INPUT_HASH_MISMATCH）、analyze 故障用例 1（两次运行归一化 hash 相同 41c788da…，与汇报一致；summary PASS 1 / FAIL 1；无 generated_at）、clean dry-run 0 + 真删 0、无标记目录拒绝 exit 2、缺 --trace 参数 exit 2、s0 --repeat 1 exit 0；**缺阶段 UNKNOWN 已复现**（删 display 阶段：exit 1，两引用均为 UNKNOWN_TRACE_MISSING，first_fault_stage null）；**snippets 已用长引文区分验证**（默认截断 40 字 + …，--include-snippets 全文；JSON 报告永不带 quote_text）；report.json 经 venv jsonschema 校验 VALID（我方首次用系统 python 4.10.3 误报 RefResolutionError，系探针解释器用错，非产品问题）；退出码表与 §12.2 原文逐项核对一致。
- 记录：交接中 1 次 exec exit 2 是有意的 hash 不符 validate（按设计返回 2），已解释，无问题。`fixtures build` 未实现见 DECISIONS.md（P2）。
- 合入后全量 pytest 614/614。
- T011 已派发（集成、端到端与隐私回归；T008/T009/T010 全部 PASS，依赖满足）。

## 2026-11-17 ~02:02 GMT — T011 PASS（已合并）

- 任务 commit `5e33a95`，合并 commit `2e7d0f8`（--no-ff，分支已删，worktree 已移除）。
- 交付：`tests/e2e/test_e2e.py`（13 测试）+ `tests/privacy/test_privacy.py`（12 测试）、`05_tests/TEST_PLAN.md`、`05_tests/s0-final/S0_REPORT.json` + `replay-hashes.txt`、`05_tests/test-results/t011-pytest.log`、证据日志与 3 张截图（桌面 1280×2000、窄屏 390×844、全量顶部 1280×2400）+ 单用例与 96 条全量真实报告。
- S0 final：检出 48/48、首错阶段 48/48、控制误报 0、parity 96/96、100 次重放唯一 hash 1 个 = 5195fc9a…，与基线完全一致。
- 协调员亲自核验：diff 仅 21 个 T011 专属文件（Golden/核心算法/生产 UI 未动）；重跑全量 pytest 639/639（614 基线 + 25 新增，零回归、无 skip）；S0 final 与基线报告逐项比对（counts、input_hashes、gates、per_case 全等，仅 base_commit 不同，属预期）；隐私扫描日志 10 个产物 0 泄漏，我方独立扫描的三处嫌疑逐项裁决均为误报（见 DECISIONS.md）；亲自目视桌面与窄屏截图（四栏齐全、对照表“错误页码 p.4 → 首错阶段 抽取 → 正确来源 p.3”、stage diffs、窄屏无横向溢出）。
- T012 已派发（独立只读代码审查；T011 PASS，依赖满足）。

## 2026-11-17 ~03:10 GMT — T014 PASS（已合并）—— 冻结完成

- 任务 commit `62d6e8a`，合并 commit `28ceb72`（--no-ff，分支已删，worktree 已移除）。
- 冻结源码 commit `cfc8b94`；交付：`04_source/source-release.zip`（252 文件，1,125,629 B，sha `ec4ceae6ccf96dbe03bd85c3009eeff96c95b21195ede684f59bf896bf01b215`，确定性构建二次验证相同）+ `04_source/SOURCE_MANIFEST.csv`（sha `e118da2c…`）+ `04_source/SHA256SUMS.txt`；`08_release/` 三文档（README/USER_GUIDE/HOW_TO_REPRODUCE）；审查包 `REVIEW_PACK_RELEASE_01/02` + `RELEASE_REVIEW_INDEX.md` + `RELEASE_REVIEW_SHA256SUMS.txt`（14 文件）；`06_reviews/GPT_FINAL_REVIEW.md`（终审提交模板）；S0-release 报告（`05_tests/s0-release/`）；三份运行日志（pytest/s0-release/clean-copy）。
- 协调员亲自核验：diff 仅 16 个 T014 专属文件；冻结源码/Golden/lock 零改动；ZIP↔manifest 逐文件比对 252/252 一致；`sha256sum -c` 全部通过；S0-release PASS（48/48、48/48、控制 0、parity 96/96、重放 hash 5195fc9a… 不变）；工作树内重跑全量 pytest 652/652（PYTHONPATH=src，已确认导入 worktree 代码）；干净副本 fresh venv 复现通过（validate 0、analyze 1 预期、s0 --repeat 1 PASS）；首轮 venv 解析问题已发现并重跑处置（见 DECISIONS.md）；构建脚本已归档到 `07_evidence/runtime_logs/t014-build-release.py`。
- T001–T014 全部 PASS。下一步：Drive 归档 → GPT 终审。

## 2026-11-17 ~03:11 GMT — Drive 归档完成，终审就绪

- Drive `04_release` 文件夹（id `1Yg5I1ZlMj7297duZcjgEiTMmtX3o44Jz`）：12 文件已上传并逐个核对大小 + MD5 全部一致（ZIP、清单、校验表、S0 报告、重放哈希、两份 release 审查包、索引、终审模板、三份发布文档；文件 id 见 DECISIONS.md）。
- GPT 终审 R1 可派发（模板 `06_reviews/GPT_FINAL_REVIEW.md`，GPT-6 + Extra High，Drive 尾巴）。

## 2026-11-17 ~02:43 GMT — T013 PASS（已合并）

- 任务 commit `17e5438`（12 个 commit，一项一修复 + 文档 + 核验），合并 commit `b99a77b`（--no-ff，分支已删，worktree 已移除）。
- 交付：13 个 P2 逐项处置（修复 10 项：P2-01/02/03/04/05/06/08/09/12/13；记录 3 项：P2-07/10/11）+ `07_evidence/runtime_logs/T013_FIX_RECORD.md`；MIT LICENSE + NOTICE + README.md + docs/LIMITATIONS.md；许可证扫描 `license_scan.py` + `license-report.txt`（19/19 OK）；wheel 构建日志 3 份 + `wheel-final.whl`（sha a674d565…）+ 隔离安装 analyze 日志；S0-r13 报告（`05_tests/s0-r13/`）。
- 协调员亲自核验：diff 仅 41 个 T013 专属文件（生产源码/测试/文档/许可证/打包 + 证据日志 + S0-r13；fixtures/Golden/冻结规格零改动）；重跑全量 pytest 652/652（工作树内）；S0-r13 与基线逐项比对（counts/gates/per_case 全等，重放 hash 5195fc9a… 不变；input_hashes 仅 pyproject 与 lock 两处合法改动）；逐项 P2 探针（P2-01/02/03/04/05/13）全部按预期行为；wheel 内容与隔离安装已核查；P2-04 Oracle 分歧有意保留（见 DECISIONS.md）。
- 合入后：共享 venv 已重装 `pip install -e ".[dev]"`（旧 editable 安装指向已删 stub）；不带 PYTHONPATH 的 CLI --help 已验证正常。
- T014 已派发（最终冻结、发布包与 GPT 审查交接）。

## 2026-11-17 ~02:15 GMT — T012 PASS（已合并）

- 任务 commit `5f2219c`，合并 commit `9bd5270`（--no-ff，分支已删，worktree 已移除）。
- 交付：`06_reviews/TASK_REVIEWS/T012_REVIEW.md`（结论通过进 T013；0 P0 / 0 P1 / 13 P2）、`07_evidence/REVIEW_PACKS/REVIEW_INDEX.md` + `REVIEW_PACK_01.md`（逐文件覆盖表 + 硬断言核查引代码行原文 + 13 P2）+ `REVIEW_PACK_02.md`（复核证据）+ `REVIEW_PACK_SHA256SUMS.txt`、`04_source/source/tools/verify_review_pack.py`（177 行，只读校验脚本）。
- 协调员亲自核验：diff 仅 6 个审查文件（生产源码/测试/Golden/文档零改动）；亲自跑验收命令（仓库根与 PACKAGE_ROOT 两种跑法均 VERIFIED，exit 0；sha256sum -c 3 行 OK）；重跑全量 pytest 639/639；审查包正文含真实哈希/行号/代码原文，非目录清单；审查者身份独立（会话 d470301b…，模型 Muse Spark，与施工 gpt-6-luna 不同）。
- **P2-03 审查员是对的，我方此前结论须修正**（见 DECISIONS.md）：None 守卫改变 1 处边界异常类型，已亲自复现。
- 其余 P2 我方独立复核：P2-02、P2-05、P2-06、P2-04、P2-13、P2-12(b)、P2-01 均已复现/读码确认；Pillow 许可证已闭合（MIT-CMU 正确，计划 §10.2 措辞过时，T013 在仓库文档中更正，不改冻结规格与 lock）。
- T013 已派发（13 个 P2 修复 + 文档/许可证/打包；P2-08 改打包布局后须重跑全量 pytest 与 S0）。
