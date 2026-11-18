# 决策记录（DECISIONS.md）

## 2026-11-16 ~23:38 GMT — 立项与 GO

- 规格 v1.0.0（PROJECT_BOOK.md + IMPLEMENTATION_PLAN.md）已由主 agent 核验通过：Drive 重新下载，大小 + SHA-256 与 GPT 回复一致；S0 门槛、T001–T014、88h、零真人、MIT、去重边界均在场。立项已宣告，施工开始。
- 计划书正文状态栏仍写 `WAITING_OWNER_REVIEW / NO_GO`，那是 GPT 生成时的草案状态；主 agent 的核验通过 + 本次施工派发即为 GO，不改规格原文。
- Drive 文件夹目前仍叫 `P026-reviewreceipt`（id `1oT85-N7qs0uECf26dKk4oKIrTyRtszjU`），改名需 Sam 批准，暂不动。

## 2026-11-16 ~23:40 GMT — 仓库布局

- 工作目录 `~/workspace/p026-pagetrace/` 为 git 仓库根；产品源码树根为 `04_source/source/`（PACKAGE_ROOT），内含 pyproject.toml、src/、tests/、contracts/、docs/、fixtures/、tools/。任务卡中的相对路径均以 PACKAGE_ROOT 为准；项目级证据（S0 报告等）放 `05_tests/`。
- 主测试平台为当前 Linux VM；Windows 平台一律静态审查 + 标记 NOT_TESTED（计划 §0.3）。

## 2026-11-16 ~23:40 GMT — 模型路线

- 模型优先 gpt-6-luna；WorkBuddy 优先，但 Sam 的电脑约 2026-11-17 05:55 GMT 关机，之后用桥 / Copilot CLI / agy。协调员不亲自写业务代码或测试，只调度、复核证据、跑门禁。
- 每个任务独立新会话；构建者与审查者不同模型/会话；T012 只读审查。

## S0 铁律（计划 §1、§3、§11）

- S0（T001–T007）先行：48/48 检出、48/48 阶段定位、控制 0 误报、Oracle parity、100 次重放 1 哈希；任一门失败 = STOP，不进 T008。
- T005 原型不阻断 S0，不改算法门槛。
- 未经批准不得上传 GitHub、不得对外发布、不得改规格。

## 2026-11-17 ~00:26 GMT — UNLOCATABLE 4/4/4 确认

- T004 核验确认：12 组 UNLOCATABLE 为 image-only-page ×4 / blank-page ×4 / near-miss-quote ×4（spec 的 variant 字段为准）；实现按 IMAGE_ONLY / EMPTY / NO_EXACT_MATCH 分别归因，first_fault_stage 均为 extraction。
- un-ext-12（near-miss，8 页全 text）不含图像页或空白页，与 PROJECT_BOOK §8.1 字面表述有 1 组偏差；行为正确，不阻塞；T006 Golden 按同一 4/4/4 记录。
- T004 的三项设计裁决已接受并写入 compare_stages.py docstring：（1）重复文本无强制选页→AMBIGUOUS，display 记录缺失但真值单页时仍判 FAIL_METADATA_MISSING（mm-dsp-10）；（2）UNKNOWN_PAGE_BASIS 的 first_fault_stage 记 display；（3）跨页引用的 display 值落在 span 内任一页即接受。

## 2026-11-17 ~01:11 GMT — S0 PASS（T007 已合并，S1 启动）

- **S0_RESULT: PASS** — 检出 48/48（每类 12/12）、first stage 48/48、控制误报 0、parity 96/96 引用一致（576/576 字段比较，0 不匹配）、重放 100 次唯一 hash 1 个（5195fc9a…）、uncertainty 违规 0、Golden 全字段不匹配 0。8 门全过：§8.3 的 6 门 + 支撑门 golden_agreement + 聚合门 s0_pass。
- runner 另设的 golden_agreement 支撑门（生产与 Golden 全字段一致）是更严而非更松，且子 agent 已主动披露；接受，不剔除。
- 协调员独立核验：diff 仅 7 个 T007 专属文件（无生产算法/Golden/夹具/规格改动）；报告逐项复算（检出、阶段、控制、parity 576 字段、Oracle vs Golden 0 差异）全符；148 个 fixture 哈希 + Golden SHA（417e3ed3…）+ lock SHA（ac77f4ee…）+ 48 个 PDF SHA 全部重算一致；**亲自重跑完整验收**（tests/s0 9/9、全量 pytest 287/287、run_s0 --repeat 100 退出 0），重放 hash 与提交版完全相同；与提交版报告的唯一差异是 base_commit 字段（子 agent 在 5095c37 上跑验收、提交前未改；我方在 ed550d0 上重跑），除此之外报告内容字节一致——已恢复提交版报告再合并。
- 合并 commit 7455ddf（--no-ff，分支已删）；合入后 tests/s0 9/9 PASS（25 秒）。
- S1：T008 与 T010 并行（不同 worktree：~/workspace/p026-pagetrace-t008 / -t010，分支 task/t008 / task/t010，基线 7455ddf，文件不重叠）；T009 依赖 T010 冻结 schema；T011 等 T008/T009/T010 全部 PASS。
- 遗留 P2 不变：Pillow 许可证（T013）；双包 import 路径（T013，runner 沿用 sys.path 做法并已文档说明）。

## 2026-11-17 ~01:26 GMT — T010 核验：resolve 函数的 None 守卫（已审查，非缺陷）

- T001 冻结的 7 个页码纯函数移入 `src/pagetrace/contracts.py`：6 个与 T001 参考实现（`tests/unit/test_page_semantics.py`）字节一致；`resolve_citation_to_index0` 多一段显式 `value is None` 守卫（抛 PageSemanticsError，引 R-07“缺失不得默认成 0”）。
- 已审查：该守卫不改变任何输入的结果——T001 版对 None 同样抛错（`_require_int`/`label_to_index0`/未知 basis 分支均抛 PageSemanticsError 或 UnknownBasisError；UNKNOWN basis 的检查在守卫之前，仍抛 UnknownBasisError）。差异仅在错误消息文本。接受，不阻塞；T012 审阅时可再看。
- 衍生 P2（T013 统一时处理）：页码函数现存两份（T001 测试文件内参考实现 + contracts.py 生产实现），有漂移风险；另双包 import 路径问题仍在。

## 2026-11-17 ~01:40 GMT — T009 核验：`fixtures build` 未实现（P2，留待 T013/T014 决定）

- PROJECT_BOOK §12.1 示例命令含 `python -m pagetrace.cli fixtures build --out fixtures/generated`，T009 只实现了 analyze/validate/s0/clean 四命令。任务卡硬断言亦只要求这四命令，且 §12.1 末尾称“命令名和参数以 T009 实际冻结的 CLI contract 为准”。子 agent 已在 docs/CLI.md 中如实记录该缺口，不属 T009 失败。
- 48 组 fixture 是 T002 冻结产物，仓库无 fixture 生成器；如需 `fixtures build` 应另立任务卡（T013/T014 时决定），不得在 T011 测试任务中顺手加业务代码。

## 2026-11-17 ~02:02 GMT — T011 核验：三处“泄漏”嫌疑均为误报（已裁决）

- 我方独立扫描曾 flag 三处，经逐项核查全部不是泄漏：(1) report.html 含 quote_text 键与短引文——冻结引文 ≤40 字，默认摘要即全文，是 §13 摘录规则本身，隐私测试用长引文 sentinel tail 作真凭据；(2) t011-evidence.log 含 "/home/" 与 quote_text——均为描述性文字（“0 泄漏 /home/”“JSON 报告永不含 quote_text”），无真实路径；(3) netlog 1 个 "http" 命中——是 DNS 配置键名 allow_dns_over_https_upgrade，非 URL。隐私测试设计合理（sentinel tail、非 naive 子串）。
- 遗留观察（P2，T012/T013 再看）：CLI `clean` 把解析后的绝对 TARGET 打印到 stdout（T009 安全设计，先显示目标路径）。§13“不记录绝对路径到默认日志”针对持久化日志；stdout 是用户刚给的路径的解析形式，属常规 CLI 行为，不算 T011 失败；隐私测试目前只覆盖 analyze 的相对路径输出，未覆盖 clean 的 stdout。

## 2026-11-17 ~02:15 GMT — T012 核验：P2-03 审查员是对的，协调员此前结论须修正

- **更正（协调员此前结论不精确）**：T010 核验时我说 resolve_citation_to_index0 的 None 守卫“不改变任何输入的结果，仅消息不同”——审查员 250 输入差分证明这是错的：`resolve(None, "PDF_LABEL", 6, label_map=None)` 时参考实现抛 `UnresolvableLabelError`（`PageSemanticsError` 的子类），生产实现抛基类 `PageSemanticsError`。我方已亲自复现确认（另 3 组 None 输入确实仅消息不同）。影响窄（只影响精确捕获 `UnresolvableLabelError` 的调用方；捕获基类的行为不变；S0 不走该路径），定 P2-03，T013 修复（None 守卫在 `PDF_LABEL` 且 `label_map is None` 时仍抛 `UnresolvableLabelError`）。
- 其余 P2 我方独立复核：P2-02（非列表 source_page_indices0 → 原始 TypeError）、P2-05（UNKNOWN_TRACE_MISSING 的 reason 生产 TRACE_MISSING vs Oracle null，verdict 一致；reason 不在 S0 parity 6 字段内）、P2-06（docstring 宣称不存在的 display 回退）、P2-04（越界 display 值原因误标）、P2-13（NEEDS_MANUAL_REVIEW 落入 else → kind="offset"）、P2-12(b)（0 引用仍得真实哈希，doc“为 null”错误；我方实测 0 引用哈希 d3dda26f…，非 null）均已复现/读码确认；P2-01（clean 打印绝对 TARGET）此前已亲自观测。P2-07/08/09/10/11 接受审查包证据。
- Pillow 许可证已闭合：审查员以已安装 13.0.0 LICENSE 原文 + 官方文档证明 MIT-CMU 正确；计划 §10.2 的 HPND 是旧版措辞。T013 更新措辞时**不得改冻结规格文件**（~/workspace/p026-specs/ 不动），在仓库文档中记录更正即可，lock 不改。
- T013 冻结套件禁令：P2-07 不得向 48 组冻结 fixture 加 3 页跨页样本；修复 = 在 Oracle 探针处加注释说明子集性质（+ 测试计划记录）。

## 2026-11-17 ~02:43 GMT — T013 核验：13 个 P2 全部处置，0 遗留

- 处置：修复 10 项（P2-01 clean 原样打印路径、P2-02 非列表 source_page_indices0 判 PAGE_METADATA_MISSING、P2-03 None+PDF_LABEL+无 label_map 抛 UnresolvableLabelError、P2-04 越界值原因 VALUE_OUT_OF_RANGE、P2-05 Oracle 缺失快照 reason=TRACE_MISSING、P2-06 docstring 去 display 回退、P2-08 单一 src 打包布局、P2-09 Pillow/reportlab 移入 [fixtures] extra、P2-12 PAGE_SEMANTICS.md 两处措辞、P2-13 NEEDS_MANUAL_REVIEW 的 stage diff kind=needs_review）；记录 3 项（P2-07 Oracle 子集探针注释 + LIMITATIONS + TEST_PLAN §6、P2-10 `fixtures build` 仍未实现、P2-11 un-ext-12 §8.1 措辞偏差）。P0/P1：0。无遗留 P2。
- **P2-04 Oracle 分歧有意保留**：Oracle 仍把越界值映射为 VALUE_BASIS_TYPE_MISMATCH，生产为 VALUE_OUT_OF_RANGE；verdict 一致，reason 不在 S0 parity 字段内；Oracle 是独立实现，不为迎合生产静默改动。已记入 LIMITATIONS.md。
- P2-08 打包（高风险项）已核验：顶层 stub 已删；pyproject 为 package-dir + packages.find where=src，package-data 含 assets/* 与 schemas/*.json；包内 schema 与 contracts/ 字节一致（6ef5332f… / a123094b…）；wheel 构建成功（sha a674d565…，21 文件），两次 SOURCE_DATE_EPOCH 构建字节一致；隔离 venv 安装后 analyze 故障用例 exit 1 且 verdicts 正确（cite-fault FAIL_PAGE_OFFSET / cite-control PASS），report.json + report.html + assets 齐全；`contracts.py` 加载 schema 改为包内优先、仓库后备（原直接读 PACKAGE_ROOT/contracts/ 在 wheel 中不存在）。
- Pillow 许可证已闭合：MIT-CMU（13.0.0 LICENSE 原文 + METADATA License-Expression）；lock 仅注释更新，**全部 pinned 版本未变**（我方 diff 核查：无 pinned-version 行改动）；冻结规格文件未动（PROJECT_BOOK 735aa0b8… / IMPLEMENTATION_PLAN 2e5b16bb… 重算一致）；fixtures/Golden 零改动。
- S0-r13 与基线逐项比对：counts、gates、per_case 全等；input_hashes 仅 pyproject_sha256 与 requirements_lock_sha256 两处不同（均为 T013 合法改动的文件），fixtures 与 golden_sha256 相同；重放 100 次唯一 hash 5195fc9a… 与基线完全一致。许可证扫描 19/19 OK，0 问题。
- 协调员独立复核（工作树内亲自跑）：全量 pytest 652/652（639 基线 + 13 新增回归测试）；P2-03 探针（resolve(None, PDF_LABEL, 6, None) → UnresolvableLabelError）；P2-02 探针（非列表 → FAIL_METADATA_MISSING / PAGE_METADATA_MISSING / chunking，anchor 探针返回 None 无 TypeError）；P2-04/P2-13 探针（citation_page_value=0 → NEEDS_MANUAL_REVIEW + VALUE_OUT_OF_RANGE + display，stage diff kind={needs_review}）；P2-01 探针（clean --dry-run rel/path 打印 `TARGET: rel/path` 原样，无绝对路径）；P2-05 读码确认（attribute.py:391 reason="TRACE_MISSING"）；21 个 P2 回归测试单跑通过；S0 smoke --repeat 2 exit 0（Golden 417e3ed3…）。
- 备注：子 agent 运行中有 3 次 exec 非零退出（exit 2、1、2），交接已解释其中两处（analyze 故障用例 exit 1 为预期；首次无 PYTHONPATH 的 S0 尝试失败，系共享 venv 的 editable 安装仍指向已删 stub）；第三处 exit 2 未单独说明，但全部最终验收命令均已绿，无影响。
- **合入后动作（协调员已做）**：共享 venv 重装 `pip install -e ".[dev]"`（旧 editable 安装映射已删 stub，不带 PYTHONPATH 的 `python -m pagetrace.cli` 会失败）；重装后从 /tmp 不带 PYTHONPATH 跑 CLI --help 正常 exit 0。安装版 CLI 的 `s0` 子命令仍需源码检出（tools/fixtures/Oracle 不随 wheel 发布），已记入 README/LIMITATIONS。
- T014 已就绪：P0/P1 为 0，13 个 P2 全部修复或记录，全量 pytest 与 S0 通过且重放哈希不变，MIT/NOTICE/README/LIMITATIONS/wheel 齐全。

## 2026-11-17 ~03:10 GMT — T014 核验：冻结完成，首轮 venv 解析问题已发现并重跑

- 冻结源码 commit：`cfc8b94`（T013 控制提交）；T014 合并 commit `28ceb72`；T014 只加发布元数据/清单/文档/审查包，冻结源码、Golden、lock 零改动（`git diff cfc8b94 -- 04_source/source/` 为空；T012 审查包 diff 为空）。
- **首轮证据路径错误（子 agent 已发现并处置，我方已复核）**：worktree 的 `.venv` 是指向主仓库 venv 的符号链接，其 editable 安装指向主仓库 src/；`cli.py` 用 `Path(__file__).resolve().parents[2]` 推导 PACKAGE_ROOT，导致不带 PYTHONPATH 的首轮 pytest/S0 实际执行的是主仓库代码，首轮 S0 报告写到了主仓库的 `05_tests/s0-release/`。两棵树在 cfc8b94 上字节相同，首轮数字本身正确；处置：删除主仓库被误写的 untracked 目录（我方核查主仓库 git status 干净、无 05_tests/s0-release/），pytest 与 S0 用 `PYTHONPATH=$PWD/src` 重跑并事先验证 `pagetrace.__file__` 确为 worktree 路径；提交的证据均为重跑结果。是否修复 cli.py 的路径推导属 T015+ 决策（超出 T014 范围，未动冻结源码）。
- 协调员独立核验：diff 仅 16 个 T014 专属文件（1558 行新增，0 删除）；ZIP sha `ec4ceae6…`、1,125,629 B、252 文件；我方逐文件比对 ZIP↔manifest 252/252 一致、0 不匹配、无 venv/__pycache__/*.pyc/用户 PDF/密钥/绝对路径条目；`sha256sum -c` 两份（SHA256SUMS 与 RELEASE_REVIEW_SHA256SUMS 14 文件）全部 OK；S0-release 与基线逐项比对（counts/gates/per_case 全等，重放 hash 5195fc9a… 不变；input_hashes 与 s0-r13 完全相等）；我方在工作树内用 PYTHONPATH=src 重跑全量 pytest 652/652（已确认 `pagetrace.__file__` 为 worktree 路径）；干净副本日志已读（fresh venv：validate 0、analyze 1 预期、s0 --repeat 1 PASS 同一哈希）；GPT 终审模板已读（明确“模板非终审本身、不填 verdict”、PASS 范围限定为工程修复+离线验收+交付完整性、Drive 尾巴在场）；发布文档无夸大宣传，Windows/macOS 明确 NOT_TESTED。
- 构建脚本缺口（已补）：T014 的 ZIP 构建脚本原只在 /tmp（`/tmp/t014-build-release.py`，VM 重启即失）；我方已将其原样复制到 `07_evidence/runtime_logs/t014-build-release.py`（sha `06b01f72…`，与 /tmp 版一致），随控制提交归档；重建参数（排序、1980-01-01 时间戳、0o644、deflate）另见 REVIEW_PACK_RELEASE_02 §1。
- 下一步：Drive 归档（04_release）→ GPT 终审 R1（协调员/主 agent 派发，GPT-6 + Extra High，同一立项对话已用 0 轮终审——注意：立项对话为 GPT 规格对话，终审应按工厂规则用终审对话；T014 模板为准）。

## 2026-11-17 ~03:11 GMT — Drive 归档完成（04_release，12 文件全核对一致）

- Drive 文件夹：P026 项目文件夹（id `1oT85-N7qs0uECf26dKk4oKIrTyRtszjU`，仍叫 P026-reviewreceipt）下新建 `04_release`（id `1Yg5I1ZlMj7297duZcjgEiTMmtX3o44Jz`）。
- 上传 12 文件，逐个核对本地大小 + MD5 与 Drive 返回的 size + md5Checksum，全部 MATCH：source-release.zip（1,125,629 B，md5 `7dff4213…`，id `1dSa_hj75d9EQi5Uc_gPDFU70HodXU38M`）、SOURCE_MANIFEST.csv（26,718 B，id `1l7yTOmzZJJJmv8iRrhkbs9nAHE0FuHIo`）、SHA256SUMS.txt（191 B，id `1GeXTblno7Rn_YbRVSJF1qrOcU3I-lpWD`）、S0_REPORT.json（169,431 B，id `1poQS6QeMeemvasoM3GNBaYIO9u0pVn8J`）、replay-hashes.txt（6,500 B，id `1b_BxP9Xc04wtBKeLmb_CZFxdrGRT1Bbg`）、REVIEW_PACK_RELEASE_01.md（34,402 B，id `10Ha4CPvcGYkybeqL-9CVgcfLCWWRRNbv`）、REVIEW_PACK_RELEASE_02.md（6,804 B，id `18Cp4OkyvMqqzW1MSK1Xyv__UC1dqPBhM`）、RELEASE_REVIEW_INDEX.md（4,522 B，id `1nsRYFJLtH1wyPaQA_d35Degu8JQNZx0u`）、GPT_FINAL_REVIEW.md（5,810 B，id `1GElbamc9Xl8MWpX3LzCiY_N37oNUGZg_`）、README.md（6,191 B，id `18ue1YtbrUNFJdNn7KInuhZxaP9ytT763`）、USER_GUIDE.md（7,196 B，id `1OLX3GoKzJeWZ9SRSU1TMKzv5Eh6xJ8PI`）、HOW_TO_REPRODUCE.md（6,796 B，id `1Y0K_RPqoPzkM8zTvfRMED_pAQV05xOjO`）。
- 终审就绪：GPT 终审 R1 可派发（模板 + 审查包 + Drive 证据齐全）。
