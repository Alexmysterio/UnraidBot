"""Comando para generar y enviar el resumen diario bajo demanda."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..broadcast import broadcast
from ..health import detect_problems
from ..keyboards import refresh_menu
from ..views import build_digest
from .common import authorized, get_settings, notify, render, role_for


@authorized
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    if user is None or role_for(settings, user.id) != "admin":
        await notify(update, context, "🔒 Solo los administradores pueden enviar el resumen.")
        return

    client = context.bot_data["client"]
    store = context.bot_data["store"]
    snapshot = await client.snapshot(include_storage=True)
    problems = detect_problems(snapshot, settings) if snapshot.reachable else []
    text = build_digest(snapshot, settings, problems)

    subscribers = store.subscribers()
    footer = ""
    if subscribers:
        delivered = await broadcast(context.bot, store, subscribers, text)
        if delivered:
            footer = f"\n\n📬 Enviado a {len(subscribers)} chat(s)."
        else:
            footer = "\n\n⚠️ No se pudo entregar el resumen."
    else:
        footer = "\n\n<i>No hay chats suscritos; no se ha enviado nada.</i>"

    await render(update, context, text + footer, refresh_menu("m:main"))
