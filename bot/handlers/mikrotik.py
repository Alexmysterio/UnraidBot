"""Herramienta opcional: MikroTik (RouterOS 7 REST)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..keyboards import (
    confirm_keyboard,
    mikrotik_main_keyboard,
    mikrotik_paged_keyboard,
)
from ..services import ServiceError
from ..services.mikrotik import MikroTik
from ..views import paginate
from ..views_integrations import (
    MT_LEASE_PER_PAGE,
    MT_LOG_PER_PAGE,
    MT_PER_PAGE,
    build_mikrotik_firewall,
    build_mikrotik_interfaces,
    build_mikrotik_leases,
    build_mikrotik_logs,
    build_mikrotik_main,
    build_mikrotik_routes,
)
from .common import authorized, ensure_writable, get_settings, notify, render

USAGE = (
    "📡 <b>Uso de /mikrotik</b>\n\n"
    "/mikrotik — resumen del router\n"
    "/mikrotik interfaces — interfaces y tráfico\n"
    "/mikrotik leases — concesiones DHCP\n"
    "/mikrotik rutas — tabla de rutas\n"
    "/mikrotik firewall — reglas de filtrado\n"
    "/mikrotik logs — últimos registros\n"
    "/mikrotik reboot — reiniciar el router"
)


def _page(data: str) -> int:
    parts = data.split(":")
    return int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0


def _service(settings) -> MikroTik:
    return MikroTik(settings)


async def _render_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        identity = await service.identity()
        resource = await service.resource()
        interfaces = await service.interfaces()
        leases = await service.leases()
        routes = await service.routes()
        firewall = await service.firewall()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await render(
        update,
        context,
        build_mikrotik_main(identity, resource, interfaces, leases, routes, firewall),
        mikrotik_main_keyboard(),
    )


async def _render_interfaces(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        interfaces = await service.interfaces()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    _, page, pages = paginate(interfaces, page, MT_PER_PAGE)
    await render(
        update,
        context,
        build_mikrotik_interfaces(interfaces, page),
        mikrotik_paged_keyboard("mt:i", page, pages),
    )


async def _render_leases(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        leases = await service.leases()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    _, page, pages = paginate(leases, page, MT_LEASE_PER_PAGE)
    await render(
        update,
        context,
        build_mikrotik_leases(leases, page),
        mikrotik_paged_keyboard("mt:l", page, pages),
    )


async def _render_routes(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        routes = await service.routes()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    _, page, pages = paginate(routes, page, MT_PER_PAGE)
    await render(
        update,
        context,
        build_mikrotik_routes(routes, page),
        mikrotik_paged_keyboard("mt:r", page, pages),
    )


async def _render_firewall(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        rules = await service.firewall()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    _, page, pages = paginate(rules, page, MT_PER_PAGE)
    await render(
        update,
        context,
        build_mikrotik_firewall(rules, page),
        mikrotik_paged_keyboard("mt:f", page, pages),
    )


async def _render_logs(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    settings = get_settings(context)
    service = _service(settings)
    try:
        logs = await service.logs()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    ordered = sorted(
        logs,
        key=lambda item: str(item.get("time") or ""),
        reverse=True,
    )
    _, page, pages = paginate(ordered, page, MT_LOG_PER_PAGE)
    await render(
        update,
        context,
        build_mikrotik_logs(ordered, page),
        mikrotik_paged_keyboard("mt:g", page, pages),
    )


@authorized
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_main(update, context)


@authorized
async def on_interfaces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await _render_interfaces(update, context, _page(query.data))


@authorized
async def on_leases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await _render_leases(update, context, _page(query.data))


@authorized
async def on_routes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await _render_routes(update, context, _page(query.data))


@authorized
async def on_firewall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await _render_firewall(update, context, _page(query.data))


@authorized
async def on_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await _render_logs(update, context, _page(query.data))


@authorized
async def ask_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    if not await ensure_writable(update, context):
        return
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="mikrotik.reboot",
        target="router",
        args={},
        prompt=(
            "🔁 <b>Reiniciar MikroTik</b>\n\n"
            "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?"
        ),
        success_text="🔁 <b>Reinicio de MikroTik enviado.</b>",
        return_callback="tool:mt",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


@authorized
async def cmd_mikrotik(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    if not args:
        await _render_main(update, context)
        return
    action = args[0].lower()
    if action in {"interfaces", "ifaces", "interfaz"}:
        await _render_interfaces(update, context, 0)
    elif action in {"leases", "dhcp"}:
        await _render_leases(update, context, 0)
    elif action in {"rutas", "routes"}:
        await _render_routes(update, context, 0)
    elif action in {"firewall", "reglas"}:
        await _render_firewall(update, context, 0)
    elif action in {"logs", "registros"}:
        await _render_logs(update, context, 0)
    elif action in {"reboot", "reiniciar"}:
        if not await ensure_writable(update, context):
            return
        manager = context.bot_data["confirmations"]
        user = update.effective_user
        chat = update.effective_chat
        if user is None or chat is None:
            return
        confirmation = manager.create(
            user_id=user.id,
            chat_id=chat.id,
            action="mikrotik.reboot",
            target="router",
            args={},
            prompt=(
                "🔁 <b>Reiniciar MikroTik</b>\n\n"
                "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?"
            ),
            success_text="🔁 <b>Reinicio de MikroTik enviado.</b>",
            return_callback="tool:mt",
        )
        await render(
            update, context, confirmation.prompt, confirm_keyboard(confirmation.token)
        )
    else:
        await notify(update, context, USAGE)
