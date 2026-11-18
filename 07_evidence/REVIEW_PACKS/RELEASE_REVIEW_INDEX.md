# T014 发布审查包索引（RELEASE_REVIEW_INDEX）

- 项目：P026 PageTrace 引文落页镜；任务：T014 最终冻结、发布包与 GPT 审查交接

- 基线 commit：`cfc8b94`（T013 已合并 + 控制提交；T001–T013 全部 PASS）

- 工作树：`~/workspace/p026-pagetrace-t014`，分支 `task/t014`

- 本索引覆盖**本次提交终审的全部文件**（发布包、清单、发布文档、本次审查包、终审模板、门禁证据）。

  T012 的审查包（`REVIEW_PACK_01/02.md` + `REVIEW_INDEX.md` +

  `REVIEW_PACK_SHA256SUMS.txt`）是上一轮审查的原始记录，未被覆盖或改动，

  其索引仍以 `REVIEW_INDEX.md` 为准，不在本索引重复列出。

- `sha256` 为文件写入时的完整 SHA-256；`RELEASE_REVIEW_SHA256SUMS.txt`

  为本索引所列文件的 `sha256sum` 输出（仓库根相对路径），可用

  `sha256sum -c 07_evidence/REVIEW_PACKS/RELEASE_REVIEW_SHA256SUMS.txt` 复核。

- ZIP 内 252 个源码文件的逐一哈希见 `REVIEW_PACK_RELEASE_01.md` §2

  （与 `04_source/SOURCE_MANIFEST.csv` 逐行一致），不在此重复。


## 审查包清单


| 文件 | 字节 | sha256 | 内容 |
|---|---:|---|---|
| `04_source/source-release.zip` | 1125629 | `ec4ceae6ccf96dbe03bd85c3009eeff96c95b21195ede684f59bf896bf01b215` | 源码发布包：冻结源码树 252 文件，确定性构建 |
| `04_source/SOURCE_MANIFEST.csv` | 26718 | `e118da2c301a6d43da76fa95e88885924b54dc38d6d54c0b8f9f05c8a3c2e5c0` | ZIP 内每个文件的 SHA-256 清单（252 行） |
| `04_source/SHA256SUMS.txt` | 191 | `91fad8965b8be1d78e8b466feb86727694677a5828f0fdb34e0a1b49234458cd` | 发布包 + 清单的 sha256sum 校验表 |
| `08_release/README.md` | 6191 | `f91f85e44e3ea3c0dd8f2807945d0a06dd0f22bd9738ba590f2efc38ae8c3a33` | 发布说明：内容、门禁结果、平台、已知遗留项 |
| `08_release/USER_GUIDE.md` | 7196 | `ae0f6b1b9b2f3eb0d6c5b31de6f74219ff92d766598f44731d51ea29d8b2a12c` | 用户指南：安装、四条命令、报告解读、边界 |
| `08_release/HOW_TO_REPRODUCE.md` | 6796 | `2079eff049e53896f8121777762eb27cedabc654c93c9c1694b7ba2162066a36` | 复现说明：环境、逐条命令、预期输出、venv 说明 |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_01.md` | 34402 | `c1e694e8e05d95eb2ea2c1d04f98f036ac0340ed20ca61542d6e012bc291bf7c` | 审查包 01：冻结树 252 文件逐一哈希 + 门禁证据 |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_02.md` | 6804 | `de7bdfdf12122cb9f4143cf9b0b52ead9cb6a9185eee121abb0bde1e832b9d08` | 审查包 02：独立复现证据（ZIP 一致性、pytest、S0、干净副本、venv 发现） |
| `06_reviews/GPT_FINAL_REVIEW.md` | 5810 | `79838628dc68bd11451168953ff1ade3cdf7b9113d938cbfbb004580d3320ddf` | 终审提交模板（不是终审本身；终审由协调员另行派发） |
| `05_tests/s0-release/S0_REPORT.json` | 169431 | `1b052612f9a377536f8d88c7a1fc42e340c78af93477c849b0ac7ed5a6e899bd` | S0 门禁报告（repeat 100，base_commit cfc8b94） |
| `05_tests/s0-release/replay-hashes.txt` | 6500 | `d17399e2ba52a98941c4be244621a665d65d2ee58cb03be5c8662115a7bddab9` | S0 100 次重放哈希（100 行同一哈希） |
| `07_evidence/runtime_logs/pytest-t014.log` | 831 | `600f82178fae8c1284b6101e26a093ff8e8b97f20d090b5a3e4933f1a73c1b1b` | 全量 pytest 日志：652 passed |
| `07_evidence/runtime_logs/s0-release.log` | 438 | `5a25f863baeb5b8110e36d1ada16fbbb07343a5ddbbb642e1eb58446fa2ec936` | S0 repeat-100 日志：PASS |
| `07_evidence/runtime_logs/clean-copy-t014.log` | 2743 | `7b4ed2ea74c2aba0577d0052512735d2f68297f73b8d10a3e24cca3ac8453a34` | 干净副本复现日志：validate/analyze/s0 |

## 门禁摘要（T014 实测，见 REVIEW_PACK_RELEASE_02）

- 全量 pytest：**652 passed**，0 failed（`pytest-t014.log`）。
- S0 `--repeat 100`：**PASS**；检出 48/48，首错阶段 48/48，控制误报 0，
  parity 96/96，100 次重放 1 个唯一哈希
  `5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8`。
- 干净副本（全新 venv，仅 ZIP 内容）：`validate` 退出 0，`analyze` 退出 1
  （预期），`s0 --repeat 1` **PASS**，同一重放哈希。
- `sha256sum -c 04_source/SHA256SUMS.txt`：全部 OK；ZIP ↔ manifest：252 文件 0 不匹配。
- 平台：仅 Linux x86_64 + CPython 3.12.3 实测；Windows / macOS NOT_TESTED。
- 终审范围：工程修复 + 48 组冻结合成 fixture 上的离线验收 + 交付完整性；
  不证明任何真实系统通过，不含优越性/非劣效性结论。

---
## FIX-R1 定稿（2026-11-17，发布工 F）
- 冻结 commit：`8cfd7dc`（`8cfd7dcb06b270d21e016b55365bf759002e0744`）；分支 `task/fix-r1`；工作树 `~/workspace/p026-pagetrace`。
- 冻结分两步：`d0aa21f` 为代码冻结（5 项 P1 + 3 项 P2 修复），`8cfd7dc` 为文档修正（仅改发布文档中的 T014 残留数字；冻结源码内只改 `04_source/source/README.md` 一行重放哈希）。**第二轮（F2，2026-11-17 ~05:00–05:05 UTC）**：新发布包已重建并独立核对，15 件已变文件已在 Drive 原位换传（见下表与 §2/§4），其余 10 件未变，只清点核对。首轮值（`d0aa21f` / 旧 ZIP `c51b9d32…5131`）已被取代，不再引用。
- 本节**取代**上文由修复工 D 起草的“FIX-R1 补证草稿”节：草稿中的本地证据清单已按新冻结重算，Drive 位置已填入上传后的实际文件 id；草稿本身不再保留（其 Drive 核对结论——R1 点名的缺失项当时确实不在 Drive 上——仍属实，见下文 §2）。
- 上文 T014 历史记录未改动：上文表格仍是 T014 提交时的原始值；FIX-R1 改动的文件只在本节重新计入。
- Drive 归档：`04_release` 文件夹（`1Yg5I1ZlMj7297duZcjgEiTMmtX3o44Jz`）下新建子文件夹 `FIX_R1_2026-11-17_d0aa21f`，文件夹 id：`16nQDtKj04UC_qHsXzr16BYMq6YfV2U5N`。
- `sha256` 为文件写入时的完整 SHA-256；`RELEASE_REVIEW_SHA256SUMS.txt` 为下表 31 个文件的 `sha256sum` 输出（仓库根相对路径），可用 `sha256sum -c 07_evidence/REVIEW_PACKS/RELEASE_REVIEW_SHA256SUMS.txt` 复核。本索引文件本身与校验表本身不列入该校验表（避免自指），其最终哈希见本节末。
- ZIP 内 255 个源码文件的逐一哈希见 `REVIEW_PACK_RELEASE_03.md` §2（与 `04_source/SOURCE_MANIFEST.csv` 逐行一致），不在此重复。

### 1. 审查包清单（FIX-R1，33 个上传文件；Drive id 已定稿）

| 文件 | 字节 | sha256 | Drive 文件 id | 内容 |
|---|---:|---|:---:|---|
| `04_source/source-release.zip` | 1148388 | `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b` | 1pLpbRkf_r8HeHa2XJM7Lf3dfWJPH8QQs | 源码发布包：冻结源码树 255 文件，确定性构建（第二轮重建，二次构建字节相同） |
| `04_source/SOURCE_MANIFEST.csv` | 27041 | `b6db053e8e5c11b1bfbd55e1f62e8570c0c84683b1a4191819768224b7fcc33f` | 1rbsZUdAJ7CeJq72P2zSppUAE8XGx5JiJ | ZIP 内每个文件的 SHA-256 清单（255 行；唯一变化 `README.md`） |
| `04_source/SHA256SUMS.txt` | 191 | `64c6e3ee00d0c52cc99df969e3739bb624560f3945a758bff7ceeede3dfd5e7a` | 1u0DGMPbLGWUWN151kpG4qFjdqKUbJ9ec | 发布包 + 清单的 sha256sum 校验表 |
| `05_tests/s0-release/S0_REPORT.json` | 172664 | `47980f755135dd72473d1420db37c3a3baba9632cddae698d5604ca63fc466a7` | 1I3zp7fc2jAtqLunIhdukvikAzx54Uc6v | S0 门禁报告（repeat 100；base_commit 8cfd7dc） |
| `05_tests/s0-release/replay-hashes.txt` | 6500 | `f458e1d8b4806704580a145c32150a6a880a207bffcab564781713cf44c2d357` | 1D2M1LmzgmIkddX8eSH0OqDiywqZJZaWF | S0 100 次重放哈希（100 行同一哈希 a06b87fc…） |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_03.md` | 37658 | `17900a096dee2f6dd5c127d1a18bef579a3b061514efd312fb5393711c83db92` | 1sGUROggrQW8XuoNz53v439C0kOzCaYBK | 审查包 03：冻结树 255 文件逐一哈希 + 门禁证据（第二轮重生成） |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_RELEASE_04.md` | 14142 | `8afc5961f776728993f29c65163c2ffa7630cebf98cca7f868605ca969468f80` | 1Tbr0sdLf3f-oXzplm-7kzHor2X89B46X | 审查包 04：独立复现证据（ZIP 一致性、pytest、S0、干净副本、P1/P2 修复验证；第二轮重生成） |
| `08_release/README.md` | 6561 | `9731d192ec8de34015087cc10dc241b1aef8c3aeecdd0ffa51f63edf944b57f5` | 1QYnZYzvfsE9tY3uWMD8v9sJvKo3zk_LG | 发布说明（已更新：ZIP 255 文件 / 新 SHA / 重放哈希 a06b87fc…） |
| `08_release/USER_GUIDE.md` | 7196 | `94ab976dba42189f79f4d116aa39a07108f7ba65dcdb5805c1dfec08917cca5d` | 1aK_SM2IUB8Vu0mu1XUzuim_IldG_hxWQ | 用户指南（已更新：重放哈希 a06b87fc…；754 测试） |
| `08_release/HOW_TO_REPRODUCE.md` | 8139 | `23caf8636174c024c6c91b82b0310c62e065382fa948d0328165ad42e990a20a` | 11gu3b4ROXgYlT49dxZIv6ojqfUV2R-FL | 复现说明（§4 改用 requirements.lock 安装；预期输出已更新为新 ZIP / a06b87fc… / SMOKE_PASS） |
| `06_reviews/GPT_FINAL_REVIEW.md` | 5810 | `79838628dc68bd11451168953ff1ade3cdf7b9113d938cbfbb004580d3320ddf` | 1SkVU5jewT5DJZc_VCaVPZIVLEjpc8HBh | 终审 R1 提交模板（参考件；R2 是否提交由协调员决定） |
| `07_evidence/runtime_logs/pytest-fixr1.log` | 1205 | `e9c59af9b39cf3fc6fa09dbae2b357a924c11cd3e5afed4d19d1bc558924e6a5` | 1th1aKqu9MhJyx2385ulzcUTrXBgFqkRK | 全量 pytest 日志：754 passed（F2 第二轮重跑，106.09 s） |
| `07_evidence/runtime_logs/s0-fixr1.log` | 438 | `868c5ab919f46b2796dda4bb3255a1bc6224b34cfe22245d37195ab1ec018351` | 1A7LLuPh_vBvd3tJ1vJkgmJgJJhGcJrxc | S0 repeat-100 日志：PASS（协调员在 8cfd7dc 上重跑；内容与首轮 F 重跑逐字节相同） |
| `07_evidence/runtime_logs/clean-copy-fixr1-release.log` | 7965 | `6e9a117448d3118c96ea204525234142c5f4185300b57f19c1f0ab6bfb8cc097` | 1u38e-4k95cdWWw1rmaOVx8U8vIX3ips6 | 干净副本复现日志（从新 ZIP，F2 第二轮重跑 05:00:37–05:01:16 UTC）：validate 0 / analyze 1 / s0 SMOKE_PASS |
| `07_evidence/runtime_logs/T013_FIX_RECORD.md` | 7168 | `cc34f335549190ff1654eb6187d97cd29e1646c24076b20105465fb205d18eef` | 16rO8k-xF4AJOQSd3wiaMMJVnZqKyfLu2 | T013 修复记录（R1 P1-R1-05 点名的缺失项之一） |
| `06_reviews/TASK_REVIEWS/T012_REVIEW.md` | 7864 | `cdb99df316558fb8224fc9ed3047ba63f4ce73440041959ddb1263ff255e6555` | 1nU8nmPKcLC5ZASrTZl36udVTtHEiB6R- | T012 审查报告（R1 P1-R1-05 点名的缺失项之一） |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md` | 25051 | `57dd5a77686598ad0a90efc85cb3ef22cf0ee3e15524b1a2680de1cea192a917` | 1YSx46KMIH1eJgW0F7NSm9qaSQNnZtGvW | T012 审查包 01（原始记录，未改动） |
| `07_evidence/REVIEW_PACKS/REVIEW_PACK_02.md` | 9083 | `dd30d04272845fecf0971570de0b75129c2adbdf20b71840e15bda6f3a02bebf` | 1NTHnYva-6uvq0u-3lFnxLDAGaD4glXdP | T012 审查包 02（原始记录，未改动） |
| `07_evidence/runtime_logs/license-report.txt` | 3447 | `06c17e99ba8633f85a570fc7a49b2d6d10fc613b285b3c53c797ebc6bf187d17` | 1WhHLjrptMZutKm0B6oNUl0kMJ1frffSR | 依赖 license 扫描报告：19 个 lock 条目，0 问题 |
| `07_evidence/runtime_logs/git-diff-011f523-d0aa21f-stat.txt` | 3051 | `7fbed12c257a3013d3cd0494ec4411ab83326ddea9b29f460afecce61715bcae` | 1-KoTulpdkBkT66lU-IhWlasNrs_4sjy7 | git diff 011f523..d0aa21f --stat（48 文件 +4645/−475） |
| `07_evidence/runtime_logs/git-diff-011f523-d0aa21f.txt` | 1258310 | `8cf5be1c1cdee48f7d4c09bd5bd462b587ad5ae558b584c3355041464e55d790` | 15Z8e6kil4imY0-l5cTfLtpUPBpkK96q3 | git diff 011f523..d0aa21f 完整 diff |
| `07_evidence/runtime_logs/git-diff-cfc8b94-d0aa21f-frozen-source-stat.txt` | 2289 | `5958765b08c34c9596fd7b3b092cef7327d3e0586432c158fbca2a514ca215bc` | 123U7dFHCg63hmUy7PC-BqLBCfwonTGpV | git diff cfc8b94..d0aa21f -- 04_source/source --stat（35 文件 +1962/−268） |
| `07_evidence/runtime_logs/git-diff-cfc8b94-d0aa21f-frozen-source.txt` | 188876 | `ed314076274e8aa605c3166acd6109adf1280e82db404b23148e506eddaa3e4d` | 1qkLBAKH2lEPvvhhB8YuPELfyuPFVY1fD | git diff cfc8b94..d0aa21f -- 04_source/source 完整 diff |
| `07_evidence/runtime_logs/pytest-t014.log` | 831 | `600f82178fae8c1284b6101e26a093ff8e8b97f20d090b5a3e4933f1a73c1b1b` | 10mdROdCTUbjs6Qzf6s3M6CNIhAiueB_E | T014 原始日志：全量 pytest 652 passed（R1 P1-R1-05 点名的缺失项；补传） |
| `07_evidence/runtime_logs/s0-release.log` | 438 | `5a25f863baeb5b8110e36d1ada16fbbb07343a5ddbbb642e1eb58446fa2ec936` | 1G2lwCtFZqBcMXSgkoi_dQbskTyEwpwiC | T014 原始日志：S0 repeat-100 PASS（R1 P1-R1-05 点名的缺失项；补传） |
| `07_evidence/runtime_logs/clean-copy-t014.log` | 2743 | `7b4ed2ea74c2aba0577d0052512735d2f68297f73b8d10a3e24cca3ac8453a34` | 1jNj0OBSoKV7Nl2Hp7JpSuw5D4EWcaTQT | T014 原始日志：干净副本复现（R1 P1-R1-05 点名的缺失项；补传） |
| `07_evidence/runtime_logs/git-diff-cfc8b94-011f523-stat.txt` | 1480 | `531057090a5cd6ac674bf8503333fc31d607a582e5a6f6cb9dd2f236a3803f87` | 1dsM-350C_mTMAX52ZSSMFJ-gLD6_4jgM | git diff cfc8b94..011f523 --stat（T014 本步：22 文件 +1700/−2，均为发布元数据；补传） |
| `07_evidence/runtime_logs/git-diff-cfc8b94-011f523.txt` | 301613 | `b9e2b63ec4668f68c59fcbd97590d79737653aa72a54adf66ca7d0e4d739aadf` | 1GbkADZsxkqHffxhRA6WtqSNEn0LUhlwv | git diff cfc8b94..011f523 完整 diff（T014 本步；0 处改动在 04_source/source/ 内，证明 T014 未改冻结源码；补传） |
| `07_evidence/runtime_logs/git-diff-cfc8b94-011f523-frozen-source-stat.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 15sFmVxT6-BT-5whTqtG3FFgagJrVrl1H | git diff cfc8b94..011f523 -- 04_source/source --stat（空 diff：T014 未改冻结源码；0 字节为正确值；补传） |
| `07_evidence/runtime_logs/git-diff-cfc8b94-011f523-frozen-source.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 1zheQYOCST1yu-qaktEHR8K1tpEjVXItg | git diff cfc8b94..011f523 -- 04_source/source 完整 diff（空 diff：T014 未改冻结源码；0 字节为正确值；补传） |
| `06_reviews/TASK_REVIEWS/T013_FIX_R1_REVIEW.md` | 28291 | `b506144b215e05d180211ccd83f1b9d56a212ba44216e6ae00d3258f82296589` | 1b7liBAs5V93VxwRjOiqGXKlN3WfAtfUj | 独立内部重审报告（T013 风格）：4/5 P1 CLOSED，P1-R1-05 当时 PARTIAL（缺 T014 历史证据；本次补传后已关闭） |

另有 1 个上传文件（校验表本身，不列入上表校验范围；本索引本身亦不自列——其 Drive id 见发布汇报）：

| 文件 | 字节 | sha256 | Drive 文件 id | 内容 |
|---|---:|---|:---:|---|
| `07_evidence/REVIEW_PACKS/RELEASE_REVIEW_SHA256SUMS.txt` | 3440 | `ff215d66813bfad21a0b61730fa2e6c63d227466a6de74db279e411a36c6453f` | 1XWIB8S8Kz57HGA9e3IQTdev-ehUudVci | 上表 31 个文件的 sha256sum 输出（补传后重算，31/31 OK） |

### 2. 门禁摘要（FIX-R1 发布工 F 实测，见 REVIEW_PACK_RELEASE_04）

- 全量 pytest：**754 passed**，0 failed，106.09 s（F2 第二轮重跑；首轮 99.95 s）（`pytest-fixr1.log`）。
- S0 `--repeat 100`：**PASS**；检出 48/48，首错阶段 48/48，控制误报 0，parity 96/96，100 次重放 1 个唯一哈希 `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`，Golden 0 不匹配。
- 干净副本（全新 venv，**从新 ZIP**）：`validate` 退出 0，`analyze` 退出 1（预期），`s0 --repeat 1` **SMOKE_PASS**，同一重放哈希 `a06b87fc…`。
- 独立内部重审（`06_reviews/TASK_REVIEWS/T013_FIX_R1_REVIEW.md`，2026-11-17 ~05:13–05:25 UTC）：全量 pytest **754/754**（136.25 s）与 S0 `--repeat 100` **PASS** 均已独立重跑；ZIP ↔ 冻结树 `8cfd7dc` 0 不匹配，确定性重建 SHA 与发布包完全相同；5 项 P1 中 4 项 CLOSED，P1-R1-05 当时 PARTIAL（缺 T014 历史证据）——本次补传后已关闭（见 §3）。
- `sha256sum -c 04_source/SHA256SUMS.txt`：全部 OK；ZIP ↔ manifest：255 文件 0 不匹配；ZIP 内容与冻结 commit `8cfd7dc` 的 git 树逐文件 0 内容不匹配（仅 `.gitignore` 未打包）。
- 平台：仅 Linux x86_64 + CPython 3.12.3 实测；Windows / macOS NOT_TESTED。
- 终审范围：工程修复 + 48 组冻结合成 fixture 上的离线验收 + 交付完整性；不证明任何真实系统通过，不含优越性/非劣效性结论。

### 3. 修复与改动规模

- 终审 R1 的 5 项 P1（TOCTOU、UNLOCATABLE 错归因、clean 误删、绝对路径泄露、证据不完整）与 3 项 P2（SMOKE_PASS、图像枚举 ERROR、lock 安装）均已修复，验证摘要见 `REVIEW_PACK_RELEASE_04.md` §5 与 `00_control/FIX_R1_FREEZE_REPORT.md` §3。
- 相对 T014 master `011f523`：51 文件、+4694/−519；冻结源码范围 `cfc8b94..8cfd7dc -- 04_source/source`：36 文件、+1963/−269——FIX-R1 本就改了冻结源码，与 T014 的“冻结源码零改动”不同，如实记录。（相对首轮 `d0aa21f` 的 48 文件 +4645/−475 与 35 文件 +1962/−268，只多文档修正 commit 的改动。）
- 据修复工 D 草稿记录，R1 读到的 `04_release` 12 文件中没有三份 T014 日志、T013/T012 记录、license 报告、SHA256SUMS 与 git-diff 证据；本次 25 文件上传补齐了 FIX-R1 的全部证据（含 T013/T012 记录与 license 报告）。**补传（2026-11-17 ~05:30 UTC，协调员执行）**：独立内部重审发现 R1 点名的 3 份 T014 原始日志与 T014 本步 git-diff 仍不在 Drive 上（当时发布任务的上传清单未包含它们）；现已补传 7 个文件（3 份 T014 日志 + `git-diff-cfc8b94-011f523` 的 stat 与完整 diff + 冻结源码范围的 stat 与完整 diff——后两者为空 diff，0 字节，证明 T014 未改冻结源码）及独立内部重审报告，共 8 个新文件；本节清单现为 33 个上传文件，校验表 31 个文件 31/31 OK。P1-R1-05 的历史证据缺口已关闭。

### 4. 已知残留项（见 REVIEW_PACK_RELEASE_04 §6 与冻结报告 §4）

1. ~~文档重放哈希滞后~~**已解决（`8cfd7dc`）**：首轮的 P2 级问题已在文档修正 commit 中更正；F2 核实 `5195fc9a` 在 `04_source/source/README.md` 与 `08_release/` 三文档中零命中，`a06b87fc` 各 1/1/1/2 处。
2. ~~协调员版 S0 报告 `base_commit` 不是冻结 commit~~**已解决**：新版 `05_tests/s0-release/S0_REPORT.json` 的 `base_commit` 已为冻结 `8cfd7dc`；与首轮 F 在 `d0aa21f` 上的重跑逐字段一致，仅 `base_commit` 不同。
3. 协调员旧 `clean-copy-fixr1.log` 已过期（工作树副本 + 旧哈希），以 `clean-copy-fixr1-release.log` 为准（第二轮 F2 从新 ZIP 重跑并覆盖，2026-11-17 05:00:37–05:01:16 UTC）。
4. 平台：仅 Linux x86_64 + CPython 3.12.3 实测；Windows / macOS NOT_TESTED。
5. ~~第二轮 F2 未重跑 S0 `--repeat 100`~~**已解决**：独立内部重审已亲自重跑 S0 `--repeat 100`，PASS（100 次重放 1 哈希 `a06b87fc…`，与冻结报告逐字段一致，仅 `base_commit` 为合并提交 `04cefb3`，因在已合并的 master 工作树上运行）。
