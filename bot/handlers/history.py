"""Historial de auditoría consultable (solo administradores)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..keyboards import back_menu, history_keyboard
from ..security import AuditLog
from ..views import build_history
from .common import authorized, get_settings, notify, render, role_for

PER_PAGE = 8
PROMPT = (
    "🗂️ <b>Filtrar historial</b>\n\n"
    "Escribe un texto para filtrar por acción, objetivo o usuario.\n"
    "Ejemplos: <code>docker</code>, <code>array.stop</code>, <code>alois</code>."
)


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return role_for(get_settings(context), user.id) == "admin"


async def _run(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 0,
    query: str | None = None,
) -> None:
    settings = get_settings(context)
    log: AuditLog | None = context.bot_data.get("audit")
    if log is None:
        await notify(update, context, "La auditoría no está disponible.")
        return

    if query is None:
        stored = context.chat_data.get("history_query")
        query = str(stored) if stored else ""
    context.chat_data["history_query"] = query

    records, total = await log.read(limit=PER_PAGE, offset=max(0, page) * PER_PAGE, query=query)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    clamped = max(0, min(page, pages - 1))
    if clamped != page:
        page = clamped
        records, total = await log.read(limit=PER_PAGE, offset=page * PER_PAGE, query=query)
    await render(
        update,
        context,
        build_history(records, total, page, PER_PAGE, query, settings),
        history_keyboard(page, pages, bool(query)),
    )


@authorized
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update, context):
        await notify(update, context, "🔒 El historial de auditoría es solo para administradores.")
        return
    query = " ".join(context.args or []).strip()
    await _run(update, context, 0, query)


@authorized
async def on_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update, context):
        await notify(update, context, "🔒 El historial de auditoría es solo para administradores.")
        return
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "f":
        context.chat_data["history_armed"] = True
        await render(update, context, PROMPT, back_menu())
        return
    if action == "c":
        context.chat_data["history_query"] = ""
        await _run(update, context, 0, "")
        return
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    await _run(update, context, page)


async def consume_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Consume el siguiente mensaje si se está escribiendo un filtro."""
    if not context.chat_data.pop("history_armed", False):
        return False
    if not _is_admin(update, context):
        await notify(update, context, "🔒 El historial de auditoría es solo para administradores.")
        return True
    message = update.effective_message
    text = (message.text or "").strip() if message is not None else ""
    await _run(update, context, 0, text)
    return True
