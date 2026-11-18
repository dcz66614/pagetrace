---
TASK_ID: P026-T012
PROJECT_ID: P026
TITLE: 独立只读代码审查
ROLE: REVIEWER
STATUS: TODO
PRIORITY: P0
DEPENDENCIES: ["T011 PASS"]
WORKSPACE: /home/hatch/workspace/p026-pagetrace
PACKAGE_ROOT: /home/hatch/workspace/p026-pagetrace/04_source/source
BASE_COMMIT: (由协调员在派发时填写)
FILE_OWNERSHIP: ["06_reviews/TASK_REVIEWS/T012_REVIEW.md", "07_evidence/REVIEW_PACKS/REVIEW_INDEX.md", "07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md", "07_evidence/REVIEW_PACKS/REVIEW_PACK_02.md", "tools/verify_review_pack.py"]
FORBIDDEN_PATHS: ["全部生产源码、测试、Golden、文档与发布文件"]
INPUTS: ["冻结候选 commit、REVIEW_INDEX.md、源码审查包、S0 / pytest 日志"]
DELIVERABLES: ["06_reviews/TASK_REVIEWS/T012_REVIEW.md", "07_evidence/REVIEW_PACKS/REVIEW_INDEX.md", "07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md", "07_evidence/REVIEW_PACKS/REVIEW_PACK_02.md", "tools/verify_review_pack.py"]
ACCEPTANCE_COMMANDS: ["python tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md", "sha256sum -c 07_evidence/REVIEW_PACKS/REVIEW_PACK_SHA256SUMS.txt"]
EVIDENCE_REQUIRED: ["逐文件审查覆盖表、P0/P1/P2 缺陷条目、引用代码行/文件 hash、审查模型与独立会话标识"]
REVIEWER: 独立新会话
MAX_RETRIES_PER_MODEL: 2
---

# T012 — 独立只读代码审查

**工时：** 6h；**依赖：** T011 PASS；**优先级：** P0

## 目标

由不同模型/独立新会话检查核心代码、schema、依赖、测试覆盖和隐私边界。只读审查，不写源码。

## 输出路径（相对 PACKAGE_ROOT `04_source/source/`，除非另有说明）

- 06_reviews/TASK_REVIEWS/T012_REVIEW.md
- 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
- 07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md
- 07_evidence/REVIEW_PACKS/REVIEW_PACK_02.md
- tools/verify_review_pack.py

## 允许修改

- 仅审查报告、REVIEW_PACK 与只读校验脚本 tools/verify_review_pack.py；审查 Agent 只读生产源码

## 禁止修改

- 全部生产源码、测试、Golden、文档与发布文件

## 验收命令（在 PACKAGE_ROOT 下运行）

- python tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
- sha256sum -c 07_evidence/REVIEW_PACKS/REVIEW_PACK_SHA256SUMS.txt

## 硬断言

- 审查重点：0/1-based 转换、page label 混用、跨页和重复文本、阶段归因顺序、UNKNOWN 是否被误判 PASS、PDF 资源限制、路径/内容泄露、Oracle 独立性、哈希规范化、MIT 与依赖许可证

## 证据

- 逐文件审查覆盖表、P0/P1/P2 缺陷条目、引用代码行/文件 hash、审查模型与独立会话标识

## 完成定义

主要源码/配置/测试均被覆盖；0 个未解决 P0/P1，或明确交给 T013 修复；审查者未写源码。

## 失败回退

审查包缺文件则补包，不以目录清单代替正文；发现核心缺陷进入 T013，不直接修改。

## 交接格式（完成后必须按此汇报）

```text
TASK_RESULT: DONE | FAILED | BLOCKED
TASK_ID: P026-T012
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
