"""Envío de mensajes a varios chats con reintentos y respeto del silencio."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from telegram import Bot, InlineKeyboardMarkup
from telegram.error import Forbidden, RetryAfter, TelegramError

from .i18n import localize, localize_keyboard, set_language
from .state import StateStore

LOG = logging.getLogger(__name__)


async def broadcast(
    bot: Bot,
    store: StateStore,
    chat_ids: Iterable[int],
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> bool:
    """Envía un texto a los chats suscritos. Devuelve True si llegó a alguno."""
    delivered = False
    for chat_id in chat_ids:
        if store.is_muted(chat_id):
            LOG.debug("Chat %s silenciado; no se envía el mensaje.", chat_id)
            continue
        set_language(store.get_language(chat_id) or "en")
        chat_keyboard = localize_keyboard(keyboard)
        chat_text = localize(text)
        for attempt in range(2):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=chat_text[:4000],
                    parse_mode="HTML",
                    reply_markup=chat_keyboard,
                    disable_web_page_preview=True,
                )
                delivered = True
                break
            except RetryAfter as exc:
                if attempt == 0:
                    await asyncio.sleep(retry_after_seconds(exc))
                    continue
                LOG.warning("Telegram sigue limitando el envío a %s: %s", chat_id, exc)
            except Forbidden:
                LOG.info("El chat %s bloqueó el bot; se desuscribe.", chat_id)
                await store.unsubscribe(chat_id)
                break
            except TelegramError as exc:
                LOG.warning("No se pudo enviar el mensaje a %s: %s", chat_id, exc)
                break
    return delivered


def retry_after_seconds(exc: RetryAfter) -> float:
    value = getattr(exc, "retry_after", 1)
    if hasattr(value, "total_seconds"):
        return max(0.0, float(value.total_seconds()))
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 1.0
