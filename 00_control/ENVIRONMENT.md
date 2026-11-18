# 环境事实探测（IMPLEMENTATION_PLAN §0.3，2026-11-16 ~23:40 GMT 实测）

- Python: 3.12.3 (main, Aug 31 2026) [GCC 13.3.0]
- 平台：Linux-7.0.0-44-generic-x86_64-with-glibc2.39，x86_64
- pip: 24.0（系统 pip，/usr/lib/python3/dist-packages/pip）
- CPU：4 核；RAM：7.7 Gi（可用约 1.9 Gi）；磁盘：/home/hatch 150G，剩余 128G（15% 已用）
- 工作区绝对路径：/home/hatch/workspace/p026-pagetrace
- 主测试平台：当前 Linux VM（计划 §0.3：以当前系统为主测试平台；Windows 路径/文件名/命令做静态审查；未实际运行的平台一律写 NOT_TESTED）
- 浏览器：本 VM 上的浏览器检查由主 agent 另行安排（T005/T008 截图时记录实际浏览器名称/版本）
- 网络：VM 有互联网（可 pip install）；产品本身运行时不得联网（T011 隐私门禁）
- 系统已装：jsonschema 4.10.3、fastjsonschema 2.19.0、pillow 10.2.0
- 系统未装：pypdf、reportlab、pdfminer.six、pytest——由 T001/T002 在项目 venv 中安装并锁定版本（`python -m venv .venv` + `pip install -e ".[dev]"`，见 PROJECT_BOOK §12.1）
- /tmp 为 512M tmpfs，VM 重启会清空：pytest 等全量运行须把 TMPDIR 指到持久磁盘
