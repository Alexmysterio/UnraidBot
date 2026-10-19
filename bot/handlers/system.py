"""Pantallas del sistema: array, paridad, UPS, notificaciones y shares."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..keyboards import (
    array_keyboard,
    confirm_keyboard,
    parity_keyboard,
    simple_back_keyboard,
    system_keyboard,
)
from ..unraid import Snapshot
from ..views import (
    build_array,
    build_info,
    build_notifications,
    build_parity,
    build_shares,
    build_system_menu,
    build_ups,
)
from .common import audit, authorized, ensure_writable, get_settings, notify, render


@authorized
async def show_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    snapshot = await client.snapshot(include_info=False)
    await render(update, context, build_system_menu(snapshot), system_keyboard())


@authorized
async def show_array(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    array = await client.array()
    snapshot = Snapshot(array=array)
    await render(
        update,
        context,
        build_array(snapshot, settings),
        array_keyboard(array.get("state")),
    )


@authorized
async def show_parity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    array = await client.array()
    snapshot = Snapshot(array=array)
    parity = array.get("parityCheckStatus") or {}
    await render(
        update,
        context,
        build_parity(snapshot, settings),
        parity_keyboard(bool(parity.get("running")), bool(parity.get("paused"))),
    )


@authorized
async def show_ups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    snapshot = Snapshot(ups=await client.ups())
    await render(update, context, build_ups(snapshot), simple_back_keyboard("s:ups"))


@authorized
async def show_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    snapshot = Snapshot(notifications=await client.notifications())
    await render(
        update,
        context,
        build_notifications(snapshot, settings),
        simple_back_keyboard("s:notif"),
    )


@authorized
async def show_shares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    shares = await client.shares()
    await render(update, context, build_shares(shares), simple_back_keyboard("s:shares"))


@authorized
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    snapshot = await client.snapshot()
    await render(update, context, build_info(snapshot, settings), simple_back_keyboard("s:info"))


# ---------------------------------------------------------------------------
# Acciones del array
# ---------------------------------------------------------------------------

@authorized
async def array_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    action = query.data.split(":")[1]
    if not await ensure_writable(update, context):
        return

    manager = context.bot_data["confirmations"]
    if action == "astart":
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="array.start",
            target="array",
            args={},
            prompt=(
                "▶️ <b>Iniciar el array</b>\n\n"
                "Se montarán los discos y arrancarán los servicios. Si el array está "
                "cifrado, la API necesitará la contraseña y esta operación fallará: "
                "en ese caso, inícialo desde el WebGUI.\n\n¿Continuar?"
            ),
            success_text=(
                "▶️ <b>Iniciando el array…</b>\n\n"
                "Puede tardar unos segundos. Abre «Array» para ver el estado actualizado."
            ),
            return_callback="s:array",
        )
    else:
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="array.stop",
            target="array",
            args={},
            prompt=(
                "⏹ <b>Detener el array</b>\n\n"
                "Se desmontarán los discos y los shares dejarán de estar disponibles. "
                "Los contenedores y VMs que usen el array pueden fallar.\n\n¿Continuar?"
            ),
            success_text=(
                "⏹ <b>Deteniendo el array…</b>\n\n"
                "Espera unos segundos y comprueba el estado en «Array»."
            ),
            return_callback="s:array",
        )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


# ---------------------------------------------------------------------------
# Acciones de paridad
# ---------------------------------------------------------------------------

@authorized
async def parity_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    action = query.data.split(":")[1]
    if not await ensure_writable(update, context):
        return

    manager = context.bot_data["confirmations"]
    if action == "pstart":
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="parity.start",
            target="parity",
            args={},
            prompt=(
                "🧮 <b>Iniciar comprobación de paridad</b>\n\n"
                "Es una comprobación <b>no correctiva</b>: lee todos los discos y puede "
                "tardar horas con carga de E/S elevada.\n\n¿Continuar?"
            ),
            success_text="🧮 <b>Comprobación de paridad iniciada.</b>",
            return_callback="s:parity",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    if action == "pcancel":
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action="parity.cancel",
            target="parity",
            args={},
            prompt="⏹ <b>Cancelar la comprobación de paridad</b>\n\n¿Seguro?",
            success_text="⏹ <b>Comprobación de paridad cancelada.</b>",
            return_callback="s:parity",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    client = context.bot_data["client"]
    if action == "ppause":
        await client.parity_action("pause")
        await audit(update, context, "parity.pause", "parity")
        toast = "⏸ Comprobación pausada"
    elif action == "presume":
        await client.parity_action("resume")
        await audit(update, context, "parity.resume", "parity")
        toast = "▶️ Comprobación reanudada"
    else:
        await notify(update, context, "Acción de paridad no válida.")
        return

    try:
        await query.answer(toast)
    except TelegramError:
        pass
    await asyncio.sleep(1.0)
    await show_parity(update, context)
