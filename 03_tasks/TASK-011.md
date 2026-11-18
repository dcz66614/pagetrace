---
TASK_ID: P026-T011
PROJECT_ID: P026
TITLE: 集成、端到端与隐私回归
ROLE: INTEGRATOR
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T008", "T009", "T010"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["tests/e2e/", "tests/privacy/", "05_tests/test-results/", "05_tests/TEST_PLAN.md"]
FORBIDDEN_PATHS: ["已冻结的 Golden、核心算法和生产 UI；发现缺陷须另派 FIX 任务，不在测试任务中直接改业务代码"]
INPUTS: ["所有 PASS 分支、S0 suite、CLI/UI schema"]
DELIVERABLES: ["tests/e2e/", "tests/privacy/", "05_tests/test-results/", "05_tests/TEST_PLAN.md"]
ACCEPTANCE_COMMANDS: ["python -m pytest -q", "python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-final"]
EVIDENCE_REQUIRED: ["全量 pytest 日志、S0 final JSON、隐私扫描日志、UI 截图与浏览器版本"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T011 — 集成、端到端与隐私回归

**工时：** 7h；**依赖：** T008、T009、T010；**优先级：** P0

## 目标

从 PDF + trace 到 JSON/HTML 报告完成完整端到端验证，并确认隐私约束。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- tests/e2e/
- tests/privacy/
- 05_tests/test-results/
- 05_tests/TEST_PLAN.md

## 允许修改

- 集成测试、测试计划、必要的测试 fixture

## 禁止修改

- 已冻结的 Golden、核心算法和生产 UI；发现缺陷须另派 FIX 任务，不在测试任务中直接改业务代码

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest -q
- python -m pagetrace.cli s0 --suite fixtures --repeat 100 --out 05_tests/s0-final

## 硬断言

- CLI 端到端成功；四栏报告字段齐全；S0 结果不变；断网状态仍可运行；测试日志和报告不泄露默认禁存的全文/绝对路径；用户文件不上传

## 证据

- 全量 pytest 日志、S0 final JSON、隐私扫描日志、UI 截图与浏览器版本

## 完成定义

端到端链路在实际 VM 上运行；测试结果有真实命令与退出码。

## 失败回退

集成失败则回到对应 T008/T009/T010 任务派修；不得修改 S0 Golden 使其“适配实现”。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T011
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
