---
TASK_ID: P026-T003
PROJECT_ID: P026
TITLE: pypdf 逐页抽取、Quote 定位与候选页
ROLE: IMPLEMENTER
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T001", "T002"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["src/pagetrace/pdf_input.py", "src/pagetrace/extract.py", "src/pagetrace/normalize.py", "src/pagetrace/locate.py", "tests/unit/test_extract.py", "tests/unit/test_locate.py"]
FORBIDDEN_PATHS: ["四类故障 verdict、stage comparator、Oracle、HTML UI"]
INPUTS: ["PDF 样本、T001 schema、T002 fixture PDFs"]
DELIVERABLES: ["src/pagetrace/pdf_input.py", "src/pagetrace/extract.py", "src/pagetrace/normalize.py", "src/pagetrace/locate.py", "tests/unit/test_extract.py", "tests/unit/test_locate.py"]
ACCEPTANCE_COMMANDS: ["python -m pytest tests/unit/test_extract.py tests/unit/test_locate.py -q"]
EVIDENCE_REQUIRED: ["每页 extraction JSON、页数/hash 对照、中文/重复句/跨页/扫描页定位输出、异常输入日志"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T003 — pypdf 逐页抽取、Quote 定位与候选页

**工时：** 8h；**依赖：** T001、T002；**优先级：** P0

## 目标

完成 PDF 输入校验、逐页文本抽取、页标签读取、规范化 quote 定位、重复文本候选集合与相邻页跨页定位。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- src/pagetrace/pdf_input.py
- src/pagetrace/extract.py
- src/pagetrace/normalize.py
- src/pagetrace/locate.py
- tests/unit/test_extract.py
- tests/unit/test_locate.py

## 允许修改

- 上述模块与测试

## 禁止修改

- 四类故障 verdict、stage comparator、Oracle、HTML UI

## 验收命令（在 PACKAGE_ROOT 下运行）

- python -m pytest tests/unit/test_extract.py tests/unit/test_locate.py -q

## 硬断言

- 页数与 PDF reader 一致；物理页索引连续从 0 开始；空白/图像页返回 EMPTY/IMAGE_ONLY 或诚实的 EMPTY；加密/损坏/超限输入返回受控错误；默认拒绝超过 50 MiB 或 500 页的输入；NFC 与空白折叠固定；标点/大小写/全半角不做模糊替换；同句多页返回所有候选；跨相邻页引用返回完整页集合；0 候选不猜测；不启动 OCR

## 证据

- 每页 extraction JSON、页数/hash 对照、中文/重复句/跨页/扫描页定位输出、异常输入日志

## 完成定义

48 份 PDF 均可读入；所有页都有记录或明确错误；locator 不依赖语义模型；无 silent skip。

## 失败回退

不合并；保留 pypdf 生产路径；不通过换用未审查的 AGPL 工具规避问题。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T003
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
