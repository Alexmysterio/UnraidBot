"""Persistencia sencilla en JSON para suscripciones y estado de alertas."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

def _empty_state() -> dict[str, Any]:
    return {
        "version": 1,
        "subscribers": {},
        "alerts": {},
        "languages": {},
        "mutes": {},
        "metrics": [],
        "digest": {},
    }


class StateStore:
    """Estado del bot en un único archivo JSON con escritura atómica."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = _empty_state()

    async def load(self) -> None:
        async with self._lock:
            if not self.path.exists():
                self._data = _empty_state()
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("el estado no es un objeto JSON")
            except (OSError, ValueError) as exc:
                LOG.warning("No se pudo leer %s: %s. Se empieza de cero.", self.path, exc)
                self._data = _empty_state()
                return
            raw.setdefault("version", 1)
            raw.setdefault("subscribers", {})
            raw.setdefault("alerts", {})
            raw.setdefault("languages", {})
            raw.setdefault("mutes", {})
            raw.setdefault("metrics", [])
            raw.setdefault("digest", {})
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

    # -- idioma -------------------------------------------------------------

    def get_language(self, chat_id: int) -> str | None:
        languages = self._data.get("languages")
        if not isinstance(languages, dict):
            return None
        value = languages.get(str(chat_id))
        return str(value) if value else None

    async def set_language(self, chat_id: int, language: str) -> None:
        async with self._lock:
            self._data.setdefault("languages", {})[str(chat_id)] = language
            await self._save()

    # -- silencio temporal --------------------------------------------------

    def muted_until(self, chat_id: int) -> float | None:
        """Timestamp hasta el que el chat está silenciado, o ``None``."""
        mutes = self._data.get("mutes")
        if not isinstance(mutes, dict):
            return None
        try:
            until = float(mutes.get(str(chat_id)) or 0)
        except (TypeError, ValueError):
            return None
        return until if until > time.time() else None

    def is_muted(self, chat_id: int) -> bool:
        return self.muted_until(chat_id) is not None

    async def mute(self, chat_id: int, seconds: int) -> float:
        """Silencia un chat durante ``seconds`` y devuelve el instante final."""
        until = time.time() + max(1, int(seconds))
        async with self._lock:
            self._data.setdefault("mutes", {})[str(chat_id)] = until
            await self._save()
        return until

    async def unmute(self, chat_id: int) -> bool:
        async with self._lock:
            removed = self._data.setdefault("mutes", {}).pop(str(chat_id), None)
            if removed is not None:
                await self._save()
        return removed is not None

    # -- métricas y digest ---------------------------------------------------

    def metric_history(self, limit: int = 60) -> list[dict[str, Any]]:
        metrics = self._data.get("metrics")
        if not isinstance(metrics, list):
            return []
        entries = [item for item in metrics if isinstance(item, dict)]
        return entries[-max(1, int(limit)) :]

    async def record_metric(
        self,
        cpu: float | None,
        ram: float | None,
        ts: float | None = None,
        limit: int = 288,
    ) -> None:
        """Guarda una muestra de CPU/RAM para las sparklines."""
        if cpu is None and ram is None:
            return
        entry = {"ts": float(ts if ts is not None else time.time()), "cpu": cpu, "ram": ram}
        async with self._lock:
            metrics = self._data.get("metrics")
            if not isinstance(metrics, list):
                metrics = []
            metrics.append(entry)
            self._data["metrics"] = metrics[-max(2, int(limit)) :]
            await self._save()

    def digest_last(self) -> str | None:
        digest = self._data.get("digest")
        if not isinstance(digest, dict):
            return None
        value = digest.get("last")
        return str(value) if value else None

    async def set_digest_last(self, day: str) -> None:
        async with self._lock:
            self._data.setdefault("digest", {})["last"] = day
            await self._save()

    # -- alertas ------------------------------------------------------------

    def alert_entries(self) -> dict[str, dict[str, Any]]:
        alerts = self._data.get("alerts")
        if not isinstance(alerts, dict):
            return {}
        return {key: value for key, value in alerts.items() if isinstance(value, dict)}

    async def mark_alert(
        self, key: str, title: str, sent_at: float, severity: str = "warning"
    ) -> None:
        async with self._lock:
            self._data.setdefault("alerts", {})[key] = {
                "title": title,
                "last_sent": sent_at,
                "severity": severity,
            }
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
