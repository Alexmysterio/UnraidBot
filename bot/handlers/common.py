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
from ..i18n import DEFAULT_LANGUAGE, localize, localize_keyboard, set_language, t
from ..keyboards import language_keyboard, main_menu
from ..security import AuditLog, RateLimiter
from ..unraid import UnraidError

LOG = logging.getLogger(__name__)

HTML = ParseMode.HTML
Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


def apply_language(context: ContextTypes.DEFAULT_TYPE, update: Update) -> str:
    """Fija el idioma del chat en el contextvar de esta actualización."""
    store = context.bot_data.get("store")
    chat = update.effective_chat
    language = store.get_language(chat.id) if store is not None and chat is not None else None
    language = language or DEFAULT_LANGUAGE
    set_language(language)
    return language


def _processing_key(update: Update) -> str:
    """Clave única por mensaje de origen para no pisar actualizaciones concurrentes."""
    query = update.callback_query
    if query is not None and query.message is not None:
        return f"{query.message.chat_id}:{query.message.message_id}"
    message = update.effective_message
    if message is not None:
        return f"{message.chat_id}:{message.message_id}"
    return f"update:{update.update_id}"


def _pop_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    store = context.chat_data.get("_processing")
    if not isinstance(store, dict):
        return None
    marker = store.pop(_processing_key(update), None)
    if not store:
        context.chat_data.pop("_processing", None)
    return marker if isinstance(marker, dict) else None


async def begin_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra «Procesando…» mientras se consulta la API."""
    text = t("processing")
    query = update.callback_query
    try:
        if query is not None and query.message is not None:
            await query.edit_message_text(text=text, parse_mode=HTML)
            marker = {
                "chat_id": query.message.chat_id,
                "message_id": query.message.message_id,
            }
        elif update.effective_message is not None:
            message = await update.effective_message.reply_text(text=text, parse_mode=HTML)
            marker = {"chat_id": message.chat_id, "message_id": message.message_id}
        else:
            return
        context.chat_data.setdefault("_processing", {})[_processing_key(update)] = marker
    except TelegramError as exc:
        LOG.debug("No se pudo mostrar el mensaje de proceso: %s", exc)


def is_authorized(settings: Settings, update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if user.id not in settings.allowed_user_ids and user.id not in settings.viewer_user_ids:
        return False
    chat = update.effective_chat
    if settings.allowed_chat_ids and chat is not None:
        if chat.type != "private" and chat.id not in settings.allowed_chat_ids:
            return False
    return True


def role_for(settings: Settings, user_id: int) -> str | None:
    """Devuelve 'admin', 'viewer' o None."""
    if user_id in settings.allowed_user_ids:
        return "admin"
    if user_id in settings.viewer_user_ids:
        return "viewer"
    return None


def is_writable(settings: Settings, user_id: int) -> bool:
    """True si el usuario puede ejecutar acciones que modifican el servidor."""
    if settings.read_only:
        return False
    return user_id in settings.allowed_user_ids


async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Envía un aviso breve, como alerta si viene de un botón."""
    text = localize(text)
    marker = _pop_processing(update, context)
    if marker is not None:
        try:
            await context.bot.edit_message_text(
                chat_id=marker["chat_id"],
                message_id=marker["message_id"],
                text=text,
                parse_mode=HTML,
            )
        except TelegramError:
            pass
    query = update.callback_query
    if query is not None:
        try:
            await query.answer(text[:190], show_alert=True)
            return
        except TelegramError:
            pass
    if marker is not None:
        return
    if update.effective_message is not None:
        try:
            await update.effective_message.reply_text(text, parse_mode=HTML)
        except TelegramError as exc:
            LOG.debug("No se pudo notificar: %s", exc)


async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    apply_language(context, update)
    user = update.effective_user
    user_id = user.id if user else "desconocido"
    username = user.username if user else None
    LOG.warning("Acceso denegado a user_id=%s username=%s", user_id, username)

    query = update.callback_query
    if query is not None:
        try:
            await query.answer(localize("⛔ No autorizado"), show_alert=True)
        except TelegramError:
            pass
        return

    chat = update.effective_chat
    if chat is None or chat.type != "private":
        return
    if not settings.is_configured:
        text = (
            "⚙️ <b>Bot sin configurar</b>\n\n"
            f"Tu ID de Telegram es <code>{user_id}</code>.\n\n"
            "Añádelo a <code>ALLOWED_USER_IDS</code> (administración) o "
            "<code>VIEWER_USER_IDS</code> (solo lectura) y reinicia el contenedor:\n"
            "<code>docker compose up -d --force-recreate</code>"
        )
    else:
        text = (
            "⛔ <b>No autorizado</b>\n\n"
            f"Tu ID de Telegram es <code>{user_id}</code>. "
            "No está en <code>ALLOWED_USER_IDS</code> ni en <code>VIEWER_USER_IDS</code>."
        )
    try:
        await update.effective_message.reply_text(localize(text), parse_mode=HTML)
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

        apply_language(context, update)
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
            if update.callback_query.data.endswith(":noop"):
                return await handler(update, context)

        await begin_processing(update, context)
        return await handler(update, context)

    return wrapper


async def ensure_writable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    user = update.effective_user
    if user is not None and is_writable(settings, user.id):
        return True
    if settings.read_only:
        await notify(update, context, "🔒 El bot está en modo solo lectura (READ_ONLY=true).")
    else:
        await notify(update, context, "🔒 Tu usuario tiene acceso de solo lectura.")
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
    text = clamp(localize(text), 4000)
    keyboard = localize_keyboard(keyboard)
    marker = _pop_processing(update, context)
    if marker is not None:
        try:
            await context.bot.edit_message_text(
                chat_id=marker["chat_id"],
                message_id=marker["message_id"],
                text=text,
                reply_markup=keyboard,
                parse_mode=HTML,
                disable_web_page_preview=True,
            )
            return
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            LOG.debug("No se pudo editar el mensaje de proceso: %s", exc)
        except TelegramError as exc:
            LOG.debug("No se pudo editar el mensaje de proceso: %s", exc)

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
    apply_language(context, update)
    if not is_authorized(settings, update):
        await deny(update, context)
        return
    chat = update.effective_chat
    store = context.bot_data["store"]
    if chat is not None and store.get_language(chat.id) is None:
        await render(update, context, t("lang_choose"), language_keyboard())
        return
    user = update.effective_user
    name = esc(user.first_name) if user and user.first_name else "👋"
    await render(update, context, t("start_welcome", name=name), main_menu())


@authorized
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    store = context.bot_data["store"]
    if chat is not None and store.get_language(chat.id) is None:
        await render(update, context, t("lang_choose"), language_keyboard())
        return
    await render(update, context, "🏠 <b>" + t("Menú") + "</b>", main_menu())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    apply_language(context, update)
    await render(update, context, t("help"), main_menu())


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    apply_language(context, update)
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
    role = role_for(settings, user.id)
    if role == "admin":
        lines.append("✅ Estás autorizado como <b>administrador</b>.")
    elif role == "viewer":
        lines.append("👁️ Estás autorizado en <b>solo lectura</b>.")
    elif not settings.is_configured:
        lines.append("⚙️ El bot no tiene usuarios autorizados. Añade el ID de usuario a <code>ALLOWED_USER_IDS</code>.")
    else:
        lines.append("⛔ No estás autorizado. Pide que añadan tu ID a <code>ALLOWED_USER_IDS</code>.")
    await render(update, context, "\n".join(lines), main_menu())


@authorized
async def show_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render(update, context, t("lang_choose"), language_keyboard())


@authorized
async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    parts = query.data.split(":")
    code = parts[2] if len(parts) > 2 else DEFAULT_LANGUAGE
    store = context.bot_data["store"]
    if code not in {"en", "es", "fr", "it"}:
        await notify(update, context, "Idioma no válido.")
        return
    await store.set_language(update.effective_chat.id, code)
    set_language(code)
    await audit(update, context, "language.set", code)
    user = update.effective_user
    name = esc(user.first_name) if user and user.first_name else "👋"
    await render(update, context, t("language_saved") + "\n\n" + t("start_welcome", name=name), main_menu())


@authorized
async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    if query.data == "m:main":
        chat = update.effective_chat
        store = context.bot_data["store"]
        if chat is not None and store.get_language(chat.id) is None:
            await render(update, context, t("lang_choose"), language_keyboard())
            return
        await render(update, context, "🏠 <b>" + t("Menú") + "</b>", main_menu())
    elif query.data == "m:help":
        await render(update, context, t("help"), main_menu())
    elif query.data == "m:noop":
        return


@authorized
async def on_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botón decorativo (p. ej. el contador de páginas): no hace nada."""
    return None


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
    """Texto libre: primero busca o filtra, si no hay captura muestra el menú."""
    from . import history, qbittorrent, search

    if await qbittorrent.consume_text(update, context):
        return
    if await search.consume_text(update, context):
        return
    if await history.consume_text(update, context):
        return
    await render(update, context, "🏠 <b>Menú principal</b>", main_menu())


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    LOG.error("Error no controlado: %s", error, exc_info=error)
    if not isinstance(update, Update):
        return
    apply_language(context, update)
    if isinstance(error, UnraidError):
        text = f"❌ {error}"
    else:
        text = "❌ Ha ocurrido un error inesperado. Revisa los logs del contenedor."
    await notify(update, context, text)
