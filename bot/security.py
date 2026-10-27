"""Autorización, limitación de frecuencia, confirmaciones y auditoría."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Identificadores cortos para callback_data
# ---------------------------------------------------------------------------

def short_id(value: str, length: int = 10) -> str:
    """Hash corto y estable para meter IDs largos en callback_data."""
    import hashlib

    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:length]


def resolve_short(items: list[dict[str, Any]], token: str, key: str = "id") -> dict[str, Any] | None:
    """Busca el elemento cuyo id produce el token corto."""
    for item in items:
        raw = item.get(key)
        if raw is not None and short_id(str(raw)) == token:
            return item
    return None


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token bucket sencillo por usuario."""

    def __init__(self, actions: int = 30, window: int = 60) -> None:
        self.actions = actions
        self.window = window
        self._events: dict[int, list[float]] = {}

    def allow(self, key: int) -> bool:
        now = time.monotonic()
        events = [stamp for stamp in self._events.get(key, []) if now - stamp < self.window]
        if len(events) >= self.actions:
            self._events[key] = events
            return False
        events.append(now)
        self._events[key] = events
        return True

    def reset(self, key: int) -> None:
        self._events.pop(key, None)


# ---------------------------------------------------------------------------
# Confirmaciones con caducidad
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Confirmation:
    token: str
    user_id: int
    chat_id: int
    action: str
    target: str
    args: dict[str, Any]
    prompt: str
    success_text: str
    return_callback: str
    created_at: float = field(default_factory=time.time)


class ConfirmationManager:
    """Confirmaciones en memoria con caducidad y ligadas al usuario."""

    def __init__(self, ttl_seconds: int = 180) -> None:
        self.ttl = ttl_seconds
        self._items: dict[str, Confirmation] = {}

    def _purge(self) -> None:
        now = time.time()
        expired = [token for token, item in self._items.items() if now - item.created_at > self.ttl]
        for token in expired:
            self._items.pop(token, None)

    def create(
        self,
        *,
        user_id: int,
        chat_id: int,
        action: str,
        target: str,
        args: dict[str, Any],
        prompt: str,
        success_text: str,
        return_callback: str,
    ) -> Confirmation:
        self._purge()
        token = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10]
        item = Confirmation(
            token=token,
            user_id=user_id,
            chat_id=chat_id,
            action=action,
            target=target,
            args=args,
            prompt=prompt,
            success_text=success_text,
            return_callback=return_callback,
        )
        self._items[token] = item
        return item

    def pop(self, token: str, user_id: int) -> Confirmation | None:
        self._purge()
        item = self._items.get(token)
        if item is None or item.user_id != user_id:
            return None
        return self._items.pop(token)

    def cancel(self, token: str, user_id: int) -> Confirmation | None:
        return self.pop(token, user_id)


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------

class AuditLog:
    """Registro JSONL de acciones, con rotación por tamaño."""

    def __init__(self, path: Path, max_bytes: int = 5_000_000) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self._lock = asyncio.Lock()

    async def write(
        self,
        *,
        user_id: int | None,
        username: str | None,
        chat_id: int | None,
        action: str,
        target: str = "",
        outcome: str = "ok",
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user_id": user_id,
            "username": username,
            "chat_id": chat_id,
            "action": action,
            "target": target,
            "outcome": outcome,
        }
        try:
            async with self._lock:
                await asyncio.to_thread(self._write_sync, record)
        except OSError as exc:  # la auditoría nunca debe tumbar el bot
            LOG.warning("No se pudo escribir la auditoría: %s", exc)

    def _write_sync(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > self.max_bytes:
            rotated = self.path.with_suffix(self.path.suffix + ".1")
            rotated.unlink(missing_ok=True)
            self.path.rename(rotated)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def read(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        query: str = "",
    ) -> tuple[list[dict[str, Any]], int]:
        """Devuelve registros del más reciente al más antiguo y el total filtrado."""
        async with self._lock:
            return await asyncio.to_thread(self._read_sync, limit, offset, query)

    def _read_sync(
        self,
        limit: int,
        offset: int,
        query: str,
    ) -> tuple[list[dict[str, Any]], int]:
        if not self.path.exists():
            return [], 0
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            LOG.warning("No se pudo leer la auditoría: %s", exc)
            return [], 0

        records: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                records.append(item)
        records.reverse()

        needle = query.strip().casefold()
        if needle:
            records = [
                item
                for item in records
                if any(
                    needle in str(item.get(key) or "").casefold()
                    for key in ("action", "target", "username", "outcome", "user_id")
                )
            ]

        total = len(records)
        start = max(0, int(offset))
        size = max(1, int(limit))
        return records[start : start + size], total
