---
TASK_ID: P026-T014
PROJECT_ID: P026
TITLE: 最终冻结、发布包与 GPT 审查交接
ROLE: RELEASE
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T013"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["04_source/source-release.zip", "04_source/SOURCE_MANIFEST.csv", "04_source/SHA256SUMS.txt", "08_release/README.md", "08_release/USER_GUIDE.md", "08_release/HOW_TO_REPRODUCE.md", "07_evidence/REVIEW_PACKS/", "06_reviews/GPT_FINAL_REVIEW.md（模板）"]
FORBIDDEN_PATHS: ["冻结源码、Golden、依赖 lock；如需改动必须回到 T013 并重新执行 T014"]
INPUTS: ["T013 PASS commit、全量测试、S0 报告、许可证报告"]
DELIVERABLES: ["04_source/source-release.zip", "04_source/SOURCE_MANIFEST.csv", "04_source/SHA256SUMS.txt", "08_release/README.md", "08_release/USER_GUIDE.md", "08_release/HOW_TO_REPRODUCE.md", "07_evidence/REVIEW_PACKS/", "06_reviews/GPT_FINAL_REVIEW.md（模板）"]
ACCEPTANCE_COMMANDS: ["python -m pytest -q", "python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-release", "sha256sum -c 04_source/SHA256SUMS.txt", "从 ZIP 解压后的干净副本重跑核心命令"]
EVIDENCE_REQUIRED: ["最终 commit、ZIP 字节数/SHA-256、文件数、manifest、SHA256SUMS 校验日志、干净副本测试日志、截图与 REVIEW_INDEX.md"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T014 — 最终冻结、发布包与 GPT 审查交接

**工时：** 8h；**依赖：** T013；**优先级：** P0

## 目标

从干净工作树重跑门禁，生成源码发布包、清单、哈希和完整独立审查包。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- 04_source/source-release.zip
- 04_source/SOURCE_MANIFEST.csv
- 04_source/SHA256SUMS.txt
- 08_release/README.md
- 08_release/USER_GUIDE.md
- 08_release/HOW_TO_REPRODUCE.md
- 07_evidence/REVIEW_PACKS/
- 06_reviews/GPT_FINAL_REVIEW.md（模板）

## 允许修改

- 发布元数据、清单、复现说明、审查包；冻结后不得再改源码

## 禁止修改

- 冻结源码、Golden、依赖 lock；如需改动必须回到 T013 并重新执行 T014

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest -q
- python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-release
- sha256sum -c 04_source/SHA256SUMS.txt
- 从 ZIP 解压后的干净副本重跑核心命令

## 硬断言

- ZIP 内容与 manifest 一致；SHA256SUMS 全部通过；S0 与全量 pytest 真实通过；README/USER_GUIDE/LIMITATIONS 与实现一致；不含用户 PDF、密钥、缓存、venv、绝对路径；REVIEW_INDEX 覆盖全部应审查文件

## 证据

- 最终 commit、ZIP 字节数/SHA-256、文件数、manifest、SHA256SUMS 校验日志、干净副本测试日志、截图与 REVIEW_INDEX.md

## 完成定义

交付包可独立复现；Muse 能将文件链接和审查包加入 ChatGPT 项目来源；所有未验证平台如实标记。

## 失败回退

哈希不一致或干净副本失败时，不冻结、不上传为正式 release；回退 T013 修复后重新运行 T014。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T014
BASE_COMMIT: ...
RESULT_COMMIT: ...
CHANGED_FILES: [路径 + 变更摘要]
COMMANDS_RUN: [完整命令]
EXIT_CODES: [真实退出码]
EVIDENCE_PATHS: [日志/截图/报告]
TEST_COUNTS: [真实计数]
OPEN_ISSUES: [P0/P1/P2 或 NONE]
NEXT_TASKS_READY: [依赖满足的任务]
ROLLBACK_POINT: [commit / worktree]
```
