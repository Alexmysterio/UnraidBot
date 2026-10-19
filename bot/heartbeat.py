"""Latido para el healthcheck de Docker."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

LOG = logging.getLogger(__name__)


def heartbeat_path(data_dir: Path) -> Path:
    return data_dir / "heartbeat"


def touch_heartbeat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(time.time())), encoding="utf-8")


async def heartbeat_loop(path: Path, interval: int = 60) -> None:
    while True:
        try:
            await asyncio.to_thread(touch_heartbeat, path)
        except OSError as exc:
            LOG.warning("No se pudo escribir el latido: %s", exc)
        await asyncio.sleep(interval)
