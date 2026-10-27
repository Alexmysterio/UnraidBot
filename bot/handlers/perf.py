"""Pantalla de rendimiento con sparklines de CPU y RAM."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..keyboards import performance_keyboard
from ..metrics import record_metric
from ..views import build_performance
from .common import authorized, get_settings, render


@authorized
async def show_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    store = context.bot_data["store"]
    snapshot = await client.snapshot(include_storage=True)
    await record_metric(context, snapshot)
    await render(
        update,
        context,
        build_performance(snapshot, store.metric_history(60), settings),
        performance_keyboard(),
    )
