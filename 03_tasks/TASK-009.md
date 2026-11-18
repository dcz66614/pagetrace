---
TASK_ID: P026-T009
PROJECT_ID: P026
TITLE: CLI 分析、验证与导出
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P1
DEPENDENCIES: ["T010"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["src/pagetrace/cli.py", "tests/integration/test_cli.py", "docs/CLI.md"]
FORBIDDEN_PATHS: ["核心定位/归因算法、UI CSS/JS、Golden/Oracle"]
INPUTS: ["PDF path、trace JSON、T010 schema、T008 report renderer"]
DELIVERABLES: ["src/pagetrace/cli.py", "tests/integration/test_cli.py", "docs/CLI.md"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/integration/test_cli.py -q", "python -m pagetrace.cli validate --trace fixtures/bundles/sample.json --pdf fixtures/pdfs/sample.pdf", "python -m pagetrace.cli clean --dry-run out/case-001"]
EVIDENCE_REQUIRED: ["CLI help、正常/错误命令日志、退出码表、输出文件清单"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T009 — CLI 分析、验证与导出

**工时：** 5h；**依赖：** T010；**优先级：** P1

## 目标

将核心模块封装成可复现 CLI，支持用户自带 PDF 与 trace bundle。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- src/pagetrace/cli.py
- tests/integration/test_cli.py
- docs/CLI.md

## 允许修改

- CLI 与命令文档

## 禁止修改

- 核心定位/归因算法、UI CSS/JS、Golden/Oracle

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/integration/test_cli.py -q
- python -m pagetrace.cli validate --trace fixtures/bundles/sample.json --pdf fixtures/pdfs/sample.pdf
- python -m pagetrace.cli clean --dry-run out/case-001

## 硬断言

- analyze/validate/s0/clean 命令参数明确；analyze 支持可选 --include-snippets；输入 hash 不符返回 2；分析 FAIL 与工具崩溃退出码区分；没有 trace 时输出 UNKNOWN，不臆测阶段；输出 JSON + HTML；clean 只删除用户明确指定的 PageTrace 输出目录并先显示目标路径

## 证据

- CLI help、正常/错误命令日志、退出码表、输出文件清单

## 完成定义

新用户可按 README 命令从本地 PDF 和 bundle 得到报告。

## 失败回退

回退 CLI 分支；不通过隐藏异常或将所有错误返回 0。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T009
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
