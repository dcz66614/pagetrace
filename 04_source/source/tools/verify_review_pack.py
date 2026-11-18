"""Verify a T012 review pack (P026 PageTrace, read-only).

Usage (from the repository root, the layout the acceptance command
assumes)::

    python 04_source/source/tools/verify_review_pack.py \
        --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md

or from PACKAGE_ROOT (``04_source/source``)::

    python tools/verify_review_pack.py \
        --index 07_evidence/REVIEW_PACKS/REVIEW_INDEX.md

The ``--index`` path is resolved against the current working
directory first and then against the repository root (the parent of
``04_source/`` as seen from this file), so the mixed
PACKAGE_ROOT / repository-root layout of the acceptance commands
works from either directory.  Nothing is written: this script only
reads the index, the pack files and the SHA-256 sums file and
compares hashes.

The index must contain one manifest table row per pack file::

    | PACK_01 | 07_evidence/REVIEW_PACKS/REVIEW_PACK_01.md | <sha256-64-hex> | ... |

Exit codes (PROJECT_BOOK §12.2): 0 = pack verifies; 2 = invalid
input (missing file, bad index, hash mismatch); 3 = internal error.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# This file lives at <REPO_ROOT>/04_source/source/tools/, so
# parents[3] is the repository root.
TOOLS_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = TOOLS_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[1]

_ROW_RE = re.compile(
    r"^\|\s*(PACK_\d+)\s*\|\s*`?([^|`]+?)`?\s*\|\s*`?([0-9a-f]{64})`?\s*\|",
    re.MULTILINE,
)
_SHA256_RE = re.compile(r"^([0-9a-f]{64})\s+\*?(\S+)\s*$")

#: Pack file -> text markers that must appear in its body.  A pack is
#: not a directory listing: PACK_01 must carry the per-file review
#: coverage (hashes + line references + findings) and PACK_02 the
#: re-verified evidence (replay hash, pytest count).
REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "REVIEW_PACK_01.md": (
        "T012-P2-",
        "sha256",
        "compare_stages.py",
        "contracts.py",
    ),
    "REVIEW_PACK_02.md": (
        "5195fc9a17e8fbae37a9975234ffccef31017bc8a68ce1f081a23315355f33f8",
        "639 passed",
        "48/48",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_index(arg: str) -> Path:
    path = Path(arg)
    if path.is_absolute():
        return path
    for base in (Path.cwd(), REPO_ROOT):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return Path.cwd() / path  # error path below reports it as missing


def check_sums_file(index_path: Path, failures: list[str]) -> int:
    """Verify REVIEW_PACK_SHA256SUMS.txt next to the index, if present."""
    sums_path = index_path.parent / "REVIEW_PACK_SHA256SUMS.txt"
    if not sums_path.is_file():
        failures.append(f"missing sums file: {sums_path}")
        return 0
    checked = 0
    for lineno, line in enumerate(
            sums_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        match = _SHA256_RE.match(line.strip())
        if not match:
            failures.append(f"{sums_path}:{lineno}: unparsable sums line")
            continue
        expected, rel = match.groups()
        target = REPO_ROOT / rel
        if not target.is_file():
            failures.append(f"sums entry missing file: {rel}")
            continue
        actual = sha256_file(target)
        checked += 1
        if actual != expected:
            failures.append(
                f"sums mismatch for {rel}: file {actual} != sums {expected}")
        else:
            print(f"OK sums {rel} {actual[:16]}…")
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a T012 review pack against its index.")
    parser.add_argument("--index", required=True,
                        help="REVIEW_INDEX.md path (repo-root-relative "
                             "or absolute)")
    args = parser.parse_args(argv)
    try:
        index_path = resolve_index(args.index)
        if not index_path.is_file():
            print(f"INPUT ERROR: index not found: {args.index}",
                  file=sys.stderr)
            return 2
        text = index_path.read_text(encoding="utf-8")
        rows = _ROW_RE.findall(text)
        if not rows:
            print("INPUT ERROR: index has no PACK manifest rows "
                  "(expected '| PACK_NN | <path> | <sha256> | ... |')",
                  file=sys.stderr)
            return 2
        failures: list[str] = []
        for pack_id, rel_path, expected in rows:
            rel_path = rel_path.strip()
            target = REPO_ROOT / rel_path
            if not target.is_file():
                failures.append(f"{pack_id}: missing file: {rel_path}")
                continue
            actual = sha256_file(target)
            if actual != expected:
                failures.append(
                    f"{pack_id}: hash mismatch for {rel_path}: "
                    f"file {actual} != index {expected}")
                continue
            print(f"OK {pack_id} {rel_path} {actual[:16]}…")
            body = target.read_text(encoding="utf-8")
            if len(body.strip()) == 0:
                failures.append(f"{pack_id}: pack file is empty")
                continue
            for marker in REQUIRED_MARKERS.get(target.name, ()):
                if marker not in body:
                    failures.append(
                        f"{pack_id}: missing required content marker "
                        f"{marker!r} (pack must carry review text, not "
                        f"a directory listing)")
        sums_checked = check_sums_file(index_path, failures)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}", file=sys.stderr)
            return 2
        print(f"REVIEW PACK VERIFIED: {len(rows)} pack file(s), "
              f"{sums_checked} sums entr(ies), index {index_path}")
        return 0
    except Exception:  # noqa: BLE001 - internal error path, exit 3
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
