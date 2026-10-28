"""Teclados inline de Telegram."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from . import features
from .config import WolDevice
from .formatting import (
    container_emoji,
    disk_emoji,
    shorten,
    vm_emoji,
)
from .integrations import is_downloading, is_paused, is_seeding
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
    rows = [
        [Button("📊 Estado", callback_data="m:status"), Button("💾 Discos", callback_data="m:disks")],
        [Button("🐳 Docker", callback_data="m:docker"), Button("🖥️ VMs", callback_data="m:vms")],
        [Button("⚙️ Sistema", callback_data="m:sys"), Button("🔔 Alertas", callback_data="m:alerts")],
        [Button("🔎 Buscar", callback_data="m:search"), Button("📈 Rendimiento", callback_data="m:perf")],
    ]
    if features.count():
        rows.append([Button("🧰 Herramientas", callback_data="m:tools")])
    rows.append([Button("🌐 Idioma", callback_data="m:lang"), Button("❓ Ayuda", callback_data="m:help")])
    return Keyboard(rows)


def tools_keyboard() -> Keyboard:
    rows = [[Button(feature.label, callback_data=feature.callback)] for feature in features.enabled()]
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def language_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("English", callback_data="lang:set:en"), Button("Español", callback_data="lang:set:es")],
            [Button("Français", callback_data="lang:set:fr"), Button("Italiano", callback_data="lang:set:it")],
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


def physical_disks_keyboard(
    disks: list[dict[str, Any]] | None = None, page: int = 0, pages: int = 1
) -> Keyboard:
    rows: list[list[Button]] = []
    for disk in disks or []:
        name = disk.get("name") or disk.get("device") or "disco"
        token = short_id(str(disk.get("id") or name))
        rows.append(
            [Button(f"🔍 {shorten(str(name), 26)}", callback_data=f"s:smart:{token}")]
        )
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"k:p:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="k:p:noop"),
                Button("▶️", callback_data=f"k:p:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("🔄 Actualizar", callback_data=f"k:p:{page}"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


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
    rows.append([Button("🧹 Mantenimiento", callback_data="d:maint"), Button("📦 Tamaños", callback_data="d:sizes")])
    rows.append([Button("🔄 Actualizar", callback_data=f"d:l:{page}"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def docker_maintenance_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("📦 Tamaños", callback_data="d:sizes"), Button("🔄 Actualizar", callback_data="d:maint")],
            [Button("🐳 Docker", callback_data="d:l:0"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def docker_sizes_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🧹 Mantenimiento", callback_data="d:maint"), Button("🔄 Actualizar", callback_data="d:sizes")],
            [Button("🐳 Docker", callback_data="d:l:0"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


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
    auto_label = "🔔 Autostart: Sí" if container.get("autoStart") else "🔕 Autostart: No"
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
            [Button("🕓 Historial paridad", callback_data="s:ph"), Button("🪪 Licencia", callback_data="s:license")],
            [Button("🔌 Plugins", callback_data="s:plugins"), Button("🧩 Servicios", callback_data="s:services")],
            [Button("🌐 Red", callback_data="s:network"), Button("📜 Logs", callback_data="s:logs")],
            [Button("🌡️ Temperaturas", callback_data="s:temp"), Button("🔑 Claves API", callback_data="s:keys")],
            [Button("🏷️ Identidad", callback_data="s:identity"), Button("🩺 Diagnóstico", callback_data="s:diag")],
            [Button("🔄 Actualizar", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def array_keyboard(state: str | None) -> Keyboard:
    rows: list[list[Button]] = []
    if state == "STARTED":
        rows.append([Button("⏹ Detener array", callback_data="s:astop")])
    else:
        rows.append([Button("▶️ Iniciar array", callback_data="s:astart")])
        rows.append([Button("🔐 Iniciar array cifrado", callback_data="s:astart:enc")])
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


def notifications_keyboard(page: int = 0, pages: int = 1) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"s:notif:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="s:notif:noop"),
                Button("▶️", callback_data=f"s:notif:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("🗑 Archivar todas", callback_data="s:notifclear")])
    rows.append(
        [
            Button("🔄 Actualizar", callback_data=f"s:notif:{page}"),
            Button("🔙 Sistema", callback_data="m:sys"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


# ---------------------------------------------------------------------------
# 1.6.0 · pantallas ampliadas del sistema
# ---------------------------------------------------------------------------

def parity_history_keyboard(page: int = 0, pages: int = 1) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"s:ph:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="s:ph:noop"),
                Button("▶️", callback_data=f"s:ph:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("🧮 Paridad actual", callback_data="s:parity")])
    rows.append(
        [Button("🔄 Actualizar", callback_data=f"s:ph:{page}"), Button("🔙 Sistema", callback_data="m:sys")]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def parity_choice_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("✅ Correctiva (escribe)", callback_data="s:pc:1")],
            [Button("👁️ No correctiva (solo lee)", callback_data="s:pc:0")],
            [Button("🔙 Paridad", callback_data="s:parity"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def notifications_list_keyboard(
    items: list[dict[str, Any]],
    *,
    page: int = 0,
    pages: int = 1,
    archived: bool = False,
    importance: str | None = None,
) -> Keyboard:
    rows: list[list[Button]] = []
    for item in items:
        token = short_id(str(item.get("id") or item.get("title") or ""))
        emoji = {"ALERT": "🔴", "WARNING": "🟠", "INFO": "🔵"}.get(
            str(item.get("importance") or "").upper(), "•"
        )
        label = f"{emoji} {shorten(str(item.get('subject') or item.get('title') or 'Notificación'), 26)}"
        rows.append([Button(label, callback_data=f"s:notif:d:{token}")])

    if pages > 1:
        suffix = f":{importance or 'all'}:{'1' if archived else '0'}"
        rows.append(
            [
                Button("◀️", callback_data=f"s:notif:p:{max(0, page - 1)}{suffix}"),
                Button(f"{page + 1}/{pages}", callback_data="s:notif:noop"),
                Button("▶️", callback_data=f"s:notif:p:{min(pages - 1, page + 1)}{suffix}"),
            ]
        )

    if archived:
        rows.append([Button("📥 Ver sin leer", callback_data="s:notif:f:all:0")])
    else:
        rows.append([Button("🗂 Ver archivadas", callback_data="s:notif:f:all:1")])
    rows.append(
        [
            Button("🔴 Alertas", callback_data=f"s:notif:f:ALERT:{'1' if archived else '0'}"),
            Button("🟠 Avisos", callback_data=f"s:notif:f:WARNING:{'1' if archived else '0'}"),
        ]
    )
    rows.append(
        [
            Button("🔵 Info", callback_data=f"s:notif:f:INFO:{'1' if archived else '0'}"),
            Button("📋 Todas", callback_data=f"s:notif:f:all:{'1' if archived else '0'}"),
        ]
    )
    rows.append([Button("🗑 Archivar todas", callback_data="s:notifclear")])
    rows.append(
        [
            Button("🔄 Actualizar", callback_data="s:notif:0"),
            Button("🔙 Sistema", callback_data="m:sys"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def notification_detail_keyboard(
    item: dict[str, Any], *, archived: bool = False, importance: str | None = None
) -> Keyboard:
    token = short_id(str(item.get("id") or item.get("title") or ""))
    back = f"s:notif:f:{importance or 'all'}:{'1' if archived else '0'}"
    rows: list[list[Button]] = []
    if archived:
        rows.append(
            [
                Button("📤 Desarchivar", callback_data=f"s:notif:u:{token}"),
                Button("🗑 Borrar", callback_data=f"s:notif:x:{token}"),
            ]
        )
    else:
        rows.append(
            [
                Button("📥 Archivar", callback_data=f"s:notif:a:{token}"),
                Button("🔵 Marcar no leída", callback_data=f"s:notif:m:{token}"),
            ]
        )
    rows.append([Button("🔙 Notificaciones", callback_data=back), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def license_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("💾 Backup del flash", callback_data="s:flash")],
            [Button("🔄 Actualizar", callback_data="s:license"), Button("🔙 Sistema", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def plugins_keyboard(page: int = 0, pages: int = 1) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"s:plugins:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="s:plugins:noop"),
                Button("▶️", callback_data=f"s:plugins:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("➕ Instalar plugin", callback_data="s:plugin:add")])
    rows.append(
        [Button("🔄 Actualizar", callback_data=f"s:plugins:{page}"), Button("🔙 Sistema", callback_data="m:sys")]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def services_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data="s:services"), Button("🌐 Red", callback_data="s:network")],
            [Button("🔙 Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def network_keyboard(access_urls: list[dict[str, Any]] | None = None) -> Keyboard:
    rows: list[list[Button]] = []
    for access in access_urls or []:
        if not isinstance(access, dict):
            continue
        url = access.get("ipv4") or access.get("ipv6")
        if not url:
            continue
        label = f"🌐 {access.get('name') or access.get('type') or 'Abrir WebGUI'}"
        rows.append([Button(shorten(label, 30), url=str(url))])
    rows.append([Button("🔄 Actualizar", callback_data="s:network"), Button("🧩 Servicios", callback_data="s:services")])
    rows.append([Button("🔙 Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def logs_keyboard(files: list[dict[str, Any]]) -> Keyboard:
    rows: list[list[Button]] = []
    for log in files[:12]:
        path = str(log.get("path") or log.get("name") or "")
        if not path:
            continue
        label = f"📜 {shorten(str(log.get('name') or path), 24)}"
        rows.append([Button(label, callback_data=f"s:log:{short_id(path)}:0")])
    rows.append([Button("🩺 Diagnóstico", callback_data="s:diag"), Button("🔄 Actualizar", callback_data="s:logs")])
    rows.append([Button("🔙 Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def log_content_keyboard(token: str, page: int = 0, pages: int = 1) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"s:log:{token}:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="s:log:noop"),
                Button("▶️", callback_data=f"s:log:{token}:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("📥 Enviar como archivo", callback_data=f"s:logfile:{token}")])
    rows.append(
        [Button("🔄 Recargar", callback_data=f"s:log:{token}:{page}"), Button("🔙 Logs", callback_data="s:logs")]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def shares_keyboard(shares: list[dict[str, Any]]) -> Keyboard:
    rows: list[list[Button]] = []
    for share in sorted(shares, key=lambda item: str(item.get("name") or "").lower()):
        name = str(share.get("name") or "share")
        token = short_id(name)
        rows.append([Button(f"📚 {shorten(name, 28)}", callback_data=f"s:share:{token}")])
    rows.append([Button("🔄 Actualizar", callback_data="s:shares"), Button("🔙 Sistema", callback_data="m:sys")])
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def share_detail_keyboard(name: str) -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data=f"s:share:{short_id(name)}"), Button("📚 Shares", callback_data="s:shares")],
            [Button("🔙 Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def smart_keyboard(disk: dict[str, Any], *, mountable: bool = False) -> Keyboard:
    rows: list[list[Button]] = []
    disk_id = disk.get("id")
    if mountable and disk_id:
        token = short_id(str(disk_id))
        rows.append(
            [
                Button("📂 Montar", callback_data=f"s:disk:mount:{token}"),
                Button("📤 Desmontar", callback_data=f"s:disk:unmount:{token}"),
            ]
        )
    rows.append([Button("🔍 Discos físicos", callback_data="k:p"), Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def temperatures_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("⚙️ Umbrales", callback_data="s:thresh"), Button("🔧 Configurar", callback_data="s:thresh:set")],
            [Button("🔄 Actualizar", callback_data="s:temp"), Button("🔙 Sistema", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def api_keys_keyboard(keys: list[dict[str, Any]]) -> Keyboard:
    rows: list[list[Button]] = [[Button("➕ Crear clave VIEWER", callback_data="s:key:new")]]
    for key in keys[:10]:
        key_id = str(key.get("id") or "")
        if not key_id:
            continue
        rows.append(
            [
                Button(
                    f"🗑 {shorten(str(key.get('name') or 'clave'), 24)}",
                    callback_data=f"s:key:del:{short_id(key_id)}",
                )
            ]
        )
    rows.append([Button("🔄 Actualizar", callback_data="s:keys"), Button("🔙 Sistema", callback_data="m:sys")])
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def identity_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("✏️ Editar nombre", callback_data="s:identity:edit")],
            [Button("🔄 Actualizar", callback_data="s:identity"), Button("🔙 Sistema", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def diagnostics_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("📜 Logs", callback_data="s:logs"), Button("🔄 Actualizar", callback_data="s:diag")],
            [Button("🔙 Sistema", callback_data="m:sys"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def flash_backup_keyboard(remotes: list[dict[str, Any]]) -> Keyboard:
    rows: list[list[Button]] = []
    for remote in remotes:
        name = str(remote.get("name") or "").strip()
        if not name:
            continue
        kind = remote.get("type")
        label = f"💾 {name}" + (f" ({kind})" if kind else "")
        rows.append([Button(shorten(label, 30), callback_data=f"s:flash:{short_id(name)}")])
    rows.append(
        [Button("🔙 Licencia", callback_data="s:license"), Button("🏠 Menú", callback_data="m:main")]
    )
    return Keyboard(rows)


def simple_back_keyboard(callback: str = "m:sys") -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data=callback), Button("🔙 Volver", callback_data="m:sys")],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def search_keyboard(items: list[Any], page: int, pages: int) -> Keyboard:
    buttons = []
    for hit in items:
        emoji = getattr(hit, "kind", "")
        emoji = {"docker": "🐳", "vm": "🖥️", "disk": "💾", "physical_disk": "🔍",
                 "share": "📚", "notification": "🔔", "ups": "🔋"}.get(emoji, "•")
        label = f"{emoji} {shorten(str(getattr(hit, 'title', 'resultado')), 22)}"
        buttons.append(Button(label, callback_data=str(getattr(hit, "callback", "m:main"))))
    rows = _rows(buttons, per_row=2)
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"q:p:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="q:noop"),
                Button("▶️", callback_data=f"q:p:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("🔎 Nueva búsqueda", callback_data="q:s"), Button("🔄 Repetir", callback_data=f"q:r:{page}")])
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def history_keyboard(page: int, pages: int, has_filter: bool) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"h:p:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="h:noop"),
                Button("▶️", callback_data=f"h:p:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append([Button("🔎 Filtrar", callback_data="h:f"), Button("🔄 Actualizar", callback_data="h:r")])
    if has_filter:
        rows.append([Button("🧹 Quitar filtro", callback_data="h:c")])
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def performance_keyboard() -> Keyboard:
    return Keyboard(
        [
            [Button("🔄 Actualizar", callback_data="m:perf"), Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def alerts_keyboard(subscribed: bool, muted_until: float | None = None) -> Keyboard:
    toggle = (
        Button("🔕 Desactivar aquí", callback_data="a:off")
        if subscribed
        else Button("✅ Activar aquí", callback_data="a:on")
    )
    rows: list[list[Button]] = [[toggle]]
    if muted_until is not None:
        rows.append([Button("🔔 Quitar silencio", callback_data="a:unmute")])
    else:
        rows.append(
            [
                Button("🔕 1 h", callback_data="a:mute:3600"),
                Button("🔕 8 h", callback_data="a:mute:28800"),
                Button("🔕 24 h", callback_data="a:mute:86400"),
            ]
        )
    rows.append(
        [
            Button("📣 Enviar prueba", callback_data="a:test"),
            Button("🔄 Actualizar", callback_data="m:alerts"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def _torrent_emoji(torrent: dict[str, Any]) -> str:
    if is_paused(torrent):
        return "⏸"
    if is_downloading(torrent):
        return "⬇️"
    if is_seeding(torrent):
        return "⬆️"
    return "•"


def qb_list_keyboard(
    torrents: list[dict[str, Any]],
    page: int,
    pages: int,
    filter_key: str,
    alt_speed: bool,
) -> Keyboard:
    rows: list[list[Button]] = [
        [
            Button("⏸ Pausar todo", callback_data="qb:all:pause"),
            Button("▶️ Reanudar todo", callback_data="qb:all:resume"),
        ],
        [
            Button("➕ Añadir", callback_data="qb:a"),
            Button("⚙️ Límites", callback_data="qb:lim"),
        ],
    ]
    filters = [
        ("all", "Todos"),
        ("downloading", "Descargando"),
        ("seeding", "Sembrando"),
        ("paused", "Pausados"),
    ]
    filter_buttons = [
        Button(
            f"{'• ' if key == filter_key else ''}{label}",
            callback_data=f"qb:l:{key}:0",
        )
        for key, label in filters
    ]
    rows.extend(_rows(filter_buttons, per_row=2))
    for torrent in torrents:
        token = short_id(str(torrent.get("hash") or torrent.get("name") or "torrent"))
        label = f"{_torrent_emoji(torrent)} {shorten(torrent.get('name') or 'torrent', 24)}"
        rows.append([Button(label, callback_data=f"qb:d:{token}:{filter_key}:{page}")])
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"qb:l:{filter_key}:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data="qb:noop"),
                Button(
                    "▶️",
                    callback_data=f"qb:l:{filter_key}:{min(pages - 1, page + 1)}",
                ),
            ]
        )
    rows.append(
        [
            Button("📚 Categorías", callback_data="qb:cat"),
            Button("🔄 Actualizar", callback_data=f"qb:l:{filter_key}:{page}"),
        ]
    )
    rows.append(
        [
            Button("🧰 Herramientas", callback_data="m:tools"),
            Button("🏠 Menú", callback_data="m:main"),
        ]
    )
    return Keyboard(rows)


def qb_detail_keyboard(
    torrent: dict[str, Any], filter_key: str, page: int
) -> Keyboard:
    token = short_id(str(torrent.get("hash") or torrent.get("name") or "torrent"))
    toggle = "▶️ Reanudar" if is_paused(torrent) else "⏸ Pausar"
    return Keyboard(
        [
            [
                Button(toggle, callback_data=f"qb:t:{token}:{filter_key}:{page}"),
                Button("🗑 Borrar", callback_data=f"qb:x:{token}:{filter_key}:{page}"),
            ],
            [
                Button("🔙 Lista", callback_data=f"qb:l:{filter_key}:{page}"),
                Button(
                    "🔄 Actualizar",
                    callback_data=f"qb:d:{token}:{filter_key}:{page}",
                ),
            ],
            [
                Button("🧰 Herramientas", callback_data="m:tools"),
                Button("🏠 Menú", callback_data="m:main"),
            ],
        ]
    )


def qb_limits_keyboard(alt_speed: bool) -> Keyboard:
    label = (
        "⚡ Desactivar alternativa" if alt_speed else "⚡ Activar alternativa"
    )
    return Keyboard(
        [
            [Button(label, callback_data="qb:alt")],
            [
                Button("🔙 qBittorrent", callback_data="qb:l:all:0"),
                Button("🏠 Menú", callback_data="m:main"),
            ],
        ]
    )


def qb_categories_keyboard() -> Keyboard:
    return Keyboard(
        [
            [
                Button("🔙 qBittorrent", callback_data="qb:l:all:0"),
                Button("🏠 Menú", callback_data="m:main"),
            ],
        ]
    )


def mikrotik_main_keyboard() -> Keyboard:
    return Keyboard(
        [
            [
                Button("🖧 Interfaces", callback_data="mt:i:0"),
                Button("📋 Leases", callback_data="mt:l:0"),
            ],
            [
                Button("🧭 Rutas", callback_data="mt:r:0"),
                Button("🛡 Firewall", callback_data="mt:f:0"),
            ],
            [
                Button("📜 Registros", callback_data="mt:g:0"),
                Button("🔄 Actualizar", callback_data="tool:mt"),
            ],
            [
                Button("🔁 Reiniciar", callback_data="mt:reboot"),
                Button("🧰 Herramientas", callback_data="m:tools"),
            ],
            [Button("🏠 Menú", callback_data="m:main")],
        ]
    )


def mikrotik_paged_keyboard(prefix: str, page: int, pages: int) -> Keyboard:
    rows: list[list[Button]] = []
    if pages > 1:
        rows.append(
            [
                Button("◀️", callback_data=f"{prefix}:{max(0, page - 1)}"),
                Button(f"{page + 1}/{pages}", callback_data=f"{prefix}:noop"),
                Button("▶️", callback_data=f"{prefix}:{min(pages - 1, page + 1)}"),
            ]
        )
    rows.append(
        [
            Button("🔄 Actualizar", callback_data=f"{prefix}:{page}"),
            Button("🔙 MikroTik", callback_data="tool:mt"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def wol_keyboard(devices: list[WolDevice]) -> Keyboard:
    rows = [
        [
            Button(
                f"⚡ {shorten(device.name, 24)}",
                callback_data=f"wol:w:{short_id(device.name + device.mac)}",
            )
        ]
        for device in devices
    ]
    if len(devices) > 1:
        rows.append([Button("⚡ Encender todos", callback_data="wol:all")])
    rows.append(
        [
            Button("🔄 Actualizar", callback_data="tool:wol"),
            Button("🧰 Herramientas", callback_data="m:tools"),
        ]
    )
    rows.append([Button("🏠 Menú", callback_data="m:main")])
    return Keyboard(rows)


def confirm_keyboard(token: str) -> Keyboard:
    return Keyboard(
        [
            [Button("✅ Confirmar", callback_data=f"c:y:{token}"), Button("❌ Cancelar", callback_data=f"c:n:{token}")],
        ]
    )
