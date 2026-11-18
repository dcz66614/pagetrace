# P026 PageTrace FIX-R1 冻结报告（草稿，发布工 F 起草）

- 冻结 commit：`8cfd7dc`（`8cfd7dcb06b270d21e016b55365bf759002e0744`）
- 冻结分两步：`d0aa21f`（`d0aa21f3fdf02aa349289ac87705500b98cf817a`）为代码冻结（5 项 P1 + 3 项 P2 修复）；`8cfd7dc`（“P026 FIX-R1: update release docs to FIX-R1 numbers”）为文档修正——仅改发布文档中的 T014 残留数字（重放哈希、754 测试、Golden SHA、日志名、SMOKE_PASS 表述）；冻结源码内只改 `04_source/source/README.md` 一行重放哈希
- 分支：`task/fix-r1`；工作树：`~/workspace/p026-pagetrace`
- 冻结时间：2026-11-17 ~04:30 UTC（代码冻结 `d0aa21f` commit 时间；文档修正 `8cfd7dc` 约 04:50 UTC）；发布验证：首轮 2026-11-17 ~04:31–04:42 UTC，第二轮（F2）2026-11-17 ~05:00–05:05 UTC
- 上一冻结：T014 master `011f523`（冻结源码 `cfc8b94`）；本轮为终审 R1 返修后重新冻结
- 状态：草稿——待协调员确认后定稿；本报告本身不提交 GPT、不上传 GitHub

## 1. 发布包

| 项目 | 值 |
|---|---|
| 发布包 | `04_source/source-release.zip` |
| 文件数 | 255（git 树 `04_source/source` 在 `d0aa21f` 上为 256 文件，仅 `.gitignore` 未打包） |
| 大小 | 1,148,388 B（T014：252 文件，1,125,629 B；首轮包 1,148,389 B） |
| SHA-256 | `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b`（首轮 `c51b9d32…5131` 已取代） |
| 清单 | `04_source/SOURCE_MANIFEST.csv`（27,041 B，SHA-256 `b6db053e8e5c11b1bfbd55e1f62e8570c0c84683b1a4191819768224b7fcc33f`；唯一变化 `README.md`） |
| 校验表 | `04_source/SHA256SUMS.txt`（191 B，SHA-256 `64c6e3ee00d0c52cc99df969e3739bb624560f3945a758bff7ceeede3dfd5e7a`） |
| 确定性构建 | 协调员二次构建字节相同（同一 SHA-256）；F 未重建（任务要求），独立核对 ZIP 内容与 `d0aa21f` git 树逐文件 0 内容不匹配 |

核对（F2 第二轮独立执行，首轮 F 同法核对过旧包）：`unzip -t` 无错误；`sha256sum -c 04_source/SHA256SUMS.txt`
两行全部 OK；ZIP ↔ manifest 逐文件 SHA + 大小 255/255 一致，0 不匹配，
无多余条目；ZIP 内容与冻结 commit `8cfd7dc` 的 git 树逐文件比对 0 内容不匹配
（仅 `.gitignore` 未打包，git 树 256 文件）；无 `__pycache__` / `*.pyc` / `.venv` / `egg-info` / 绝对路径
条目；48 份 PDF 均为 `fixtures/pdfs/` 下的合成 S0 fixture；文本文件对
`/home/hatch`、`/home/sam`、`C:\Users` 零命中；全部条目时间戳 1980-01-01、
权限 0o644、namelist 与 manifest 顺序一致。

## 2. 门禁结果（F 在冻结工作树独立重跑）

| 门禁 | 结果 | 证据 |
|---|---|---|
| 全量 pytest | **754 passed**，0 failed，99.95 s，退出 0（T014：652；F2 第二轮重跑 106.09 s，同样 754 passed，日志已覆盖） | `07_evidence/runtime_logs/pytest-fixr1.log` |
| S0 `--repeat 100` | **PASS**：检出 48/48（4 类各 12），首错阶段 48/48，控制误报 0，parity 96/96，100 次重放 1 个唯一哈希 `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`，Golden 0 不匹配 | `05_tests/s0-release/S0_REPORT.json`、`07_evidence/runtime_logs/s0-fixr1.log` |
| 干净副本（仅 ZIP，全新 venv） | `validate` 退出 0（VALID，hash MATCH）；`analyze` 退出 1（预期，FAIL_PAGE_OFFSET + PASS）；`s0 --repeat 1` **SMOKE_PASS**，同一重放哈希 `a06b87fc…`，退出 0（F2 第二轮从新 ZIP 重跑，2026-11-17 05:00:37–05:01:16 UTC，日志已覆盖） | `07_evidence/runtime_logs/clean-copy-fixr1-release.log` |

分文件测试计数：`test_bundle.py` 291、`test_verdicts.py` 164、
`test_file_name_paths.py` 66（新增）、`test_page_semantics.py` 50、
`test_cli.py` 30、`test_oracle.py` 21、`test_unlocatable_attribution.py` 19（新增）、
`test_extract.py` 19、`test_locate.py` 15、`test_html_report.py` 14、
`test_e2e.py` 14、`test_privacy.py` 11、`test_run_s0.py` 10、
`test_prototype.py` 10、`test_toctou.py` 9（新增）、
`test_fixture_manifest.py` 7、`test_oracle_parity.py` 4；合计 754 =
652 + 102（66 + 19 + 9 + test_cli +7 + test_run_s0 +1）。

S0 说明：协调员在 `8cfd7dc` 上重跑的 `05_tests/s0-release/S0_REPORT.json`
（与 `05_tests/s0/S0_REPORT.json` 逐字节相同；`base_commit` 为
`8cfd7dcb06b270d21e016b55365bf759002e0744`，即冻结 commit 本身）与首轮 F
在 `d0aa21f` 上的重跑报告（`07_evidence/runtime_logs/s0-fixr1-out/S0_REPORT.json`）
逐字段比对，**唯一差异是 `base_commit`**（`8cfd7dc` 对 `d0aa21f`）。
counts、per_case、input_hashes、replay、environment 全部相同。第二轮 F2
未重跑 `--repeat 100`（任务范围：S0 门禁证据以协调员重跑为准）。
Golden sha `9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353`
（T014 为 `417e3ed3…`；变化是预期的——FIX-R1 再生了 un-ext-09..12
fixture 与 Golden）。

干净副本说明：复现目录为 `~/workspace/tmp-p026-clean-release`（持久磁盘）
而非 `/tmp`——`/tmp` 是 512M tmpfs，运行时仅剩 262M 可用，全新 venv
装不下；内容仍是且仅是 ZIP 解压物。协调员先前留下的
`clean-copy-fixr1.log`（03:50 UTC）用的是工作树副本且重放哈希为旧值
`5195fc9a…`，已被本轮从新 ZIP 的 `clean-copy-fixr1-release.log` 取代。

## 3. 修复摘要（终审 R1 的 5 项 P1 + 3 项 P2）

| 缺陷 | 修复要点 | 验证方式（F 实测） |
|---|---|---|
| P1-R1-01 PDF TOCTOU | `pdf_bytes` 随 `PdfDocumentInfo` 传递；`extract_pages` 只解析已校验字节，不再无 SHA 复核重开路径；CLI 磁盘复核拒绝同尺寸同页数调换 | 新增 `tests/integration/test_toctou.py` 9 测试全部通过（含 `test_cli_rejects_swapped_pdf_same_size_same_pages`，正是 GPT 的同尺寸同页调换复现） |
| P1-R1-02 UNLOCATABLE 错归因 | 仅可证实的抽取失败才归因 extraction；近似引用 `first_fault_stage = null`（生产 + Oracle + Golden 三方一致）；生成器修正，un-ext-09..12 再生，12 个 UN 案例均含非文本页 | 新增 `tests/unit/test_unlocatable_attribution.py` 19 测试全部通过（含 `test_un_ext_12_reproduces_gpt_findings`、`test_near_miss_cases_have_no_attributable_stage[un-ext-09..12]`、`test_unlocatable_reasons_still_split_4_4_4`）；S0 首错阶段 48/48、Golden 0 不匹配；记录 `07_evidence/runtime_logs/FIX_R1_UNLOCATABLE.md` |
| P1-R1-03 clean 误删无关目录 | marker 改为工具自写输出的自洽性检查；裸 `report.html` / 任意 `S0_REPORT.json` / 仅 schema 的 `report.json` 均被拒绝 | `test_cli.py` 中 13 个 clean 相关测试全部通过（含 `test_clean_refuses_unrelated_report_html_directory`、`test_clean_refuses_arbitrary_s0_report_json`、`test_clean_refuses_schema_only_report_json`、`test_clean_refuses_tampered_report_json/hash`） |
| P1-R1-04 报告泄露绝对路径 | schema + 运行时拒绝 POSIX/Windows/UNC/目录形式的 `document.file_name`（新规则 R-11）；错误信息脱敏，不回显原值 | 新增 `tests/unit/test_file_name_paths.py` 66 测试全部通过（15 种路径形式 × 3 层 + `test_cli_validate_gpt_repro_without_leak` 等） |
| P1-R1-05 证据不完整 | 运行日志、T012/T013 记录、license 报告、SHA256SUMS、git-diff 证据已集齐并随本包上传 Drive | 本次发布即证据：三份 FIX-R1 运行日志、T013_FIX_RECORD.md、T012_REVIEW.md、license-report.txt、重算的 RELEASE_REVIEW_SHA256SUMS.txt、git-diff 4 文件；Drive 归档见 §5 |
| P2 S0 repeat<100 误报 PASS | `repeat < 100` 只能返回 `SMOKE_PASS`，满 100 才正式 `PASS` | 干净副本 `s0 --repeat 1` 打印 `S0_RESULT: SMOKE_PASS` + 注明；相关测试通过 |
| P2 图像枚举异常误报 EMPTY | 图像枚举失败返回 ERROR，不再掩盖为 EMPTY | `test_image_enum_failure_is_error_not_empty` 等通过 |
| P2 clean-copy 不按 lock 安装 | `HOW_TO_REPRODUCE.md` §4 改用 `requirements.lock` 安装 | 本轮干净副本即按 lock 安装：退出 0，6 个直接依赖版本与 `pyproject.toml` 一致 |

改动规模：相对 T014 master `011f523` 共 51 文件、+4694/−519；
冻结源码范围 `cfc8b94..8cfd7dc -- 04_source/source` 共 36 文件、+1963/−269
（首轮 `d0aa21f` 为 48 文件 +4645/−475 与 35 文件 +1962/−268；增量仅文档修正；
FIX-R1 本就改了冻结源码，与 T014 的“冻结源码零改动”不同，如实记录）。
证据文件：`07_evidence/runtime_logs/git-diff-011f523-d0aa21f-stat.txt` /
`git-diff-011f523-d0aa21f.txt` / `git-diff-cfc8b94-d0aa21f-frozen-source-stat.txt` /
`git-diff-cfc8b94-d0aa21f-frozen-source.txt`。

## 4. 已知残留项

1. ~~**文档重放哈希滞后（P2 级）**~~**已解决（`8cfd7dc`）**：首轮记录的
   文档滞后（冻结树内 `README.md` 与 `08_release/` 三文档引用 T014 的重放哈希
   `5195fc9a…`，而 FIX-R1 实测为 `a06b87fc…5632a3`）已在文档修正 commit `8cfd7dc`
   中更正。F2 核实：`04_source/source/README.md` 与 `08_release/` 三文档中
   `5195fc9a` 零命中，`a06b87fc` 各 1/1/1/2 处；新 manifest 唯一变化的行即
   `README.md`（大小仍 5316，SHA 改为 `dc33d686…`）。
2. ~~**协调员版 S0 报告 `base_commit` 不是冻结 commit**~~**已解决**：新版
   `05_tests/s0-release/S0_REPORT.json` 的 `base_commit` 已为冻结 `8cfd7dc`
   （见 §2 说明）；与首轮 F 在 `d0aa21f` 上的重跑逐字段一致，仅 `base_commit` 不同。
3. **协调员旧 clean-copy 日志已过期**：`clean-copy-fixr1.log` 用工作树副本
   且哈希为旧值，已被从新 ZIP 的 `clean-copy-fixr1-release.log` 取代（第二轮 F2
   又从新 ZIP 重跑并覆盖，2026-11-17 05:00:37–05:01:16 UTC）；旧日志仍留在
   `07_evidence/runtime_logs/` 中，阅读时以新日志为准。
4. **平台**：仅 Linux x86_64 + CPython 3.12.3 实测；Windows / macOS NOT_TESTED。
5. **范围**：S0 只覆盖 48 组冻结合成 fixture；不证明任何真实 PDF 流水线通过；
   终审结论以 GPT R2 为准，本报告不预判。

## 5. Drive 归档

- `04_release` 下新建子文件夹 `FIX_R1_2026-11-17_d0aa21f`，文件夹 id
  `16nQDtKj04UC_qHsXzr16BYMq6YfV2U5N`，上传 25 文件（发布包 3、S0 报告 2、
  审查包 2、索引 1、08_release 三文档、GPT 终审 R1 提交模板、三份 FIX-R1
  运行日志、T013/T012 记录、T012 审查包 2、license 报告、SHA256SUMS、
  git-diff 证据 4），逐个下载核对大小 + MD5：**25/25 通过**
  （S0_REPORT.json 按任务要求以 Drive 返回的 size + md5Checksum 核对，
  新版 172,664 B / MD5 `11b0cba6e0f830b89ef86e14d48ce2dc`，与本地一致；
  CLI 对该 JSON 的 `--output` 下载写 0 字节，属 CLI 侧行为，已用 metadata
  核对代替下载核对）。
- 第二轮（F2）换传：同一子文件夹内 15 件已变文件原位替换（新 ZIP /
  manifest / SHA256SUMS / S0 报告 / replay-hashes / 审查包 2 件 / 索引 /
  校验表 / 08_release 三文档 / 三份运行日志），其余 10 件未变，只清点
  核对在位；换传后最终清点 25/25 通过（逐项大小 + MD5 见发布汇报；
  S0_REPORT.json 以 size + md5Checksum 核对为准）。
  索引文件本身 Drive id `1gXdqEIge2c41ipwy7Ze7LodRb-cq3ama`，
  校验表 Drive id `1XWIB8S8Kz57HGA9e3IQTdev-ehUudVci`。
- 文件夹 id 与逐文件核对结果见
  `07_evidence/REVIEW_PACKS/RELEASE_REVIEW_INDEX.md`（FIX-R1 定稿节）。
- T014 的 12 文件仍在 `04_release` 根目录，未动。

## 6. 未提交 / 未上传

- 未提交 GPT R2（由协调员决定是否派发）。
- 未上传 GitHub（须终审 PASS + Sam 批准，按工厂规则）。
- 未 commit（工作树含未提交的发布包与审查包文件，属发布工产出，留待协调员处置）。
