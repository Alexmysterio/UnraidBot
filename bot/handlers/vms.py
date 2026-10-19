"""Gestión de máquinas virtuales."""

from __future__ import annotations

import asyncio
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc
from ..keyboards import confirm_keyboard, vm_detail_keyboard, vms_keyboard
from ..security import resolve_short
from ..unraid import UnraidError
from ..views import build_vm_detail, build_vm_list
from .common import audit, authorized, ensure_writable, notify, render

ACTION_LABELS = {
    "start": "▶️ Iniciando",
    "stop": "⏹ Apagando",
    "reboot": "🔄 Reiniciando",
    "pause": "⏸ Pausando",
    "resume": "▶️ Reanudando",
    "force_stop": "⏏ Forzando apagado",
    "reset": "↩️ Reseteando",
}

CONFIRM_ACTIONS = {"reboot", "force_stop", "reset"}


def _name(vm: dict[str, Any]) -> str:
    return str(vm.get("name") or vm.get("id") or "VM")


@authorized
async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    vms = await client.vms()
    await render(update, context, build_vm_list(vms), vms_keyboard(vms))


async def _get_vm(context: ContextTypes.DEFAULT_TYPE, token: str) -> dict[str, Any] | None:
    client = context.bot_data["client"]
    vms = await client.vms()
    return resolve_short(vms, token)


@authorized
async def show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    vm = await _get_vm(context, token)
    if vm is None:
        await notify(update, context, "Esa VM ya no existe.")
        return
    await render(update, context, build_vm_detail(vm), vm_detail_keyboard(vm))


@authorized
async def vm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.message is None:
        return
    parts = query.data.split(":")
    action = parts[2] if len(parts) > 2 else ""
    token = parts[3] if len(parts) > 3 else ""

    if action not in ACTION_LABELS:
        await notify(update, context, "Acción no válida.")
        return
    vm = await _get_vm(context, token)
    if vm is None:
        await notify(update, context, "Esa VM ya no existe.")
        return
    if not await ensure_writable(update, context):
        return

    name = _name(vm)
    if action in CONFIRM_ACTIONS:
        manager = context.bot_data["confirmations"]
        prompts = {
            "reboot": f"🔄 <b>Reiniciar {esc(name)}</b>\n\nSe reiniciará la VM. ¿Continuar?",
            "force_stop": (
                f"⏏ <b>Forzar apagado de {esc(name)}</b>\n\n"
                "Equivale a quitar la corriente: puede provocar pérdida de datos. ¿Continuar?"
            ),
            "reset": (
                f"↩️ <b>Resetear {esc(name)}</b>\n\n"
                "Se reinicia de forma forzada, sin apagado ordenado. ¿Continuar?"
            ),
        }
        confirmation = manager.create(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            action=f"vm.{action}",
            target=str(vm.get("id") or name),
            args={"id": str(vm.get("id")), "name": name},
            prompt=prompts[action],
            success_text=f"✅ <b>{ACTION_LABELS[action]}</b>\n\nVM: <b>{esc(name)}</b>",
            return_callback=f"v:v:{token}",
        )
        await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))
        return

    client = context.bot_data["client"]
    try:
        ok = await client.vm_action(action, str(vm["id"]))
    except UnraidError as exc:
        await audit(update, context, f"vm.{action}", name, outcome="error")
        await notify(update, context, f"❌ No se pudo aplicar «{action}»: {exc}")
        return

    await audit(update, context, f"vm.{action}", name)
    try:
        await query.answer(f"{ACTION_LABELS[action]} {name}…" if ok else "La API no confirmó la acción")
    except TelegramError:
        pass

    await asyncio.sleep(1.0)
    refreshed = await _get_vm(context, token)
    if refreshed is None:
        vms = await client.vms()
        await render(update, context, build_vm_list(vms), vms_keyboard(vms))
        return
    await render(update, context, build_vm_detail(refreshed), vm_detail_keyboard(refreshed))
