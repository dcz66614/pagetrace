# FIX-R1 审查包 RELEASE-04 — 独立复现证据（实测数据）

- 项目：P026 PageTrace 引文落页镜；任务：FIX-R1 发布（终审 R1 返修后重新冻结）
- 冻结：`8cfd7dc`（`8cfd7dcb06b270d21e016b55365bf759002e0744`）；分支 `task/fix-r1`；工作树：`~/workspace/p026-pagetrace`
- 冻结分两步：`d0aa21f` 为代码冻结（5 项 P1 + 3 项 P2 修复），`8cfd7dc` 为文档修正（仅改发布文档中的 T014 残留数字；冻结源码内只改 `04_source/source/README.md` 一行重放哈希）。本包为第二轮重生成（发布工 F2，2026-11-17 ~05:00–05:05 UTC）。
- 本包所列数字均为发布工 F 亲自跑出的结果，不是转述施工汇报或协调员交接
  （以下命令均在工作树内执行，Python 为 `04_source/source/.venv/bin/python`
  Python 3.12.3 / pytest 9.2.0；协调员交接的数字只在注明处引用，并逐项复核）。
- T012 的 `REVIEW_PACK_01/02.md` + `REVIEW_INDEX.md` +
  `REVIEW_PACK_SHA256SUMS.txt` 未被覆盖或改动。
  T014 的 `REVIEW_PACK_RELEASE_01/02.md` 亦未改动。

## §1 ZIP ↔ manifest 一致性：255 文件，0 不匹配

```bash
unzip -t 04_source/source-release.zip
# No errors detected in compressed data of 04_source/source-release.zip.（255 条目）
sha256sum -c 04_source/SHA256SUMS.txt
# 04_source/source-release.zip: OK
# 04_source/SOURCE_MANIFEST.csv: OK
```

独立复核（`zipfile` + `csv`，逐文件哈希与字节数比对）：

```text
zip entries: 255  manifest rows: 255
namelist == manifest order: True
hash/size mismatches inside zip: 0
extra entries in zip: 0
absolute-path entries: []
key-like entries (secret/*.pem/id_rsa/credentials): []
forbidden entries: 48 PDFs, all under fixtures/pdfs/ (synthetic S0 fixtures,
  tracked in git; no user PDFs, no __pycache__ / *.pyc / .venv / egg-info)
distinct zip dates: [(1980, 1, 1, 0, 0, 0)]
distinct zip perms: {0o644}
absolute-path hits in text files (/home/hatch, /home/sam, C:\Users, /root/): []
```

冻结一致性：ZIP 内容与 `git ls-tree -r 8cfd7dc -- 04_source/source` 逐文件
比对（`git hash-object`），0 内容不匹配；唯一差异是 `.gitignore` 未打包
（git 树 256 文件，ZIP 255 文件）。发布包与冻结 commit 一致，无需重建。
（F2 独立执行；首轮为 `d0aa21f` / 旧 ZIP `c51b9d32…5131`。）

确定性：协调员二次构建字节相同（同一 SHA-256
`7526f511…fad6b`）；F2 未重建发布包（任务要求：已建好的包不得重建），以上
ZIP 静态属性（单一 1980 时间戳、统一 0o644、排序后顺序与 manifest 一致）
与确定性构建一致。

## §2 全量 pytest 复现：754 passed（冻结工作树代码）

```bash
cd 04_source/source
PYTHONPATH=$PWD/src TMPDIR=~/workspace/tmp-p026-pytest ./.venv/bin/python -m pytest -q
# 754 passed in 106.09s (0:01:46)，退出码 0（F2 第二轮重跑，2026-11-17 05:01:23–05:03:10 UTC；首轮 99.95s）
```

日志：`07_evidence/runtime_logs/pytest-fixr1.log`。分文件计数
（`pytest --collect-only -q` 实测，与总数 754 一致）：
`test_bundle.py` 291、`test_verdicts.py` 164、`test_file_name_paths.py` 66、
`test_page_semantics.py` 50、`test_cli.py` 30、`test_oracle.py` 21、
`test_unlocatable_attribution.py` 19、`test_extract.py` 19、
`test_locate.py` 15、`test_html_report.py` 14、`test_e2e.py` 14、
`test_privacy.py` 11、`test_run_s0.py` 10、`test_prototype.py` 10、
`test_toctou.py` 9、`test_fixture_manifest.py` 7、`test_oracle_parity.py` 4。

## §3 S0 复现：PASS，100 次重放 1 个唯一哈希

协调员在冻结 `8cfd7dc` 上重跑 `--repeat 100`（日志
`07_evidence/runtime_logs/s0-fixr1.log`；报告
`05_tests/s0-release/S0_REPORT.json`，与 `05_tests/s0/S0_REPORT.json`
逐字节相同）：
`S0_RESULT: PASS`；`counts = {detection: 48, first_fault_stage: 48,
control_false_positives: 0, parity_citations_matching: 96,
parity_mismatches: 0, replay_unique_hashes: 1, golden_mismatches: 0,
uncertainty_violations: 0}`；`replay.unique_hashes =
[a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3]`；
`base_commit` 为 `8cfd7dcb06b270d21e016b55365bf759002e0744`（即冻结 commit
本身）；golden sha `9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353`
（T014 为 `417e3ed3…`；变化是预期的——FIX-R1 再生了 un-ext-09..12
fixture 与 Golden）。

与首轮发布工 F 在 `d0aa21f` 上的独立重跑报告
（`07_evidence/runtime_logs/s0-fixr1-out/S0_REPORT.json`，约 5 分 38 秒）
逐字段比对：**唯一差异是 `base_commit`**（新版 `8cfd7dc`，F 版
`d0aa21f`）。counts、per_case、input_hashes、replay、environment
全部相同。第二轮 F2 未重跑 `--repeat 100`（任务范围：S0 门禁证据以
协调员重跑为准；F2 独立重跑了全量 pytest 与干净副本，见 §2/§4）。
上传 Drive 的是协调员新版（`05_tests/s0-release/`）。

## §4 干净副本复现（仅 ZIP 内容，全新 venv）：SMOKE_PASS

```bash
rm -rf ~/workspace/tmp-p026-clean-release && mkdir -p ~/workspace/tmp-p026-clean-release
cd ~/workspace/tmp-p026-clean-release
unzip -q ~/workspace/p026-pagetrace/04_source/source-release.zip -d pkg   # exit 0
python3 -m venv venv                                                        # exit 0
./venv/bin/pip install -r pkg/requirements.lock                            # exit 0
./venv/bin/pip install -e ./pkg --no-deps                                  # exit 0
# versions: pypdf 7.1.0, pdfminer.six 20260107, jsonschema 4.26.0, pytest 9.2.0
cd pkg
./../venv/bin/python -m pagetrace.cli --help                               # exit 0
./../venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf
# VALID: bundle is a well-formed pagetrace.bundle/v1 document
# document hash: MATCH；退出 0
./../venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out ~/workspace/tmp-p026-clean-release/out-po-ext-01
# citations: 2 (PASS 1, FAIL 1)；cite-fault FAIL_PAGE_OFFSET /
#   PAGE_OFFSET / extraction；report.json 为 pagetrace.report/v1；
#   退出 1（预期：含 FAIL 引用，不是工具崩溃）
TMPDIR=$PWD/.tmp ./../venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 1 --out ~/workspace/tmp-p026-clean-release/s0-clean
# S0_RESULT: SMOKE_PASS；replay hash a06b87fc…5632a3（与 100 次门禁相同）；退出 0
# json s0_result: SMOKE_PASS | base_commit: None（干净副本无 git 仓库，符合预期）
```

完整日志：`07_evidence/runtime_logs/clean-copy-fixr1-release.log`
（F2 第二轮从新 ZIP 重跑，2026-11-17 05:00:37–05:01:16 UTC；首轮
04:41:42–04:42:13 UTC 的日志已被覆盖）。两处与 `HOW_TO_REPRODUCE.md` §4
字面的偏离，均不影响“仅 ZIP 内容”这一验证本质，已在日志头注明：

- 复现目录用 `~/workspace/tmp-p026-clean-release`（持久磁盘）而非
  `/tmp/fixr1-clean-release`：`/tmp` 是 512M tmpfs，运行时仅剩 262M
  可用，全新 venv 装不下；内容仍是且仅是 ZIP 解压物。
- 协调员先前留下的 `clean-copy-fixr1.log`（03:50 UTC）用的是**工作树副本**
  而非新 ZIP，且其 `s0 --repeat 1` 重放哈希为旧值 `5195fc9a…`（当时
  un-ext fixture 尚未再生）；**该日志已被从新 ZIP 的实跑取代**（首轮
  `clean-copy-fixr1-release.log`，第二轮 F2 又从新 ZIP 重跑并覆盖），
  不应再引用为 FIX-R1 干净副本证据。

## §5 五项 P1 + 三项 P2 修复验证摘要

以下每项的“验证方式”均为发布工在冻结工作树上实际跑出的测试/命令，
不是转述修复工的自述；修复内容本身以冻结 commit `8cfd7dc` 的 diff 为准
（磁盘上的 diff 证据文件仍是 `d0aa21f` 版本：`git-diff-011f523-d0aa21f.txt`，
48 文件 +4645/−475；`d0aa21f..8cfd7dc` 增量仅 `README.md` 一行重放哈希
与 `08_release/` 三文档数字修正，全树 51 文件 +4694/−519）。
修复验证摘要本轮不变（任务要求）；门禁数字按第二轮重跑更新，见 §1–§4。

| 缺陷 | 修复要点（diff 所见） | 验证方式（F 实测） |
|---|---|---|
| P1-R1-01 PDF TOCTOU | `pdf_bytes` 随 `PdfDocumentInfo` 传递；`extract_pages` 只解析已校验字节，不再无 SHA 复核重开路径；CLI 磁盘复核拒绝同尺寸同页数调换 | 新增 `tests/integration/test_toctou.py` 9 测试全部通过（含 `test_cli_rejects_swapped_pdf_same_size_same_pages`，正是 GPT 的同尺寸同页调换复现；`test_extract_pdf_rejects_swapped_file_with_expected_sha`） |
| P1-R1-02 UNLOCATABLE 错归因 | 仅可证实的抽取失败才归因 extraction；近似引用 `first_fault_stage = null`（生产 + Oracle + Golden 三方一致）；生成器修正，un-ext-09..12 再生，12 个 UN 案例均含非文本页 | 新增 `tests/unit/test_unlocatable_attribution.py` 19 测试全部通过（含 `test_un_ext_12_reproduces_gpt_findings`、`test_near_miss_cases_have_no_attributable_stage[un-ext-09..12]`、`test_unlocatable_reasons_still_split_4_4_4`）；S0 首错阶段 48/48、Golden 0 不匹配（§3）；修复记录 `07_evidence/runtime_logs/FIX_R1_UNLOCATABLE.md` |
| P1-R1-03 clean 误删无关目录 | marker 改为工具自写输出的自洽性检查；裸 `report.html` / 任意 `S0_REPORT.json` / 仅 schema 的 `report.json` 均被拒绝 | `tests/integration/test_cli.py` 中 13 个 clean 相关测试全部通过（含 `test_clean_refuses_unrelated_report_html_directory`、`test_clean_refuses_arbitrary_s0_report_json`、`test_clean_refuses_schema_only_report_json`、`test_clean_refuses_tampered_report_json/hash`；正是 GPT 删无关目录的复现） |
| P1-R1-04 报告泄露绝对路径 | schema + 运行时拒绝 POSIX/Windows/UNC/目录形式的 `document.file_name`（新规则 R-11）；错误信息脱敏，不回显原值 | 新增 `tests/unit/test_file_name_paths.py` 66 测试全部通过（15 种路径形式 × 3 层：裸名判定、bundle 解析、schema 层，另含 `test_cli_validate_gpt_repro_without_leak`、`test_cli_analyze_rejects_absolute_path_without_leak`） |
| P1-R1-05 证据不完整 | 运行日志、T012/T013 记录、license 报告、SHA256SUMS、git-diff 证据已集齐并随本包上传 Drive（见 §7 与 RELEASE_REVIEW_INDEX.md） | 本包即证据：pytest/s0/clean-copy 三份新日志、T013_FIX_RECORD.md、T012_REVIEW.md、license-report.txt、RELEASE_REVIEW_SHA256SUMS.txt（重算）、git-diff 4 文件；Drive 归档见 §7 |
| P2 S0 repeat<100 误报 PASS | `repeat < 100` 只能返回 `SMOKE_PASS`，满 100 才正式 `PASS` | 干净副本 `s0 --repeat 1` 打印 `S0_RESULT: SMOKE_PASS` + 注明（§4）；`test_s0_repeat_1_smoke_pass`、`test_s0_result_threshold` 通过 |
| P2 图像枚举异常误报 EMPTY | 图像枚举失败返回 ERROR，不再掩盖为 EMPTY | `test_image_enum_failure_is_error_not_empty`、`test_image_enum_failure_does_not_mask_real_text` 通过 |
| P2 clean-copy 不按 lock 安装 | §4 改用 `requirements.lock` 安装 | 本轮干净副本即按 lock 安装：`pip install -r pkg/requirements.lock` 退出 0，6 个直接依赖版本与 `pyproject.toml` 一致（§4） |

F 未独立重做的事（如实标记）：未在 GPT R1 原始复现步骤之外另写新的
TOCTOU/误删攻击脚本——上述新增测试本身就是对 GPT 复现的覆盖；未验证
Windows 路径在真实 Windows 上的行为（仅 Linux 下的路径字符串判定测试）。

## §6 发现的问题（已记录，未改冻结源码）

1. **文档重放哈希滞后（P2 级）——已解决（`8cfd7dc`）**：首轮记录的
   文档滞后（冻结树内 `README.md` 与 `08_release/` 三文档引用 T014 的
   重放哈希 `5195fc9a…`，而 FIX-R1 实测为 `a06b87fc…5632a3`）已在文档修正
   commit `8cfd7dc` 中更正。F2 核实：`04_source/source/README.md` 与
   `08_release/` 三文档中 `5195fc9a` 零命中，`a06b87fc` 各 1/1/1/2 处；
   新 ZIP 的 manifest 唯一变化的行即 `README.md`（见 RELEASE-03 §2）。
2. **协调员版 S0 报告 `base_commit` 不是冻结 commit——已解决**（见 §3）：
   新版 `05_tests/s0-release/S0_REPORT.json` 的 `base_commit` 已为冻结
   `8cfd7dc`；与首轮 F 在 `d0aa21f` 上的重跑逐字段一致，仅 `base_commit`
   不同。
3. **协调员旧 clean-copy 日志已过期**（见 §4）：`clean-copy-fixr1.log`
   用工作树副本且哈希为旧值，已被从新 ZIP 的实跑
   `clean-copy-fixr1-release.log` 取代（第二轮 F2 又从新 ZIP 重跑并覆盖，
   2026-11-17 05:00:37–05:01:16 UTC）；旧日志仍留在
   `07_evidence/runtime_logs/` 中，阅读时以新日志为准。

## §7 Drive 归档

FIX-R1 证据归档于 Drive `04_release` 下子文件夹
`FIX_R1_2026-11-17_d0aa21f`（文件夹 id 见 RELEASE_REVIEW_INDEX.md
定稿表；文件夹名保留 `d0aa21f`——它记录代码冻结 commit，不改名）。
上传文件清单、逐个大小 + MD5 核对结果见该索引。
共 25 文件：发布包 3 件（zip/manifest/SHA256SUMS）、S0 报告 2 件、
审查包 2 件、索引 1 件、08_release 三文档、GPT 终审 R1 提交模板、
三份 FIX-R1 运行日志、T013/T012 记录、T012 审查包 2 件、license 报告、
SHA256SUMS（重算）、git-diff 证据 4 件。第二轮（F2）对其中 15 件已变文件
做了原位换传（新 ZIP / manifest / SHA256SUMS / S0 报告 / replay-hashes /
审查包 2 件 / 索引 / 校验表 / 08_release 三文档 / 三份运行日志），其余
10 件未变，只清点核对在位。

## §8 未验证项（如实标记）

- Windows / macOS：未运行，NOT_TESTED（仅静态审查；Linux 下的 Windows
  路径字符串判定测试通过，不等于 Windows 真机通过）。
- 真实系统：S0 只覆盖 48 组冻结合成 fixture；不证明任何真实 PDF
  流水线通过。
- GPT 终审 R2 本身：不在发布工范围，是否提交由协调员决定；本包只提供
  R2 可读的证据，不预判结论。
