"""Herramienta opcional: qBittorrent."""

from __future__ import annotations

import asyncio
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc, shorten
from ..i18n import localize
from ..integrations import filter_torrents, is_paused
from ..keyboards import (
    confirm_keyboard,
    qb_categories_keyboard,
    qb_detail_keyboard,
    qb_limits_keyboard,
    qb_list_keyboard,
)
from ..search import find_named
from ..security import resolve_short
from ..services import ServiceError
from ..services.qbittorrent import QBittorrent
from ..views import paginate
from ..views_integrations import (
    QB_PER_PAGE,
    build_qb_categories,
    build_qb_detail,
    build_qb_limits,
    build_qb_list,
)
from .common import audit, authorized, ensure_writable, get_settings, notify, render

USAGE = (
    "🐳 <b>Uso de /qbittorrent</b>\n\n"
    "/qbittorrent — lista de torrents\n"
    "/qbittorrent add &lt;magnet|url&gt;\n"
    "/qbittorrent pause|resume &lt;nombre&gt;\n"
    "/qbittorrent delete &lt;nombre&gt; [files]\n"
    "/qbittorrent limit down|up|both &lt;KB/s&gt;\n"
    "/qbittorrent limits\n"
    "/qbittorrent alt\n"
    "/qbittorrent categories"
)


def _name(torrent: dict[str, Any]) -> str:
    return str(torrent.get("name") or torrent.get("hash") or "torrent")


async def _load(settings) -> tuple[dict, list[dict], bool]:
    service = QBittorrent(settings)
    try:
        status = await service.status()
        torrents = await service.torrents()
        alt_speed = await service.alt_speed_enabled()
    finally:
        await service.close()
    return status, torrents, alt_speed


async def _render_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    filter_key: str = "all",
    page: int = 0,
) -> None:
    settings = get_settings(context)
    try:
        status, torrents, alt_speed = await _load(settings)
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    visible = filter_torrents(torrents, filter_key)
    items, page, pages = paginate(visible, page, QB_PER_PAGE)
    await render(
        update,
        context,
        build_qb_list(status, torrents, page, QB_PER_PAGE, filter_key, alt_speed),
        qb_list_keyboard(items, page, pages, filter_key, alt_speed),
    )


async def _render_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
    filter_key: str,
    page: int,
) -> None:
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        torrents = await service.torrents()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    torrent = resolve_short(torrents, token, key="hash")
    if torrent is None:
        await notify(update, context, "Ese torrent ya no existe.")
        await _render_list(update, context, filter_key, page)
        return
    await render(
        update,
        context,
        build_qb_detail(torrent, settings),
        qb_detail_keyboard(torrent, filter_key, page),
    )


async def _render_limits(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        preferences = await service.preferences()
        alt_speed = await service.alt_speed_enabled()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await render(
        update,
        context,
        build_qb_limits(preferences, alt_speed),
        qb_limits_keyboard(alt_speed),
    )


async def _render_categories(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        categories = await service.categories()
        torrents = await service.torrents()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await render(
        update,
        context,
        build_qb_categories(categories, torrents),
        qb_categories_keyboard(),
    )


def _parse_target(data: str) -> tuple[str, str, int]:
    parts = data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    filter_key = parts[3] if len(parts) > 3 and parts[3] else "all"
    page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
    return token, filter_key, page


async def _add_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE, url: str
) -> None:
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        await service.add(url)
    except ServiceError as exc:
        await audit(update, context, "qbittorrent.add", url, outcome="error")
        await notify(update, context, f"❌ No se pudo añadir el torrent: {exc}")
        return
    finally:
        await service.close()
    await audit(update, context, "qbittorrent.add", shorten(url, 80))
    await notify(update, context, "✅ Torrent añadido")
    await _render_list(update, context, "all", 0)


@authorized
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_list(update, context, "all", 0)


@authorized
async def on_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    filter_key = parts[2] if len(parts) > 2 and parts[2] else "all"
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    await _render_list(update, context, filter_key, page)


@authorized
async def show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    token, filter_key, page = _parse_target(query.data)
    await _render_detail(update, context, token, filter_key, page)


@authorized
async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    if not await ensure_writable(update, context):
        return
    token, filter_key, page = _parse_target(query.data)
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        torrents = await service.torrents()
        torrent = resolve_short(torrents, token, key="hash")
        if torrent is None:
            await notify(update, context, "Ese torrent ya no existe.")
            return
        paused = is_paused(torrent)
        await service.set_paused(str(torrent["hash"]), not paused)
    except ServiceError as exc:
        await audit(update, context, "qbittorrent.toggle", outcome="error")
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await audit(
        update,
        context,
        "qbittorrent.resume" if paused else "qbittorrent.pause",
        _name(torrent),
    )
    try:
        await query.answer(localize("▶️ Torrent reanudado" if paused else "⏸ Torrent pausado"))
    except TelegramError:
        pass
    await asyncio.sleep(0.2)
    await _render_detail(update, context, token, filter_key, page)


@authorized
async def ask_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    if not await ensure_writable(update, context):
        return
    token, filter_key, page = _parse_target(query.data)
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        torrents = await service.torrents()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    torrent = resolve_short(torrents, token, key="hash")
    if torrent is None:
        await notify(update, context, "Ese torrent ya no existe.")
        return
    name = _name(torrent)
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="qbittorrent.delete",
        target=name,
        args={"hash": str(torrent["hash"]), "delete_files": False},
        prompt=(
            f"🗑 <b>Borrar {esc(shorten(name, 60))}</b>\n\n"
            "Se eliminará el torrent de qBittorrent, pero no los archivos descargados.\n\n"
            "¿Continuar?"
        ),
        success_text=f"🗑 <b>Torrent eliminado</b>\n\n{esc(shorten(name, 60))}",
        return_callback=f"qb:l:{filter_key}:{page}",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


@authorized
async def arm_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    context.chat_data["qb_add_armed"] = True
    await render(
        update,
        context,
        "➕ <b>Añadir torrent</b>\n\n"
        "Envía un enlace magnet o una URL .torrent.\n"
        "Se añadirá a la categoría por defecto.",
        qb_categories_keyboard(),
    )


async def consume_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Captura el enlace cuando el usuario pulsó «Añadir»."""
    if not context.chat_data.pop("qb_add_armed", False):
        return False
    message = update.effective_message
    url = (message.text or "").strip() if message is not None else ""
    if not url:
        return True
    if not await ensure_writable(update, context):
        return True
    if not (url.startswith(("magnet:", "http://", "https://"))):
        await notify(update, context, "❌ Envía un enlace magnet o una URL http(s).")
        return True
    await _add_url(update, context, url)
    return True


@authorized
async def show_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_limits(update, context)


@authorized
async def toggle_alt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    settings = get_settings(context)
    service = QBittorrent(settings)
    try:
        await service.toggle_alt_speed()
    except ServiceError as exc:
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await audit(update, context, "qbittorrent.alt_speed", "toggle")
    await _render_limits(update, context)


@authorized
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_categories(update, context)


@authorized
async def action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pausa o reanuda todos los torrents."""
    query = update.callback_query
    if query is None:
        return
    if not await ensure_writable(update, context):
        return
    settings = get_settings(context)
    service = QBittorrent(settings)
    pause = query.data.endswith("pause")
    try:
        if pause:
            await service.pause_all()
        else:
            await service.resume_all()
    except ServiceError as exc:
        await audit(update, context, "qbittorrent.action", outcome="error")
        await notify(update, context, f"❌ {exc}")
        return
    finally:
        await service.close()
    await audit(
        update,
        context,
        "qbittorrent.pause_all" if pause else "qbittorrent.resume_all",
        "all",
    )
    try:
        await query.answer(
            localize(
                "⏸ Todos los torrents pausados"
                if pause
                else "▶️ Todos los torrents reanudados"
            )
        )
    except TelegramError:
        pass
    await asyncio.sleep(0.3)
    await _render_list(update, context, "all", 0)


@authorized
async def cmd_qbittorrent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    if not args or args[0].lower() in {"list", "ls"}:
        await _render_list(update, context, "all", 0)
        return

    action_name = args[0].lower()
    rest = args[1:]
    if action_name == "add":
        if not rest:
            await arm_add(update, context)
            return
        url = " ".join(rest).strip()
        if not url.startswith(("magnet:", "http://", "https://")):
            await notify(update, context, "❌ Envía un enlace magnet o una URL http(s).")
            return
        if not await ensure_writable(update, context):
            return
        await _add_url(update, context, url)
        return

    if action_name in {"pause", "resume"}:
        query = " ".join(rest).strip()
        if not query:
            await notify(update, context, USAGE)
            return
        if not await ensure_writable(update, context):
            return
        settings = get_settings(context)
        service = QBittorrent(settings)
        try:
            torrents = await service.torrents()
            torrent, candidates = find_named(torrents, query, keys=("name", "hash"))
            if torrent is None:
                if candidates:
                    names = ", ".join(shorten(_name(item), 30) for item in candidates[:6])
                    await notify(update, context, f"Hay varias coincidencias: {names}. Sé más específico.")
                else:
                    await notify(update, context, f"No encontré ningún torrent llamado «{query}».")
                return
            await service.set_paused(str(torrent["hash"]), action_name == "pause")
        except ServiceError as exc:
            await notify(update, context, f"❌ {exc}")
            return
        finally:
            await service.close()
        await audit(update, context, f"qbittorrent.{action_name}", _name(torrent))
        await notify(
            update,
            context,
            "⏸ Torrent pausado" if action_name == "pause" else "▶️ Torrent reanudado",
        )
        return

    if action_name == "delete":
        if not rest:
            await notify(update, context, USAGE)
            return
        delete_files = rest[-1].lower() in {"files", "archivos", "datos"}
        if delete_files:
            rest = rest[:-1]
        query = " ".join(rest).strip()
        if not query:
            await notify(update, context, USAGE)
            return
        if not await ensure_writable(update, context):
            return
        settings = get_settings(context)
        service = QBittorrent(settings)
        try:
            torrents = await service.torrents()
            torrent, candidates = find_named(torrents, query, keys=("name", "hash"))
            if torrent is None:
                if candidates:
                    names = ", ".join(shorten(_name(item), 30) for item in candidates[:6])
                    await notify(update, context, f"Hay varias coincidencias: {names}. Sé más específico.")
                else:
                    await notify(update, context, f"No encontré ningún torrent llamado «{query}».")
                return
        except ServiceError as exc:
            await notify(update, context, f"❌ {exc}")
            return
        finally:
            await service.close()
        name = _name(torrent)
        manager = context.bot_data["confirmations"]
        confirmation = manager.create(
            user_id=update.effective_user.id if update.effective_user else 0,
            chat_id=update.effective_chat.id if update.effective_chat else 0,
            action="qbittorrent.delete",
            target=name,
            args={"hash": str(torrent["hash"]), "delete_files": delete_files},
            prompt=(
                f"🗑 <b>Borrar {esc(shorten(name, 60))}</b>\n\n"
                + (
                    "Se eliminará el torrent y también los archivos descargados.\n\n"
                    if delete_files
                    else "Se eliminará el torrent, pero no los archivos descargados.\n\n"
                )
                + "¿Continuar?"
            ),
            success_text=f"🗑 <b>Torrent eliminado</b>\n\n{esc(shorten(name, 60))}",
            return_callback="qb:l:all:0",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    if action_name in {"limit", "limits"}:
        if action_name == "limits" or not rest:
            await _render_limits(update, context)
            return
        if not await ensure_writable(update, context):
            return
        target = rest[0].lower()
        if target not in {"down", "up", "both"}:
            await notify(update, context, USAGE)
            return
        try:
            kbps = int(rest[1]) if len(rest) > 1 else -1
        except ValueError:
            kbps = -1
        if kbps < 0:
            await notify(update, context, USAGE)
            return
        limit_bytes = kbps * 1024
        settings = get_settings(context)
        service = QBittorrent(settings)
        try:
            if target in {"down", "both"}:
                await service.set_download_limit(limit_bytes)
            if target in {"up", "both"}:
                await service.set_upload_limit(limit_bytes)
        except ServiceError as exc:
            await notify(update, context, f"❌ {exc}")
            return
        finally:
            await service.close()
        await audit(update, context, "qbittorrent.limit", f"{target}={kbps}KB/s")
        await notify(update, context, "⚙️ Límites actualizados")
        await _render_limits(update, context)
        return

    if action_name == "alt":
        if not await ensure_writable(update, context):
            return
        settings = get_settings(context)
        service = QBittorrent(settings)
        try:
            await service.toggle_alt_speed()
        except ServiceError as exc:
            await notify(update, context, f"❌ {exc}")
            return
        finally:
            await service.close()
        await audit(update, context, "qbittorrent.alt_speed", "toggle")
        await _render_limits(update, context)
        return

    if action_name in {"categories", "cats"}:
        await _render_categories(update, context)
        return

    await notify(update, context, USAGE)
