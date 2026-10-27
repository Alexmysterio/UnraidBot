"""Vigilancia periódica y envío de alertas a los chats suscritos."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from .broadcast import broadcast
from .config import Settings
from .health import Problem, detect_problems
from .metrics import sample_usage
from .state import StateStore
from .unraid import Snapshot, UnraidClient
from .views import build_alert_message, build_recovery_message

LOG = logging.getLogger(__name__)

MAX_PROBLEMS_PER_MESSAGE = 8
OFFLINE_ALERT_AFTER_CYCLES = 2
SEVERITY_ORDER = {"warning": 1, "critical": 2}


class AlertMonitor:
    def __init__(self, settings: Settings, client: UnraidClient, store: StateStore, bot: Bot) -> None:
        self.settings = settings
        self.client = client
        self.store = store
        self.bot = bot
        self._task: asyncio.Task[None] | None = None
        self._offline_cycles = 0
        self._offline_alerted = False

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

    async def _record_metrics(self, snapshot: Snapshot) -> None:
        cpu, ram = sample_usage(snapshot)
        if cpu is None and ram is None:
            return
        try:
            await self.store.record_metric(cpu, ram)
        except OSError as exc:  # la telemetría no debe romper el monitor
            LOG.warning("No se pudo guardar la muestra de CPU/RAM: %s", exc)

    async def tick(self) -> None:
        subscribers = self.store.subscribers()
        if not subscribers:
            return

        snapshot = await self.client.snapshot(include_storage=True)
        if not snapshot.reachable:
            await self._handle_offline(subscribers)
            return

        await self._record_metrics(snapshot)

        if self._offline_alerted:
            hostname = str(((snapshot.info or {}).get("os") or {}).get("hostname") or "Unraid")
            if await self._broadcast(
                subscribers,
                build_recovery_message(["Sin conexión con la API de Unraid"], hostname),
                None,
            ):
                self._offline_alerted = False
        self._offline_cycles = 0

        problems = detect_problems(snapshot, self.settings)
        current = {problem.key: problem for problem in problems}
        known = self.store.alert_entries()
        now = time.time()
        repeat_seconds = self.settings.alert_repeat_minutes * 60

        new_problems: list[Problem] = []
        for key, problem in current.items():
            entry = known.get(key)
            last_sent = float(entry.get("last_sent") or 0) if entry else 0
            escalated = entry is not None and _severity_rank(problem.severity) > _severity_rank(
                str(entry.get("severity") or "warning")
            )
            if entry is None or escalated or now - last_sent >= repeat_seconds:
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
                    InlineKeyboardButton("🔕 Silenciar 8 h", callback_data="a:mute:28800"),
                ],
                [InlineKeyboardButton("🔕 Desactivar", callback_data="a:off")],
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
            pending = resolved_keys[:MAX_PROBLEMS_PER_MESSAGE]
            titles = [
                str((known.get(key) or {}).get("title") or key)
                for key in pending
            ]
            if titles:
                text = build_recovery_message(titles, hostname)
                if await self._broadcast(subscribers, text, None):
                    for key in pending:
                        await self.store.clear_alert(key)

        if delivered:
            for problem in new_problems:
                await self.store.mark_alert(
                    problem.key, problem.title, now, severity=problem.severity
                )

        if resolved_keys:
            await self.store.prune_alerts()

    async def _handle_offline(self, subscribers: list[int]) -> None:
        self._offline_cycles += 1
        LOG.warning(
            "Alertas: API de Unraid inaccesible (%s ciclo(s) consecutivo(s))",
            self._offline_cycles,
        )
        if (
            not self.settings.api_offline_alert
            or self._offline_alerted
            or self._offline_cycles < OFFLINE_ALERT_AFTER_CYCLES
        ):
            return
        problem = Problem(
            key="api:offline",
            severity="critical",
            title="Sin conexión con la API de Unraid",
            detail=(
                "El bot no puede contactar con la API local. Revisa que Unraid esté "
                "encendido, la URL y la conectividad de la red Docker."
            ),
            screen="m:status",
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔄 Reintentar", callback_data="m:status")]]
        )
        if await self._broadcast(subscribers, build_alert_message([problem], "Unraid"), keyboard):
            self._offline_alerted = True

    async def _broadcast(
        self,
        chat_ids: list[int],
        text: str,
        keyboard: InlineKeyboardMarkup | None,
    ) -> bool:
        return await broadcast(self.bot, self.store, chat_ids, text, keyboard)


def _severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.get(severity, 0)


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
    if key.startswith(("cpu:", "network:")):
        return snapshot.info is not None
    if key.startswith("memory:"):
        return snapshot.metrics is not None
    if key.startswith("share:"):
        return snapshot.shares is not None
    if key.startswith("smart:"):
        return snapshot.physical_disks is not None
    if key.startswith("docker:"):
        return snapshot.docker is not None
    if key.startswith("vm:"):
        return snapshot.vms is not None
    if key.startswith("ups:"):
        return snapshot.ups is not None
    if key.startswith("notif:"):
        return snapshot.notifications is not None
    return True
