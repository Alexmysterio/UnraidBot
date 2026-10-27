"""Pantalla de herramientas opcionales."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from .. import features
from ..formatting import esc
from ..i18n import t
from ..keyboards import tools_keyboard
from .common import authorized, render


@authorized
async def show_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    enabled = features.enabled()
    if not enabled:
        await render(update, context, t("tools_empty"), tools_keyboard())
        return
    lines = [t("tools_title"), "", t("tools_choose"), ""]
    for feature in enabled:
        lines.append(f"• <b>{esc(feature.label)}</b> — {esc(feature.description)}")
    await render(update, context, "\n".join(lines), tools_keyboard())
