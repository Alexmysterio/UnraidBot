"""Teclados inline de Telegram."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .formatting import (
    container_emoji,
    disk_emoji,
    shorten,
    vm_emoji,
)
from .security import short_id

Button = InlineKeyboardButton
Keyboard = InlineKeyboardMarkup


def _rows(buttons: list[Button], per_row: int = 2) -> list[list[Button]]:
    return [buttons[index : index + per_row] for index in range(0, len(buttons), per_row)]


def _container_name(container: dict[str, Any]) -> str:
    names = container.get("names") or []
    if names:
        return str(names[0]).lstrip("/")
    return "contenedor"


def _vm_name(vm: dict[str, Any]) -> str:
    return str(vm.get("name") or vm.get("id") or "VM")


def main_menu() -> Keyboard:
    return Keyboard(
        [
            [Button("📊 Estado", callback_data="m:status"), Button("💾 Discos", callback_data="m:disks")],
            [Button("🐳 Docker", callback_data="m:docker"), Button("🖥️ VMs", callback_data="m:vms")],
            [Button("⚙️ Sistema", callback_data="m:sys"), Button("🔔 Alertas", callback_data="m:alerts")],
            [Button("❓ Ayuda", callback_data="m:help")],
        ]
    )


def refresh_menu(callback: str = "m:main") -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data=callback), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def back_menu(callback: str = "m:main") -> Keyboard:
    return Keyboard([[Button("🔙 Volver", callback_data=callback), Button("🏠 Menú", callback_data="m:main")]])


def disks_keyboard(disks: list[dict[str, Any]]) -> Keyboard:
    buttons = []
    for disk in disks:
        name = disk.get("name") or disk.get("device") or "disco"
        label = f"{disk_emoji(disk.get('status'), disk.get('color'))} {shorten(str(name), 22)}"
        buttons.append(Button(label, callback_data=f"k:v:{short_id(str(disk.get('id') or name))}"))
    rows = _rows(buttons, per_row=2)
    rows.append([Button("🔍 Discos físicos", callback_data="k:p"), Button("🔄 Actualizar", callback_data="m:disks")])
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def disk_detail_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("💾 Volver a discos", callback_data="m:disks"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def physical_disks_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🔙 Discos", callback_data="m:disks"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def docker_list_keyboard(
    containers: list[dict[str, Any]], page: int, total_pages: int, update_count: int = 0
) -> Keyboard:
    buttons = []
    for container in containers:
        name = _container_name(container)
        label = f"{container_emoji(container.get('state'))} {shorten(name, 20)}"
        buttons.append(Button(label, callback_data=f"d:v:{short_id(str(container.get('id') or name))}:{page}"))
    rows = _rows(buttons, per_row=2)

    if update_count:
        rows.append(
            [Button(f"⬆️ Actualizar todo ({update_count})", callback_data="d:updateall")]
        )

    nav: list[Button] = []
    if total_pages > 1:
        nav.append(Button("◀️", callback_data=f"d:l:{max(0, page - 1)}"))
        nav.append(Button(f"{page + 1}/{total_pages}", callback_data="d:noop"))
        nav.append(Button("▶️", callback_data=f"d:l:{min(total_pages - 1, page + 1)}"))
        rows.append(nav)
    rows.append([Button("🔄 Actualizar", callback_data=f"d:l:{page}"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def docker_detail_keyboard(container: dict[str, Any], page: int = 0) -> Keyboard:
    token = short_id(str(container.get("id") or _container_name(container)))
    state = container.get("state")
    rows: list[list[Button]] = []

    if state == "RUNNING":
        rows.append(
            [
                Button("⏹ Detener", callback_data=f"d:stop:{token}:{page}"),
                Button("🔄 Reiniciar", callback_data=f"d:restart:{token}:{page}"),
            ]
        )
        rows.append([Button("⏸ Pausar", callback_data=f"d:pause:{token}:{page}")])
    elif state == "PAUSED":
        rows.append(
            [
                Button("▶️ Reanudar", callback_data=f"d:unpause:{token}:{page}"),
                Button("⏹ Detener", callback_data=f"d:stop:{token}:{page}"),
            ]
        )
    else:
        rows.append([Button("▶️ Iniciar", callback_data=f"d:start:{token}:{page}")])

    rows.append(
        [
            Button("📜 Logs", callback_data=f"d:log:{token}:{page}"),
            Button("🔄 Actualizar", callback_data=f"d:v:{token}:{page}"),
        ]
    )
    auto_label = "🔔 Autostart: sí" if container.get("autoStart") else "🔕 Autostart: no"
    rows.append([Button(auto_label, callback_data=f"d:autostart:{token}:{page}")])
    if container.get("isUpdateAvailable"):
        rows.append([Button("⬆️ Actualizar imagen", callback_data=f"d:update:{token}:{page}")])
    if container.get("webUiUrl"):
        rows.append([Button("🌐 Abrir WebUI", url=str(container["webUiUrl"]))])
    rows.append(
        [
            Button("🔙 Docker", callback_data=f"d:l:{page}"),
            Button("🏠 Menú", callback_data="m:main"),
        ]
    )
    return Keyboard(rows)


def docker_logs_keyboard(container: dict[str, Any], page: int = 0) -> Keyboard:
    token = short_id(str(container.get("id") or _container_name(container)))
    return Keyboard(
        [
            [Button("🔄 Recargar", callback_data=f"d:log:{token}:{page}"), Button("🔙 Ficha", callback_data=f"d:v:{token}:{page}")],
            [Button("🐳 Docker", callback_data=f"d:l:{page}"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def vms_keyboard(vms: list[dict[str, Any]]) -> Keyboard:
    buttons = []
    for vm in vms:
        label = f"{vm_emoji(vm.get('state'))} {shorten(_vm_name(vm), 22)}"
        buttons.append(Button(label, callback_data=f"v:v:{short_id(str(vm.get('id') or _vm_name(vm)))}"))
    rows = _rows(buttons, per_row=1)
    rows.append([Button("🔄 Actualizar", callback_data="m:vms"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def vm_detail_keyboard(vm: dict[str, Any]) -> Keyboard:
    token = short_id(str(vm.get("id") or _vm_name(vm)))
    state = vm.get("state")
    rows: list[list[Button]] = []

    if state in {"RUNNING", "IDLE"}:
        rows.append(
            [
                Button("⏹ Apagar", callback_data=f"v:a:stop:{token}"),
                Button("🔄 Reiniciar", callback_data=f"v:a:reboot:{token}"),
            ]
        )
        rows.append(
            [
                Button("⏸ Pausar", callback_data=f"v:a:pause:{token}"),
                Button("⏏ Forzar apagado", callback_data=f"v:a:force_stop:{token}"),
            ]
        )
    elif state == "PAUSED":
        rows.append(
            [
                Button("▶️ Reanudar", callback_data=f"v:a:resume:{token}"),
                Button("⏹ Apagar", callback_data=f"v:a:stop:{token}"),
            ]
        )
        rows.append([Button("⏏ Forzar apagado", callback_data=f"v:a:force_stop:{token}")])
    else:
        rows.append(
            [
                Button("▶️ Iniciar", callback_data=f"v:a:start:{token}"),
                Button("↩️ Reset", callback_data=f"v:a:reset:{token}"),
            ]
        )

    rows.append(
        [
            Button("🔄 Actualizar", callback_data=f"v:v:{token}"),
            Button("🔙 VMs", callback_data="m:vms"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def system_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🧱 Array", callback_data="s:array"), Button("🧮 Paridad", callback_data="s:parity")],
            [Button("🔋 UPS", callback_data="s:ups"), Button("🔔 Notificaciones", callback_data="s:notif")],
            [Button("📚 Shares", callback_data="s:shares"), Button("ℹ️ Información", callback_data="s:info")],
            [Button("🔄 Actualizar", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def array_keyboard(state: str | None) -> Keyboard:
    rows: list[list[Button]] = []
    if state == "STARTED":
        rows.append([Button("⏹ Detener array", callback_data="s:astop")])
    else:
        rows.append([Button("▶️ Iniciar array", callback_data="s:astart")])
    rows.append([Button("🧮 Paridad", callback_data="s:parity"), Button("🔄 Actualizar", callback_data="s:array")])
    rows.append([Button("⚙️ Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def parity_keyboard(running: bool, paused: bool) -> Keyboard:
    rows: list[list[Button]] = []
    if running:
        rows.append(
            [
                Button("⏸ Pausar", callback_data="s:ppause"),
                Button("⏹ Cancelar", callback_data="s:pcancel"),
            ]
        )
    elif paused:
        rows.append(
            [
                Button("▶️ Reanudar", callback_data="s:presume"),
                Button("⏹ Cancelar", callback_data="s:pcancel"),
            ]
        )
    else:
        rows.append([Button("▶️ Iniciar comprobación", callback_data="s:pstart")])
    rows.append([Button("🔄 Actualizar", callback_data="s:parity"), Button("🧱 Array", callback_data="s:array")])
    rows.append([Button("⚙️ Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def notifications_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🗑 Archivar todas", callback_data="s:notifclear")],
            [Button("🔄 Actualizar", callback_data="s:notif"), Button("🔙 Sistema", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def simple_back_keyboard(callback: str = "m:sys") -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data=callback), Button("🔙 Volver", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def alerts_keyboard(subscribed: bool) -> Keyboard:
    toggle = (
        Button("🔕 Desactivar aquí", callback_data="a:off")
        if subscribed
        else Button("✅ Activar aquí", callback_data="a:on")
    )
    return Keyboard(
        [
            [toggle],
            [Button("📣 Enviar prueba", callback_data="a:test"), Button("🔄 Actualizar", callback_data="m:alerts")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def confirm_keyboard(token: str) -> Keyboard:
    return Keyboard(
        [
            [Button("✅ Confirmar", callback_data=f"c:y:{token}"), Button("❌ Cancelar", callback_data=f"c:n:{token}")],
        ]
    )
