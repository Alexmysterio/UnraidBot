"""Búsqueda de recursos desde el comando y desde el menú."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..keyboards import back_menu, search_keyboard
from ..search import search_snapshot
from ..views import build_search, paginate
from .common import authorized, notify, render

PER_PAGE = 8
PROMPT = (
    "🔎 <b>Buscar</b>\n\n"
    "Escribe el nombre de un contenedor, VM, disco, share, UPS o notificación.\n\n"
    "<i>También puedes usar /buscar texto directamente.</i>"
)


async def _run(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, page: int = 0) -> None:
    client = context.bot_data["client"]
    snapshot = await client.snapshot(include_storage=True)
    hits = search_snapshot(snapshot, query)
    items, page, pages = paginate(hits, page, PER_PAGE)
    context.chat_data["search"] = {"query": query, "page": page}
    await render(
        update,
        context,
        build_search(query, hits, page, PER_PAGE),
        search_keyboard(items, page, pages),
    )


@authorized
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args or []).strip()
    if not query:
        context.chat_data["search_armed"] = True
        await render(update, context, PROMPT, back_menu())
        return
    await _run(update, context, query, 0)


@authorized
async def on_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["search_armed"] = True
    await render(update, context, PROMPT, back_menu())


@authorized
async def on_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "s":
        context.chat_data["search_armed"] = True
        await render(update, context, PROMPT, back_menu())
        return

    stored = context.chat_data.get("search")
    if not isinstance(stored, dict) or not stored.get("query"):
        await notify(update, context, "La búsqueda ha caducado. Vuelve a empezar.")
        return

    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    await _run(update, context, str(stored["query"]), page)


async def consume_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Consume el siguiente mensaje si la búsqueda está armada."""
    if not context.chat_data.pop("search_armed", False):
        return False
    message = update.effective_message
    text = (message.text or "").strip() if message is not None else ""
    if not text:
        context.chat_data["search_armed"] = True
        await render(update, context, PROMPT, back_menu())
        return True
    await _run(update, context, text, 0)
    return True
