"""Gestión de contenedores Docker."""

from __future__ import annotations

import asyncio
import socket
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc
from ..keyboards import confirm_keyboard, docker_detail_keyboard, docker_list_keyboard, docker_logs_keyboard
from ..security import resolve_short
from ..unraid import UnraidError
from ..views import (
    build_docker_detail,
    build_docker_list,
    paginate,
    sort_containers,
)
from .common import audit, authorized, ensure_writable, get_settings, notify, render

PER_PAGE = 8

ACTION_LABELS = {
    "start": "▶️ Iniciando",
    "stop": "⏹ Deteniendo",
    "restart": "🔄 Reiniciando",
    "pause": "⏸ Pausando",
    "unpause": "▶️ Reanudando",
}


def _name(container: dict[str, Any]) -> str:
    names = container.get("names") or []
    return str(names[0]).lstrip("/") if names else "contenedor"


def _is_self(container: dict[str, Any], context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    bot_name = settings.bot_container_name.strip().lower()
    if bot_name and _name(container).strip().lower() == bot_name:
        return True
    # El hostname del contenedor es su ID corto: protege aunque se renombre.
    hostname = socket.gethostname()
    raw_id = str(container.get("id") or "").split(":")[-1]
    return len(hostname) >= 6 and raw_id.startswith(hostname)


@authorized
async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = 0
    query = update.callback_query
    if query is not None and query.data.startswith("d:l:"):
        try:
            page = int(query.data.split(":")[2])
        except (IndexError, ValueError):
            page = 0

    client = context.bot_data["client"]
    containers = await client.docker_containers()
    items, page, pages = paginate(sort_containers(containers), page, PER_PAGE)
    await render(
        update,
        context,
        build_docker_list(containers, page, PER_PAGE),
        docker_list_keyboard(items, page, pages),
    )


async def _detail_by_token(
    context: ContextTypes.DEFAULT_TYPE, token: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    client = context.bot_data["client"]
    containers = await client.docker_containers()
    return resolve_short(containers, token), containers


@authorized
async def show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    container, _ = await _detail_by_token(context, token)
    if container is None:
        await notify(update, context, "Ese contenedor ya no existe.")
        return
    await render(update, context, build_docker_detail(container), docker_detail_keyboard(container, page))


@authorized
async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    client = context.bot_data["client"]
    container, _ = await _detail_by_token(context, token)
    if container is None:
        await notify(update, context, "Ese contenedor ya no existe.")
        return
    try:
        lines = await client.docker_logs(str(container["id"]), tail=40)
    except UnraidError as exc:
        await notify(update, context, f"❌ No se pudieron leer los logs: {exc}")
        return
    await render(
        update,
        context,
        build_docker_detail(container, logs=lines),
        docker_logs_keyboard(container, page),
    )


@authorized
async def container_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    token = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

    if action not in ACTION_LABELS:
        await notify(update, context, "Acción no válida.")
        return

    container, _ = await _detail_by_token(context, token)
    if container is None:
        await notify(update, context, "Ese contenedor ya no existe.")
        return

    name = _name(container)
    if _is_self(container, context) and action in {"stop", "restart", "pause"}:
        await notify(
            update,
            context,
            "🛑 No puedo detener ni reiniciar el contenedor del propio bot. "
            "Hazlo desde el WebGUI o con docker compose.",
        )
        return

    if not await ensure_writable(update, context):
        return

    client = context.bot_data["client"]
    try:
        await client.docker_action(action, str(container["id"]))
    except UnraidError as exc:
        await audit(update, context, f"docker.{action}", name, outcome="error")
        await notify(update, context, f"❌ No se pudo aplicar «{action}»: {exc}")
        return

    await audit(update, context, f"docker.{action}", name)
    try:
        await query.answer(f"{ACTION_LABELS[action]} {name}…")
    except TelegramError:
        pass

    await asyncio.sleep(0.7)
    refreshed, _ = await _detail_by_token(context, token)
    if refreshed is None:
        containers = await client.docker_containers()
        items, current_page, pages = paginate(sort_containers(containers), page, PER_PAGE)
        await render(
            update,
            context,
            build_docker_list(containers, current_page, PER_PAGE),
            docker_list_keyboard(items, current_page, pages),
        )
        return
    await render(
        update,
        context,
        build_docker_detail(refreshed),
        docker_detail_keyboard(refreshed, page),
    )


@authorized
async def ask_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

    container, _ = await _detail_by_token(context, token)
    if container is None:
        await notify(update, context, "Ese contenedor ya no existe.")
        return
    if _is_self(container, context):
        await notify(
            update,
            context,
            "🛑 No puedo actualizar el contenedor del propio bot desde aquí.",
        )
        return
    if not await ensure_writable(update, context):
        return

    name = _name(container)
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="docker.update",
        target=str(container["id"]),
        args={"id": str(container["id"]), "name": name},
        prompt=(
            f"⬆️ <b>Actualizar {esc(name)}</b>\n\n"
            "Se descargará la imagen más reciente y se recreará el contenedor. "
            "Puede tardar varios minutos y el servicio estará unos segundos caído.\n\n"
            "¿Continuar?"
        ),
        success_text=(
            f"✅ <b>Actualización lanzada</b>\n\n"
            f"Contenedor: <b>{esc(name)}</b>\n"
            "El proceso puede tardar unos minutos. Revisa la ficha para ver el estado."
        ),
        return_callback=f"d:v:{token}:{page}",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
