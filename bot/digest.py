"""Resumen diario programado (digest) para los chats suscritos."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Bot

from .broadcast import broadcast
from .config import Settings
from .health import detect_problems
from .state import StateStore
from .unraid import UnraidClient
from .views import build_digest

LOG = logging.getLogger(__name__)


class DigestScheduler:
    """Comprueba cada minuto si toca enviar el resumen del día."""

    def __init__(
        self,
        settings: Settings,
        client: UnraidClient,
        store: StateStore,
        bot: Bot,
    ) -> None:
        self.settings = settings
        self.client = client
        self.store = store
        self.bot = bot
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name="digest-scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def run(self) -> None:
        if not self.settings.digest_enabled:
            LOG.info("Resumen diario desactivado por configuración.")
            return
        await asyncio.sleep(20)
        while True:
            try:
                await self.send_if_due()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - el planificador no debe morir
                LOG.exception("Fallo al enviar el resumen diario")
            await asyncio.sleep(60)

    def _local_now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.settings.timezone))
        except Exception:  # pragma: no cover - zona validada al arrancar
            return datetime.now()

    async def send_if_due(self, now: datetime | None = None) -> bool:
        """Envía el digest si ya es la hora y no se ha enviado hoy."""
        if not self.settings.digest_enabled:
            return False
        moment = now or self._local_now()
        if (moment.hour, moment.minute) < (
            self.settings.digest_hour,
            self.settings.digest_minute,
        ):
            return False

        day = moment.date().isoformat()
        if self.store.digest_last() == day:
            return False

        subscribers = self.store.subscribers()
        if not subscribers:
            return False

        snapshot = await self.client.snapshot(include_storage=True)
        problems = detect_problems(snapshot, self.settings) if snapshot.reachable else []
        text = build_digest(snapshot, self.settings, problems)
        delivered = await broadcast(self.bot, self.store, subscribers, text)
        if delivered:
            await self.store.set_digest_last(day)
            LOG.info("Resumen diario enviado a %s chat(s).", len(subscribers))
        return delivered


def scheduler_due(settings: Settings, store: StateStore, now: datetime) -> bool:
    """Utilidad para tests: indica si el digest está pendiente."""
    if not settings.digest_enabled or store.digest_last() == now.date().isoformat():
        return False
    return (now.hour, now.minute) >= (settings.digest_hour, settings.digest_minute)
