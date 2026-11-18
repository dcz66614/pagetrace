# T012 独立只读代码审查报告

- 项目：P026 PageTrace 引文落页镜
- 任务：T012 独立只读代码审查（P0，依赖 T011 PASS 已满足）
- 基线：`2e7d0f8`（master，T011 合并后）
- 审查者：独立会话 `d470301b-fe7f-4398-a72b-170af3572a20`，模型 Muse Spark（与施工路线不同；施工多用 gpt-6-luna）
- 工作区：`~/workspace/p026-pagetrace-t012`，分支 `task/t012`
- 审查包：`07_evidence/REVIEW_PACKS/REVIEW_INDEX.md`（PACK_01 源码审查、PACK_02 复核证据）
- 校验脚本：`04_source/source/tools/verify_review_pack.py`（只读）

## 结论

**审查通过，可进 T013。0 个 P0，0 个 P1，13 个 P2**——P2 全部明确交给 T013 修复或记录，无一阻塞终审提交。审查者未写任何源码；本次提交只含审查报告、审查包与只读校验脚本。

## 审查方法（亲自复核，非转述）

- 通读全部生产源码（`src/pagetrace/` 11 个模块 + assets，3,924 行）、Oracle（`tests/oracle/` 6 个文件，1,192 行）、两份 schema、两份文档、`pyproject.toml`、`requirements.lock`、`tools/run_s0.py` / `generate_fixtures.py` / `render_previews.py`，逐文件哈希见 PACK_01 §1。
- 全量 pytest 亲自复现：**639 passed in 162.13s**，退出码 0（`TMPDIR=$PWD/.tmp`）。
- S0 双报告逐项核对：`05_tests/s0/S0_REPORT.json` 与 `05_tests/s0-final/S0_REPORT.json` 除 `base_commit` 外一致——检出 48/48（四类各 12）、阶段归因 48/48、控制误报 0、parity 96/96、Golden 0 失配、不确定误判 0、重放 100 次唯一哈希 `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`。
- 参考实现差分：`test_page_semantics.py` 参考实现 vs `contracts.py` 生产实现，250 输入组合逐项比对。
- Oracle 独立性：grep + import 图 + 全文件通读；定位算法等价性手工证明。
- 许可证：已安装发行版元数据 + Pillow 13.0.0 自带 LICENSE 原文 + 官方文档复核。
- 隐私与健壮性：`clean` 相对路径 live 运行、TypeError / reason 分歧 / 0 引用哈希探针均为本次实测。

## 硬断言核查结果

| 断言 | 结果 |
|---|---|
| 0/1-based 转换（只允许 +1/-1，布尔排除） | PASS |
| page label 混用（只查表，字符串 "7" ≠ 数字 7） | PASS |
| 跨页和重复文本（单页优先、全集返回、三元组只探测） | PASS |
| 阶段归因顺序（固定 Extraction→Chunking→Indexing→Display，首错即返） | PASS |
| UNKNOWN 误判 PASS（缺失快照 / UNKNOWN basis / null 值三道防线） | PASS |
| PDF 资源限制（50 MiB / 500 页，只可下调） | PASS |
| 路径/内容泄露（报告无 quote 原文、无时间戳、HTML 转义完整、无网络代码） | 1 P2（P2-01） |
| Oracle 独立性（仅 stdlib + pdfminer + 相对模块） | PASS（附 P2-05、P2-07） |
| 哈希规范化（§4.2 + 规范 JSON + 100 次唯一哈希） | PASS |
| MIT 与依赖许可证 | PASS（Pillow 已闭合） |

## 缺陷清单（全 P2，交 T013）

| 编号 | 缺陷 | 位置 |
|---|---|---|
| T012-P2-01 | `clean` 打印解析后的绝对路径到 stdout（§13 偏差；隐私测试未覆盖 clean） | `cli.py:377-378,405` |
| T012-P2-02 | 未校验输入的非列表 `source_page_indices0` 使 `analyze_bundle` 抛原始 `TypeError` | `compare_stages.py:577,852,857` |
| T012-P2-03 | `resolve_citation_to_index0` 的 None 守卫改变 1 处边界异常类型（协调员“仅消息不同”不精确） | `contracts.py:375-380` |
| T012-P2-04 | 越界 display 值的原因误标 `VALUE_BASIS_TYPE_MISMATCH`（verdict 正确） | `compare_stages.py:737-751` |
| T012-P2-05 | 生产与 Oracle 在 `UNKNOWN_TRACE_MISSING` 的 `reason` 上不一致（TRACE_MISSING vs null） | `compare_stages.py` / `attribute.py` |
| T012-P2-06 | `_trace_anchor_pages` docstring 宣称不存在的 display 回退 | `compare_stages.py:842-847` |
| T012-P2-07 | Oracle 三元组探针为生产穷举的子集；S0 从未演练不确定类 verdict | `tests/oracle/locate.py:92-115` |
| T012-P2-08 | 双包 import 路径（已知；`packages=["pagetrace"]` 装 stub） | `pyproject.toml:25` |
| T012-P2-09 | Pillow/reportlab 列为运行时依赖，实际只用于 fixture 生成 | `pyproject.toml:16-17` |
| T012-P2-10 | `fixtures build` 未实现（§12.1 有示例；已记录，无修复动作） | `docs/CLI.md` |
| T012-P2-11 | UN §8.1 措辞偏差：un-ext-12 全文本页（1/12；行为正确，已登记） | `fixtures/specs/un-ext-12.json` |
| T012-P2-12 | `PAGE_SEMANTICS.md` 两处表述超前于代码（字段名扫描不存在；0 引用哈希非 null） | `docs/PAGE_SEMANTICS.md` §5、§1.3 |
| T012-P2-13 | `stage_diffs_for_bundle` 把 `NEEDS_MANUAL_REVIEW` 标为 `kind="offset"`（仅测试调用） | `compare_stages.py:927-939` |

另有 3 项观察（O-1 Oracle label 样式回退、O-2 `build_entries_from_fixtures` 不摘要、O-3 越界 extraction diff kind 差异），见 PACK_01 §4，不立项。

## 已知遗留项逐一核实（任务要求）

1. **Pillow 许可证——已闭合，MIT-CMU 正确。**已安装 13.0.0 的 LICENSE 原文与官方 13.0.0 文档均写 “MIT-CMU License”；计划 §10.2 的 HPND 是旧版措辞，同一文本的不同名称。T013 更新计划措辞，不改 lock。
2. **双包 import 路径——仍成立，P2-08。**stub 与 `src/` 并存，`pyproject` 装 stub；CLI/run_s0/测试靠 `sys.path.insert(0, "src")` 绕过；已在文档中如实记录。
3. **T001 页码函数两份副本——基本成立，但协调员结论需修正，P2-03。**250 输入差分：1 处异常类型差异（`None + PDF_LABEL + 无 label_map`：参考实现 `UnresolvableLabelError`，生产实现基类 `PageSemanticsError`），另 7 处仅消息不同。
4. **UN 4/4/4 与 un-ext-12 措辞偏差——仍成立，P2-11。**Golden 记 `IMAGE_ONLY 4 / EMPTY 4 / NO_EXACT_MATCH 4`；`un-ext-12` 8 页全文本，其余 11 组均含 image/blank 页；行为正确。
5. **`fixtures build` 未实现——仍成立，P2-10。**§12.1 有示例，任务卡只要求 4 命令，CLI.md 已记录；无修复动作。
6. **CLI clean 打印解析后的绝对 TARGET——已判定，P2-01。**§13 针对持久化日志，stdout 属常规行为不假，但隐私测试对 `analyze` 的标准是“相对路径调用时 stdout 不得含绝对路径”，`clean` 不受覆盖且 `test_cli.py:292,301` 锁定了绝对路径打印。判定：T013 改为打印用户原样路径（解析路径只用于内部校验），同步更新两处测试断言。

## 验收命令（实际跑法与结果）

任务卡两条命令混合 PACKAGE_ROOT（`tools/`）与仓库根（`07_evidence/`）路径；校验脚本对 `--index` 做双重解析（先当前目录、再仓库根），两种跑法均实测通过：

```bash
# 从仓库根：
python3 04_source/source/tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
# → OK PACK_01 / OK PACK_02 / OK sums ×3 / "REVIEW PACK VERIFIED: 2 pack file(s), 3 sums entr(ies)"，退出码 0
sha256sum -c 07_evidence/REVIEW_PACKS/REVIEW_PACK_SHA256SUMS.txt
# → 3 行全部 OK，退出码 0
# 从 PACKAGE_ROOT（任务卡字面命令原样）：
cd 04_source/source && python3 tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
# → 同样 VERIFIED，退出码 0
```

> 注意：本机无 `python` 命令，实测用 `python3`；任务卡字面命令中的 `python` 在此环境须换成 `python3`。

## 交给 T013

13 个 P2（上表）；其中 P2-01、P2-02、P2-03、P2-04、P2-05、P2-12、P2-13 为代码或文档改动，P2-06、P2-08、P2-09、P2-10、P2-11 为记录/打包类。修复后须重跑全量 pytest 与 S0（P2-08 改打包布局尤其如此）。审查包缺文件问题不存在——PACK_01/PACK_02 均为正文，非目录清单。
