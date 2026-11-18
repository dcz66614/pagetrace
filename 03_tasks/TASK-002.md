---
TASK_ID: P026-T002
PROJECT_ID: P026
TITLE: 合成 PDF 生成器与 48 份 Fixture Spec
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T001"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["tools/generate_fixtures.py", "fixtures/specs/", "fixtures/pdfs/", "fixtures/README.md"]
FORBIDDEN_PATHS: ["src/pagetrace/ 生产逻辑、fixtures/golden/expected.json、Oracle 代码"]
INPUTS: ["T001 schema；PROJECT_BOOK §8 的样本矩阵"]
DELIVERABLES: ["tools/generate_fixtures.py", "fixtures/specs/", "fixtures/pdfs/", "fixtures/README.md"]
ACCEPTANCE_COMMANDS: ["python tools/generate_fixtures.py --out fixtures", "python -m pytest tests/unit/test_fixture_manifest.py -q"]
EVIDENCE_REQUIRED: ["fixture manifest、PDF SHA 清单、每类至少 2 张预览截图、生成日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T002 — 合成 PDF 生成器与 48 份 Fixture Spec

**工时：** 6h；**依赖：** T001；**优先级：** P0

## 目标

生成 48 份确定性 PDF，覆盖四类故障各 12 组；每份 PDF 含至少一条正常引用控制项。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- tools/generate_fixtures.py
- fixtures/specs/
- fixtures/pdfs/
- fixtures/README.md

## 允许修改

- 上述 fixture 与生成器路径

## 禁止修改

- src/pagetrace/ 生产逻辑、fixtures/golden/expected.json、Oracle 代码

## 验收命令（在 PACKAGE_ROOT 下运行）

- python tools/generate_fixtures.py --out fixtures
- python -m pytest tests/unit/test_fixture_manifest.py -q

## 硬断言

- 每类 12 个；中文、空白页、重复文本、跨页断句、图像式无文本页均有覆盖；生成后 PDF 页数、文件 hash 与 manifest 一致；每 PDF 至少一个正常 control citation；固定生成两次结果字节哈希一致

## 证据

- fixture manifest、PDF SHA 清单、每类至少 2 张预览截图、生成日志

## 完成定义

48 份 PDF 可重复生成；spec 与 PDF 内容一一对应；生成器不依赖外部数据或网络字体下载。

## 失败回退

丢弃未通过的 fixtures 输出；保留 fixture spec 修改前版本；不得手工修 PDF 二进制绕过生成器。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T002
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
