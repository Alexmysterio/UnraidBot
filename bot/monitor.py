"""Vigilancia periódica y envío de alertas a los chats suscritos."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, TelegramError

from .config import Settings
from .health import Problem, detect_problems
from .state import StateStore
from .unraid import UnraidClient
from .views import build_alert_message, build_recovery_message

LOG = logging.getLogger(__name__)

MAX_PROBLEMS_PER_MESSAGE = 8


class AlertMonitor:
    def __init__(self, settings: Settings, client: UnraidClient, store: StateStore, bot: Bot) -> None:
        self.settings = settings
        self.client = client
        self.store = store
        self.bot = bot
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name="alert-monitor")

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
        if not self.settings.alerts_enabled:
            LOG.info("Monitor de alertas desactivado por configuración.")
            return
        await asyncio.sleep(15)
        while True:
            started = time.monotonic()
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - el monitor no debe morir
                LOG.exception("Fallo en el ciclo de alertas")
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(5.0, self.settings.alert_interval_seconds - elapsed))

    async def tick(self) -> None:
        subscribers = self.store.subscribers()
        if not subscribers:
            return

        snapshot = await self.client.snapshot()
        if not snapshot.array and not snapshot.info:
            LOG.warning("Alertas: API de Unraid inaccesible, se omite el ciclo")
            return

        problems = detect_problems(snapshot, self.settings)
        current = {problem.key: problem for problem in problems}
        known = self.store.alert_entries()
        now = time.time()
        repeat_seconds = self.settings.alert_repeat_minutes * 60

        new_problems: list[Problem] = []
        for key, problem in current.items():
            entry = known.get(key)
            last_sent = float(entry.get("last_sent") or 0) if entry else 0
            if entry is None or now - last_sent >= repeat_seconds:
                new_problems.append(problem)

        # No dar por resuelta una incidencia si la consulta de su sección falló.
        resolved_keys = [
            key
            for key in known
            if key not in current and _section_available(key, snapshot)
        ]
        if not new_problems and not resolved_keys:
            return

        hostname = str(((snapshot.info or {}).get("os") or {}).get("hostname") or "Unraid")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📊 Estado", callback_data="m:status"),
                    InlineKeyboardButton("🔕 Desactivar", callback_data="a:off"),
                ]
            ]
        )

        delivered = False
        if new_problems:
            shown = new_problems[:MAX_PROBLEMS_PER_MESSAGE]
            extra = len(new_problems) - len(shown)
            text = build_alert_message(shown, hostname)
            if extra > 0:
                text += f"\n\n… y {extra} incidencia(s) más. Abre el estado para verlas."
            delivered = await self._broadcast(subscribers, text, keyboard)

        if resolved_keys:
            titles = []
            for key in resolved_keys[:MAX_PROBLEMS_PER_MESSAGE]:
                title = await self.store.clear_alert(key)
                if title:
                    titles.append(title)
            if titles:
                text = build_recovery_message(titles, hostname)
                await self._broadcast(subscribers, text, None)

        if delivered:
            for problem in new_problems:
                await self.store.mark_alert(problem.key, problem.title, now)

        if resolved_keys:
            await self.store.prune_alerts()

    async def _broadcast(
        self,
        chat_ids: list[int],
        text: str,
        keyboard: InlineKeyboardMarkup | None,
    ) -> bool:
        delivered = False
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text[:4000],
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )
                delivered = True
            except Forbidden:
                LOG.info("El chat %s bloqueó el bot; se desuscribe.", chat_id)
                await self.store.unsubscribe(chat_id)
            except TelegramError as exc:
                LOG.warning("No se pudo enviar alerta a %s: %s", chat_id, exc)
        return delivered


def problems_summary(problems: list[Problem]) -> list[dict[str, Any]]:
    """Representación serializable útil para tests/logs."""
    return [
        {"key": item.key, "severity": item.severity, "title": item.title, "screen": item.screen}
        for item in problems
    ]


def _section_available(key: str, snapshot: Any) -> bool:
    """True si la consulta que produciría esa incidencia respondió bien."""
    if key.startswith(("array:", "parity:", "disk:")):
        return snapshot.array is not None
    if key.startswith("cpu:"):
        return snapshot.info is not None
    if key.startswith("memory:"):
        return snapshot.metrics is not None
    if key.startswith("docker:"):
        return snapshot.docker is not None
    if key.startswith("vm:"):
        return snapshot.vms is not None
    if key.startswith("ups:"):
        return snapshot.ups is not None
    if key.startswith("notif:"):
        return snapshot.notifications is not None
    return True
