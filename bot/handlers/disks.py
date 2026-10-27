"""Pantallas de discos: array, pools y discos físicos."""

from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ..keyboards import (
    disk_detail_keyboard,
    disks_keyboard,
    physical_disks_keyboard,
)
from ..security import resolve_short
from ..unraid import Snapshot
from ..views import build_disk_detail, build_disks, build_physical_disks, paginate
from .common import authorized, get_settings, notify, render

PER_PAGE = 10


def _all_disks(array: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("parities", "disks", "caches"):
        value = array.get(key)
        if isinstance(value, list):
            result.extend(item for item in value if isinstance(item, dict))
    return result


@authorized
async def show_disks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    array = await client.array()
    snapshot = Snapshot(array=array)
    await render(
        update,
        context,
        build_disks(snapshot),
        disks_keyboard(_all_disks(array)),
    )


@authorized
async def show_disk_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    settings = get_settings(context)
    client = context.bot_data["client"]
    array = await client.array()
    disk = resolve_short(_all_disks(array), token)
    if disk is None:
        await notify(update, context, "Ese disco ya no existe. Vuelve a abrir la lista.")
        return
    await render(update, context, build_disk_detail(disk, settings), disk_detail_keyboard())


@authorized
async def show_physical_disks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = 0
    query = update.callback_query
    if query is not None and query.data.startswith("k:p:"):
        part = query.data.split(":")[2]
        if part.isdigit():
            page = int(part)
    client = context.bot_data["client"]
    disks = await client.physical_disks()
    _, page, pages = paginate(disks, page, PER_PAGE)
    await render(
        update,
        context,
        build_physical_disks(disks, page, PER_PAGE),
        physical_disks_keyboard(page, pages),
    )
