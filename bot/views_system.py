"""Pantallas ampliadas del sistema (1.6.0).

Se mantienen aquí, y no en ``views.py``, para que el módulo principal no siga
creciendo. Todas las funciones son puras: reciben datos de la API y devuelven
el texto HTML que se envía a Telegram.
"""

from __future__ import annotations

from typing import Any

from .config import Settings
from .formatting import (
    bar,
    esc,
    fmt_bytes,
    fmt_kb,
    fmt_net_speed,
    fmt_runtime,
    fmt_temp,
    fmt_timestamp,
    fmt_when,
    pct,
    shorten,
)
from .unraid import Snapshot
from .views import paginate

PARITY_PER_PAGE = 8
NOTIF_PER_PAGE = 5
PLUGIN_PER_PAGE = 10
LOG_LINES_PER_PAGE = 60


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _get(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _reading(reading: Any) -> str:
    """Formatea una lectura de temperatura respetando su unidad."""
    if not isinstance(reading, dict):
        return "—"
    value = _number(reading.get("value"))
    if value is None:
        return "—"
    unit = str(reading.get("unit") or "CELSIUS").upper()
    suffix = {
        "CELSIUS": "°C",
        "FAHRENHEIT": "°F",
        "KELVIN": " K",
        "RANKINE": " °R",
    }.get(unit, f" {unit}")
    return f"{value:.1f}{suffix}"


def _bool_text(value: Any) -> str:
    return "sí" if value else "no"


def _importance_emoji(importance: Any) -> str:
    return {"ALERT": "🔴", "WARNING": "🟠", "INFO": "🔵"}.get(
        str(importance or "").upper(), "•"
    )


def _status_emoji(online: Any) -> str:
    return "🟢" if online else "🔴"


# ---------------------------------------------------------------------------
# Paridad
# ---------------------------------------------------------------------------

def build_parity_history(
    history: list[dict[str, Any]], settings: Settings, page: int = 0
) -> str:
    lines = ["🧮 <b>Historial de paridad</b>", ""]
    if not history:
        lines.append("La API no ha devuelto ninguna comprobación registrada.")
        return "\n".join(lines)

    ordered = sorted(
        (item for item in history if isinstance(item, dict)),
        key=lambda item: str(item.get("date") or ""),
        reverse=True,
    )
    items, page, pages = paginate(ordered, page, PARITY_PER_PAGE)
    lines.append(f"Total: {len(ordered)} · pág. {page + 1}/{pages}")
    lines.append("")
    for item in items:
        status = str(item.get("status") or "").upper()
        emoji = "✅" if status in {"COMPLETED", "SUCCESS"} else (
            "❌" if status in {"FAILED", "ERROR"} else "⏳"
        )
        when = fmt_timestamp(item.get("date"), settings.timezone) if item.get("date") else "sin fecha"
        lines.append(f"{emoji} <b>{when}</b>")
        details: list[str] = []
        if item.get("duration") is not None:
            details.append(fmt_runtime(item.get("duration")))
        if item.get("speed"):
            details.append(f"{esc(item.get('speed'))} MB/s")
        details.append("correctiva" if item.get("correcting") else "no correctiva")
        lines.append("   " + " · ".join(details))
        errors = item.get("errors")
        if errors is not None:
            marker = "⚠️" if _number(errors) else "✅"
            lines.append(f"   {marker} Errores: {esc(errors)}")
        if item.get("paused"):
            lines.append("   ⏸ Pausada")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------

def build_notification_list(
    items: list[dict[str, Any]],
    overview: dict[str, Any],
    settings: Settings,
    *,
    archived: bool = False,
    importance: str | None = None,
    page: int = 0,
    pages: int = 1,
) -> str:
    unread = overview.get("unread") or {}
    archive = overview.get("archive") or {}
    lines = ["🔔 <b>Notificaciones</b>", ""]
    lines.append(
        f"Sin leer: {unread.get('alert', 0)} alertas · "
        f"{unread.get('warning', 0)} avisos · {unread.get('info', 0)} info"
    )
    lines.append(
        f"Archivadas: {archive.get('alert', 0)} alertas · "
        f"{archive.get('warning', 0)} avisos · {archive.get('info', 0)} info"
    )
    lines.append("")
    scope = "Archivadas" if archived else "Sin leer"
    if importance:
        scope += f" · {importance}"
    lines.append(f"<b>{scope}</b> · pág. {page + 1}/{max(1, pages)}")
    lines.append("")
    if not items:
        lines.append("No hay notificaciones en esta vista. ✅")
        return "\n".join(lines).rstrip()

    for item in items:
        emoji = _importance_emoji(item.get("importance"))
        lines.append(
            f"{emoji} <b>{esc(item.get('subject') or item.get('title') or 'Notificación')}</b>"
        )
        if item.get("description"):
            lines.append(esc(shorten(str(item["description"]), 200)))
        when = fmt_when(str(item.get("timestamp") or ""), settings.timezone)
        if when != "—":
            lines.append(f"<i>{when}</i>")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_notification_detail(item: dict[str, Any], settings: Settings) -> str:
    lines = ["🔔 <b>Notificación</b>", ""]
    lines.append(f"<b>{esc(item.get('subject') or item.get('title') or '—')}</b>")
    lines.append(f"Importancia: {_importance_emoji(item.get('importance'))} "
                 f"{esc(item.get('importance') or '—')}")
    lines.append(f"Tipo: {esc(item.get('type') or '—')}")
    when = fmt_when(str(item.get("timestamp") or ""), settings.timezone)
    if when != "—":
        lines.append(f"Fecha: {when}")
    if item.get("description"):
        lines.append("")
        lines.append(esc(str(item["description"])))
    if item.get("link"):
        lines.append("")
        lines.append(f"🔗 {esc(item['link'])}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Licencia, flash, plugins y servicios
# ---------------------------------------------------------------------------

def build_license(data: dict[str, Any]) -> str:
    registration = data.get("registration") or {}
    flash = data.get("flash") or {}
    lines = ["🪪 <b>Licencia y flash</b>", ""]
    if not registration and not flash:
        lines.append("La API no ha devuelto información de licencia ni del dispositivo flash.")
        return "\n".join(lines)

    if registration:
        state = str(registration.get("state") or "").upper()
        emoji = "❌" if state in {"INVALID", "EXPIRED", "TRIAL_EXPIRED"} else "✅"
        lines.append(f"Estado: {emoji} <b>{esc(state or '—')}</b>")
        lines.append(f"Tipo: {esc(registration.get('type') or '—')}")
        if registration.get("expiration"):
            lines.append(f"Caduca: {esc(registration.get('expiration'))}")
        if registration.get("updateExpiration"):
            lines.append(f"Actualizaciones hasta: {esc(registration.get('updateExpiration'))}")
        key_file = registration.get("keyFile") or {}
        if key_file.get("location"):
            lines.append(f"Key file: <code>{esc(key_file.get('location'))}</code>")
        if state in {"TRIAL", "TRIAL_EXPIRED"}:
            lines.append("")
            lines.append("<i>Estás en periodo de prueba: revisa la fecha de caducidad.</i>")
    else:
        lines.append("Licencia: no disponible.")

    lines.append("")
    lines.append("<b>Dispositivo flash</b>")
    if flash:
        lines.append(f"Producto: {esc(flash.get('product') or '—')}")
        lines.append(f"Fabricante: {esc(flash.get('vendor') or '—')}")
        lines.append(f"GUID: <code>{esc(flash.get('guid') or '—')}</code>")
    else:
        lines.append("No se pudo leer el dispositivo flash.")
    return "\n".join(lines)


def build_plugins(plugins: list[dict[str, Any]], page: int = 0) -> str:
    lines = ["🔌 <b>Plugins</b>", ""]
    if not plugins:
        lines.append("No hay plugins instalados o la API no los ha devuelto.")
        return "\n".join(lines)
    ordered = sorted(plugins, key=lambda item: str(item.get("name") or "").lower())
    items, page, pages = paginate(ordered, page, PLUGIN_PER_PAGE)
    lines.append(f"Total: {len(ordered)} · pág. {page + 1}/{pages}")
    lines.append("")
    for plugin in items:
        name = str(plugin.get("name") or "plugin")
        badges = []
        if plugin.get("hasApiModule"):
            badges.append("API")
        if plugin.get("hasCliModule"):
            badges.append("CLI")
        suffix = f" · {', '.join(badges)}" if badges else ""
        lines.append(f"• <b>{esc(name)}</b> <code>{esc(plugin.get('version') or '—')}</code>{suffix}")
    return "\n".join(lines)


def build_services(services: list[dict[str, Any]]) -> str:
    lines = ["🧩 <b>Servicios</b>", ""]
    if not services:
        lines.append("La API no ha devuelto servicios.")
        return "\n".join(lines)
    online = sum(1 for item in services if item.get("online"))
    lines.append(f"Activos: {online}/{len(services)}")
    lines.append("")
    for service in sorted(services, key=lambda item: str(item.get("name") or "").lower()):
        name = str(service.get("name") or service.get("id") or "servicio")
        line = f"{_status_emoji(service.get('online'))} <b>{esc(name)}</b>"
        if service.get("version"):
            line += f" · {esc(service.get('version'))}"
        lines.append(line)
        uptime = _get(service, "uptime", "timestamp")
        if uptime:
            when = fmt_when(str(uptime), "Europe/Madrid")
            if when != "—":
                lines.append(f"   <i>desde {when}</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------

def build_network(data: dict[str, Any]) -> str:
    interfaces = data.get("interfaces") or []
    access_urls = data.get("access_urls") or []
    lines = ["🌐 <b>Red</b>", ""]
    if not interfaces:
        lines.append("La API no ha devuelto interfaces de red.")
    for interface in interfaces:
        name = str(interface.get("name") or "interfaz")
        state = str(interface.get("operstate") or "unknown").lower()
        emoji = "🟢" if state == "up" else ("🔴" if state == "down" else "⚪")
        line = f"{emoji} <b>{esc(name)}</b>"
        if interface.get("description"):
            line += f" · {esc(shorten(str(interface['description']), 40))}"
        lines.append(line)
        details: list[str] = []
        if interface.get("speed"):
            details.append(fmt_net_speed(interface.get("speed")))
        if interface.get("duplex"):
            details.append(str(interface.get("duplex")))
        if interface.get("mtu"):
            details.append(f"MTU {interface.get('mtu')}")
        if interface.get("vlanId"):
            details.append(f"VLAN {interface.get('vlanId')}")
        if details:
            lines.append("   " + " · ".join(esc(part) for part in details))
        for address in interface.get("ipv4Addresses") or []:
            if isinstance(address, dict) and address.get("address"):
                lines.append(f"   IPv4: <code>{esc(address['address'])}</code>")
        for address in interface.get("ipv6Addresses") or []:
            if isinstance(address, dict) and address.get("address"):
                lines.append(f"   IPv6: <code>{esc(address['address'])}</code>")
        if interface.get("macAddress"):
            lines.append(f"   MAC: <code>{esc(interface['macAddress'])}</code>")
        lines.append("")

    if access_urls:
        lines.append("<b>Accesos</b>")
        for access in access_urls:
            if not isinstance(access, dict):
                continue
            label = access.get("name") or access.get("type") or "acceso"
            url = access.get("ipv4") or access.get("ipv6")
            if url:
                lines.append(f"• {esc(str(label))}: {esc(str(url))}")
            else:
                lines.append(f"• {esc(str(label))}")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def build_log_files(files: list[dict[str, Any]]) -> str:
    lines = ["📜 <b>Logs</b>", ""]
    if not files:
        lines.append("La API no ha devuelto archivos de log.")
        return "\n".join(lines)
    lines.append("Elige un log para ver las últimas líneas.")
    lines.append("")
    for log in sorted(files, key=lambda item: str(item.get("name") or "").lower()):
        name = str(log.get("name") or log.get("path") or "log")
        size = fmt_bytes(log.get("size"))
        modified = fmt_when(str(log.get("modifiedAt") or ""), "Europe/Madrid")
        line = f"• <b>{esc(name)}</b> · {size}"
        if modified != "—":
            line += f" · {modified}"
        lines.append(line)
    return "\n".join(lines)


def build_log_content(data: dict[str, Any], *, page: int = 0) -> str:
    path = str(data.get("path") or "log")
    content = str(data.get("content") or "")
    all_lines = content.splitlines()
    total = int(_number(data.get("totalLines")) or len(all_lines))
    shown, page, pages = paginate(all_lines, page, LOG_LINES_PER_PAGE)
    lines = [f"📜 <b>{esc(path)}</b>", ""]
    if not shown:
        lines.append("<i>El log está vacío.</i>")
        return "\n".join(lines)
    first = page * LOG_LINES_PER_PAGE + 1
    last = first + len(shown) - 1
    lines.append(f"Líneas {first}–{last} de {total} · pág. {page + 1}/{pages}")
    lines.append("")
    body = "\n".join(shown)
    if len(body) > 3400:
        body = body[-3400:]
    lines.append(f"<pre>{esc(body)}</pre>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discos, shares y temperaturas
# ---------------------------------------------------------------------------

def build_smart(disk: dict[str, Any]) -> str:
    name = str(disk.get("name") or disk.get("device") or "disco")
    lines = [f"🔍 <b>{esc(name)}</b>", ""]
    if not disk:
        lines.append("No se pudo leer el disco.")
        return "\n".join(lines)
    rows = [
        ("Dispositivo", disk.get("device")),
        ("Tipo", disk.get("type")),
        ("Interfaz", disk.get("interfaceType")),
        ("Tamaño", fmt_bytes(disk.get("size")) if disk.get("size") else None),
        ("Serie", disk.get("serialNum")),
        ("Firmware", disk.get("firmwareRevision")),
        ("Temperatura", fmt_temp(disk.get("temperature")) if disk.get("temperature") else None),
        ("SMART", disk.get("smartStatus")),
        ("Girando", _bool_text(disk.get("isSpinning")) if disk.get("isSpinning") is not None else None),
    ]
    for label, value in rows:
        if value in (None, "", "—"):
            continue
        lines.append(f"{label}: <code>{esc(value)}</code>")
    partitions = [item for item in disk.get("partitions") or [] if isinstance(item, dict)]
    if partitions:
        lines.append("")
        lines.append("<b>Particiones</b>")
        for partition in partitions:
            label = partition.get("name") or "partición"
            details = []
            if partition.get("fsType"):
                details.append(str(partition.get("fsType")))
            if partition.get("size"):
                details.append(fmt_bytes(partition.get("size")))
            suffix = f" · {' · '.join(details)}" if details else ""
            lines.append(f"• {esc(label)}{esc(suffix)}")
    return "\n".join(lines)


def build_share_detail(share: dict[str, Any]) -> str:
    name = str(share.get("name") or "share")
    used, size = _number(share.get("used")), _number(share.get("size"))
    free = _number(share.get("free"))
    usage = pct(used, size)
    lines = [f"📚 <b>{esc(name)}</b>", ""]
    if share.get("comment"):
        lines.append(f"<i>{esc(share['comment'])}</i>")
        lines.append("")
    if usage is not None:
        lines.append(f"Uso: {fmt_kb(used)} / {fmt_kb(size)} ({usage:.0f}%)")
        lines.append(bar(usage))
    elif free is not None:
        lines.append(f"Libre: {fmt_kb(free)}")
    lines.append(f"Caché: {'sí' if share.get('cache') else 'no'}")
    if share.get("allocator"):
        lines.append(f"Asignador: {esc(share.get('allocator'))}")
    if share.get("splitLevel"):
        lines.append(f"Split level: {esc(share.get('splitLevel'))}")
    if share.get("floor"):
        lines.append(f"Floor: {esc(share.get('floor'))}")
    if share.get("cow"):
        lines.append(f"COW: {esc(share.get('cow'))}")
    if share.get("luksStatus"):
        lines.append(f"LUKS: {esc(share.get('luksStatus'))}")
    include = share.get("include") or []
    exclude = share.get("exclude") or []
    if include:
        lines.append(f"Incluye: {esc(', '.join(str(item) for item in include))}")
    if exclude:
        lines.append(f"Excluye: {esc(', '.join(str(item) for item in exclude))}")
    return "\n".join(lines)


def build_temperatures(data: dict[str, Any], settings: Settings) -> str:
    temperature = data.get("temperature") or {}
    network = data.get("network") or []
    sensors = temperature.get("sensors") or []
    summary = temperature.get("summary") or {}
    lines = ["🌡️ <b>Temperaturas y tráfico</b>", ""]
    if summary:
        average = _number(summary.get("average"))
        if average is not None:
            lines.append(f"Media: {average:.1f}°C")
        hottest = summary.get("hottest") or {}
        coolest = summary.get("coolest") or {}
        if hottest.get("name"):
            lines.append(
                f"Más caliente: <b>{esc(hottest.get('name'))}</b> "
                f"{_reading(hottest.get('current'))}"
            )
        if coolest.get("name"):
            lines.append(
                f"Más frío: {esc(coolest.get('name'))} {_reading(coolest.get('current'))}"
            )
        lines.append(
            f"Fuera de rango: {summary.get('warningCount', 0)} avisos · "
            f"{summary.get('criticalCount', 0)} críticos"
        )
        lines.append("")

    if sensors:
        lines.append("<b>Sensores</b>")
        for sensor in sensors:
            current = sensor.get("current") or {}
            status = str(current.get("status") or "NORMAL").upper()
            emoji = {"WARNING": "🟠", "CRITICAL": "🔴"}.get(status, "🟢")
            name = sensor.get("name") or sensor.get("type") or "sensor"
            line = f"{emoji} <b>{esc(name)}</b>: {_reading(current)}"
            warning = _number(sensor.get("warning"))
            if warning is not None:
                line += f" <i>(aviso {warning:.0f}°C)</i>"
            lines.append(line)
            low, high = sensor.get("min"), sensor.get("max")
            if isinstance(low, dict) or isinstance(high, dict):
                lines.append(f"   mín {_reading(low)} · máx {_reading(high)}")
    else:
        lines.append("No hay sensores de temperatura configurados.")
        lines.append("<i>Actívalos en Settings → Temperature Settings.</i>")

    if network:
        lines.append("")
        lines.append("<b>Tráfico de red</b>")
        for interface in network:
            name = interface.get("name") or "interfaz"
            received = _number(interface.get("bytesReceived"))
            sent = _number(interface.get("bytesSent"))
            errors = (_number(interface.get("receiveErrors")) or 0) + (
                _number(interface.get("transmitErrors")) or 0
            )
            line = f"• <b>{esc(name)}</b>: ↓ {fmt_bytes(received)} · ↑ {fmt_bytes(sent)}"
            if errors:
                line += f" · ⚠️ {errors:.0f} errores"
            lines.append(line)
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# API keys, identidad y diagnóstico
# ---------------------------------------------------------------------------

def build_api_keys(keys: list[dict[str, Any]]) -> str:
    lines = ["🔑 <b>Claves de API</b>", ""]
    if not keys:
        lines.append("No hay claves de API creadas.")
    for key in sorted(keys, key=lambda item: str(item.get("name") or "").lower()):
        name = str(key.get("name") or "clave")
        roles = ", ".join(str(role) for role in key.get("roles") or [])
        line = f"• <b>{esc(name)}</b>"
        if roles:
            line += f" · <code>{esc(roles)}</code>"
        lines.append(line)
        if key.get("description"):
            lines.append(f"   <i>{esc(shorten(str(key['description']), 120))}</i>")
        if key.get("createdAt"):
            lines.append(f"   Creada: {esc(str(key.get('createdAt')))}")
    lines.append("")
    lines.append("<i>El bot solo crea claves con rol VIEWER (solo lectura).</i>")
    return "\n".join(lines)


def build_identity(server: dict[str, Any]) -> str:
    lines = ["🏷️ <b>Identidad del servidor</b>", ""]
    if not server:
        lines.append("La API no ha devuelto la identidad del servidor.")
        return "\n".join(lines)
    lines.append(f"Nombre: <b>{esc(server.get('name') or '—')}</b>")
    lines.append(f"Comentario: {esc(server.get('comment') or '—')}")
    if server.get("id"):
        lines.append(f"ID: <code>{esc(server.get('id'))}</code>")
    return "\n".join(lines)


def build_diagnostics(
    snapshot: Snapshot,
    settings: Settings,
    problems: list[Any],
    *,
    log_tail: str | None = None,
) -> str:
    info = snapshot.info or {}
    os_info = info.get("os") or {}
    core = _get(info, "versions", "core", default={}) or {}
    array = snapshot.array or {}
    lines = ["🩺 <b>Diagnóstico</b>", ""]
    lines.append(f"Servidor: <b>{esc(os_info.get('hostname') or 'Unraid')}</b>")
    lines.append(f"Unraid: {esc(core.get('unraid') or '—')} · API: {esc(core.get('api') or '—')}")
    lines.append(f"Array: {esc(array.get('state') or '—')}")
    if snapshot.fetched_at:
        lines.append(f"Consulta: {fmt_timestamp(snapshot.fetched_at.isoformat(), settings.timezone)}")
    lines.append("")
    if problems:
        lines.append(f"<b>Incidencias ({len(problems)})</b>")
        for problem in problems[:10]:
            title = getattr(problem, "title", str(problem))
            detail = getattr(problem, "detail", "")
            lines.append(f"• <b>{esc(title)}</b>")
            if detail:
                lines.append(f"   {esc(detail)}")
    else:
        lines.append("✅ No se han detectado incidencias.")
    if log_tail:
        lines.append("")
        lines.append("<b>Últimas líneas del syslog</b>")
        tail = log_tail[-2500:]
        lines.append(f"<pre>{esc(tail)}</pre>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Docker ampliado
# ---------------------------------------------------------------------------

def build_docker_extras(extras: dict[str, Any]) -> str:
    updates = [item for item in extras.get("updates") or [] if isinstance(item, dict)]
    conflicts = extras.get("conflicts") or {}
    lines = ["🐳 <b>Docker · mantenimiento</b>", ""]
    pending = [
        item for item in updates
        if str(item.get("updateStatus") or "").upper()
        in {"UPDATE_AVAILABLE", "REBUILD_READY"}
    ]
    lines.append(f"Actualizaciones pendientes: <b>{len(pending)}</b>")
    for item in pending[:15]:
        name = item.get("name") or "contenedor"
        state = str(item.get("updateStatus") or "").upper()
        emoji = "🔁" if state == "REBUILD_READY" else "⬆️"
        lines.append(f"{emoji} {esc(name)}")
    if len(pending) > 15:
        lines.append(f"… y {len(pending) - 15} más.")

    container_ports = conflicts.get("containerPorts") or []
    lan_ports = conflicts.get("lanPorts") or []
    if container_ports or lan_ports:
        lines.append("")
        lines.append("⚠️ <b>Conflictos de puertos</b>")
        for conflict in container_ports[:8]:
            port = conflict.get("privatePort")
            names = ", ".join(
                str(item.get("name") or "") for item in conflict.get("containers") or []
            )
            lines.append(f"• Interno {esc(port)} · {esc(names or '—')}")
        for conflict in lan_ports[:8]:
            lines.append(
                f"• {esc(conflict.get('lanIpPort'))} · "
                f"{esc(', '.join(str(item.get('name') or '') for item in conflict.get('containers') or []))}"
            )
    else:
        lines.append("")
        lines.append("✅ Sin conflictos de puertos detectados.")
    return "\n".join(lines)


def build_docker_sizes(extras: dict[str, Any]) -> str:
    """Tamaños de imagen, capa escribible y logs por contenedor."""
    containers = [item for item in extras.get("containers") or [] if isinstance(item, dict)]
    lines = ["🐳 <b>Docker · tamaños</b>", ""]
    if not containers:
        lines.append("No hay datos de tamaño disponibles.")
        return "\n".join(lines)
    total_log = 0.0
    rows = []
    for container in containers:
        names = container.get("names") or []
        name = str(names[0]).lstrip("/") if names else str(container.get("id") or "contenedor")
        log_size = _number(container.get("sizeLog")) or 0.0
        total_log += log_size
        rows.append(
            (
                name,
                _number(container.get("sizeRootFs")),
                _number(container.get("sizeRw")),
                log_size,
                bool(container.get("isOrphaned")),
                bool(container.get("isRebuildReady")),
            )
        )
    for name, image, writable, logs, orphaned, rebuild in sorted(
        rows, key=lambda item: item[3], reverse=True
    ):
        line = f"• <b>{esc(name)}</b>"
        if image is not None:
            line += f" · imagen {fmt_bytes(image)}"
        if writable is not None:
            line += f" · RW {fmt_bytes(writable)}"
        line += f" · log {fmt_bytes(logs)}"
        if orphaned:
            line += " · 👻 huérfano"
        if rebuild:
            line += " · 🔁 rebuild"
        lines.append(line)
    lines.append("")
    lines.append(f"Total de logs: <b>{fmt_bytes(total_log)}</b>")
    return "\n".join(lines)
