"""Utilidades compartidas por los handlers: auth, render y comandos base."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from ..config import Settings
from ..formatting import clamp, esc
from ..keyboards import main_menu
from ..security import AuditLog, RateLimiter
from ..unraid import UnraidError
from ..views import build_help

LOG = logging.getLogger(__name__)

HTML = ParseMode.HTML
Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


def is_authorized(settings: Settings, update: Update) -> bool:
    user = update.effective_user
    if user is None or user.id not in settings.allowed_user_ids:
        return False
    chat = update.effective_chat
    if settings.allowed_chat_ids and chat is not None:
        if chat.type != "private" and chat.id not in settings.allowed_chat_ids:
            return False
    return True


async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Envía un aviso breve, como alerta si viene de un botón."""
    query = update.callback_query
    if query is not None:
        try:
            await query.answer(text[:190], show_alert=True)
            return
        except TelegramError:
            pass
    if update.effective_message is not None:
        try:
            await update.effective_message.reply_text(text, parse_mode=HTML)
        except TelegramError as exc:
            LOG.debug("No se pudo notificar: %s", exc)


async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    user_id = user.id if user else "desconocido"
    username = user.username if user else None
    LOG.warning("Acceso denegado a user_id=%s username=%s", user_id, username)

    query = update.callback_query
    if query is not None:
        try:
            await query.answer("⛔ No autorizado", show_alert=True)
        except TelegramError:
            pass
        return

    chat = update.effective_chat
    if chat is None or chat.type != "private":
        return
    if not settings.allowed_user_ids:
        text = (
            "⚙️ <b>Bot sin configurar</b>\n\n"
            f"Tu ID de Telegram es <code>{user_id}</code>.\n\n"
            "Añádelo a <code>ALLOWED_USER_IDS</code> en el archivo <code>.env</code> "
            "y reinicia el contenedor:\n"
            "<code>docker compose up -d --force-recreate</code>"
        )
    else:
        text = (
            "⛔ <b>No autorizado</b>\n\n"
            f"Tu ID de Telegram es <code>{user_id}</code>. "
            "No está en <code>ALLOWED_USER_IDS</code>."
        )
    try:
        await update.effective_message.reply_text(text, parse_mode=HTML)
    except TelegramError:
        pass


def authorized(handler: Handler) -> Handler:
    """Comprueba allowlist + rate limit y responde al callback."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        settings = get_settings(context)
        if not is_authorized(settings, update):
            await deny(update, context)
            return None

        user = update.effective_user
        limiter: RateLimiter | None = context.bot_data.get("rate")
        if user is not None and limiter is not None and not limiter.allow(user.id):
            await notify(update, context, "⏳ Demasiadas acciones seguidas. Espera un minuto.")
            return None

        if update.callback_query is not None:
            try:
                await update.callback_query.answer()
            except TelegramError:
                pass

        return await handler(update, context)

    return wrapper


async def ensure_writable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    if not settings.read_only:
        return True
    await notify(update, context, "🔒 El bot está en modo solo lectura (READ_ONLY=true).")
    return False


async def audit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    target: str = "",
    outcome: str = "ok",
) -> None:
    log: AuditLog | None = context.bot_data.get("audit")
    if log is None:
        return
    user = update.effective_user
    chat = update.effective_chat
    await log.write(
        user_id=user.id if user else None,
        username=user.username if user else None,
        chat_id=chat.id if chat else None,
        action=action,
        target=target,
        outcome=outcome,
    )


async def render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Edita el mensaje del botón o envía uno nuevo, con fallback."""
    text = clamp(text, 4000)
    query = update.callback_query
    if query is not None:
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=HTML,
                disable_web_page_preview=True,
            )
            return
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            LOG.debug("No se pudo editar el mensaje: %s", exc)
        except TelegramError as exc:
            LOG.debug("No se pudo editar el mensaje: %s", exc)
        if query.message is not None:
            try:
                await query.message.reply_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=HTML,
                    disable_web_page_preview=True,
                )
            except TelegramError as exc:
                LOG.warning("No se pudo enviar el mensaje: %s", exc)
        return

    if update.effective_message is not None:
        try:
            await update.effective_message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=HTML,
                disable_web_page_preview=True,
            )
        except TelegramError as exc:
            LOG.warning("No se pudo enviar el mensaje: %s", exc)


# ---------------------------------------------------------------------------
# Comandos base
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    if not is_authorized(settings, update):
        await deny(update, context)
        return
    user = update.effective_user
    name = esc(user.first_name) if user and user.first_name else "hola"
    text = (
        f"👋 Hola, {name}.\n\n"
        "Este bot administra tu servidor Unraid sin exponerlo a Internet: "
        "todo el tráfico con Telegram es saliente y las órdenes van a la API local.\n\n"
        "Elige una opción:"
    )
    await render(update, context, text, main_menu())


@authorized
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(update, context, "🏠 <b>Menú principal</b>", main_menu())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(update, context, build_help(), main_menu())


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    lines = [
        "🪪 <b>Identificadores de Telegram</b>",
        "",
        f"Usuario: <code>{user.id}</code>",
        f"Chat: <code>{chat.id}</code> (<code>{chat.type}</code>)",
    ]
    if user.username:
        lines.append(f"Usuario: @{esc(user.username)}")
    lines.append("")
    if not settings.allowed_user_ids:
        lines.append("⚙️ El bot no tiene usuarios autorizados. Añade el ID de usuario a <code>ALLOWED_USER_IDS</code>.")
    elif user.id in settings.allowed_user_ids:
        lines.append("✅ Estás autorizado.")
    else:
        lines.append("⛔ No estás autorizado. Pide que añadan tu ID a <code>ALLOWED_USER_IDS</code>.")
    await render(update, context, "\n".join(lines), main_menu())


@authorized
async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    if query.data == "m:main":
        await render(update, context, "🏠 <b>Menú principal</b>", main_menu())
    elif query.data == "m:help":
        await render(update, context, build_help(), main_menu())
    elif query.data == "m:noop":
        return


@authorized
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(
        update,
        context,
        "❓ Comando no reconocido. Usa /menu para ver las opciones.",
        main_menu(),
    )


@authorized
async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(update, context, "🏠 <b>Menú principal</b>", main_menu())


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    LOG.error("Error no controlado: %s", error, exc_info=error)
    if not isinstance(update, Update):
        return
    if isinstance(error, UnraidError):
        text = f"❌ {error}"
    else:
        text = "❌ Ha ocurrido un error inesperado. Revisa los logs del contenedor."
    await notify(update, context, text)
