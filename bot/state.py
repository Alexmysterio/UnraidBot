"""Persistencia sencilla en JSON para suscripciones y estado de alertas."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


class StateStore:
    """Estado del bot en un único archivo JSON con escritura atómica."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = {"version": 1, "subscribers": {}, "alerts": {}}

    async def load(self) -> None:
        async with self._lock:
            if not self.path.exists():
                self._data = {"version": 1, "subscribers": {}, "alerts": {}}
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("el estado no es un objeto JSON")
            except (OSError, ValueError) as exc:
                LOG.warning("No se pudo leer %s: %s. Se empieza de cero.", self.path, exc)
                self._data = {"version": 1, "subscribers": {}, "alerts": {}}
                return
            raw.setdefault("version", 1)
            raw.setdefault("subscribers", {})
            raw.setdefault("alerts", {})
            self._data = raw

    async def _save(self) -> None:
        payload = json.dumps(self._data, ensure_ascii=False, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def write() -> None:
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(self.path)

        await asyncio.to_thread(write)

    # -- suscripciones ------------------------------------------------------

    def subscribers(self) -> list[int]:
        return [int(chat_id) for chat_id in self._data.get("subscribers", {})]

    def is_subscribed(self, chat_id: int) -> bool:
        return str(chat_id) in self._data.get("subscribers", {})

    async def subscribe(self, chat_id: int) -> None:
        from datetime import datetime, timezone

        async with self._lock:
            self._data.setdefault("subscribers", {})[str(chat_id)] = {
                "since": datetime.now(timezone.utc).isoformat(timespec="seconds")
            }
            await self._save()

    async def unsubscribe(self, chat_id: int) -> None:
        async with self._lock:
            self._data.setdefault("subscribers", {}).pop(str(chat_id), None)
            await self._save()

    # -- alertas ------------------------------------------------------------

    def alert_entries(self) -> dict[str, dict[str, Any]]:
        alerts = self._data.get("alerts")
        if not isinstance(alerts, dict):
            return {}
        return {key: value for key, value in alerts.items() if isinstance(value, dict)}

    async def mark_alert(self, key: str, title: str, sent_at: float) -> None:
        async with self._lock:
            self._data.setdefault("alerts", {})[key] = {"title": title, "last_sent": sent_at}
            await self._save()

    async def clear_alert(self, key: str) -> str | None:
        async with self._lock:
            entry = self._data.setdefault("alerts", {}).pop(key, None)
            await self._save()
        if isinstance(entry, dict):
            return str(entry.get("title") or key)
        return None

    async def prune_alerts(self, max_age_seconds: float = 7 * 86400) -> None:
        """Elimina estados huérfanos antiguos."""
        import time

        now = time.time()
        async with self._lock:
            alerts = self._data.setdefault("alerts", {})
            stale = [
                key
                for key, value in alerts.items()
                if not isinstance(value, dict) or now - float(value.get("last_sent") or 0) > max_age_seconds
            ]
            for key in stale:
                alerts.pop(key, None)
            if stale:
                await self._save()
