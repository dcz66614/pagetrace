---
TASK_ID: P026-T008
PROJECT_ID: P026
TITLE: 四栏联动 HTML 报告
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P1
DEPENDENCIES: ["T007 PASS"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["src/pagetrace/report_html.py", "src/pagetrace/assets/report.css", "src/pagetrace/assets/report.js", "tests/integration/test_html_report.py"]
FORBIDDEN_PATHS: ["S0 算法、bundle schema、Oracle、CLI 主入口"]
INPUTS: ["pagetrace.report/v1 JSON、PDF 与阶段证据"]
DELIVERABLES: ["src/pagetrace/report_html.py", "src/pagetrace/assets/report.css", "src/pagetrace/assets/report.js", "tests/integration/test_html_report.py"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/integration/test_html_report.py -q", "用本地浏览器打开 report.html"]
EVIDENCE_REQUIRED: ["桌面截图、窄屏截图、浏览器版本、离线网络日志、HTML 文件 hash"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T008 — 四栏联动 HTML 报告

**工时：** 7h；**依赖：** T007 PASS；**优先级：** P1

## 目标

实现本地离线四栏交互视图与“错误页码 → 错误环节 → 正确来源位置”表。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- src/pagetrace/report_html.py
- src/pagetrace/assets/report.css
- src/pagetrace/assets/report.js
- tests/integration/test_html_report.py

## 允许修改

- HTML/CSS/JS 报告模块与对应测试

## 禁止修改

- S0 算法、bundle schema、Oracle、CLI 主入口

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/integration/test_html_report.py -q
- 用本地浏览器打开 report.html

## 硬断言

- 四栏分别显示 PDF 真值、抽取、chunk/index、最终引用；点击 citation 四栏同步；过滤故障类型/阶段/状态；UNKNOWN/AMBIGUOUS 不显示为 PASS；无任何外部网络请求

## 证据

- 桌面截图、窄屏截图、浏览器版本、离线网络日志、HTML 文件 hash

## 完成定义

本地文件双击即可打开报告；无需 npm build server、CDN 或 API。

## 失败回退

回退 UI 分支；保留 JSON 报告可用，不让 UI 缺陷影响 S0 核心。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T008
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
