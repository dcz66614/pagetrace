---
TASK_ID: P026-T007
PROJECT_ID: P026
TITLE: S0 门禁与 100 次规范化重放
ROLE: QA
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T005", "T006"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["tools/run_s0.py", "tests/s0/", "05_tests/s0/S0_REPORT.json", "05_tests/s0/replay-hashes.txt"]
FORBIDDEN_PATHS: ["生产算法、Golden expected（除非独立审查证明 Golden 错误并留下 ADR）、UI"]
INPUTS: ["48 PDFs、Golden、生产实现、Oracle"]
DELIVERABLES: ["tools/run_s0.py", "tests/s0/", "05_tests/s0/S0_REPORT.json", "05_tests/s0/replay-hashes.txt"]
ACCEPTANCE_COMMANDS: ["python tools/run_s0.py --suite fixtures --repeat 100 --out 05_tests/s0"]
EVIDENCE_REQUIRED: ["完整命令、stdout/stderr、退出码、每项计数、100 个 hash 或唯一 hash 摘要、fixture / golden SHA"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T007 — S0 门禁与 100 次规范化重放

**工时：** 5h；**依赖：** T005、T006；**优先级：** P0

## 目标

将 S0 的所有阻断条件变成一条可重复运行命令。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- tools/run_s0.py
- tests/s0/
- 05_tests/s0/S0_REPORT.json
- 05_tests/s0/replay-hashes.txt

## 允许修改

- S0 runner、S0 tests、S0 报告模板

## 禁止修改

- 生产算法、Golden expected（除非独立审查证明 Golden 错误并留下 ADR）、UI

## 验收命令（在 PACKAGE_ROOT 下运行）

- python tools/run_s0.py --suite fixtures --repeat 100 --out 05_tests/s0

## 硬断言

- 48/48 故障检出；48/48 first stage 正确；正常控制误报 0；生产与 Oracle parity 全部一致；100 次规范化哈希唯一值为 1；任一门失败退出码 4

## 证据

- 完整命令、stdout/stderr、退出码、每项计数、100 个 hash 或唯一 hash 摘要、fixture / golden SHA

## 完成定义

一条命令可从干净工作树复现全部 S0 指标；S0 报告不写预期结果冒充实际结果。

## 失败回退

S0 FAIL，停止 S1；按具体失败回退到 T003/T004/T005/T006 修复，重新开会话和重跑全 S0。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T007
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
