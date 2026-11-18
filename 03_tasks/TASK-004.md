---
TASK_ID: P026-T004
PROJECT_ID: P026
TITLE: 四类故障判定与首错阶段归因
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T003"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["src/pagetrace/compare_stages.py", "src/pagetrace/verdicts.py", "tests/unit/test_verdicts.py"]
FORBIDDEN_PATHS: ["fixture 生成器、Golden expected、Oracle、UI"]
INPUTS: ["PageTextRecord、QuoteMatch、TraceBundle、PROJECT_BOOK §5 与 §7"]
DELIVERABLES: ["src/pagetrace/compare_stages.py", "src/pagetrace/verdicts.py", "tests/unit/test_verdicts.py"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/unit/test_verdicts.py -q"]
EVIDENCE_REQUIRED: ["每类至少 3 个阶段定位样例；stage diff JSON；测试日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T004 — 四类故障判定与首错阶段归因

**工时：** 6h；**依赖：** T003；**优先级：** P0

## 目标

按 Extraction → Chunking → Indexing → Display 顺序比较来源页身份，识别四类故障并定位 first divergence。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- src/pagetrace/compare_stages.py
- src/pagetrace/verdicts.py
- tests/unit/test_verdicts.py

## 允许修改

- 上述模块与测试

## 禁止修改

- fixture 生成器、Golden expected、Oracle、UI

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/unit/test_verdicts.py -q

## 硬断言

- PAGE_OFFSET、PAGE_METADATA_MISSING、DUPLICATE_TEXT_AMBIGUITY、UNLOCATABLE 各有正反例；首个差异阶段必须准确；trace 缺失输出 UNKNOWN；扫描页不把无文本误判为引用不存在；重复文本不得强行选择单页

## 证据

- 每类至少 3 个阶段定位样例；stage diff JSON；测试日志

## 完成定义

所有状态和阶段均由明确输入决定；不确定状态不被转为 PASS。

## 失败回退

回退归因分支；任何归因不确定的场景改为 UNKNOWN，不做猜测。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T004
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
