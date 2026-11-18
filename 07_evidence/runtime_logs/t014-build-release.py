#!/usr/bin/env python3
"""P026-T014: build source-release.zip + SOURCE_MANIFEST.csv + SHA256SUMS.txt.

Deterministic: sorted file order, fixed ZIP timestamps (1980-01-01),
fixed permissions 0o644, deflate. Run from the worktree root.
Excludes: .venv, __pycache__, *.pyc, .tmp, .pytest_cache, .gitignore,
and any user PDF / secret / cache (none exist in the frozen tree).
"""
import csv
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()          # worktree root
PKG = ROOT / "04_source" / "source"         # PACKAGE_ROOT
OUT_DIR = ROOT / "04_source"

TOP_FILES = ["README.md", "LICENSE", "NOTICE", "pyproject.toml",
             "requirements.lock"]
TOP_DIRS = ["src", "tests", "tools", "contracts", "docs", "fixtures"]
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def collect() -> list[Path]:
    files: list[Path] = []
    for name in TOP_FILES:
        p = PKG / name
        assert p.is_file(), f"missing {p}"
        files.append(p)
    for d in TOP_DIRS:
        for p in sorted((PKG / d).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(PKG)
            parts = rel.parts
            if "__pycache__" in parts or ".pytest_cache" in parts:
                continue
            if p.suffix in (".pyc", ".pyo"):
                continue
            if p.name in (".DS_Store",):
                continue
            files.append(p)
    files.sort(key=lambda p: p.relative_to(PKG).as_posix())
    return files


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = collect()
    # Safety: no absolute-path strings, no user PDFs outside fixtures,
    # no key/secret material in the frozen tree.
    for p in files:
        rel = p.relative_to(PKG).as_posix()
        assert not rel.startswith("/"), rel
        if rel.endswith(".pdf"):
            assert rel.startswith("fixtures/pdfs/"), rel
    zip_path = OUT_DIR / "source-release.zip"
    manifest_path = OUT_DIR / "SOURCE_MANIFEST.csv"
    sums_path = OUT_DIR / "SHA256SUMS.txt"

    rows = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        for p in files:
            rel = p.relative_to(PKG).as_posix()
            data = p.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            rows.append((rel, digest, len(data)))
            info = zipfile.ZipInfo(rel, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3  # Unix
            zf.writestr(info, data)
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["path", "sha256", "bytes"])
        w.writerows(rows)
    zip_digest = sha256(zip_path)
    manifest_digest = sha256(manifest_path)
    with sums_path.open("w", encoding="utf-8") as f:
        f.write(f"{zip_digest}  04_source/source-release.zip\n")
        f.write(f"{manifest_digest}  04_source/SOURCE_MANIFEST.csv\n")
    print(f"files: {len(rows)}")
    print(f"zip: {zip_path} {zip_path.stat().st_size} bytes "
          f"sha256={zip_digest}")
    print(f"manifest: {manifest_path} sha256={manifest_digest}")


if __name__ == "__main__":
    main()
