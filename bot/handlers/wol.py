"""Herramienta opcional: Wake-on-LAN multi-equipo."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..config import WolDevice
from ..formatting import esc, shorten
from ..keyboards import wol_keyboard
from ..search import find_named
from ..security import short_id
from ..services import ServiceError
from ..services.wol import wake
from ..views_integrations import build_wol
from .common import audit, authorized, ensure_writable, get_settings, notify, render

USAGE = (
    "⚡ <b>Uso de /wol</b>\n\n"
    "/wol — equipos configurados\n"
    "/wol &lt;nombre&gt; — encender un equipo\n"
    "/wol all — encender todos"
)


def _devices(settings) -> list[WolDevice]:
    return list(settings.wol_devices)


def _device_token(device: WolDevice) -> str:
    return short_id(device.name + device.mac)


def _find(devices: list[WolDevice], token: str) -> WolDevice | None:
    for device in devices:
        if _device_token(device) == token:
            return device
    return None


async def _wake_device(device: WolDevice) -> None:
    await wake(device.mac, device.broadcast)


@authorized
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    devices = _devices(settings)
    await render(update, context, build_wol(devices), wol_keyboard(devices))


@authorized
async def on_wake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    if not await ensure_writable(update, context):
        return
    settings = get_settings(context)
    devices = _devices(settings)
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    device = _find(devices, token)
    if device is None:
        await notify(update, context, "Ese equipo ya no está configurado.")
        await render(update, context, build_wol(devices), wol_keyboard(devices))
        return
    try:
        await _wake_device(device)
    except (OSError, ValueError, ServiceError) as exc:
        await audit(update, context, "wol.send", device.name, outcome="error")
        await notify(update, context, f"❌ No se pudo enviar el magic packet: {exc}")
        return
    await audit(update, context, "wol.send", f"{device.name} ({device.mac})")
    try:
        await query.answer(f"⚡ Magic packet enviado a {device.name}")
    except TelegramError:
        pass
    await render(
        update,
        context,
        build_wol(devices) + f"\n\n✅ Magic packet enviado a <b>{esc(device.name)}</b>.",
        wol_keyboard(devices),
    )


@authorized
async def wake_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    if not await ensure_writable(update, context):
        return
    settings = get_settings(context)
    devices = _devices(settings)
    if not devices:
        await notify(update, context, "No hay equipos configurados en WOL_DEVICES.")
        return
    results = await asyncio.gather(
        *(_wake_device(device) for device in devices),
        return_exceptions=True,
    )
    failed = [
        device.name
        for device, result in zip(devices, results)
        if isinstance(result, BaseException)
    ]
    sent = len(devices) - len(failed)
    await audit(
        update,
        context,
        "wol.send_all",
        f"{sent}/{len(devices)}" + (f" (fallos: {', '.join(failed)})" if failed else ""),
        outcome="error" if failed else "ok",
    )
    try:
        await query.answer(f"⚡ Magic packets enviados: {sent}/{len(devices)}")
    except TelegramError:
        pass
    lines = [build_wol(devices), ""]
    lines.append(f"✅ Magic packets enviados: <b>{sent}/{len(devices)}</b>")
    if failed:
        lines.append("❌ Fallaron: " + esc(shorten(", ".join(failed), 120)))
    await render(update, context, "\n".join(lines), wol_keyboard(devices))


@authorized
async def cmd_wol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = list(context.args or [])
    settings = get_settings(context)
    devices = _devices(settings)
    if not args:
        await render(update, context, build_wol(devices), wol_keyboard(devices))
        return
    target = " ".join(args).strip()
    if target.lower() in {"all", "todos", "*"}:
        if not await ensure_writable(update, context):
            return
        results = await asyncio.gather(
            *(_wake_device(device) for device in devices),
            return_exceptions=True,
        )
        failed = [
            device.name
            for device, result in zip(devices, results)
            if isinstance(result, BaseException)
        ]
        sent = len(devices) - len(failed)
        await audit(
            update,
            context,
            "wol.send_all",
            f"{sent}/{len(devices)}" + (f" (fallos: {', '.join(failed)})" if failed else ""),
            outcome="error" if failed else "ok",
        )
        lines = [f"⚡ <b>Magic packets enviados: {sent}/{len(devices)}</b>"]
        if failed:
            lines.append("❌ Fallaron: " + esc(shorten(", ".join(failed), 120)))
        await render(update, context, "\n".join(lines), wol_keyboard(devices))
        return

    names = [{"name": device.name, "mac": device.mac} for device in devices]
    match, candidates = find_named(names, target, keys=("name",))
    if match is None:
        if candidates:
            options = ", ".join(shorten(item["name"], 30) for item in candidates[:6])
            await notify(
                update,
                context,
                f"Hay varias coincidencias: {options}. Sé más específico.",
            )
        else:
            await notify(update, context, f"No encontré ningún equipo llamado «{target}».")
        return
    device = next((item for item in devices if item.name == match["name"]), None)
    if device is None:
        await notify(update, context, "Ese equipo ya no está configurado.")
        return
    if not await ensure_writable(update, context):
        return
    try:
        await _wake_device(device)
    except (OSError, ValueError, ServiceError) as exc:
        await audit(update, context, "wol.send", device.name, outcome="error")
        await notify(update, context, f"❌ No se pudo enviar el magic packet: {exc}")
        return
    await audit(update, context, "wol.send", f"{device.name} ({device.mac})")
    await render(
        update,
        context,
        build_wol(devices) + f"\n\n✅ Magic packet enviado a <b>{esc(device.name)}</b>.",
        wol_keyboard(devices),
    )
