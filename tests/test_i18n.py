from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import get_language, localize, localize_keyboard, set_language, t


def test_spanish_is_identity() -> None:
    set_language("es")
    assert localize("Estado: Array iniciado") == "Estado: Array iniciado"
    assert get_language() == "es"


def test_english_translation() -> None:
    set_language("en")
    text = localize("Estado: <b>Array iniciado</b> · Docker 1/2 activos")
    assert "Status: " in text
    assert "Array started" in text
    assert "1/2 active" in text
    assert t("processing") == "⏳ Processing…"


def test_french_and_italian() -> None:
    set_language("fr")
    assert "État : " in localize("Estado: ")
    set_language("it")
    assert "Stato: " in localize("Estado: ")


def test_keyboard_translation() -> None:
    set_language("en")
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Estado", callback_data="m:status")]])
    localized = localize_keyboard(keyboard)
    assert localized is not None
    assert localized.inline_keyboard[0][0].text == "📊 Status"
    assert localized.inline_keyboard[0][0].callback_data == "m:status"
