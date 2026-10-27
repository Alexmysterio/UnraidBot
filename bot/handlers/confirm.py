"""Ejecución de acciones previamente confirmadas."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc, fmt_elapsed
from ..i18n import get_language, localize, localize_keyboard, set_language
from ..keyboards import back_menu
from ..security import AuditLog, Confirmation, ConfirmationManager
from ..services import ServiceError
from ..services.mikrotik import MikroTik
from ..services.qbittorrent import QBittorrent
from ..unraid import UnraidError
from .common import audit, authorized, ensure_writable, failure_text, notify, render

LOG = logging.getLogger(__name__)


def _return_keyboard(item: Confirmation):
    """Teclado de vuelta; nunca deja al usuario sin navegación."""
    return back_menu(item.return_callback or "m:main")

LONG_ACTIONS = {
    "docker.update",
    "docker.update_all",
    "array.start",
    "array.stop",
    "vm.reboot",
    "vm.force_stop",
    "vm.reset",
}

LONG_TITLES = {
    "docker.update": "Actualizando contenedor",
    "docker.update_all": "Actualizando contenedores",
    "array.start": "Iniciando el array",
    "array.stop": "Deteniendo el array",
    "vm.reboot": "Reiniciando la VM",
    "vm.force_stop": "Forzando el apagado de la VM",
    "vm.reset": "Reseteando la VM",
}

PROGRESS_INTERVAL = 5.0


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
    elif action == "mikrotik.reboot":
        service = MikroTik(context.bot_data["settings"])
        try:
            await service.reboot()
        finally:
            await service.close()
    elif action == "qbittorrent.delete":
        service = QBittorrent(context.bot_data["settings"])
        try:
            await service.delete(
                str(item.args["hash"]),
                delete_files=bool(item.args.get("delete_files", False)),
            )
        finally:
            await service.close()
    else:
        raise UnraidError(f"Acción desconocida: {action}")


async def _edit(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    text: str,
    keyboard=None,
) -> None:
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=localize(text)[:4000],
            parse_mode="HTML",
            reply_markup=localize_keyboard(keyboard),
            disable_web_page_preview=True,
        )
    except TelegramError as exc:
        LOG.debug("No se pudo actualizar el progreso: %s", exc)


async def _write_audit(
    context: ContextTypes.DEFAULT_TYPE,
    item: Confirmation,
    user_id: int | None,
    username: str | None,
    chat_id: int | None,
    outcome: str,
) -> None:
    log: AuditLog | None = context.bot_data.get("audit")
    if log is None:
        return
    await log.write(
        user_id=user_id,
        username=username,
        chat_id=chat_id,
        action=item.action,
        target=item.target,
        outcome=outcome,
    )


async def run_long_operation(
    context: ContextTypes.DEFAULT_TYPE,
    item: Confirmation,
    chat_id: int,
    message_id: int,
    language: str,
    username: str | None = None,
) -> None:
    """Ejecuta una operación larga y va editando el mensaje con el progreso."""
    set_language(language)
    title = LONG_TITLES.get(item.action, item.action)
    keyboard = _return_keyboard(item)
    started = time.monotonic()
    await _edit(
        context,
        chat_id,
        message_id,
        f"⏳ <b>{title}</b>\n\nOperación en curso… 0 s",
        keyboard,
    )

    task = asyncio.create_task(_execute(context, item))
    while True:
        done, _ = await asyncio.wait({task}, timeout=PROGRESS_INTERVAL)
        if done:
            break
        elapsed = time.monotonic() - started
        await _edit(
            context,
            chat_id,
            message_id,
            f"⏳ <b>{title}</b>\n\nOperación en curso… {fmt_elapsed(elapsed)}",
            keyboard,
        )

    elapsed = time.monotonic() - started
    try:
        await task
    except (UnraidError, ServiceError) as exc:
        LOG.warning("Operación larga falló (%s): %s", item.action, exc)
        await _write_audit(context, item, item.user_id, username, chat_id, "error")
        await _edit(
            context,
            chat_id,
            message_id,
            f"{failure_text(exc)}\n\nDuración: {fmt_elapsed(elapsed)}",
            keyboard,
        )
    except asyncio.CancelledError:
        await _write_audit(context, item, item.user_id, username, chat_id, "cancelled")
        raise
    except Exception as exc:  # noqa: BLE001 - informar sin tumbar el bot
        LOG.exception("Error inesperado en la operación larga %s", item.action)
        await _write_audit(context, item, item.user_id, username, chat_id, "error")
        await _edit(
            context,
            chat_id,
            message_id,
            (
                f"❌ <b>Error inesperado</b>\n\n<code>{esc(str(exc))}</code>\n\n"
                f"Duración: {fmt_elapsed(elapsed)}"
            ),
            keyboard,
        )
    else:
        await _write_audit(context, item, item.user_id, username, chat_id, "ok")
        await _edit(
            context,
            chat_id,
            message_id,
            f"{item.success_text}\n\n⏱️ Duración: {fmt_elapsed(elapsed)}",
            keyboard,
        )


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
        await render(update, context, "❌ <b>Operación cancelada.</b>", _return_keyboard(item))
        return

    if not await ensure_writable(update, context):
        return

    if item.action in LONG_ACTIONS:
        title = LONG_TITLES.get(item.action, item.action)
        await render(
            update,
            context,
            f"⏳ <b>{title}</b>\n\nOperación en curso… 0 s",
            _return_keyboard(item),
        )
        task = asyncio.create_task(
            run_long_operation(
                context,
                item,
                query.message.chat_id,
                query.message.message_id,
                get_language(),
                query.from_user.username,
            ),
            name=f"longop:{item.action}",
        )
        background: list[asyncio.Task[Any]] = context.bot_data.setdefault("background", [])
        background[:] = [running for running in background if not running.done()]
        background.append(task)
        return

    try:
        await _execute(context, item)
    except (UnraidError, ServiceError) as exc:
        LOG.warning("Acción confirmada falló (%s): %s", item.action, exc)
        await audit(update, context, item.action, item.target, outcome="error")
        await render(
            update,
            context,
            failure_text(exc),
            _return_keyboard(item),
        )
        return

    await audit(update, context, item.action, item.target)
    await render(update, context, item.success_text, _return_keyboard(item))
