"""Healthcheck para Docker: comprueba que el latido está fresco."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def main() -> int:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    path = data_dir / "heartbeat"
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        print(f"Sin latido en {path}")
        return 1
    if age > 180:
        print(f"Latido obsoleto: {age:.0f}s")
        return 1
    print(f"OK ({age:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
