# T012 审查包索引（REVIEW_INDEX）

- 项目：P026 PageTrace 引文落页镜；任务：T012 独立只读代码审查
- 基线 commit：`2e7d0f8`（master，T011 合并后）
- 审查者：独立会话 `d470301b-fe7f-4398-a72b-170af3572a20`，模型 Muse Spark（与施工路线不同）
- 审查报告：`06_reviews/TASK_REVIEWS/T012_REVIEW.md`
- 校验脚本：`04_source/source/tools/verify_review_pack.py`（只读；见下“验收命令”）

## 审查包清单

路径相对仓库根。`sha256` 为文件写入时的完整 SHA-256；校验脚本逐项复核。

| 包 | 路径 | sha256 | 内容 |
|---|---|---|---|
| PACK_01 | `07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md` | `57dd5a77686598ad0a90efc85cb3ef22cf0ee3e15524b1a2680de1cea192a917` | 源码审查：逐文件覆盖表（哈希 + 行数）、硬断言逐项核查（代码行原文）、13 个 P2 缺陷条目、观察 |
| PACK_02 | `07_evidence/REVIEW_PACKS/REVIEW_PACK_02.md` | `dd30d04272845fecf0971570de0b75129c2adbdf20b71840e15bda6f3a02bebf` | 复核证据：pytest 639 复现、S0 双报告核对、250 输入差分、Oracle 独立性、许可证与隐私实测、健壮性探针 |

另有 `07_evidence/REVIEW_PACKS/REVIEW_PACK_SHA256SUMS.txt`（本索引所列文件的 `sha256sum` 输出，仓库根相对路径）。

## 审查结论（摘要）

- 0 个 P0，0 个 P1，13 个 P2，全部明确交给 T013 修复或记录；无一阻塞终审提交。
- S0 基线复核一致：48/48 检出、48/48 阶段归因、0 控制误报、parity 96/96、重放哈希 `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`（100 次唯一）；全量 pytest 639 通过已亲自复现。
- 已知遗留项逐一核实：Pillow 许可证已闭合（MIT-CMU 对 13.0.0 正确，计划 §10.2 的 HPND 措辞过时）；双包 import 路径仍在（P2-08）；T001 页码函数双副本差分 250 输入仅 1 处异常类型差异（P2-03，协调员“仅消息不同”不精确）；UN 4/4/4 与 un-ext-12 措辞偏差仍成立（P2-11）；`fixtures build` 未实现且已记录（P2-10）；`clean` 打印解析后绝对路径，判定为 P2、T013 改为打印用户原样路径（P2-01）。
- 审查者未写源码；本次提交只含审查报告、审查包与只读校验脚本。

## 验收命令（实际跑法）

任务卡的两条验收命令混合了 PACKAGE_ROOT（`tools/`）与仓库根（`07_evidence/`）路径；校验脚本自行处理：`--index` 先按当前目录解析，再按仓库根解析（脚本所在 `04_source/source/tools/` 的 `parents[3]`）。以下两种跑法均已实测通过（见 T012 审查报告）：

```bash
# 从仓库根（任务卡字面命令的 tools/ 路径需补 PACKAGE_ROOT 前缀）：
python 04_source/source/tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
sha256sum -c 07_evidence/REVIEW_PACKS/REVIEW_PACK_SHA256SUMS.txt

# 从 PACKAGE_ROOT（任务卡字面命令原样）：
cd 04_source/source
python tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md
```

> 注意：任务卡字面命令 `python tools/verify_review_pack.py --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md` 只有在 PACKAGE_ROOT 下运行才成立（`tools/` 在 PACKAGE_ROOT 内，`07_evidence/` 在仓库根）；脚本对 `--index` 的双重解析使两种跑法都通，交接中如实记录。
