"""Pantallas del sistema: array, paridad, UPS, notificaciones y shares."""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..keyboards import (
    array_keyboard,
    back_menu,
    confirm_keyboard,
    notification_detail_keyboard,
    notifications_list_keyboard,
    parity_choice_keyboard,
    parity_keyboard,
    shares_keyboard,
    simple_back_keyboard,
    system_keyboard,
)
from ..formatting import esc
from ..i18n import localize
from ..security import resolve_short
from ..unraid import Snapshot, UnraidError
from ..views import (
    build_array,
    build_info,
    build_parity,
    build_shares,
    build_system_menu,
    build_ups,
)
from ..views_system import (
    NOTIF_PER_PAGE,
    build_notification_detail,
    build_notification_list,
)
from .common import audit, authorized, ensure_writable, get_settings, notify, render

LOG = logging.getLogger(__name__)

# Mensajes con los que la API avisa de que no hay ningún UPS que leer.
_MISSING_UPS_HINTS = (
    "apcaccess",
    "no ups",
    "ups data",
    "not configured",
    "sin datos",
)


def _ups_missing(exc: UnraidError) -> bool:
    """True si el error solo significa «este servidor no tiene UPS»."""
    message = str(exc).lower()
    return any(hint in message for hint in _MISSING_UPS_HINTS)


def _page_from(data: str, index: int = 2) -> int:
    parts = data.split(":")
    if len(parts) > index and parts[index].isdigit():
        return int(parts[index])
    return 0


@authorized
async def show_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    snapshot = await client.snapshot(include_info=False, include_health=True)
    await render(update, context, build_system_menu(snapshot), system_keyboard())


@authorized
async def show_array(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    array = await client.array()
    snapshot = Snapshot(array=array)
    await render(
        update,
        context,
        build_array(snapshot, settings),
        array_keyboard(array.get("state")),
    )


@authorized
async def show_parity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    array = await client.array()
    snapshot = Snapshot(array=array)
    parity = array.get("parityCheckStatus") or {}
    await render(
        update,
        context,
        build_parity(snapshot, settings),
        parity_keyboard(bool(parity.get("running")), bool(parity.get("paused"))),
    )


@authorized
async def show_ups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    try:
        devices = await client.ups()
    except UnraidError as exc:
        LOG.info("No se pudo leer el UPS: %s", exc)
        await render(
            update,
            context,
            build_ups(Snapshot(ups=[]), problem=None if _ups_missing(exc) else str(exc)),
            simple_back_keyboard("s:ups"),
        )
        return
    await render(
        update, context, build_ups(Snapshot(ups=devices)), simple_back_keyboard("s:ups")
    )


def _notif_state(context: ContextTypes.DEFAULT_TYPE) -> dict[str, object]:
    state = context.chat_data.setdefault("notif_filter", {})
    if not isinstance(state, dict):
        state = {}
        context.chat_data["notif_filter"] = state
    return state


def _notif_totals(overview: dict, archived: bool, importance: str | None) -> int:
    bucket = (overview.get("archive") if archived else overview.get("unread")) or {}
    if importance:
        return int(bucket.get(str(importance).lower(), 0) or 0)
    return int(bucket.get("total", 0) or 0)


async def _render_notifications(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    archived: bool | None = None,
    importance: str | None | object = ...,
    page: int = 0,
) -> None:
    settings = get_settings(context)
    state = _notif_state(context)
    if archived is not None:
        state["archived"] = archived
    if importance is not ...:
        state["importance"] = importance or None
    archived = bool(state.get("archived", False))
    importance = state.get("importance") or None
    client = context.bot_data["client"]
    view = await client.notifications_filtered(
        archived=archived,
        importance=str(importance) if importance else None,
        offset=page * NOTIF_PER_PAGE,
        limit=NOTIF_PER_PAGE,
    )
    overview = view.get("overview") or {}
    items = view.get("items") or []
    total = _notif_totals(overview, archived, str(importance) if importance else None)
    pages = max(1, (total + NOTIF_PER_PAGE - 1) // NOTIF_PER_PAGE)
    page = max(0, min(page, pages - 1))
    if page * NOTIF_PER_PAGE >= max(total, 1) and items:
        items = items[:NOTIF_PER_PAGE]
    await render(
        update,
        context,
        build_notification_list(
            items,
            overview,
            settings,
            archived=archived,
            importance=str(importance) if importance else None,
            page=page,
            pages=pages,
        ),
        notifications_list_keyboard(
            items,
            page=page,
            pages=pages,
            archived=archived,
            importance=str(importance) if importance else None,
        ),
    )


@authorized
async def show_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data if query is not None else ""
    archived: bool | None = None
    importance: str | None | object = ...
    page = 0
    if data.startswith("s:notif:f:"):
        parts = data.split(":")
        importance = None if len(parts) < 4 or parts[3] == "all" else parts[3]
        archived = len(parts) > 4 and parts[4] == "1"
    elif data.startswith("s:notif:p:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        importance = None if len(parts) < 4 or parts[3] == "all" else parts[3]
        archived = len(parts) > 4 and parts[4] == "1"
    elif data.startswith("s:notif:"):
        page = _page_from(data)
    await _render_notifications(
        update,
        context,
        archived=archived,
        importance=importance,
        page=page,
    )


async def _notification_from_token(
    context: ContextTypes.DEFAULT_TYPE, token: str
) -> dict | None:
    state = _notif_state(context)
    archived = bool(state.get("archived", False))
    importance = state.get("importance") or None
    client = context.bot_data["client"]
    view = await client.notifications_filtered(
        archived=archived,
        importance=str(importance) if importance else None,
        offset=0,
        limit=100,
    )
    return resolve_short(view.get("items") or [], token)


@authorized
async def notification_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[3] if len(parts) > 3 else ""
    item = await _notification_from_token(context, token)
    if item is None:
        await notify(update, context, "Esa notificación ya no existe.")
        await _render_notifications(update, context)
        return
    state = _notif_state(context)
    await render(
        update,
        context,
        build_notification_detail(item, settings),
        notification_detail_keyboard(
            item,
            archived=bool(state.get("archived", False)),
            importance=state.get("importance") or None,
        ),
    )


@authorized
async def notification_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    action = parts[2] if len(parts) > 2 else ""
    token = parts[3] if len(parts) > 3 else ""
    if not await ensure_writable(update, context):
        return
    item = await _notification_from_token(context, token)
    if item is None:
        await notify(update, context, "Esa notificación ya no existe.")
        await _render_notifications(update, context)
        return
    item_id = str(item.get("id") or "")
    client = context.bot_data["client"]
    state = _notif_state(context)
    archived = bool(state.get("archived", False))

    if action == "a":
        await client.archive_notification(item_id)
        await audit(update, context, "notification.archive", item_id)
        await _render_notifications(update, context)
    elif action == "u":
        await client.unarchive_notification(item_id)
        await audit(update, context, "notification.unarchive", item_id)
        await _render_notifications(update, context)
    elif action == "m":
        await client.mark_notification_unread(item_id)
        await audit(update, context, "notification.unread", item_id)
        await _render_notifications(update, context)
    elif action == "x":
        confirmation = context.bot_data["confirmations"].create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="notification.delete",
            target=item_id,
            args={"id": item_id, "archived": archived},
            prompt=(
                "🗑 <b>Borrar notificación</b>\n\n"
                f"<b>{esc(str(item.get('subject') or item.get('title') or '—'))}</b>\n\n"
                "Se eliminará de forma permanente.\n\n¿Continuar?"
            ),
            success_text="🗑 <b>Notificación borrada.</b>",
            return_callback="s:notif",
        )
        await render(
            update, context, confirmation.prompt, confirm_keyboard(confirmation.token)
        )
    else:
        await notify(update, context, "Acción de notificación no válida.")


@authorized
async def notifications_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    if not await ensure_writable(update, context):
        return

    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="notifications.archive_all",
        target="notifications",
        args={},
        prompt=(
            "🗑 <b>Archivar todas las notificaciones</b>\n\n"
            "Las notificaciones no leídas pasarán al archivo de Unraid. "
            "No se borra nada de forma permanente.\n\n¿Continuar?"
        ),
        success_text="🗑 <b>Notificaciones archivadas.</b>",
        return_callback="s:notif",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


@authorized
async def show_shares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    shares = await client.shares()
    await render(update, context, build_shares(shares), shares_keyboard(shares))


@authorized
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    snapshot = await client.snapshot()
    await render(update, context, build_info(snapshot, settings), simple_back_keyboard("s:info"))


# ---------------------------------------------------------------------------
# Acciones del array
# ---------------------------------------------------------------------------

@authorized
async def array_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    action = parts[1]
    encrypted = len(parts) > 2 and parts[2] == "enc"
    if not await ensure_writable(update, context):
        return

    if action == "astart" and encrypted:
        context.chat_data["pending_input"] = {"kind": "array_password"}
        await render(
            update,
            context,
            "🔐 <b>Iniciar array cifrado</b>\n\n"
            "Envía la contraseña del array. La usaré una sola vez, borraré tu "
            "mensaje y no la guardaré.",
            back_menu("s:array"),
        )
        return

    manager = context.bot_data["confirmations"]
    if action == "astart":
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="array.start",
            target="array",
            args={},
            prompt=(
                "▶️ <b>Iniciar el array</b>\n\n"
                "Se montarán los discos y arrancarán los servicios. Si el array "
                "está cifrado, usa mejor «🔐 Iniciar array cifrado».\n\n¿Continuar?"
            ),
            success_text=(
                "✅ <b>Array iniciado</b>\n\n"
                "Los discos están montados y los servicios disponibles. "
                "Abre «Array» para ver el estado actualizado."
            ),
            return_callback="s:array",
        )
    else:
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="array.stop",
            target="array",
            args={},
            prompt=(
                "⏹ <b>Detener el array</b>\n\n"
                "Se desmontarán los discos y los shares dejarán de estar disponibles. "
                "Los contenedores y VMs que usen el array pueden fallar.\n\n¿Continuar?"
            ),
            success_text=(
                "✅ <b>Array detenido</b>\n\n"
                "Los discos están desmontados y los shares ya no están disponibles."
            ),
            return_callback="s:array",
        )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


# ---------------------------------------------------------------------------
# Acciones de paridad
# ---------------------------------------------------------------------------

@authorized
async def parity_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    action = query.data.split(":")[1]
    if not await ensure_writable(update, context):
        return

    manager = context.bot_data["confirmations"]
    if action == "pstart":
        await render(
            update,
            context,
            "🧮 <b>Iniciar comprobación de paridad</b>\n\n"
            "Elige el tipo:\n\n"
            "• <b>Correctiva</b>: escribe las correcciones en el disco de paridad. "
            "Úsala si sospechas que hay errores.\n"
            "• <b>No correctiva</b>: solo lee y compara; más segura para "
            "comprobaciones rutinarias.",
            parity_choice_keyboard(),
        )
        return

    if action == "pcancel":
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="parity.cancel",
            target="parity",
            args={},
            prompt="⏹ <b>Cancelar la comprobación de paridad</b>\n\n¿Seguro?",
            success_text="⏹ <b>Comprobación de paridad cancelada.</b>",
            return_callback="s:parity",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    client = context.bot_data["client"]
    if action == "ppause":
        await client.parity_action("pause")
        await audit(update, context, "parity.pause", "parity")
        toast = "⏸ Comprobación pausada"
    elif action == "presume":
        await client.parity_action("resume")
        await audit(update, context, "parity.resume", "parity")
        toast = "▶️ Comprobación reanudada"
    else:
        await notify(update, context, "Acción de paridad no válida.")
        return

    try:
        await query.answer(localize(toast))
    except TelegramError:
        pass
    await asyncio.sleep(1.0)
    await show_parity(update, context)


@authorized
async def parity_start_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    correct = len(parts) > 2 and parts[2] == "1"
    if not await ensure_writable(update, context):
        return
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=query.from_user.id,
        chat_id=query.message.chat_id,
        action="parity.start",
        target="parity",
        args={"correct": correct},
        prompt=(
            "🧮 <b>Comprobación de paridad correctiva</b>\n\n"
            "Se escribirán las correcciones en paridad. Puede tardar horas con "
            "carga de E/S elevada.\n\n¿Continuar?"
            if correct
            else "🧮 <b>Comprobación de paridad no correctiva</b>\n\n"
            "Solo lee los discos y compara. Puede tardar horas con carga de E/S "
            "elevada.\n\n¿Continuar?"
        ),
        success_text=(
            "🧮 <b>Comprobación de paridad correctiva iniciada.</b>"
            if correct
            else "🧮 <b>Comprobación de paridad no correctiva iniciada.</b>"
        ),
        return_callback="s:parity",
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
