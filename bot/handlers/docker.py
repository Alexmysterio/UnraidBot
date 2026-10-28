"""Gestión de contenedores Docker."""

from __future__ import annotations

import asyncio
import socket
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc
from ..i18n import localize
from ..keyboards import (
    confirm_keyboard,
    docker_detail_keyboard,
    docker_list_keyboard,
    docker_logs_keyboard,
    docker_maintenance_keyboard,
    docker_sizes_keyboard,
)
from ..security import resolve_short
from ..search import find_named
from ..unraid import UnraidError
from ..views import (
    build_docker_detail,
    build_docker_list,
    paginate,
    sort_containers,
)
from ..views_system import build_docker_extras, build_docker_sizes
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
    await _render_list(update, context, page)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    client = context.bot_data["client"]
    containers = await client.docker_containers()
    items, page, pages = paginate(sort_containers(containers), page, PER_PAGE)
    update_count = sum(1 for container in containers if container.get("isUpdateAvailable"))
    await render(
        update,
        context,
        build_docker_list(containers, page, PER_PAGE),
        docker_list_keyboard(items, page, pages, update_count),
    )


COMMAND_ACTIONS = {"start", "stop", "restart", "pause", "unpause", "update", "logs"}
USAGE = (
    "🐳 <b>Uso de /docker</b>\n\n"
    "/docker — lista de contenedores\n"
    "/docker start|stop|restart|pause|unpause &lt;nombre&gt;\n"
    "/docker update &lt;nombre&gt;\n"
    "/docker logs &lt;nombre&gt;"
)


@authorized
async def cmd_docker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    if not args or args[0].lower() in {"list", "ls"}:
        await _render_list(update, context, 0)
        return

    action = args[0].lower()
    if action not in COMMAND_ACTIONS:
        await notify(update, context, USAGE)
        return
    query = " ".join(args[1:]).strip()
    if not query:
        await notify(update, context, USAGE)
        return

    client = context.bot_data["client"]
    containers = await client.docker_containers()
    container, candidates = find_named(containers, query, keys=("names",))
    if container is None:
        if candidates:
            names = ", ".join(_name(item) for item in candidates[:6])
            await notify(update, context, f"Hay varias coincidencias: {names}. Sé más específico.")
        else:
            await notify(update, context, f"No encontré ningún contenedor llamado «{query}».")
        return

    name = _name(container)
    if action == "logs":
        try:
            lines = await client.docker_logs(str(container["id"]), tail=40)
        except UnraidError as exc:
            await notify(update, context, f"❌ No se pudieron leer los logs: {exc}")
            return
        await render(
            update,
            context,
            build_docker_detail(container, logs=lines),
            docker_logs_keyboard(container, 0),
        )
        return

    if _is_self(container, context) and action in {"stop", "restart", "pause", "update"}:
        await notify(
            update,
            context,
            "🛑 No puedo detener ni reiniciar el contenedor del propio bot. "
            "Hazlo desde el WebGUI o con docker compose.",
        )
        return
    if not await ensure_writable(update, context):
        return

    if action == "update":
        manager = context.bot_data["confirmations"]
        confirmation = manager.create(
            user_id=update.effective_user.id if update.effective_user else 0,
            chat_id=update.effective_chat.id if update.effective_chat else 0,
            action="docker.update",
            target=str(container["id"]),
            args={"id": str(container["id"]), "name": name},
            prompt=(
                f"⬆️ <b>Actualizar {esc(name)}</b>\n\n"
                "Se descargará la imagen más reciente y se recreará el contenedor. "
                "Puede tardar varios minutos.\n\n¿Continuar?"
            ),
            success_text=f"✅ <b>Actualización de {esc(name)} completada</b>",
            return_callback="m:docker",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    try:
        await client.docker_action(action, str(container["id"]))
    except UnraidError as exc:
        await audit(update, context, f"docker.{action}", name, outcome="error")
        await notify(update, context, f"❌ No se pudo aplicar «{action}»: {exc}")
        return

    await audit(update, context, f"docker.{action}", name)
    await asyncio.sleep(0.7)
    refreshed_list = await client.docker_containers()
    refreshed = next(
        (item for item in refreshed_list if str(item.get("id")) == str(container.get("id"))),
        None,
    )
    if refreshed is None:
        await _render_list(update, context, 0)
        return
    await render(
        update,
        context,
        build_docker_detail(refreshed),
        docker_detail_keyboard(refreshed, 0),
    )


async def _detail_by_token(
    context: ContextTypes.DEFAULT_TYPE, token: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    client = context.bot_data["client"]
    containers = await client.docker_containers()
    return resolve_short(containers, token), containers


async def _extras_for(
    context: ContextTypes.DEFAULT_TYPE, container: dict[str, Any]
) -> dict[str, Any] | None:
    """Datos de mantenimiento del contenedor; nunca impide abrir su ficha."""
    client = context.bot_data["client"]
    try:
        extras = await client.docker_extras()
    except UnraidError:
        return None
    name = _name(container)
    merged: dict[str, Any] = {}
    for item in extras.get("containers") or []:
        if not isinstance(item, dict):
            continue
        names = [str(value).lstrip("/") for value in item.get("names") or []]
        if str(item.get("id") or "") == str(container.get("id") or "") or name in names:
            merged.update(item)
            break
    for item in extras.get("updates") or []:
        if isinstance(item, dict) and str(item.get("name") or "") == name:
            merged["updateStatus"] = item.get("updateStatus")
            break
    conflicts: list[str] = []
    port_conflicts = extras.get("conflicts") or {}
    for conflict in port_conflicts.get("containerPorts") or []:
        members = conflict.get("containers") or []
        if any(str(item.get("name") or "") == name for item in members if isinstance(item, dict)):
            conflicts.append(f"interno {conflict.get('privatePort')}")
    for conflict in port_conflicts.get("lanPorts") or []:
        members = conflict.get("containers") or []
        if any(str(item.get("name") or "") == name for item in members if isinstance(item, dict)):
            conflicts.append(str(conflict.get("lanIpPort") or "LAN"))
    if conflicts:
        merged["conflicts"] = conflicts
    return merged or None


@authorized
async def show_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    extras = await client.docker_extras()
    await render(
        update,
        context,
        build_docker_extras(extras),
        docker_maintenance_keyboard(),
    )


@authorized
async def show_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    extras = await client.docker_extras()
    await render(update, context, build_docker_sizes(extras), docker_sizes_keyboard())


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
    extras = await _extras_for(context, container)
    await render(
        update,
        context,
        build_docker_detail(container, extras=extras),
        docker_detail_keyboard(container, page),
    )


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
        await query.answer(localize(f"{ACTION_LABELS[action]} {name}…"))
    except TelegramError:
        pass

    await asyncio.sleep(0.7)
    refreshed, _ = await _detail_by_token(context, token)
    if refreshed is None:
        containers = await client.docker_containers()
        items, current_page, pages = paginate(sort_containers(containers), page, PER_PAGE)
        update_count = sum(1 for item in containers if item.get("isUpdateAvailable"))
        await render(
            update,
            context,
            build_docker_list(containers, current_page, PER_PAGE),
            docker_list_keyboard(items, current_page, pages, update_count),
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
            "✅ <b>Actualización completada</b>\n\n"
            f"Contenedor: <b>{esc(name)}</b>\n"
            "La imagen se ha descargado y el contenedor se ha recreado."
        ),
        return_callback=f"d:v:{token}:{page}",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


@authorized
async def toggle_autostart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if not await ensure_writable(update, context):
        return

    name = _name(container)
    new_value = not bool(container.get("autoStart"))
    client = context.bot_data["client"]
    try:
        await client.docker_set_autostart(str(container["id"]), new_value)
    except UnraidError as exc:
        await audit(update, context, "docker.autostart", name, outcome="error")
        await notify(update, context, f"❌ No se pudo cambiar el autostart: {exc}")
        return

    await audit(update, context, "docker.autostart", f"{name}={new_value}")
    try:
        await query.answer(localize(f"Autostart {'activado' if new_value else 'desactivado'}"))
    except TelegramError:
        pass

    await asyncio.sleep(0.4)
    refreshed, _ = await _detail_by_token(context, token)
    if refreshed is not None:
        await render(
            update,
            context,
            build_docker_detail(refreshed),
            docker_detail_keyboard(refreshed, page),
        )


@authorized
async def ask_update_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    if not await ensure_writable(update, context):
        return

    client = context.bot_data["client"]
    containers = await client.docker_containers()
    updates = [container for container in containers if container.get("isUpdateAvailable")]
    if not updates:
        await notify(update, context, "✅ No hay actualizaciones pendientes.")
        return

    self_update = any(_is_self(container, context) for container in updates)
    warning = (
        "\n\n⚠️ Incluye el propio bot: se reiniciará y perderás la conexión unos segundos."
        if self_update
        else ""
    )
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="docker.update_all",
        target="all",
        args={},
        prompt=(
            f"⬆️ <b>Actualizar {len(updates)} contenedores</b>\n\n"
            "Se descargarán las imágenes más recientes y se recrearán los contenedores. "
            f"Puede tardar varios minutos.{warning}\n\n¿Continuar?"
        ),
        success_text=(
            f"✅ <b>Actualización de {len(updates)} contenedores completada</b>\n\n"
            "Las imágenes se han descargado y los contenedores se han recreado. "
            "Revisa la lista para ver el estado final."
        ),
        return_callback="m:docker",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
