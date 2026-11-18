---
TASK_ID: P026-T010
PROJECT_ID: P026
TITLE: Bundle 归一化与 Schema 校验
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P1
DEPENDENCIES: ["T001", "T007 PASS"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["src/pagetrace/contracts.py", "src/pagetrace/trace_bundle.py", "contracts/", "tests/unit/test_bundle.py"]
FORBIDDEN_PATHS: ["PDF extractor、locator、verdict algorithm、UI"]
INPUTS: ["T001 JSON Schema、四阶段样例、Open WebUI/RAGFlow 公开字段语义参考"]
DELIVERABLES: ["src/pagetrace/contracts.py", "src/pagetrace/trace_bundle.py", "contracts/", "tests/unit/test_bundle.py"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/unit/test_bundle.py -q"]
EVIDENCE_REQUIRED: ["schema valid/invalid fixture、字段映射表、测试日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T010 — Bundle 归一化与 Schema 校验

**工时：** 6h；**依赖：** T001、T007 PASS；**优先级：** P1

## 目标

实现 pagetrace.bundle/v1 的解析、字段校验、原始值保留与缺失阶段状态。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- src/pagetrace/contracts.py
- src/pagetrace/trace_bundle.py
- contracts/
- tests/unit/test_bundle.py

## 允许修改

- bundle parser / contract files 与测试

## 禁止修改

- PDF extractor、locator、verdict algorithm、UI

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/unit/test_bundle.py -q

## 硬断言

- schema 版本错误拒绝；原始 page value/basis 不丢失；缺失 stage 有显式记录；0/1-based 不隐式转换；越界页、重复 id、hash 不匹配拒绝或返回明确错误

## 证据

- schema valid/invalid fixture、字段映射表、测试日志

## 完成定义

至少 20 个合法/非法 bundle fixture 全通过；未知字段策略有文档（默认保留或拒绝须固定）。

## 失败回退

回退 parser 分支；不得在 CLI 层临时猜测字段含义。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T010
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
