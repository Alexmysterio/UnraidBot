"""Arranque de la aplicación de Telegram."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import BotCommand, Update
from telegram.ext import Application

from . import __version__, features
from .config import Settings
from .digest import DigestScheduler
from .handlers import register_handlers
from .handlers.common import on_error
from .heartbeat import heartbeat_loop, heartbeat_path
from .monitor import AlertMonitor
from .security import AuditLog, ConfirmationManager, RateLimiter
from .state import StateStore
from .telegram import configure_telegram
from .unraid import UnraidClient

LOG = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    settings: Settings = application.bot_data["settings"]
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    client = UnraidClient(settings)
    store = StateStore(settings.data_dir / "state.json")
    await store.load()

    application.bot_data["client"] = client
    application.bot_data["store"] = store
    application.bot_data["audit"] = AuditLog(settings.data_dir / "audit.log")
    application.bot_data["confirmations"] = ConfirmationManager(ttl_seconds=180)
    application.bot_data["rate"] = RateLimiter(
        actions=settings.user_rate_limit_actions,
        window=settings.user_rate_limit_window,
    )

    heartbeat_task = asyncio.create_task(
        heartbeat_loop(heartbeat_path(settings.data_dir)),
        name="heartbeat",
    )
    application.bot_data["tasks"] = [heartbeat_task]

    monitor = AlertMonitor(settings, client, store, application.bot)
    application.bot_data["monitor"] = monitor
    monitor.start()

    digest = DigestScheduler(settings, client, store, application.bot)
    application.bot_data["digest"] = digest
    digest.start()

    try:
        commands = [
            BotCommand("menu", "Menú principal"),
            BotCommand("estado", "Estado general del servidor"),
            BotCommand("discos", "Discos y estado SMART"),
            BotCommand("docker", "Gestionar contenedores"),
            BotCommand("vms", "Gestionar máquinas virtuales"),
            BotCommand("sistema", "Array, paridad, UPS y shares"),
            BotCommand("alertas", "Alertas automáticas"),
            BotCommand("buscar", "Buscar recursos del servidor"),
            BotCommand("historial", "Historial de auditoría (admin)"),
            BotCommand("rendimiento", "CPU y RAM con sparklines"),
            BotCommand("resumen", "Resumen diario ahora"),
        ]
        if features.is_enabled("qbittorrent"):
            commands.append(BotCommand("qbittorrent", "Torrents, límites y categorías"))
        if features.is_enabled("mikrotik"):
            commands.append(BotCommand("mikrotik", "Router: interfaces, rutas y firewall"))
        if features.is_enabled("wol"):
            commands.append(BotCommand("wol", "Encender equipos por Wake-on-LAN"))
        commands.extend(
            [
                BotCommand("help", "Ayuda"),
                BotCommand("id", "Ver mi ID de Telegram"),
            ]
        )
        await application.bot.set_my_commands(commands)
    except Exception as exc:  # noqa: BLE001 - no impedir el arranque por cosmética
        LOG.warning("No se pudieron publicar los comandos del bot: %s", exc)

    LOG.info("UnraidBot %s listo. API: %s", __version__, settings.unraid_api_url)
    if settings.unraid_api_socket:
        LOG.info("Usando socket Unix de Unraid: %s", settings.unraid_api_socket)
    if not settings.is_configured:
        LOG.warning(
            "ALLOWED_USER_IDS y VIEWER_USER_IDS están vacíos: el bot está en modo configuración. "
            "Envía /id al bot y añade tu ID."
        )
    if settings.read_only:
        LOG.warning("READ_ONLY=true: las acciones de escritura están deshabilitadas.")
    if not settings.alerts_enabled:
        LOG.info("ALERTS_ENABLED=false: monitor de alertas desactivado.")
    if features.count():
        LOG.info("Herramientas opcionales: %s", ", ".join(feature.label for feature in features.enabled()))


async def post_shutdown(application: Application) -> None:
    digest: DigestScheduler | None = application.bot_data.get("digest")
    if digest is not None:
        await digest.stop()

    monitor: AlertMonitor | None = application.bot_data.get("monitor")
    if monitor is not None:
        await monitor.stop()

    tasks: list[asyncio.Task[Any]] = list(application.bot_data.get("tasks", []))
    tasks.extend(application.bot_data.get("background", []))
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    client: UnraidClient | None = application.bot_data.get("client")
    if client is not None:
        await client.close()
    LOG.info("UnraidBot detenido.")


def build_application(settings: Settings) -> Application:
    features.configure(settings)
    builder = (
        Application.builder()
        .token(settings.telegram_token)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
    )
    builder = configure_telegram(builder, settings)
    application = builder.build()
    application.bot_data["settings"] = settings
    register_handlers(application)
    application.add_error_handler(on_error)
    return application


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)

    if not settings.is_configured:
        LOG.warning("Arranque sin usuarios autorizados: solo responderá /id y /help.")

    application = build_application(settings)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
