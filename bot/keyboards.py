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


def physical_disks_keyboard(page: int = 0, pages: int = 1) -> Keyboard:
    rows: list[list[Button]] = []
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
