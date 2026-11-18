---
TASK_ID: P026-T005
PROJECT_ID: P026
TITLE: 四栏联动交互原型
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P1
DEPENDENCIES: ["T004"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["prototypes/report-prototype.html", "prototypes/report-prototype.css", "prototypes/report-prototype.js", "tests/prototypes/"]
FORBIDDEN_PATHS: ["src/pagetrace/ 生产模块、Golden、Oracle、CLI"]
INPUTS: ["T002 合成样本、T003 定位输出、T004 verdict / stage diff"]
DELIVERABLES: ["prototypes/report-prototype.html", "prototypes/report-prototype.css", "prototypes/report-prototype.js", "tests/prototypes/"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/prototypes -q", "用实际浏览器打开 prototypes/report-prototype.html"]
EVIDENCE_REQUIRED: ["原型截图、浏览器版本、交互录屏或逐步截图、测试日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T005 — 四栏联动交互原型

**工时：** 6h；**依赖：** T004；**优先级：** P1

## 目标

在 S0 前做出四栏本地交互原型，验证错误页码、阶段差异和正确来源位置能被清晰呈现。不阻断 S0，不改算法门槛。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- prototypes/report-prototype.html
- prototypes/report-prototype.css
- prototypes/report-prototype.js
- tests/prototypes/

## 允许修改

- prototypes 与原型测试；不进入正式 src UI

## 禁止修改

- src/pagetrace/ 生产模块、Golden、Oracle、CLI

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/prototypes -q
- 用实际浏览器打开 prototypes/report-prototype.html

## 硬断言

- 四栏分别显示 PDF 真值、抽取、chunk/index、最终引用；选中 citation 时四栏联动；错误页码、首错阶段、正确来源位置三项同时可见；UNKNOWN/AMBIGUOUS/UNLOCATABLE 不显示为 PASS；无 CDN 或网络请求

## 证据

- 原型截图、浏览器版本、交互录屏或逐步截图、测试日志

## 完成定义

原型能用至少 4 个不同故障案例演示定位结果；不要求此时具备正式报告导出。

## 失败回退

原型不阻断 S0 核心；若原型表现不清晰，保留 JSON 输出并在 T008 生产 UI 中重做，不改动算法门槛。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T005
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
