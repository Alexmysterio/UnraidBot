"""Suscripción a alertas y envío de prueba."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc, fmt_epoch
from ..health import detect_problems
from ..i18n import localize
from ..keyboards import alerts_keyboard, main_menu
from ..views import build_alert_message, build_alerts
from .common import audit, authorized, get_settings, notify, render

LOG = logging.getLogger(__name__)


@authorized
async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    store = context.bot_data["store"]
    client = context.bot_data["client"]
    chat_id = update.effective_chat.id if update.effective_chat else 0
    snapshot = await client.snapshot(include_storage=True)
    problems = detect_problems(snapshot, settings)
    muted_until = store.muted_until(chat_id)
    await render(
        update,
        context,
        build_alerts(settings, store.is_subscribed(chat_id), problems, muted_until),
        alerts_keyboard(store.is_subscribed(chat_id), muted_until),
    )


@authorized
async def alerts_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    action = query.data.split(":")[1]
    settings = get_settings(context)
    store = context.bot_data["store"]
    client = context.bot_data["client"]
    chat_id = update.effective_chat.id

    if action == "on":
        await store.subscribe(chat_id)
        await audit(update, context, "alerts.subscribe", str(chat_id))
        await notify(update, context, "✅ Alertas activadas en este chat.")
    elif action == "off":
        await store.unsubscribe(chat_id)
        await store.unmute(chat_id)
        await audit(update, context, "alerts.unsubscribe", str(chat_id))
        await notify(update, context, "🔕 Alertas desactivadas en este chat.")
    elif action == "mute":
        try:
            seconds = int(query.data.split(":")[2])
        except (IndexError, ValueError):
            await notify(update, context, "Duración de silencio no válida.")
            return
        until = await store.mute(chat_id, seconds)
        await audit(update, context, "alerts.mute", f"{chat_id}:{seconds}")
        await notify(
            update,
            context,
            f"🔕 Alertas silenciadas hasta el {localize(fmt_epoch(until, settings.timezone))}.",
        )
    elif action == "unmute":
        removed = await store.unmute(chat_id)
        await audit(update, context, "alerts.unmute", str(chat_id))
        await notify(
            update,
            context,
            "🔔 Silencio desactivado." if removed else "ℹ️ Este chat no estaba silenciado.",
        )
    elif action == "test":
        snapshot = await client.snapshot(include_storage=True)
        problems = detect_problems(snapshot, settings)
        hostname = str(((snapshot.info or {}).get("os") or {}).get("hostname") or "Unraid")
        if problems:
            text = build_alert_message(problems[:8], hostname)
        else:
            text = (
                f"✅ <b>Sin incidencias · {esc(hostname)}</b>\n\n"
                "El servidor no presenta problemas según los umbrales configurados."
            )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text[:4000],
                parse_mode="HTML",
                reply_markup=main_menu(),
                disable_web_page_preview=True,
            )
            await audit(update, context, "alerts.test", str(chat_id))
            await query.answer(localize("📣 Prueba enviada."))
        except TelegramError as exc:
            LOG.warning("No se pudo enviar la prueba: %s", exc)
            await query.answer(localize("❌ No se pudo enviar la prueba."), show_alert=True)

    snapshot = await client.snapshot(include_storage=True)
    problems = detect_problems(snapshot, settings)
    muted_until = store.muted_until(chat_id)
    await render(
        update,
        context,
        build_alerts(settings, store.is_subscribed(chat_id), problems, muted_until),
        alerts_keyboard(store.is_subscribed(chat_id), muted_until),
    )
