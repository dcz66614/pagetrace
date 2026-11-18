# FIX-R1 审查包 RELEASE-03 — 冻结树清单与门禁证据

- 项目：P026 PageTrace 引文落页镜；任务：FIX-R1 发布（终审 R1 返修后重新冻结）

- 冻结 commit：`8cfd7dc`（`8cfd7dcb06b270d21e016b55365bf759002e0744`；“P026 FIX-R1: update release docs to FIX-R1 numbers”）

- 冻结分两步：`d0aa21f`（`d0aa21f3fdf02aa349289ac87705500b98cf817a`）为代码冻结（5 项 P1 + 3 项 P2 修复）；`8cfd7dc` 为文档修正（仅改发布文档中的 T014 残留数字：重放哈希、754 测试、Golden SHA、日志名、SMOKE_PASS 表述；冻结源码内只改 `04_source/source/README.md` 一行重放哈希，见下）。本包为第二轮重生成（发布工 F2，2026-11-17 ~05:00–05:05 UTC），以 `8cfd7dc` 为准。

- 分支 `task/fix-r1`；工作树：`~/workspace/p026-pagetrace`

- 发布包：`04_source/source-release.zip`（255 文件，1,148,388 字节，

  SHA-256 `7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b`）

- 清单：`04_source/SOURCE_MANIFEST.csv`（27,041 字节，SHA-256

  `b6db053e8e5c11b1bfbd55e1f62e8570c0c84683b1a4191819768224b7fcc33f`）

- 本包只记录 FIX-R1 冻结时 `04_source/source/` 的内容。**与 T014 不同，
  FIX-R1 改动了冻结源码**：`git diff cfc8b94..8cfd7dc -- 04_source/source --stat`
  为 36 文件、+1963/−269（相对 `d0aa21f` 的 35 文件 +1962/−268，只多
  `README.md` 一行重放哈希的改动）；相对 T014 master `011f523` 的全部改动
  为 51 文件、+4694/−519（相对 `d0aa21f` 的 48 文件 +4645/−475）。
  磁盘上的 git-diff 证据文件仍是 `d0aa21f` 版本
  （`07_evidence/runtime_logs/git-diff-cfc8b94-d0aa21f-frozen-source-stat.txt` /
  `git-diff-cfc8b94-d0aa21f-frozen-source.txt` /
  `git-diff-011f523-d0aa21f-stat.txt` / `git-diff-011f523-d0aa21f.txt`），
  `d0aa21f..8cfd7dc` 的增量可用 `git diff d0aa21f..8cfd7dc` 独立复核
  （源码内仅 `04_source/source/README.md` 一行；其余为 `08_release/` 三文档与
  `05_tests/s0*` 报告的数字修正）。

- T012 的 `REVIEW_PACK_01/02.md` + `REVIEW_INDEX.md` +
  `REVIEW_PACK_SHA256SUMS.txt` 未被覆盖或改动，仍是 T012 审查的原始记录。
  T014 的 `REVIEW_PACK_RELEASE_01/02.md` + `RELEASE_REVIEW_INDEX.md` 上文
  历史记录亦未改动；本包与 RELEASE-04 是 FIX-R1 的新审查包。


## §1 门禁结果（发布工 F 在冻结工作树独立重跑，全部真实通过）


| 门禁 | 结果 | 证据 |
|---|---|---|
| 全量 pytest（`TMPDIR=~/workspace/tmp-p026-pytest`） | **754 passed**，0 failed，106.09 s，退出 0（F2 第二轮重跑，2026-11-17 05:01:23–05:03:10 UTC；首轮 99.95 s） | `07_evidence/runtime_logs/pytest-fixr1.log` |
| S0 `--repeat 100` | **PASS**：检出 48/48（4 类各 12），首错阶段 48/48，控制误报 0，parity 96/96，100 次重放 1 个唯一哈希 `a06b87fccdfb0aa77c1b17bdd363caa3e9af5c7c4fecc88e285fb7a0be5632a3`，Golden 0 不匹配 | `05_tests/s0-release/S0_REPORT.json`、`07_evidence/runtime_logs/s0-fixr1.log` |
| 干净副本复现（全新 venv，仅 ZIP 内容） | `validate` 退出 0；`analyze` 退出 1（预期：含 1 条 FAIL）；`s0 --repeat 1` **SMOKE_PASS**，同一重放哈希 `a06b87fc…` | `07_evidence/runtime_logs/clean-copy-fixr1-release.log`，详见 REVIEW_PACK_RELEASE_04 |
| `sha256sum -c 04_source/SHA256SUMS.txt` | 两行全部 OK | 本包 §3 |
| ZIP ↔ manifest 一致性 | 255 条目逐一比对，0 哈希/字节不匹配；ZIP 内容与冻结 commit `8cfd7dc` 的 git 树逐文件比对，0 内容不匹配（仅 `.gitignore` 未打包） | REVIEW_PACK_RELEASE_04 §1 |
| ZIP 确定性 | 协调员二次构建字节相同（同一 SHA-256 `7526f511…fad6b`；F2 未重建）；本包核对：全部条目时间戳 1980-01-01、权限 0o644、namelist 与 manifest 顺序一致 | REVIEW_PACK_RELEASE_04 §1 |

分文件测试计数（`pytest --collect-only` 实测，与总数 754 一致）：
`test_bundle.py` 291、`test_verdicts.py` 164、`test_file_name_paths.py` 66（新增，P1-R1-04）、
`test_page_semantics.py` 50、`test_cli.py` 30、`test_oracle.py` 21、
`test_unlocatable_attribution.py` 19（新增，P1-R1-02）、`test_extract.py` 19、
`test_locate.py` 15、`test_html_report.py` 14、`test_e2e.py` 14、
`test_privacy.py` 11、`test_run_s0.py` 10、`test_prototype.py` 10、
`test_toctou.py` 9（新增，P1-R1-01 + 图像枚举 P2）、`test_fixture_manifest.py` 7、
`test_oracle_parity.py` 4。合计 754 = T014 基线 652 + FIX-R1 新增 102
（66 + 19 + 9 + `test_cli.py` +7 + `test_run_s0.py` +1）。

S0 说明：协调员在 `8cfd7dc` 上重跑的 `--repeat 100` 报告
（`05_tests/s0-release/S0_REPORT.json`，与 `05_tests/s0/S0_REPORT.json`
逐字节相同；`base_commit` 为 `8cfd7dcb06b270d21e016b55365bf759002e0744`）
与发布工首轮在 `d0aa21f` 上的独立重跑报告
（`07_evidence/runtime_logs/s0-fixr1-out/S0_REPORT.json`）逐字段比对，
**唯一差异是 `base_commit`**（`8cfd7dc` 对 `d0aa21f`）。counts、per_case、
input_hashes、replay、environment 全部相同；重放哈希同为 `a06b87fc…`。
第二轮 F2 未重跑 `--repeat 100`（任务范围：门禁证据以协调员重跑为准；
F2 独立重跑了全量 pytest 与干净副本，见 §1）。重跑日志见 `s0-fixr1.log`
（golden sha `9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353`，
与干净副本的 `s0 --repeat 1` 输出的 golden sha 一致）。


## §2 逐文件清单（255 文件；路径相对 `04_source/source/`，即 ZIP 内路径）


`sha256` 为完整 SHA-256，`bytes` 为文件字节数；与
`04_source/SOURCE_MANIFEST.csv` 逐行一致，审查者可用 §3 的命令独立复核。


| 文件 | 字节 | sha256 |
|---|---:|---|
| `LICENSE` | 1079 | `8c649c9d8cc18375dd52f08a0521fd7a844fdbdde71f108a3c8d04f237f0854a` |
| `NOTICE` | 2706 | `9e9e0454faa018ef39c098dae76531f44fabc3547fe5452b8f5b40ec2e63f31e` |
| `README.md` | 5316 | `dc33d686f2489bc49ce72c91758c5c50fdc3ae0c7fcc68144de725cc49ba222f` |
| `contracts/pagetrace.bundle.v1.schema.json` | 8108 | `2cf73d745aef9681087ad68c0323b5e3a83be8cd651bbbb54590542e276cd9ac` |
| `contracts/pagetrace.report.v1.schema.json` | 8719 | `a123094b033867d842d0068656c6025ebc64852af5f268d257ea2ef512288bb2` |
| `docs/CLI.md` | 8345 | `26c0cbe6aac533d48baf0c4921604c78d4f1d8b3fee4f485f5f8986f2e1d09b1` |
| `docs/LIMITATIONS.md` | 6332 | `bfda4522ec71282d99979a13b62424e7bf57450faebbeb905fa1661de4e11550` |
| `docs/PAGE_SEMANTICS.md` | 20305 | `88fa492e9a0184006740913293a0d0fc1399dffe1b1528610c10d17a9fb28147` |
| `fixtures/README.md` | 7476 | `90ead58a25f63d8bdea261feb9d3cad9af3e660b230e5fc6173cb97107bb499c` |
| `fixtures/bundles/du-chk-01.trace.json` | 2764 | `a89ccc864e135b9b983b4734eb03e3552e4719fa04a745c8b4541dc4e2d365c7` |
| `fixtures/bundles/du-chk-02.trace.json` | 3085 | `39057da3aee0eb03e36497e04fee59802e990cef3ff39ea8be7a40d52b968e2c` |
| `fixtures/bundles/du-chk-03.trace.json` | 3217 | `86491153f9fd6dc67d40a9e33bbd0a83c7aaad4e2cc89808c386b835a89d71fe` |
| `fixtures/bundles/du-chk-04.trace.json` | 3439 | `2bd4e934f1816d535f71b705a326a156c5ca549e37abd303adbf59ec1e41724e` |
| `fixtures/bundles/du-dsp-09.trace.json` | 2846 | `57d61214b646c86ff5ffe490f8af47f62b1152665049156873e434ee85ac7b2c` |
| `fixtures/bundles/du-dsp-10.trace.json` | 3082 | `23d3d04fe4da49336bf836cefe59951904a1cf2fbf28c5cf0676b8913e2b4191` |
| `fixtures/bundles/du-dsp-11.trace.json` | 3243 | `9e3b33d075f199cde92fc5aaee58e2cdbedb7550991495047b285575722b5fc4` |
| `fixtures/bundles/du-dsp-12.trace.json` | 3547 | `0c58ad1aae69fca89f8985721bfe5cb10ba3e451075f351dda81fc17c57aba85` |
| `fixtures/bundles/du-idx-05.trace.json` | 2833 | `b6ec5516aa017ffba0ea102a84538908d1ea3a2de6b4e87e61ef0b6f2baa9a2f` |
| `fixtures/bundles/du-idx-06.trace.json` | 3111 | `c3a2456cd1497895b2424ba3f612607d025dce58d4e6ee1c0232f69f91a03c5c` |
| `fixtures/bundles/du-idx-07.trace.json` | 3174 | `9978013a0e31c4d8144deb495cc03fcc5a4b0248ab5dbd367686dbb1b71e3c08` |
| `fixtures/bundles/du-idx-08.trace.json` | 3521 | `fc1349fa7fd8b619a6a7e1863a6618abc2380fd77c5e31af188d9ced24c433a7` |
| `fixtures/bundles/mm-chk-04.trace.json` | 3489 | `987d8e6e181ec8c3a1c1a686a83381dcbc606b00c17753ee0c41298d8871b0e6` |
| `fixtures/bundles/mm-chk-05.trace.json` | 2604 | `64e3ec1be8322b23580586afb005588861860c7a6408c20e398f195911a12e79` |
| `fixtures/bundles/mm-chk-06.trace.json` | 3065 | `bf339b118829ed90b04d2b29cc2fee470e7b90f0ce73c7b53a620c94ff1e6da8` |
| `fixtures/bundles/mm-dsp-10.trace.json` | 2939 | `4beb6ff16bf84490b3e2f402c0cf7650d17200d8fd71f26b778b1c089b0b53ac` |
| `fixtures/bundles/mm-dsp-11.trace.json` | 3202 | `0cdd9165050ac6a1dbdb1cbb33876fddc59dd1ad8517a5be8a42b4f9404f6405` |
| `fixtures/bundles/mm-dsp-12.trace.json` | 3569 | `22062b65723b83a783b3ca6dc20bf18a263a7a0603599d85e5f1e65c9774deed` |
| `fixtures/bundles/mm-ext-01.trace.json` | 2682 | `60dc90b733e0f60b07b6f7695f1145dc14df89879a5409292f62414f1459105e` |
| `fixtures/bundles/mm-ext-02.trace.json` | 3065 | `07442b78595de60858b0e2808ef663023149a8bcb35a882264ed0ab62eec332d` |
| `fixtures/bundles/mm-ext-03.trace.json` | 2998 | `dada533298292ec06e3044bcb13f79b9a03124d468ce5bc4b722ce4bed651dc6` |
| `fixtures/bundles/mm-idx-07.trace.json` | 3120 | `e7dff0ebacafc371c902159fd0e9405d23f1c49a38c1a5b50aa0ff0d5c7259b2` |
| `fixtures/bundles/mm-idx-08.trace.json` | 3428 | `acb6973f0d62d907882eb3fa0de168b96df5db913482179e1f2e7bb182ae0af7` |
| `fixtures/bundles/mm-idx-09.trace.json` | 2768 | `498f0b5d128d0d1e657e9624819de5b21784b38c7904865fe9a00de841c289ec` |
| `fixtures/bundles/po-chk-04.trace.json` | 3510 | `0fca7eaadc2f94e134495dfbcc26d74ebd44c08043a22a3b72b4ba0afec48347` |
| `fixtures/bundles/po-chk-05.trace.json` | 2799 | `c441458032610a0fa7b28d24825a75ce3e19a12cca06ded348c211d1f2e9d3c2` |
| `fixtures/bundles/po-chk-06.trace.json` | 3157 | `d303ec01c71839cbbe995f0d14dccd7f50370fccdc6ae250e63f405d12a5d07f` |
| `fixtures/bundles/po-dsp-10.trace.json` | 3099 | `6a761f829038f59b641675220ba1dd59af50b0304d7312acb21fcb4c30d9ecdd` |
| `fixtures/bundles/po-dsp-11.trace.json` | 3196 | `b127a0187608ba0e69ba2ae9b54d5e71fdaa67e090a0f72657b52c205607c386` |
| `fixtures/bundles/po-dsp-12.trace.json` | 3551 | `9b47a350c7d6abe47a7ede3d2a635879ca7c952ffbde2844e6e6972a6f9a92e5` |
| `fixtures/bundles/po-ext-01.trace.json` | 2799 | `db6c5e0b99f208049387cba5a146d45af839436709bd0f435cc6952bcdaec319` |
| `fixtures/bundles/po-ext-02.trace.json` | 3155 | `0b8974dbcd98ff27dd2b5f6587b2520fdc769edf4fe27e832fca197174412819` |
| `fixtures/bundles/po-ext-03.trace.json` | 3196 | `0984eeb86d977a95779e8e155adebf54f89008ee09aae8d054bde55b4a41ffec` |
| `fixtures/bundles/po-idx-07.trace.json` | 3140 | `9a34b150b9cc5c7b48a016fadb6a1601750cd6d933c5f532647b129b7ead2f03` |
| `fixtures/bundles/po-idx-08.trace.json` | 3566 | `6c5eaab007359aa0c063b5fe35adf1b7fd6a498d9e7750b1cccc8bd107adfbc2` |
| `fixtures/bundles/po-idx-09.trace.json` | 2813 | `e35160fb558dadce31b17ddc6717301ebdee99cfb6f9450ec676aaef9e2d02e7` |
| `fixtures/bundles/un-ext-01.trace.json` | 2742 | `503218c97dd4cfb8681caff4843973bae5e8de1783d00dbccb1abeb75607fba3` |
| `fixtures/bundles/un-ext-02.trace.json` | 3038 | `a02b4bbcce94398cfbe2775834c8a8dc93a75ea1204352244cb23edfada0d4e3` |
| `fixtures/bundles/un-ext-03.trace.json` | 3140 | `b421f66154316bc50cf891c76f81f1b8c27bd6488f85a027c564bb3c4813386f` |
| `fixtures/bundles/un-ext-04.trace.json` | 3448 | `3d5e6374b7245755bd6c5ef623a287c5ef1cc93429cd2bbe90f6eeae73fa3323` |
| `fixtures/bundles/un-ext-05.trace.json` | 2737 | `8f279204155a5d18e3aeaca44250ea3148f695951aeee4cc81e150f421205d40` |
| `fixtures/bundles/un-ext-06.trace.json` | 3033 | `47451f564b0b10337d7b191bcb25a5055b6430649349b640e9d761c7916c389b` |
| `fixtures/bundles/un-ext-07.trace.json` | 3134 | `2b7fb424d3d6cac2098bab0bd745118a1e92fe7e532307f3ddf8d22c8ee686c6` |
| `fixtures/bundles/un-ext-08.trace.json` | 3443 | `14eba077c089d9eca64c83453d76a85d03009adc711e3728a0cde5925f0f20d0` |
| `fixtures/bundles/un-ext-09.trace.json` | 2817 | `4729fadc687efd9a58b4dee4d96d215e3bd350bd8d9bd54f908c3e7111578064` |
| `fixtures/bundles/un-ext-10.trace.json` | 3118 | `cf5544329f41050ebeb929f5bd4d420e250821c1c0f81e828d5095efe8667de6` |
| `fixtures/bundles/un-ext-11.trace.json` | 3214 | `3ec1e1a197355bd39003dde538e766c8860fa48ff5231369a621b263541f35ea` |
| `fixtures/bundles/un-ext-12.trace.json` | 3523 | `1bfe56aed14f1863ac58b4dcb5629050cfcf01e66f689a012e5c8e198516f759` |
| `fixtures/golden/expected.json` | 119218 | `9db9b16e1fd8e93a5a3e2a5cde39e09ade4acbc057ef0fe8550a037ccf60e353` |
| `fixtures/manifest.json` | 46539 | `25fcf8b77a989e221a40ec9fad01e4f80e3d8f511c810070ff73336a2914b48f` |
| `fixtures/pdfs/du-chk-01.pdf` | 63596 | `5449bd32a5c224c1997470ed41f20998b06733d090eab92ed7fc07501d2ae79f` |
| `fixtures/pdfs/du-chk-02.pdf` | 6669 | `7481fedda5d7cae12fd06d8fe43de7703221a925cc30bad2dce752add46a7607` |
| `fixtures/pdfs/du-chk-03.pdf` | 6949 | `3f752602d9f9164ae769f7fbb251e67e59ac6469290efe986d3e5df68c3bc979` |
| `fixtures/pdfs/du-chk-04.pdf` | 66715 | `88d07d2aa249f3f7ef1dc832c134c7b97dabf234222c2863143a94b5c87bef58` |
| `fixtures/pdfs/du-dsp-09.pdf` | 5311 | `8127b5a834e78a453fea103d10ded96af74e9b59b072e72b526868ad3c825700` |
| `fixtures/pdfs/du-dsp-10.pdf` | 65040 | `91c835c7a30ca235163f66759624fef13fc60e7e13352ee0294e2a08704c9a4d` |
| `fixtures/pdfs/du-dsp-11.pdf` | 6839 | `20653731381b6eea10267dd69a0a105666536ab12a05f33d30fff73471ab4ea1` |
| `fixtures/pdfs/du-dsp-12.pdf` | 8107 | `725ec8fd55e74735bcda6da631ef1639488ce1976aa5c24f7bb0164d88114ab4` |
| `fixtures/pdfs/du-idx-05.pdf` | 5338 | `40ae4fe8e9c1e02b3018f1b839bb29b6426798f6449b64b3df3fdfe59a5c655e` |
| `fixtures/pdfs/du-idx-06.pdf` | 6673 | `d53443ff8dbb27610a33ea550d31b5639636d30da31b3a894fb848e28775ef65` |
| `fixtures/pdfs/du-idx-07.pdf` | 64583 | `f0000fe5d7f7f1b2e38e806c82812910e61acb06f44b9f814aad70132cbefb28` |
| `fixtures/pdfs/du-idx-08.pdf` | 8121 | `a28dcd898032f3a518c980751ab0dfd6ed0f47849569769f23e9c0a0a68ee56f` |
| `fixtures/pdfs/mm-chk-04.pdf` | 65906 | `bc0002709017a5e1a20a94ff95089e5c3dddefbabaaea40ba5038e7cca48c9b9` |
| `fixtures/pdfs/mm-chk-05.pdf` | 5402 | `6534cb5df8657e9e7d54c9e5d6217d54b998f59084baf9ba7a0cf7afe73a6bd7` |
| `fixtures/pdfs/mm-chk-06.pdf` | 6541 | `24767892979ece1956e6df6032492be8faff3dc315e3dd2067b0420040941f18` |
| `fixtures/pdfs/mm-dsp-10.pdf` | 65017 | `2408a09aeb4f217a63d737658d91835c4f5992d18ae4dc1c9688750e235979e4` |
| `fixtures/pdfs/mm-dsp-11.pdf` | 6926 | `7bfaac267104391b89d1fe5e762ae2c5fb7afa59b68bf16aa9e3c561393b587a` |
| `fixtures/pdfs/mm-dsp-12.pdf` | 7982 | `e0b8897275ad5197f8ad37409a254f47df29bc6febbbc338ae49ee91d674e8d2` |
| `fixtures/pdfs/mm-ext-01.pdf` | 62997 | `50470bd0249d80aef1d433456c7a30648d510134af54546a613d71b5aa37a95b` |
| `fixtures/pdfs/mm-ext-02.pdf` | 6680 | `b2dd1081419cc1f90dd813ead93acc9d28937b02ed6df08c4216993ad7e1dd0b` |
| `fixtures/pdfs/mm-ext-03.pdf` | 6717 | `f07725ce89964e4ade776c5c6569ce4c666626adabdf3f4498fb2c9df7d10495` |
| `fixtures/pdfs/mm-idx-07.pdf` | 64725 | `2fb020331c8ef7f86578c321ea11291e4bb6a1f9ca14eec53e2c868dd1e374a6` |
| `fixtures/pdfs/mm-idx-08.pdf` | 8228 | `fe153a538c539560797d079864fe44843b7c2fd969f3e273a33741a678e20d58` |
| `fixtures/pdfs/mm-idx-09.pdf` | 5242 | `c8659d1d7d36d599fc61e84b77487247f9379f5b35a7f69eeecf49c6f2c3538a` |
| `fixtures/pdfs/po-chk-04.pdf` | 67095 | `db5b66c3454033e6307fdae6944f2c0543b62c557fa20b5a628093747fb68fae` |
| `fixtures/pdfs/po-chk-05.pdf` | 5397 | `57ce8e8308f4dcde78fb2aa3394343c91c6714aa228844899373a9865043804a` |
| `fixtures/pdfs/po-chk-06.pdf` | 6511 | `f05572bfe00bf77caa1c3c4fb9380cf1e5d799a1b91c48b6f82147b020920c79` |
| `fixtures/pdfs/po-dsp-10.pdf` | 65301 | `0fed33d2f13c890d4c74f7ba9f4473c516eac6eba9e89a0b34e9059aaaab4111` |
| `fixtures/pdfs/po-dsp-11.pdf` | 6909 | `c98b1adf1cac0eabf405a17c4edb20820032dc69cec96d96e88cd34e853d1bfc` |
| `fixtures/pdfs/po-dsp-12.pdf` | 7942 | `63892eca8aa148bb9cc6d1d47595602222aede023ce7850e646a354336544987` |
| `fixtures/pdfs/po-ext-01.pdf` | 5239 | `97d1f68a573e09c9b6fc519dde6d37ee25158ee4f6673488770e2debef7cb9cf` |
| `fixtures/pdfs/po-ext-02.pdf` | 6658 | `cd21f24937ef8668acdc6f935767a98ba649b3cfc0c31c22ff52a58e78648a8f` |
| `fixtures/pdfs/po-ext-03.pdf` | 6713 | `fc3967b8083d8f6f5dc90f782c831afc23b5a5a4575ba902cc8f6f5a56676631` |
| `fixtures/pdfs/po-idx-07.pdf` | 66075 | `f4c6050bec5e6b7c1e125f7898ffc6420b6368aae440ced51b7ed172602ac078` |
| `fixtures/pdfs/po-idx-08.pdf` | 8210 | `bd1b630ba15b274e5c8bd3bb81be793dee7699af49a643368516fc4a422a416e` |
| `fixtures/pdfs/po-idx-09.pdf` | 5239 | `71bb0a048998cc3322aa8873657229625f22fe441e8c0eb87b490a0a8260c708` |
| `fixtures/pdfs/un-ext-01.pdf` | 61847 | `ae451bd6f4a4a616c57af583c91f7b6f04a92407dbcb375c6aef91bda2b0be07` |
| `fixtures/pdfs/un-ext-02.pdf` | 63528 | `df9894b04a5ce9aacc38bee6bb62c32c1e9f0d4a9bb5b2a17d235bcb5cac1608` |
| `fixtures/pdfs/un-ext-03.pdf` | 64291 | `b87fddf4858caea467758dac1748b4b41a41ef655fcbca11fdbec75253d95f36` |
| `fixtures/pdfs/un-ext-04.pdf` | 64437 | `436e3232431b9638e140592161f89f5d3be10709b151f9e009b8400fd952b324` |
| `fixtures/pdfs/un-ext-05.pdf` | 5426 | `164d27b1cdc2d33ff81c563371427164326e9dc1ed678f36ef598726cc42c85f` |
| `fixtures/pdfs/un-ext-06.pdf` | 6088 | `81e504b125431cf61d3afff6bd384e2bee986cd327c67ddfd0cb86741d5795e4` |
| `fixtures/pdfs/un-ext-07.pdf` | 6829 | `c147598c9bb5af2c00453a711706a486c6316982ba8171dde3aa02e26a04ab1e` |
| `fixtures/pdfs/un-ext-08.pdf` | 7792 | `02e48f53067a630049ebcc8e0a37bbacf41544538d881920e5d334e4a76886cb` |
| `fixtures/pdfs/un-ext-09.pdf` | 5258 | `be632f97afa2b688d3fe85c9c747666a05a8a62eaed1239c1774315189193955` |
| `fixtures/pdfs/un-ext-10.pdf` | 64358 | `866399d47a2a8aa8cf27d7d996d1fb7e482d911117478e6e8c29af61c2be7c76` |
| `fixtures/pdfs/un-ext-11.pdf` | 7094 | `f65caccf698abf159dc9177302f6565083f7e696a2ca37cc6bddbb0cef0bc3ea` |
| `fixtures/pdfs/un-ext-12.pdf` | 7656 | `6bb8eb975bfb134b29ca2e38c441902cf08c4e7a49e7c5f2889ffe15fdce29bf` |
| `fixtures/sha256sums.txt` | 3840 | `b79ef2c1a7c13004275b8044d7c24c5dbc79985dc195a6313636430d9f47dc8a` |
| `fixtures/specs/du-chk-01.json` | 3317 | `0f26984850181704aec57873ed0a28ef5c391e3073b3097abd8492f16802c07a` |
| `fixtures/specs/du-chk-02.json` | 4268 | `094f9e99db63cf7a6bd664040f49af399428d4aae77170aaa8e2997394cb83b2` |
| `fixtures/specs/du-chk-03.json` | 4319 | `119be70a946e011e5bce3a9e7c4da8a1b25443ee17431433c6d0121a007796c5` |
| `fixtures/specs/du-chk-04.json` | 4919 | `72b5ee7a1093f7cffd7e16d49d898ab03422f2fc0f740b6ce0e5ad92ec87f7fa` |
| `fixtures/specs/du-dsp-09.json` | 3506 | `55d8630e39bbc3907aac0259f7e571c6aa2f2510da1d287a82d34f4b338cf97f` |
| `fixtures/specs/du-dsp-10.json` | 4078 | `ac76df23109669675010f2ec4437a2550a6f31d8a9f1770015c8f66521e6b7df` |
| `fixtures/specs/du-dsp-11.json` | 4320 | `b486fe64f6f0d0267ffb1afde53b29760669286183fe27db489e56aeaf119b73` |
| `fixtures/specs/du-dsp-12.json` | 5095 | `5187e5ff1a85c5deb0d015051454cbd31e8ea8a1be55c0c733a87fcd9a2aa576` |
| `fixtures/specs/du-idx-05.json` | 3503 | `7bdc1f52a18dbf4c4650310e8ad57ffa02519e5c8161bce8369186653d19eb0f` |
| `fixtures/specs/du-idx-06.json` | 4274 | `4c3c01012770622b9e339fd2ddf953d48da3a27327aef2207bc782151b3ddec0` |
| `fixtures/specs/du-idx-07.json` | 4138 | `313aaeb5cda0533bafccbef6c6983aa08174acc8681d7c3b32b2b93b67bc3491` |
| `fixtures/specs/du-idx-08.json` | 5108 | `ac39aef69962af9c434e15ae7eba14b59da41662e801297d394782c50a5c2beb` |
| `fixtures/specs/mm-chk-04.json` | 4753 | `d6f9fc7e1a79d0f6669b15b6680f37ff7f6a3db32ebf527d8c09f75d8c4ac680` |
| `fixtures/specs/mm-chk-05.json` | 3512 | `1b92a84d57c25c37af388662345b622180467672745e183bf2633a2f7e0357ef` |
| `fixtures/specs/mm-chk-06.json` | 4115 | `d65ca1391ec1b6cb1d76bd147292e39703ff00580a55f2f14c0cf6e4d23fafb2` |
| `fixtures/specs/mm-dsp-10.json` | 3925 | `e87cb351de427c09ec6c4df63170f5aa63df6743c730f7b4ce2235a69c1cab92` |
| `fixtures/specs/mm-dsp-11.json` | 4320 | `5e1496e0b0b70e6c43f249ea8e1126c347bc2a1e6b07dd66fc6edd57e562e15c` |
| `fixtures/specs/mm-dsp-12.json` | 4949 | `fb549ba28f17cf99a87ffede3d530966b0a48a9777643f823ae5de2caa60c05e` |
| `fixtures/specs/mm-ext-01.json` | 3144 | `a812504e2af4e92358dda2212b711ca6a441d22fec18d20b34c97e715e2ad02f` |
| `fixtures/specs/mm-ext-02.json` | 4302 | `a0ef1521617f96cf3ef333743dfb5dcf03ee4eea09d4711f87a2287aec545e1a` |
| `fixtures/specs/mm-ext-03.json` | 4130 | `8db1e378d295ab9dbbf67d8158216e0d64e7f226632f2215b479b59156a416a5` |
| `fixtures/specs/mm-idx-07.json` | 3948 | `df4935b9f2a5bd945f0a93bc20a48a3d68e2657be8b3ac5f8ee1db6faec72f8b` |
| `fixtures/specs/mm-idx-08.json` | 5148 | `6f119906fb65197d9a33dafb628213a4a489ad34d89562cce59819d81dafd403` |
| `fixtures/specs/mm-idx-09.json` | 3315 | `fa65424fb223a88ddb42a5d219de94be0ab77c9801075260890c06bf2663222d` |
| `fixtures/specs/po-chk-04.json` | 4737 | `76172cf650d48dc5c4cf412c633752db9aae963ad50cbc6c7afec5930ef715d3` |
| `fixtures/specs/po-chk-05.json` | 3454 | `8ff620e02c38e8ad9c1b2061b736eca0e20cea5f32d6c0386c39197ba7e4bfa0` |
| `fixtures/specs/po-chk-06.json` | 4110 | `48744a574bc07a85ce362cd66a819d21f7c27dc494e12d61502616091e354037` |
| `fixtures/specs/po-dsp-10.json` | 3906 | `1defa754f1f29f2aaecc29fb6684087ac02ef170948cd45d8a98ee18a85f127e` |
| `fixtures/specs/po-dsp-11.json` | 4276 | `0b5926479742aa65a3cf9ae05f3be6a06098206b0de632605ae03f70ce0fdc40` |
| `fixtures/specs/po-dsp-12.json` | 4905 | `d5da9ccbc97938e6ae891c21add5abd44c7ac0b1f55df53cfcd97f39d095f55c` |
| `fixtures/specs/po-ext-01.json` | 3301 | `13637c68411a8e589ce9fcbcc8faf2d47b933fdcefe4b451f9fc9ab3e02fd4f7` |
| `fixtures/specs/po-ext-02.json` | 4289 | `706579831a38f2df0624221166ebcd77e8cfcc817afdf518c88de90cd465f3f6` |
| `fixtures/specs/po-ext-03.json` | 4125 | `b45fdd07397251263666c04330fdd35e1873e2de680c822f37439ae909689aaf` |
| `fixtures/specs/po-idx-07.json` | 3879 | `e81dffe772e010a1c1c8d3236132c656281f5e8188e631ef9079eb2eb1de153b` |
| `fixtures/specs/po-idx-08.json` | 5080 | `6e78f0f1c787d87e74a8d9bf63426737c0220b577fc8680af1e9c55c97c69809` |
| `fixtures/specs/po-idx-09.json` | 3322 | `a462dc0fadbb1f99ac82b83b2d0828f1c9a85db9fd561313636bcc3fbe9805a9` |
| `fixtures/specs/un-ext-01.json` | 3252 | `4a435ae7dbb1b73f48b7fc06e5cc457ca9d5f384b6de3a00a168a11a03ffb0d8` |
| `fixtures/specs/un-ext-02.json` | 3992 | `8a6d3b2801934f33a7a19b9461d0fec0c58d05efc6dba26d797372499131fb81` |
| `fixtures/specs/un-ext-03.json` | 4080 | `78610e5e72b053d72f7742db16a3f2c04597db6ba019e35f21bc87c1c983de3f` |
| `fixtures/specs/un-ext-04.json` | 4635 | `2837c1a7c019e3cd0b789b98c76ef1ec53c19c5170095acde3d0c890ba54bbbe` |
| `fixtures/specs/un-ext-05.json` | 3379 | `78253f11a9cf8273b2e014497d0ec145f365f873097b2aa23433057515307eb8` |
| `fixtures/specs/un-ext-06.json` | 3746 | `b9914b60de0ad1a68be0b54f609b3b35d44409f490d83abac7c692aaafe1de19` |
| `fixtures/specs/un-ext-07.json` | 4024 | `4a4ac72bb6001b412b81d60d644abda818461af20889e2b6916be0cbbfe84fb4` |
| `fixtures/specs/un-ext-08.json` | 4759 | `5929167f325097fc43d05cea7657d4fdc60812214c8539008b4f3f7cdf5f3638` |
| `fixtures/specs/un-ext-09.json` | 3720 | `8211cb6ea70ea612f0fc33ff4397b95052d8089fba2b475042ed415a243b14fc` |
| `fixtures/specs/un-ext-10.json` | 4332 | `dc876134a8cbf6431a9a1b97dfe2c281dfd8d9e0d2e8ad0b12358cc9433aa563` |
| `fixtures/specs/un-ext-11.json` | 4721 | `ae8cef445067aab6a77b8c5d5f2122de4d741b325fcde64e76925218d40d54dc` |
| `fixtures/specs/un-ext-12.json` | 5088 | `a0088ab652c8aadc08ddfcef3c55a19907cfd1a23f7e7b3558219569b338f9b4` |
| `pyproject.toml` | 1319 | `98ace64e5731416bf68e00eb5cae704b71423a6f98f343b3d0b8bd7ad1e6bd14` |
| `requirements.lock` | 2809 | `c74b73721ebc3c2aa266852f3f95a03cfa43da5b7f3878ef4e6301ceb437570a` |
| `src/pagetrace/__init__.py` | 426 | `7242691bae1ec567c5b56ec61a24e5b59d795d446193736c97b62b53e435fb0d` |
| `src/pagetrace/assets/report.css` | 5349 | `3e6ea8a033f7a05131492baacf495b192add66217c446be39fe56a5fada707f1` |
| `src/pagetrace/assets/report.js` | 15660 | `009da7e9e624c210210ea86ed5beeb0c37a888d05fac385b53706ee07d00a965` |
| `src/pagetrace/cli.py` | 29880 | `90b787169fcd1868e5de6f7797c95765be61fa0b49bcc94e649f0f7c7ccb15ec` |
| `src/pagetrace/compare_stages.py` | 49763 | `6937765a39f5e6b60a8a2e9d233509e7445ef70ae3313fd449487bc4be5f9217` |
| `src/pagetrace/contracts.py` | 19684 | `16ff40a6ec5cad52db91c93f8df20b6e88f4bc2578d9fb6ea2cb012e1ec7d22f` |
| `src/pagetrace/extract.py` | 9152 | `9e3d095d2b5335a3bf8823f0cca50bf2dc2ef9cbac3ab416d920a96c1d58cf9a` |
| `src/pagetrace/locate.py` | 7525 | `7e24f93da23642b77e9dd16ad84d91e7216c1b7d66ed0fabb324647b1d0284fa` |
| `src/pagetrace/normalize.py` | 2134 | `c315c522881c72ce252e0f5d8de4551ab9aebf257daac19026e349ebff0711ec` |
| `src/pagetrace/pdf_input.py` | 7960 | `01afe7f3d459e47a61a3d222a88ec770e8e47dd004820e019f1a56148dfbee9d` |
| `src/pagetrace/report_html.py` | 24318 | `e3cacb534bcde33dcf29efad072bcf0bc71259c49ec77d215cb72bdbd6a888ad` |
| `src/pagetrace/schemas/pagetrace.bundle.v1.schema.json` | 8108 | `2cf73d745aef9681087ad68c0323b5e3a83be8cd651bbbb54590542e276cd9ac` |
| `src/pagetrace/schemas/pagetrace.report.v1.schema.json` | 8719 | `a123094b033867d842d0068656c6025ebc64852af5f268d257ea2ef512288bb2` |
| `src/pagetrace/trace_bundle.py` | 28921 | `e588208ca1042797be3c2f84f039f70444662355b81fbcfe6c6d59d3ed4ed75b` |
| `src/pagetrace/verdicts.py` | 13157 | `6ed8fbf2871f477b00fc7b74b0ef330c978a5afc4680859861394c422d7a4f51` |
| `tests/e2e/test_e2e.py` | 13600 | `907e4b661816a788a507b5b7b0c9ed77300468f9f40b3b713aeff36e2a518b0f` |
| `tests/integration/test_cli.py` | 20212 | `e03257985acea9d02124fa5e45e566c75a7e6b20757f63ed8e3ed6bc211d0335` |
| `tests/integration/test_html_report.py` | 17330 | `3bdf1f0888ea8bad860319692091f1e8b895173d683ebbe2c9806548788d00ab` |
| `tests/integration/test_oracle_parity.py` | 8605 | `05c6bbf30527229ae71a3ff9ce85cbf7af73aeadc5b45276bba0566a010a21be` |
| `tests/integration/test_toctou.py` | 12462 | `b84422bde3abe6d62e4f6c5de8b8342a6139cf7e380ec039e5c8c680cdbf08dd` |
| `tests/oracle/__init__.py` | 1414 | `ebd2ce8596f405b910e07eeea5c15f955723a139f90995145af2dff2176e11b5` |
| `tests/oracle/api.py` | 2297 | `90b1b147f09954362c298238d8c288dcd26de83ce18c9df86fca77aeb0a21c5f` |
| `tests/oracle/attribute.py` | 33779 | `198ec6476be6205264ef0bc04fd355c92df8f87bc781d1379409f5be06dd0c25` |
| `tests/oracle/locate.py` | 7160 | `f54bd66174206d07f3e80970ab7fd7c1be2f9b4168686b0678c2f05967adcd45` |
| `tests/oracle/pdfread.py` | 9136 | `0301148f5baa42b7f7f6ddfba2c13ad8a120aa9690e6c0fc4cb047d5a09662ef` |
| `tests/oracle/test_oracle.py` | 20726 | `00ea710fd58122acc6ce26b7fc57bb3033ce242cf2cefc103809c4efbb6e0bd2` |
| `tests/oracle/textnorm.py` | 4448 | `a0980265d3b559809103c195e4e2c7027eafd10d4cabdd425da43205bbd18026` |
| `tests/privacy/test_privacy.py` | 11289 | `252d54ab83b80c77b6cdf86caf0bc08749ac9d2703481a97344609905640af1e` |
| `tests/prototypes/build_prototype_data.py` | 6770 | `d9615424c2afd2104791e279572d0a56e6f4c61576137e14aebadc80c5c3f445` |
| `tests/prototypes/test_prototype.py` | 9572 | `407fdb4a559391d01989d0eec4f4dd9386f69c3946b14f568067d4d0c50f9ad4` |
| `tests/s0/conftest.py` | 570 | `526e6efed22d78b31c23435e0f48d73795b8423ed2f6778e76f979762f6b0072` |
| `tests/s0/test_run_s0.py` | 6652 | `60acab586c679adb8ad7ffb9c4e8b4fc20c0bae14ef0b00d5cea715d1e0dc519` |
| `tests/unit/fixtures_bundle/inv-bad-sha-short.json` | 1247 | `8ccc2eff1b04f537c925c7d433456eed911dbe47cd403c87a81f78ea5146c956` |
| `tests/unit/fixtures_bundle/inv-bad-sha-uppercase.json` | 1307 | `0e453dae60b7f675120a6a7ef5a6d9f6596d83a85ae46a54335e96ebdaabfb11` |
| `tests/unit/fixtures_bundle/inv-bare-page-nested.json` | 1326 | `217f164993b362324ddcefccd167a11a0d70dbee7678c9b76dbfd35e68e7214b` |
| `tests/unit/fixtures_bundle/inv-bare-page-top.json` | 1320 | `116005f4bb1998b42a878b4ffa5cb7a11a6cebdee7518316ea397582b44aae1d` |
| `tests/unit/fixtures_bundle/inv-case-id-bad.json` | 1289 | `d7b417738a5547539b7fe7e48adfcdfd7f8867ab9a9d7f62f807da150ff0dc0c` |
| `tests/unit/fixtures_bundle/inv-citation-quote-empty.json` | 1283 | `30d5489bb4d2a70568ae14fd33a11210afc0fcb69c8365fe31ba36c8add58497` |
| `tests/unit/fixtures_bundle/inv-document-missing-sha.json` | 1225 | `4695cf5108035b4ce2e464951a9642d87fe839b5f203950e68af088c9aff1f5c` |
| `tests/unit/fixtures_bundle/inv-duplicate-chunk-id.json` | 1499 | `12ea382a4198f0411cc0d1e3d598d7d8b4f9c5edb7f892250aadb87d484bced3` |
| `tests/unit/fixtures_bundle/inv-duplicate-citation-id.json` | 1458 | `1aa99b26718dea6296b5049457d0faca10c7b8cc8758163dda9a989592a540e9` |
| `tests/unit/fixtures_bundle/inv-duplicate-display-citation.json` | 1464 | `fa4c4006319157c33d63639d47bb6de78494c5fda3df521403c9959689ffef81` |
| `tests/unit/fixtures_bundle/inv-duplicate-record-id.json` | 1440 | `6e64c31379e8701d25e4afc7107874c1a0c060b3f01719b920d6c7c751e3ddcc` |
| `tests/unit/fixtures_bundle/inv-extraction-duplicate-index.json` | 1474 | `7cea58d686c6650090ec23881574baab878e6e2aeb18a7cf225a262c25d21bc6` |
| `tests/unit/fixtures_bundle/inv-extraction-index-negative.json` | 1308 | `5821d20823b95ea4a1ea84cb4b669bc1c2e8c97ab66d9f563257ada736f003c8` |
| `tests/unit/fixtures_bundle/inv-extraction-index-overflow.json` | 1307 | `d40bb5ff9f4c9336da0dbe3b29c47426844189eff6a3df48e280afeded6853b3` |
| `tests/unit/fixtures_bundle/inv-extraction-unsorted.json` | 1474 | `3a990840f3dcf1a184d8e03ce178cf945c2a52986280ffcc342ee95f7a4408d3` |
| `tests/unit/fixtures_bundle/inv-index0-value-bool.json` | 1310 | `79929ac4eafe328b80ee9ac7a50b8d56d6ec186ecd3ea3eb81ed0bc2b0d3621b` |
| `tests/unit/fixtures_bundle/inv-index0-value-float.json` | 1309 | `7e3cc598ae98f42d4ed99666dd481e694a3c26704f525cdc7d63ec48f27dac8c` |
| `tests/unit/fixtures_bundle/inv-index0-value-negative.json` | 1308 | `b30396cecda567268f0a4ee7f886c1640fc8768704cb05e8c9b5018dff08bc41` |
| `tests/unit/fixtures_bundle/inv-index0-value-overflow.json` | 1307 | `749231820c6107c08165dae21fccac47baa7b21c3a301c446fd30d58460d594a` |
| `tests/unit/fixtures_bundle/inv-index0-value-string.json` | 1309 | `2972460264c4ed30c66b12fcd8df53b2ff4761cc38b0f9938482eba9a73e0600` |
| `tests/unit/fixtures_bundle/inv-label-value-int.json` | 1305 | `91f0cefbde1f6a177970f78a6bc858043c94b58a676303167e1335b47d15a8bc` |
| `tests/unit/fixtures_bundle/inv-missing-stage-listed-but-present.json` | 1329 | `eca276a8c2398ca191e62d6574484f1de46cf9cbbfa4ea0b0381d9a2da1a0c79` |
| `tests/unit/fixtures_bundle/inv-missing-stage-not-listed.json` | 1091 | `ecbaac131d9b4152280f38fe199c71d13f6675c2766e7eb9cfd794bb9427e5fb` |
| `tests/unit/fixtures_bundle/inv-number1-value-overflow.json` | 1308 | `51c8ef387fd7e0f9412dfac5135e427ea2e7cb34e124acf808a3d050abc567a3` |
| `tests/unit/fixtures_bundle/inv-number1-value-zero.json` | 1308 | `0be666fc768277141bf9379645efd889b317ff3d274dbd224d7812e14ac3301e` |
| `tests/unit/fixtures_bundle/inv-page-count-501.json` | 1309 | `5f649cf068901f715090a53f987f9575ea3645dafb08e5ae3c02611a810b6f74` |
| `tests/unit/fixtures_bundle/inv-page-count-zero.json` | 1307 | `5d88223ae88e7bc3ba0e7b45bdb33f275b58fcecc8d90e89efcca463a22da15b` |
| `tests/unit/fixtures_bundle/inv-page-semantics-wrong-base.json` | 1307 | `54379759a1ee9660af798a18fbcdf3183bf029e30ee3775d4df61214a7da7402` |
| `tests/unit/fixtures_bundle/inv-schema-is-report.json` | 1307 | `4f7e3e178979b4ab687b4a1d3eeccf3e2086e20fc62db5567e1b18e9c392928d` |
| `tests/unit/fixtures_bundle/inv-schema-missing.json` | 1272 | `9315a5e02dd3d04408128e07314ce5d8e9e8c9ceebaec3ada4c7de5170361d73` |
| `tests/unit/fixtures_bundle/inv-schema-version-v1.json` | 1309 | `ca870ba480b903cbb89f6b39268ec074ab26547955410d8da382c813093e8048` |
| `tests/unit/fixtures_bundle/inv-schema-version-v2.json` | 1307 | `62b2bffc847f39a9a84df4e4c2644126bbac721c7c6b9a03962a316d773042ee` |
| `tests/unit/fixtures_bundle/inv-source-duplicate.json` | 1320 | `82fd13eecf7ee2a9dfb6fd4efb8e3c0fb4c3e9c50f4237f2149dd591e7efa3fc` |
| `tests/unit/fixtures_bundle/inv-source-float.json` | 1309 | `f27d257e561e90b6908608ff8e65d390c75e2fd4efd902d275ae5fa918a6a733` |
| `tests/unit/fixtures_bundle/inv-source-negative.json` | 1308 | `6b8390b38dfdf7a7430d94a97e6b4fbc3a7c40c3aa2280a6826805e2fc591776` |
| `tests/unit/fixtures_bundle/inv-source-overflow.json` | 1307 | `6a642b5f6a1d35ffe20b2fdf1b03e620d003090185d599d679adf6dc6e312df0` |
| `tests/unit/fixtures_bundle/inv-source-unsorted.json` | 1320 | `813c69fec24cff1953e5f815d6e753d97ba0216ab2a592245a754914288edb98` |
| `tests/unit/fixtures_bundle/inv-unknown-basis-viewer-not-null.json` | 1303 | `4ad4311d891d61dbc3b54b0f570b1017c443df67f3a54db75092837562ac37ec` |
| `tests/unit/fixtures_bundle/inv-unknown-nested-field.json` | 1332 | `503681fd49500a14b80059bb94b70bf18b587c075520c6eecb186c50bc528323` |
| `tests/unit/fixtures_bundle/inv-unknown-stage-field.json` | 1322 | `dc936f7850b39a0586d822a9b57c2e744bdefb3cfc50b9994bdc8871f86adf76` |
| `tests/unit/fixtures_bundle/inv-unknown-top-field.json` | 1328 | `6510b18c6234cbd6ddcf1f6847850abc246f3a2db5e884a9dcad13d8636585e1` |
| `tests/unit/fixtures_bundle/inv-viewer-float.json` | 1309 | `04befa5b687cc2ceff4027fac559c8ad85cf4d50bf7a848c6b23f42835365ae9` |
| `tests/unit/fixtures_bundle/inv-viewer-overflow.json` | 1307 | `56b28b27724c937379ee57c27f71f536003a6065d57f5e138c2728def07c7362` |
| `tests/unit/fixtures_bundle/inv-viewer-zero.json` | 1307 | `34f4700569d7b9ccce612c0c6ad67b9d6c5440fa1020672993ad5dc8253f5824` |
| `tests/unit/fixtures_bundle/valid-cross-page.json` | 1333 | `a81a8a7ebd3308c4452b13d9b292d7db8ca023a38f24ef54cc23abaaccfc88df` |
| `tests/unit/fixtures_bundle/valid-empty-chunking-array.json` | 1111 | `cf63fe99a79a2fee1535b3118a5a01f6b481b5a88535084d0ca8ed8f609ea583` |
| `tests/unit/fixtures_bundle/valid-empty-source-set.json` | 1286 | `3d7eab120f05c916c2e21f5894f2001b6deb7fe98ae404a02e39168684c76f79` |
| `tests/unit/fixtures_bundle/valid-first-page.json` | 1307 | `5d7af6a0dd6cd343eb389e9ac3c97883d3003c54638270f5f167442c031dd4ec` |
| `tests/unit/fixtures_bundle/valid-label-citation.json` | 2735 | `d7fefe44e9438ff26de5f82694e261572db0f75a54c2372c804cffa17d2669e7` |
| `tests/unit/fixtures_bundle/valid-missing-chunking.json` | 1113 | `1713b84f01b7a2901406f545f652af74cf45708c71d4ad40d4e7174dcf5093be` |
| `tests/unit/fixtures_bundle/valid-missing-display-extraction.json` | 975 | `cb0dd783117a9d720938119dd700ec931c3d712a295ba78ed6d1f748c582fdbf` |
| `tests/unit/fixtures_bundle/valid-null-display-value.json` | 1314 | `8b7fcfbc24f2b8d6c68c6ff1da262703e7a95a5406d1a70ed19da0be35a97ba5` |
| `tests/unit/fixtures_bundle/valid-unknown-basis.json` | 1306 | `63f42782e27f1432564f6b4566dcff1a5066d39df1283ebdfd8c87d4a358cdc6` |
| `tests/unit/test_bundle.py` | 27393 | `18cbeaba959612876d82d338cd4f69251afc9142bcd856d61057193419d70e9e` |
| `tests/unit/test_extract.py` | 15057 | `710733f5f3da0bf828795e99823569b526634d97b4be11bad76bddfce39131cf` |
| `tests/unit/test_file_name_paths.py` | 8569 | `4f54d0a10d9322bbaac2c23606e4c7878b8c146640ddb832a7d38136606163e5` |
| `tests/unit/test_fixture_manifest.py` | 7436 | `839f133d9f3d13bc62e866c378b5ead7038d95e9bab058d2007771383f00aeea` |
| `tests/unit/test_locate.py` | 13469 | `07e1a05b4ebcd69d72cc19f02290bf28462afccdc741f20910b9df564af07371` |
| `tests/unit/test_page_semantics.py` | 21778 | `5abf67261dc2234d1ada97a343f9c5cabb162bc1014675e536b4697aa89aca47` |
| `tests/unit/test_unlocatable_attribution.py` | 14264 | `8dda97aa83345a4357f061e1816d17d255dee2b2564e2bd070e972018ffa4b5f` |
| `tests/unit/test_verdicts.py` | 26421 | `8be3e136aed6622ac2052830a386152cb11d233de1733786c36a9ed44ece4c9f` |
| `tools/generate_fixtures.py` | 51290 | `2559d5121f212d040b1a676fe05aa4e9fb884e4300c369e46ce1e484fc5db82f` |
| `tools/render_previews.py` | 4842 | `1d770b2099d2cf87c2cddaaefe86779641f4445d0da93dd2606d567942930478` |
| `tools/run_s0.py` | 31282 | `4736619d324ddfe3ac276bf62b5fa5862cd495b444db9b443f9ee4cf6ac954ea` |
| `tools/verify_review_pack.py` | 6398 | `a7733f82ed6a25b450a4bc823cd22a3af8d646b5e69fc81a3ff8ff71050e7e8c` |


## §3 独立复核命令

```bash
unzip -t 04_source/source-release.zip
# No errors detected in compressed data of 04_source/source-release.zip.（255 条目）

sha256sum -c 04_source/SHA256SUMS.txt
# 04_source/source-release.zip: OK
# 04_source/SOURCE_MANIFEST.csv: OK

sha256sum 04_source/source-release.zip
# 7526f511c66a6e0fcc0f2d38a3159c199660e8cb293dab8df79180d5e12fad6b
sha256sum 04_source/SOURCE_MANIFEST.csv
# b6db053e8e5c11b1bfbd55e1f62e8570c0c84683b1a4191819768224b7fcc33f
```

ZIP ↔ manifest 逐文件复核（`zipfile` + `csv`，SHA-256 与字节数逐一比对）
结果见 REVIEW_PACK_RELEASE_04 §1：255/255 一致，0 不匹配，无多余条目。

## §4 已知注意项（不阻塞门禁，见 RELEASE-04 §6 详述）

- ~~文档重放哈希滞后~~**已解决（`8cfd7dc`）**：首轮报告的 P2 级问题——
  冻结树内 `README.md` 与 `08_release/` 三文档引用 T014 的重放哈希
  `5195fc9a…`——已在文档修正 commit `8cfd7dc` 中更正为 `a06b87fc…`。
  F2 核实：`04_source/source/README.md` 与 `08_release/` 三文档中
  `5195fc9a` 零命中，`a06b87fc` 各 1/1/1/2 处；新 manifest 唯一变化的行
  即 `README.md`（大小仍 5316，SHA 改为 `dc33d686…`）。
- ~~协调员版 S0 报告 `base_commit` 不是冻结 commit~~**已解决**：
  新版 `05_tests/s0-release/S0_REPORT.json` 的 `base_commit` 已为冻结
  `8cfd7dc`（见 §1 说明）；与首轮 F 在 `d0aa21f` 上的重跑逐字段一致，
  仅 `base_commit` 不同。
- 平台：仅 Linux x86_64 + CPython 3.12.3 实测；Windows / macOS NOT_TESTED。
- 第二轮说明：本包为 F2 重生成；首轮（`d0aa21f`、旧 ZIP
  `c51b9d32…5131`）的包已由新包取代，Drive 归档亦已换传（见
  RELEASE_REVIEW_INDEX.md）。
