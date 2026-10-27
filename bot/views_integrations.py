"""Vistas de las integraciones opcionales: qBittorrent, MikroTik y WOL."""

from __future__ import annotations

from typing import Any, Iterable

from .config import WolDevice
from .formatting import bar, esc, fmt_bytes, fmt_epoch, fmt_pct, shorten
from .integrations import (
    QB_FILTERS,
    filter_torrents,
    format_eta,
    is_downloading,
    is_paused,
    number,
    torrent_state,
    truthy,
)
from .views import paginate

QB_PER_PAGE = 6
MT_PER_PAGE = 6
MT_LEASE_PER_PAGE = 8
MT_LOG_PER_PAGE = 8


def _speed(value: Any) -> str:
    return f"{fmt_bytes(value)}/s"


def _limit(value: Any) -> str:
    amount = number(value)
    if amount <= 0:
        return "ilimitado"
    return f"{fmt_bytes(amount)}/s"


def build_qb_list(
    status: dict[str, Any],
    torrents: list[dict[str, Any]],
    page: int,
    per_page: int,
    filter_key: str,
    alt_speed: bool,
) -> str:
    visible = filter_torrents(torrents, filter_key)
    items, page, pages = paginate(visible, page, per_page)
    active = sum(1 for torrent in torrents if is_downloading(torrent))
    paused = sum(1 for torrent in torrents if is_paused(torrent))
    lines = [
        "🐳 <b>qBittorrent</b>",
        "",
        f"⬇️ {_speed(status.get('dl_info_speed'))} · "
        f"⬆️ {_speed(status.get('up_info_speed'))}",
        (
            f"{len(torrents)} torrents · {active} activos · {paused} pausados · "
            f"⚡ alternativa {'activa' if alt_speed else 'inactiva'}"
        ),
        f"Filtro: {QB_FILTERS.get(filter_key, QB_FILTERS['all'])} · pág. {page + 1}/{pages}",
        "",
    ]
    if not items:
        lines.append("No hay torrents con este filtro.")
        return "\n".join(lines)
    for torrent in items:
        progress = number(torrent.get("progress")) * 100
        lines.append(
            f"• <b>{esc(shorten(torrent.get('name') or torrent.get('hash') or 'torrent', 45))}</b>"
        )
        lines.append(
            f"   {esc(torrent_state(torrent))} · {fmt_pct(progress)} · "
            f"⬇️ {_speed(torrent.get('dlspeed'))} · ⬆️ {_speed(torrent.get('upspeed'))}"
        )
    if len(visible) > len(items):
        lines.append(f"… y {len(visible) - len(items)} más en total")
    return "\n".join(lines)


def build_qb_detail(torrent: dict[str, Any], settings: Any) -> str:
    progress = number(torrent.get("progress")) * 100
    size = number(torrent.get("size"))
    total = number(torrent.get("total_size")) or size
    completed = number(torrent.get("completed")) or size * progress / 100
    lines = [
        f"🐳 <b>qBittorrent · {esc(shorten(torrent.get('name') or 'torrent', 60))}</b>",
        "",
        f"Estado: <b>{esc(torrent_state(torrent))}</b>",
        f"Progreso: <code>{bar(progress, 12)}</code> {fmt_pct(progress)}",
        f"Tamaño: {fmt_bytes(completed)} / {fmt_bytes(total)}",
        f"Velocidad: ⬇️ {_speed(torrent.get('dlspeed'))} · ⬆️ {_speed(torrent.get('upspeed'))}",
        f"ETA: {format_eta(torrent.get('eta'))} · Ratio: {number(torrent.get('ratio')):.2f}",
        (
            f"Semillas: {int(number(torrent.get('num_seeds')))} "
            f"({int(number(torrent.get('num_complete')))}) · "
            f"Pares: {int(number(torrent.get('num_leechs')))} "
            f"({int(number(torrent.get('num_incomplete')))})"
        ),
    ]
    category = str(torrent.get("category") or "")
    if category:
        lines.append(f"Categoría: <code>{esc(category)}</code>")
    path = str(torrent.get("save_path") or "")
    if path:
        lines.append(f"Ruta: <code>{esc(shorten(path, 80))}</code>")
    added = torrent.get("added_on")
    if added:
        lines.append(f"Añadido: {fmt_epoch(added, settings.timezone)}")
    return "\n".join(lines)


def build_qb_limits(preferences: dict[str, Any], alt_speed: bool) -> str:
    lines = [
        "⚙️ <b>Límites de velocidad</b>",
        "",
        f"Descarga: <b>{_limit(preferences.get('dl_limit'))}</b>",
        f"Subida: <b>{_limit(preferences.get('up_limit'))}</b>",
        f"Velocidad alternativa: <b>{'activada' if alt_speed else 'desactivada'}</b>",
        (
            f"Límites alternativa: ⬇️ {_limit(preferences.get('alt_dl_limit'))} · "
            f"⬆️ {_limit(preferences.get('alt_up_limit'))}"
        ),
        "",
        "Para cambiarlos: <code>/qbittorrent limit down 1024</code> "
        "(KB/s; 0 = ilimitado).",
    ]
    return "\n".join(lines)


def build_qb_categories(
    categories: dict[str, Any], torrents: list[dict[str, Any]]
) -> str:
    counts: dict[str, int] = {}
    for torrent in torrents:
        key = str(torrent.get("category") or "")
        counts[key] = counts.get(key, 0) + 1
    lines = ["📚 <b>Categorías</b>", ""]
    if not categories and not any(counts):
        lines.append("No hay categorías definidas.")
        return "\n".join(lines)
    for name, data in sorted(categories.items()):
        save_path = ""
        if isinstance(data, dict):
            save_path = str(data.get("savePath") or "")
        line = f"• <b>{esc(name)}</b> · {counts.get(name, 0)} torrents"
        if save_path:
            line += f"\n   <code>{esc(shorten(save_path, 70))}</code>"
        lines.append(line)
    without = counts.get("", 0)
    if without:
        lines.append(f"• <i>Sin categoría</i> · {without} torrents")
    return "\n".join(lines)


def build_mikrotik_main(
    identity: dict[str, Any],
    resource: dict[str, Any],
    interfaces: list[dict[str, Any]],
    leases: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    firewall: list[dict[str, Any]],
) -> str:
    name = identity.get("name") or "MikroTik"
    total_mem = number(resource.get("total-memory"))
    free_mem = number(resource.get("free-memory"))
    used_pct = 0 if total_mem <= 0 else (total_mem - free_mem) / total_mem * 100
    running = [item for item in interfaces if truthy(item.get("running"))]
    active_leases = [item for item in leases if str(item.get("status") or "") == "bound"]
    active_routes = [item for item in routes if truthy(item.get("active"))]
    enabled_rules = [item for item in firewall if not truthy(item.get("disabled"))]
    return "\n".join(
        [
            f"📡 <b>MikroTik · {esc(name)}</b>",
            "",
            f"Modelo: {esc(resource.get('board-name') or '—')}",
            f"RouterOS: {esc(resource.get('version') or '—')}",
            f"Uptime: {esc(resource.get('uptime') or '—')}",
            f"CPU: {esc(str(resource.get('cpu-load', '—')))}%",
            (
                f"RAM: {fmt_bytes(free_mem)} libres de {fmt_bytes(total_mem)} "
                f"({used_pct:.0f}% usada)"
            ),
            "",
            f"Interfaces: {len(running)}/{len(interfaces)} activas",
            f"Leases DHCP: {len(active_leases)}/{len(leases)} activas",
            f"Rutas: {len(active_routes)}/{len(routes)} activas",
            f"Firewall: {len(enabled_rules)}/{len(firewall)} reglas activas",
        ]
    )


def build_mikrotik_interfaces(
    interfaces: list[dict[str, Any]], page: int, per_page: int = MT_PER_PAGE
) -> str:
    ordered = sorted(
        interfaces,
        key=lambda item: (not truthy(item.get("running")), str(item.get("name") or "")),
    )
    items, page, pages = paginate(ordered, page, per_page)
    lines = [f"🖧 <b>Interfaces</b> · pág. {page + 1}/{pages}", ""]
    if not items:
        lines.append("No hay interfaces.")
        return "\n".join(lines)
    for item in items:
        running = truthy(item.get("running"))
        disabled = truthy(item.get("disabled"))
        icon = "⛔" if disabled else ("✅" if running else "⚪")
        lines.append(
            f"{icon} <b>{esc(item.get('name') or '—')}</b> · "
            f"{esc(item.get('type') or '—')} · MTU {esc(item.get('mtu') or '—')}"
        )
        lines.append(
            f"   RX {fmt_bytes(item.get('rx-byte'))} · TX {fmt_bytes(item.get('tx-byte'))} · "
            f"errores {esc(item.get('rx-error') or 0)}/{esc(item.get('tx-error') or 0)}"
        )
        mac = item.get("mac-address")
        if mac:
            lines.append(f"   <code>{esc(mac)}</code>")
    return "\n".join(lines)


def build_mikrotik_leases(
    leases: list[dict[str, Any]], page: int, per_page: int = MT_LEASE_PER_PAGE
) -> str:
    items, page, pages = paginate(leases, page, per_page)
    lines = [f"📋 <b>Leases DHCP</b> · pág. {page + 1}/{pages}", ""]
    if not items:
        lines.append("No hay leases DHCP.")
        return "\n".join(lines)
    for item in items:
        status = str(item.get("status") or "")
        icon = "🟢" if status == "bound" else "⚪"
        host = item.get("host-name") or item.get("comment") or item.get("mac-address") or "—"
        lines.append(
            f"{icon} <b>{esc(shorten(host, 32))}</b> · "
            f"<code>{esc(item.get('address') or '—')}</code>"
        )
        flags = [status or "—"]
        flags.append("dinámica" if truthy(item.get("dynamic")) else "estática")
        if item.get("server"):
            flags.append(f"server {item.get('server')}")
        lines.append(f"   {' · '.join(esc(str(flag)) for flag in flags)}")
        mac = item.get("mac-address")
        if mac:
            lines.append(f"   <code>{esc(mac)}</code>")
    return "\n".join(lines)


def build_mikrotik_routes(
    routes: list[dict[str, Any]], page: int, per_page: int = MT_PER_PAGE
) -> str:
    ordered = sorted(
        routes,
        key=lambda item: (not truthy(item.get("active")), str(item.get("dst-address") or "")),
    )
    items, page, pages = paginate(ordered, page, per_page)
    lines = [f"🧭 <b>Rutas</b> · pág. {page + 1}/{pages}", ""]
    if not items:
        lines.append("No hay rutas.")
        return "\n".join(lines)
    for item in items:
        icon = "✅" if truthy(item.get("active")) else "⚪"
        lines.append(
            f"{icon} <code>{esc(item.get('dst-address') or '—')}</code> → "
            f"{esc(item.get('gateway') or '—')}"
        )
        flags = [f"dist {esc(item.get('distance') or '—')}"]
        if truthy(item.get("static")):
            flags.append("estática")
        if truthy(item.get("disabled")):
            flags.append("deshabilitada")
        if item.get("comment"):
            flags.append(esc(shorten(item.get("comment"), 40)))
        lines.append(f"   {' · '.join(flags)}")
    return "\n".join(lines)


def build_mikrotik_firewall(
    rules: list[dict[str, Any]], page: int, per_page: int = MT_PER_PAGE
) -> str:
    items, page, pages = paginate(rules, page, per_page)
    lines = [f"🛡 <b>Firewall</b> · pág. {page + 1}/{pages}", ""]
    if not items:
        lines.append("No hay reglas de firewall.")
        return "\n".join(lines)
    for item in items:
        icon = "⛔" if truthy(item.get("disabled")) else "✅"
        lines.append(
            f"{icon} <b>{esc(item.get('chain') or '—')}</b> · "
            f"{esc(item.get('action') or '—')}"
        )
        lines.append(
            f"   {esc(item.get('packets') or 0)} paquetes · "
            f"{fmt_bytes(item.get('bytes'))}"
        )
        if item.get("comment"):
            lines.append(f"   <i>{esc(shorten(item.get('comment'), 60))}</i>")
    return "\n".join(lines)


def build_mikrotik_logs(
    logs: Iterable[dict[str, Any]], page: int, per_page: int = MT_LOG_PER_PAGE
) -> str:
    items, page, pages = paginate(list(logs), page, per_page)
    lines = [f"📜 <b>Registros</b> · pág. {page + 1}/{pages}", ""]
    if not items:
        lines.append("No hay registros.")
        return "\n".join(lines)
    for item in items:
        topics = str(item.get("topics") or "").replace(",", ", ")
        lines.append(
            f"🕒 <code>{esc(item.get('time') or '—')}</code> "
            f"<i>{esc(topics)}</i>"
        )
        lines.append(f"   {esc(shorten(item.get('message') or '—', 120))}")
    return "\n".join(lines)


def build_wol(devices: Iterable[WolDevice]) -> str:
    items = list(devices)
    lines = ["⚡ <b>Wake-on-LAN</b>", ""]
    if not items:
        lines.append("No hay equipos configurados.")
        return "\n".join(lines)
    lines.append(f"Equipos configurados: <b>{len(items)}</b>")
    lines.append("")
    for device in items:
        lines.append(f"• <b>{esc(device.name)}</b> · <code>{esc(device.mac)}</code>")
        lines.append(f"   Broadcast: <code>{esc(device.broadcast)}</code>")
    lines.append("")
    lines.append("Pulsa un equipo para enviar su magic packet.")
    return "\n".join(lines)
