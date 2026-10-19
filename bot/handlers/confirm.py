"""Ejecución de acciones previamente confirmadas."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..formatting import esc
from ..keyboards import back_menu
from ..security import Confirmation, ConfirmationManager
from ..unraid import UnraidError
from .common import audit, authorized, ensure_writable, notify, render

LOG = logging.getLogger(__name__)


async def _execute(context: ContextTypes.DEFAULT_TYPE, item: Confirmation) -> None:
    client = context.bot_data["client"]
    action = item.action
    if action == "docker.update":
        await client.docker_action("update", str(item.args["id"]))
    elif action == "docker.update_all":
        await client.docker_update_all()
    elif action.startswith("vm."):
        await client.vm_action(action.split(".", 1)[1], str(item.args["id"]))
    elif action == "array.start":
        await client.set_array_state("START")
    elif action == "array.stop":
        await client.set_array_state("STOP")
    elif action == "parity.start":
        await client.parity_action("start")
    elif action == "parity.cancel":
        await client.parity_action("cancel")
    elif action == "notifications.archive_all":
        await client.archive_all_notifications()
    else:
        raise UnraidError(f"Acción desconocida: {action}")


@authorized
async def on_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    decision = parts[1] if len(parts) > 1 else ""
    token = parts[2] if len(parts) > 2 else ""

    manager: ConfirmationManager = context.bot_data["confirmations"]
    item = manager.pop(token, query.from_user.id)
    if item is None or item.chat_id != query.message.chat_id:
        await notify(update, context, "⏳ Esta confirmación ha caducado. Vuelve a intentarlo.")
        return

    if decision != "y":
        await audit(update, context, f"{item.action}.cancel", item.target)
        await render(update, context, "❌ <b>Operación cancelada.</b>", back_menu(item.return_callback))
        return

    if not await ensure_writable(update, context):
        return

    try:
        await _execute(context, item)
    except UnraidError as exc:
        LOG.warning("Acción confirmada falló (%s): %s", item.action, exc)
        await audit(update, context, item.action, item.target, outcome="error")
        await render(
            update,
            context,
            f"❌ <b>No se pudo completar la operación</b>\n\n<code>{esc(str(exc))}</code>",
            back_menu(item.return_callback),
        )
        return

    await audit(update, context, item.action, item.target)
    await render(update, context, item.success_text, back_menu(item.return_callback))
