# T014 审查包 RELEASE-02 — 独立复现证据（实测数据）

- 项目：P026 PageTrace 引文落页镜；任务：T014 最终冻结、发布包与 GPT 审查交接
- 基线：`cfc8b94`；工作树：`~/workspace/p026-pagetrace-t014`，分支 `task/t014`
- 本包所列数字均为 T014 亲自跑出的结果，不是转述施工汇报（T014 本人即执行者；
  以下命令均在 worktree 内执行，Python 为 `04_source/source/.venv/bin/python`，
  即指向主仓库 venv 的符号链接）。
- T012 的 `REVIEW_PACK_01/02.md` + `REVIEW_INDEX.md` +
  `REVIEW_PACK_SHA256SUMS.txt` 未被覆盖或改动。

## §1 ZIP ↔ manifest 一致性：252 文件，0 不匹配

构建命令（构建脚本在 `/tmp/t014-build-release.py`，仓库外；确定性构建：
排序后的文件顺序、固定 1980-01-01 时间戳、固定 0o644 权限、deflate）：

```bash
python3 /tmp/t014-build-release.py ~/workspace/p026-pagetrace-t014
# files: 252
# zip: 04_source/source-release.zip 1125629 bytes
#   sha256=ec4ceae6ccf96dbe03bd85c3009eeff96c95b21195ede684f59bf896bf01b215
# manifest: 04_source/SOURCE_MANIFEST.csv
#   sha256=e118da2c301a6d43da76fa95e88885924b54dc38d6d54c0b8f9f05c8a3c2e5c0
sha256sum -c 04_source/SHA256SUMS.txt
# 04_source/source-release.zip: OK
# 04_source/SOURCE_MANIFEST.csv: OK
```

独立复核（`zipfile` + `csv`，逐文件哈希与字节数比对）：

```text
zip entries: 252  manifest rows: 252
namelist == manifest order: True
forbidden entries: []
hash/size mismatches inside zip: 0
files containing absolute home paths: []
distinct zip dates: [(1980, 1, 1, 0, 0, 0)]
```

确定性复核：删除后重建，SHA-256 与首次构建完全相同
（`ec4ceae6…215`，两次构建）。禁止内容检查：ZIP 内无 `__pycache__` /
`*.pyc` / `.venv` / `.tmp` 条目；唯一的 PDF 是 48 份合成 fixture
（`fixtures/pdfs/`）；全部文本文件对 `/home/hatch`、`/home/sam`、
`C:\Users` 零命中。

## §2 全量 pytest 复现：652 passed（worktree 代码）

```bash
cd 04_source/source
PYTHONPATH=$PWD/src TMPDIR=$PWD/.tmp .venv/bin/python -m pytest -q
# 652 passed in 90.56s (0:01:30)，退出码 0
```

日志：`07_evidence/runtime_logs/pytest-t014.log`。分文件计数
（`pytest --collect-only -q` 实测，与总数 652 一致）：
`test_bundle.py` 291、`test_verdicts.py` 164、
`test_page_semantics.py` 50、`test_extract.py` 19、`test_locate.py` 15、
`test_fixture_manifest.py` 7、`test_cli.py` 23、`test_html_report.py` 14、
`test_oracle_parity.py` 4、`test_e2e.py` 14、`test_oracle.py` 21、
`test_privacy.py` 11、`test_prototype.py` 10、`test_run_s0.py` 9。

## §3 S0 复现：PASS，100 次重放 1 个唯一哈希

```bash
cd 04_source/source
PYTHONPATH=$PWD/src TMPDIR=$PWD/.tmp .venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 100 --out 05_tests/s0-release
# S0_RESULT: PASS（02:56:25–03:06:08 UTC，约 9 分 43 秒；退出码 0）
```

`05_tests/s0-release/S0_REPORT.json`（`base_commit`
`cfc8b9494500f5d8f9b66ae46e14844fe6e2fa65`，即工作树 HEAD）：
`counts = {detection: 48, first_fault_stage: 48,
control_false_positives: 0, parity_citations_matching: 96,
parity_mismatches: 0, replay_unique_hashes: 1, golden_mismatches: 0,
uncertainty_violations: 0}`；`replay.unique_hashes =
[5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8]`；
`golden_sha256 =
417e3ed38e9086bbb8092593231d9ae9bcc3f058852bfcb678e6f6f5149f039c`。
`replay-hashes.txt`：100 行，全部相同。日志：
`07_evidence/runtime_logs/s0-release.log`。

## §4 干净副本复现（仅 ZIP 内容，全新 venv）：PASS

```bash
rm -rf /tmp/t014-clean && mkdir -p /tmp/t014-clean && cd /tmp/t014-clean
unzip -q <worktree>/04_source/source-release.zip -d pkg
python3 -m venv venv
./venv/bin/pip install -e "./pkg[dev]"     # 唯一需要网络的步骤；退出 0
cd pkg
./../venv/bin/python -m pagetrace.cli --help
# 退出 0
./../venv/bin/python -m pagetrace.cli validate \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --pdf fixtures/pdfs/po-ext-01.pdf
# VALID: bundle is a well-formed pagetrace.bundle/v1 document
# document hash: MATCH；退出 0
./../venv/bin/python -m pagetrace.cli analyze \
  --pdf fixtures/pdfs/po-ext-01.pdf \
  --trace fixtures/bundles/po-ext-01.trace.json \
  --out /tmp/t014-clean/out-po-ext-01
# citations: 2 (PASS 1, FAIL 1)；cite-fault FAIL_PAGE_OFFSET /
#   PAGE_OFFSET / extraction；report.json 为 pagetrace.report/v1；
#   退出 1（预期：含 FAIL 引用，不是工具崩溃）
TMPDIR=$PWD/.tmp ./../venv/bin/python -m pagetrace.cli s0 \
  --suite fixtures --repeat 1 --out /tmp/t014-clean/s0-clean
# S0_RESULT: PASS；replay hash 5195fc9a…f33f8（与 100 次门禁相同）；退出 0
```

完整日志：`07_evidence/runtime_logs/clean-copy-t014.log`。
（`/tmp/t014-clean` 本身是临时目录，已按任务要求不作为证据路径；
可凭本包 + `HOW_TO_REPRODUCE.md` §4 完整重建。）

## §5 发现并已处置的问题：共享 venv 的 editable 安装指向主仓库

T014 执行中发现一个真实的证据路径问题，已处置并记录（不是源码缺陷，
不改冻结代码）：

- 现象：按任务卡字面命令（不带 `PYTHONPATH`）在 worktree 的
  `04_source/source/` 下跑 S0，报告写到了**主仓库**的
  `05_tests/s0-release/`，而不是 worktree 的同名目录。
- 根因：worktree 的 `.venv` 是指向主仓库 venv 的符号链接（任务卡指定），
  该 venv 的 editable 安装指向主仓库的 `src/`；`cli.py` 用
  `Path(__file__).resolve().parents[2]` 推导 `PACKAGE_ROOT`，于是
  `run_s0.py` 的 `REPO_ROOT` 也落在主仓库。两棵树在 `cfc8b94` 上字节相同，
  所以首轮 S0 的数字本身正确（PASS，同一哈希），但证据不在 worktree。
- 处置：删除主仓库被误写的 `05_tests/s0-release/`（untracked 目录，主仓库
  `git status` 已恢复干净）；pytest 与 S0 用 `PYTHONPATH=$PWD/src` 重跑，
  事先验证 `pagetrace.__file__` 确为
  `.../p026-pagetrace-t014/04_source/source/src/pagetrace/__init__.py`；
  重跑的 S0 报告落在 worktree `05_tests/s0-release/`，
  `base_commit` 为工作树 HEAD `cfc8b94`。本包 §2/§3 引用的即重跑结果。
- 记录位置：`08_release/HOW_TO_REPRODUCE.md` §2（方框说明）与本包本节。
  建议后续任务沿用 `PYTHONPATH=$PWD/src` 的跑法；是否修 `cli.py` 的
  路径推导属 T015+ 决策，T014 不动冻结源码。

## §6 未验证项（如实标记）

- Windows / macOS：未运行，NOT_TESTED（仅静态审查）。
- 真实系统：S0 只覆盖 48 组冻结合成 fixture；不证明任何真实 PDF
  流水线通过。
- GPT 终审本身：不在 T014 范围内，模板见 `06_reviews/GPT_FINAL_REVIEW.md`。
