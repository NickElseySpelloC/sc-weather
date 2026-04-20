from __future__ import annotations

import sys
from pathlib import Path

# Ensure local src-layout package imports resolve in tests.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
