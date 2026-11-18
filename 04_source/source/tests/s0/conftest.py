"""S0 runner tests (P026 T007).

Inserts the same import path the runner uses: ``src/`` first (the
production ``pagetrace`` package; T013 P2-08 removed the old top-level
T001 stub), then ``tests/`` (Oracle) and ``tools/`` (``run_s0`` itself).
"""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]

for _entry in (str(PACKAGE_ROOT / "tools"),
               str(PACKAGE_ROOT / "tests"),
               str(PACKAGE_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
