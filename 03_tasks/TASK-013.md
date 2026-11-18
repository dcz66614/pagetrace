---
TASK_ID: P026-T013
PROJECT_ID: P026
TITLE: 缺陷修复、文档、许可证与打包
ROLE: IMPLEMENTER + DOCS
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T012"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["受审查问题影响的 src/、tests/", "README.md", "docs/", "LICENSE", "NOTICE", "requirements.lock", "pyproject.toml"]
FORBIDDEN_PATHS: ["无关模块、产品目标、S0 口径、用户文件；不得删减失败样本或放宽门槛"]
INPUTS: ["T012 review、已冻结 commit、PROJECT_BOOK、实际测试日志"]
DELIVERABLES: ["受审查问题影响的 src/、tests/", "README.md", "docs/", "LICENSE", "NOTICE", "requirements.lock", "pyproject.toml"]
ACCEPTANCE_COMMANDS: ["python -m pytest -q", "python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-r13", "依赖许可证扫描命令以实际选定工具记录"]
EVIDENCE_REQUIRED: ["修复前后 diff、回归测试日志、依赖许可证报告、README / LIMITATIONS、wheel 构建日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T013 — 缺陷修复、文档、许可证与打包

**工时：** 8h；**依赖：** T012；**优先级：** P0

## 目标

修复独立审查确认的 P0/P1；完成运行说明、限制说明、MIT、依赖许可证与可重建打包。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- 受审查问题影响的 src/、tests/
- README.md
- docs/
- LICENSE
- NOTICE
- requirements.lock
- pyproject.toml

## 允许修改

- 仅审查报告列出的文件与必要文档/打包文件；每项修复单独记录

## 禁止修改

- 无关模块、产品目标、S0 口径、用户文件；不得删减失败样本或放宽门槛

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest -q
- python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-r13
- 依赖许可证扫描命令以实际选定工具记录

## 硬断言

- 所有 P0/P1 修复有回归测试；P2 可登记；MIT 文件存在；第三方许可证与版本可追溯；README 不宣传 OCR、语义事实核验或真实系统已通过

## 证据

- 修复前后 diff、回归测试日志、依赖许可证报告、README / LIMITATIONS、wheel 构建日志

## 完成定义

P0/P1 关闭；所有文档与真实能力一致；构建可重现。

## 失败回退

修复引入回归时回退该修复 commit；保留最后一份全量 PASS 基线；不通过移除测试解决问题。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T013
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
