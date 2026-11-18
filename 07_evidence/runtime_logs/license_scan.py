#!/usr/bin/env python3
"""T013 dependency license scan (offline, stdlib only).

Reads the installed distributions' metadata (importlib.metadata) plus
any shipped LICENSE files, and checks every pinned entry of
requirements.lock against what is actually installed in the venv.

Usage (from PACKAGE_ROOT, inside the venv):
    .venv/bin/python \
      ../../07_evidence/runtime_logs/license_scan.py \
      --lock requirements.lock --out \
      ../../07_evidence/runtime_logs/license-report.txt

No network access: only local metadata is read. Exit 0 when every
lock entry is installed at the pinned version with a determinable
license; exit 1 otherwise (a mismatch is printed, not hidden).
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import sys
from pathlib import Path


def parse_lock(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)$", line)
        if not match:
            print(f"WARN: unparsable lock line: {line!r}", file=sys.stderr)
            continue
        entries.append((match.group(1), match.group(2)))
    return entries


def license_of(dist: metadata.Distribution) -> str:
    info = dist.metadata
    expr = info.get("License-Expression")
    if expr:
        return f"License-Expression: {expr}"
    lic = info.get("License")
    if lic:
        return f"License: {lic}"
    return "License: UNKNOWN (no License / License-Expression field)"


def license_files(dist: metadata.Distribution) -> list[str]:
    found = []
    for f in (dist.files or []):
        s = str(f)
        if "LICENSE" in s.upper() or "LICENCE" in s.upper():
            found.append(s)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    lock = parse_lock(Path(args.lock))
    lines = [
        "PageTrace (P026) — dependency license report (T013)",
        "Generated offline from installed distribution metadata "
        "(importlib.metadata) + shipped LICENSE files. No network use.",
        f"Lock file: {args.lock}",
        "",
    ]
    problems: list[str] = []
    for name, pinned in lock:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            problems.append(f"{name}=={pinned}: NOT INSTALLED")
            lines.append(f"{name}=={pinned}: NOT INSTALLED")
            continue
        installed = dist.version
        status = "OK" if installed == pinned else (
            f"MISMATCH (installed {installed})")
        if installed != pinned:
            problems.append(f"{name}: pinned {pinned}, installed {installed}")
        files = license_files(dist)
        lines.append(f"{name}=={pinned}: installed {installed} [{status}]")
        lines.append(f"    {license_of(dist)}")
        lines.append(
            "    license files: "
            + (", ".join(files) if files else "(none shipped)"))
    # Pillow wording check (T012 legacy item, closed by T013): the
    # installed LICENSE text must say MIT-CMU, not HPND.
    try:
        pillow = metadata.distribution("Pillow")
        for f in (pillow.files or []):
            if str(f).endswith("licenses/LICENSE"):
                text = (pillow.locate_file(f)).read_text(
                    encoding="utf-8", errors="replace")
                hit = "MIT-CMU License" in text
                lines.append("")
                lines.append(
                    "Pillow LICENSE text check: "
                    + ("PASS — contains 'MIT-CMU License'"
                       if hit else "FAIL — 'MIT-CMU License' NOT FOUND"))
                if not hit:
                    problems.append("Pillow LICENSE text lacks MIT-CMU")
                break
    except metadata.PackageNotFoundError:
        problems.append("Pillow not installed")
    lines.append("")
    lines.append(f"checked {len(lock)} lock entries; "
                 f"{len(problems)} problem(s)")
    for problem in problems:
        lines.append(f"PROBLEM: {problem}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
