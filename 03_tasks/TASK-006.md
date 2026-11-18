---
TASK_ID: P026-T006
PROJECT_ID: P026
TITLE: Golden Fixtures 与独立 Oracle
ROLE: IMPLEMENTER + 独立 QA
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T002", "T003", "T004", "T005"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["fixtures/golden/expected.json", "tests/oracle/", "tests/integration/test_oracle_parity.py"]
FORBIDDEN_PATHS: ["src/pagetrace/ 生产算法、fixture PDF 字节、S0 gate runner"]
INPUTS: ["48 PDF、fixture specs、项目书 S0 门槛"]
DELIVERABLES: ["fixtures/golden/expected.json", "tests/oracle/", "tests/integration/test_oracle_parity.py"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/oracle tests/integration/test_oracle_parity.py -q"]
EVIDENCE_REQUIRED: ["Oracle 独立性 grep / import graph、Golden 审核表、pdfminer 与 pypdf 页文本对照日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T006 — Golden Fixtures 与独立 Oracle

**工时：** 6h；**依赖：** T002、T003、T004、T005；**优先级：** P0

## 目标

为 48 组故障和控制引用建立人工 Golden 真值；以独立 pdfminer.six 路径与独立代码核验。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- fixtures/golden/expected.json
- tests/oracle/
- tests/integration/test_oracle_parity.py

## 允许修改

- Golden、Oracle、parity tests

## 禁止修改

- src/pagetrace/ 生产算法、fixture PDF 字节、S0 gate runner

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/oracle tests/integration/test_oracle_parity.py -q

## 硬断言

- Oracle 不 import pagetrace；不共享 normalize/locate/compare/verdict 代码；Golden 不由生产实现输出反向生成；48 个预期故障类别、阶段、页集合逐一有独立说明；控制引用全部 PASS

## 证据

- Oracle 独立性 grep / import graph、Golden 审核表、pdfminer 与 pypdf 页文本对照日志

## 完成定义

独立 Oracle 可从 fixture spec + PDF 产生期望结论；所有 Golden 项有来源依据。

## 失败回退

Oracle 不独立则任务 FAIL；重写独立实现，不允许把生产输出复制为 Golden。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T006
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
