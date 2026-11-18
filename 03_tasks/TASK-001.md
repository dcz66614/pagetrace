---
TASK_ID: P026-T001
PROJECT_ID: P026
TITLE: 页码字段语义与契约冻结
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: []
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["contracts/pagetrace.bundle.v1.schema.json", "contracts/pagetrace.report.v1.schema.json", "docs/PAGE_SEMANTICS.md", "tests/unit/test_page_semantics.py", "requirements.lock", "00_control/ENVIRONMENT.md（由协调员提供环境探测结果，见任务简报）"]
FORBIDDEN_PATHS: ["PDF 解析器、CLI、UI、Golden fixtures、许可证文件"]
INPUTS: ["PROJECT_BOOK.md；Open WebUI #33603 页码基准案例"]
DELIVERABLES: ["contracts/pagetrace.bundle.v1.schema.json", "contracts/pagetrace.report.v1.schema.json", "docs/PAGE_SEMANTICS.md", "tests/unit/test_page_semantics.py", "requirements.lock", "00_control/ENVIRONMENT.md（由协调员提供环境探测结果，见任务简报）"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/unit/test_page_semantics.py -q", "python -m json.tool contracts/pagetrace.bundle.v1.schema.json", "python -m json.tool contracts/pagetrace.report.v1.schema.json"]
EVIDENCE_REQUIRED: ["schema 校验日志、字段表、至少 12 个边界 fixture 的测试输出、commit SHA"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T001 — 页码字段语义与契约冻结

**工时：** 4h；**依赖：** 无；**优先级：** P0

## 目标

把 PROJECT_BOOK.md 第 4、6 节转为机器可校验的字段契约，消除 page 语义歧义。同时记录本 VM 的真实环境（Python、CPU、内存、磁盘、浏览器、工作区绝对路径），并从当时稳定版本中选取与 Python 3.12 兼容的依赖，精确写入 requirements.lock（不要伪称已验证未来版本）。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- contracts/pagetrace.bundle.v1.schema.json
- contracts/pagetrace.report.v1.schema.json
- docs/PAGE_SEMANTICS.md
- tests/unit/test_page_semantics.py
- requirements.lock
- 00_control/ENVIRONMENT.md（由协调员提供环境探测结果，见任务简报）

## 允许修改

- 以上输出路径；新建必要的 contracts/、docs/、tests/unit/

## 禁止修改

- PDF 解析器、CLI、UI、Golden fixtures、许可证文件

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/unit/test_page_semantics.py -q
- python -m json.tool contracts/pagetrace.bundle.v1.schema.json
- python -m json.tool contracts/pagetrace.report.v1.schema.json

## 硬断言

- 0-based -> 1-based 只允许 +1；viewer 目标只能是 1-based；page label 不得做算术转换；UNKNOWN basis 不得转换；越界页拒绝

## 证据

- schema 校验日志、字段表、至少 12 个边界 fixture 的测试输出、commit SHA

## 完成定义

所有字段都有名称/类型/基准/缺省语义；无含糊裸 page；独立审查者可按文档复算示例。

## 失败回退

不合并；回退该任务分支；保持工作树基线；重新派发新会话修订。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T001
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
