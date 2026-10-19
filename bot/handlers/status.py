"""Pantalla de estado general."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..health import detect_problems
from ..keyboards import refresh_menu
from ..views import build_status
from .common import authorized, get_settings, render


@authorized
async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    snapshot = await client.snapshot()
    problems = detect_problems(snapshot, settings)
    await render(
        update,
        context,
        build_status(snapshot, settings, problems),
        refresh_menu("m:status"),
    )
