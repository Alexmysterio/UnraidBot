"""Construcción de los mensajes HTML de cada pantalla."""

from __future__ import annotations

import re
from typing import Any

from .config import Settings
from .formatting import (
    array_emoji,
    bar,
    container_emoji,
    disk_emoji,
    docker_state_text,
    esc,
    fmt_array_disk_size,
    fmt_bytes,
    fmt_epoch,
    fmt_kb,
    fmt_net_speed,
    fmt_pct,
    fmt_runtime,
    fmt_temp,
    fmt_timestamp,
    fmt_uptime,
    fmt_when,
    pct,
    severity_emoji,
    shorten,
    sparkline,
    vm_emoji,
    vm_state_text,
)
from .health import Problem
from .search import KIND_EMOJI, KIND_LABELS, SearchHit
from .unraid import Snapshot

ARRAY_STATE_TEXT = {
    "STARTED": "iniciado",
    "STOPPED": "detenido",
    "NEW_ARRAY": "nuevo",
    "RECON_DISK": "reconstruyendo disco",
    "DISABLE_DISK": "disco deshabilitado",
    "SWAP_DSBL": "intercambiando disco",
    "INVALID_EXPANSION": "expansión inválida",
    "PARITY_NOT_BIGGEST": "paridad no es el disco mayor",
    "TOO_MANY_MISSING_DISKS": "demasiados discos ausentes",
    "NEW_DISK_TOO_SMALL": "disco nuevo demasiado pequeño",
    "NO_DATA_DISKS": "sin discos de datos",
}

ERROR_LABELS = {
    "array": "array",
    "metrics": "métricas",
    "ups": "UPS",
    "notifications": "notificaciones",
    "docker": "Docker",
    "vms": "VMs",
    "info": "información del sistema",
    "shares": "shares",
    "physical_disks": "discos físicos",
}


# ---------------------------------------------------------------------------
# Utilidades internas
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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _array_disks(array: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("parities", "disks", "caches"):
        value = array.get(key)
        if isinstance(value, list):
            result.extend(item for item in value if isinstance(item, dict))
    return result


def _disk_used_pct(disk: dict[str, Any]) -> float | None:
    return pct(disk.get("fsUsed"), disk.get("fsSize"))


def _array_disk_line(disk: dict[str, Any]) -> str:
    name = disk.get("name") or disk.get("device") or "disco"
    parts = [f"{disk_emoji(disk.get('status'), disk.get('color'))} <b>{esc(name)}</b>"]
    if disk.get("size"):
        parts.append(fmt_array_disk_size(disk.get("size")))
    used = _disk_used_pct(disk)
    if used is not None:
        parts.append(f"{used:.0f}%")
    if disk.get("temp"):
        parts.append(fmt_temp(disk.get("temp")))
    if disk.get("isSpinning") is False:
        parts.append("💤")
    status = disk.get("status")
    if status and status != "DISK_OK":
        parts.append(f"<code>{esc(status)}</code>")
    return " · ".join(parts)


def _container_name(container: dict[str, Any]) -> str:
    names = container.get("names") or []
    if names:
        return str(names[0]).lstrip("/")
    return "contenedor"


def _vm_name(vm: dict[str, Any]) -> str:
    return str(vm.get("name") or vm.get("id") or "VM")


def _server_name(snapshot: Snapshot) -> str:
    return str(_get(snapshot.info, "os", "hostname", default="Unraid"))


def _format_error(error: str) -> str:
    return f"<code>{esc(shorten(error, 280))}</code>"


def _errors_footer(snapshot: Snapshot) -> list[str]:
    if not snapshot.errors:
        return []
    names = [ERROR_LABELS.get(key, key) for key in snapshot.errors]
    return ["", f"⚠️ Sin datos de: {esc(', '.join(names))}."]


def paginate(items: list[Any], page: int, per_page: int) -> tuple[list[Any], int, int]:
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    return items[start : start + per_page], page, total_pages


# ---------------------------------------------------------------------------
# Estado general
# ---------------------------------------------------------------------------

def build_status(snapshot: Snapshot, settings: Settings, problems: list[Problem]) -> str:
    info = snapshot.info or {}
    os_info = info.get("os") or {}
    core = _get(info, "versions", "core", default={}) or {}
    name = _server_name(snapshot)

    lines: list[str] = []
    title = f"🖥️ <b>{esc(name)}</b>"
    if core.get("unraid"):
        title += f" · Unraid {esc(core['unraid'])}"
    lines.append(title)
    lines.append("")

    if not snapshot.array and not snapshot.info:
        lines.append("🔴 <b>Sin conexión con la API de Unraid</b>")
        if snapshot.errors:
            lines.append(_format_error(next(iter(snapshot.errors.values()))))
        lines.append("")
        lines.append("Revisa <code>UNRAID_API_URL</code>, la clave y el servicio <code>unraid-api</code>.")
        return "\n".join(lines)

    array = snapshot.array or {}
    state = array.get("state")
    capacity = _get(array, "capacity", "kilobytes", default={}) or {}
    used_kb, total_kb = _number(capacity.get("used")), _number(capacity.get("total"))
    usage = pct(used_kb, total_kb)
    array_line = f"{array_emoji(state)} <b>Array {esc(ARRAY_STATE_TEXT.get(state or '', state or 'desconocido'))}</b>"
    if usage is not None:
        array_line += f" · {fmt_kb(used_kb)} / {fmt_kb(total_kb)} ({usage:.0f}%)"
    lines.append(array_line)

    if array:
        parity = array.get("parityCheckStatus") or {}
        if parity.get("running"):
            parity_line = (
                f"🧮 Paridad: {parity.get('progress') or 0}%"
                f" · {esc(parity.get('speed') or '—')}"
                f" · {parity.get('errors') or 0} errores"
            )
        elif parity.get("status") == "COMPLETED":
            parity_line = f"🧮 Paridad: OK {fmt_when(parity.get('date'), settings.timezone)}"
            if parity.get("errors"):
                parity_line += f" · {parity['errors']} errores"
        elif parity.get("status") == "NEVER_RUN":
            parity_line = "🧮 Paridad: nunca comprobada"
        else:
            parity_line = f"🧮 Paridad: {esc(parity.get('status') or 'desconocida')}"
        lines.append(parity_line)

    cpu = info.get("cpu") or {}
    metrics = snapshot.metrics or {}
    cpu_load = _get(metrics, "cpu", "percentTotal")
    cpu_parts: list[str] = []
    if cpu_load is not None:
        cpu_parts.append(fmt_pct(cpu_load))
    temps = _as_list(_get(info, "cpu", "packages", "temp", default=[]))
    valid_temps = [value for value in (_number(item) for item in temps) if value is not None]
    if valid_temps:
        cpu_parts.append(fmt_temp(max(valid_temps)))
    if cpu.get("brand"):
        cpu_parts.append(esc(shorten(str(cpu["brand"]), 38)))
    if cpu_parts:
        lines.append("🧠 CPU " + " · ".join(cpu_parts))

    memory = metrics.get("memory") or {}
    mem_total, mem_used = _number(memory.get("total")), _number(memory.get("used"))
    if mem_total:
        mem_pct = _number(memory.get("percentTotal"))
        if mem_pct is None:
            mem_pct = pct(mem_used, mem_total)
        lines.append(f"💾 RAM {fmt_bytes(mem_used)} / {fmt_bytes(mem_total)} ({fmt_pct(mem_pct)})")
    elif info.get("memory"):
        layout = _get(info, "memory", "layout", default=[]) or []
        total = sum(_number(module.get("size")) or 0 for module in layout if isinstance(module, dict))
        if total:
            lines.append(f"💾 RAM {fmt_bytes(total)} en {len(layout)} módulo(s)")

    containers = snapshot.docker
    if containers is not None:
        running = sum(1 for item in containers if item.get("state") == "RUNNING")
        updates = sum(1 for item in containers if item.get("isUpdateAvailable"))
        paused = sum(1 for item in containers if item.get("state") == "PAUSED")
        docker_line = f"🐳 Docker {running}/{len(containers)} activos"
        if paused:
            docker_line += f" · {paused} pausados"
        if updates:
            docker_line += f" · {updates} actualizaciones"
        lines.append(docker_line)

    vms = snapshot.vms
    if vms is not None:
        running_vms = sum(1 for item in vms if item.get("state") in {"RUNNING", "IDLE"})
        lines.append(f"🖥️ VMs {running_vms}/{len(vms)} en marcha")

    ups = snapshot.ups or []
    if ups:
        unit = ups[0]
        battery = unit.get("battery") or {}
        ups_name = shorten(str(unit.get("name") or "UPS"), 24)
        ups_line = f"🔋 UPS {esc(ups_name)} · {esc(unit.get('status') or 'desconocido')}"
        if battery.get("chargeLevel") is not None:
            ups_line += f" · {battery['chargeLevel']}%"
        if battery.get("estimatedRuntime") is not None:
            ups_line += f" · {fmt_runtime(battery.get('estimatedRuntime'))}"
        lines.append(ups_line)

    notifications = snapshot.notifications or {}
    overview = notifications.get("overview") or {}
    unread = overview.get("unread") or {}
    if unread:
        alerts = int(unread.get("alert") or 0)
        warnings = int(unread.get("warning") or 0)
        if alerts or warnings:
            lines.append(f"🔔 {alerts} alertas · {warnings} avisos sin leer")
        else:
            lines.append("🔔 Sin notificaciones nuevas")

    network = info.get("primaryNetwork") or {}
    if network:
        ip = network.get("ipAddress") or _get(network, "ipv4Addresses", default=[{}])
        if isinstance(ip, list):
            ip = ip[0].get("address") if ip and isinstance(ip[0], dict) else None
        net_line = "🌐 " + esc(ip or "sin IP")
        if network.get("speed"):
            net_line += f" · {fmt_net_speed(network.get('speed'))}"
        lines.append(net_line)

    uptime = fmt_uptime(os_info.get("uptime"))
    if uptime != "—":
        lines.append(f"⏱️ En marcha desde hace {uptime}")

    if problems:
        lines.append("")
        lines.append("⚠️ <b>Incidencias</b>")
        for problem in problems[:5]:
            lines.append(f"{severity_emoji(problem.severity)} {esc(problem.title)}")
        if len(problems) > 5:
            lines.append(f"… y {len(problems) - 5} más")

    lines.extend(_errors_footer(snapshot))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discos
# ---------------------------------------------------------------------------

def build_disks(snapshot: Snapshot) -> str:
    array = snapshot.array or {}
    if not array:
        lines = ["💾 <b>Discos</b>", ""]
        lines.append("🔴 No se pudo obtener el estado del array.")
        if snapshot.errors.get("array"):
            lines.append(_format_error(snapshot.errors["array"]))
        return "\n".join(lines)

    lines = ["💾 <b>Discos y almacenamiento</b>", ""]
    capacity = _get(array, "capacity", "kilobytes", default={}) or {}
    used_kb, total_kb = _number(capacity.get("used")), _number(capacity.get("total"))
    usage = pct(used_kb, total_kb)
    if usage is not None:
        lines.append(f"Capacidad: {fmt_kb(used_kb)} / {fmt_kb(total_kb)} ({usage:.0f}%)")
        lines.append(bar(usage))
        lines.append("")

    sections = (
        ("Paridad", array.get("parities") or []),
        ("Datos", array.get("disks") or []),
        ("Caché / pools", array.get("caches") or []),
    )
    for title, disks in sections:
        if not disks:
            continue
        lines.append(f"<b>{title}</b>")
        for disk in disks:
            if isinstance(disk, dict):
                lines.append(_array_disk_line(disk))
        lines.append("")

    total_disks = sum(len(section[1]) for section in sections)
    lines.append(f"Total: {total_disks} dispositivos · toca un disco para ver el detalle.")
    lines.extend(_errors_footer(snapshot))
    return "\n".join(lines)


def build_disk_detail(disk: dict[str, Any], settings: Settings) -> str:
    name = disk.get("name") or disk.get("device") or "disco"
    lines = [f"💾 <b>{esc(name)}</b>", ""]
    lines.append(f"Estado: {disk_emoji(disk.get('status'), disk.get('color'))} <code>{esc(disk.get('status') or '—')}</code>")
    lines.append(f"Dispositivo: <code>{esc(disk.get('device') or '—')}</code>")
    lines.append(f"Tamaño: {fmt_array_disk_size(disk.get('size'))}")

    fs_type = disk.get("fsType")
    used, size = _number(disk.get("fsUsed")), _number(disk.get("fsSize"))
    usage = pct(used, size)
    if fs_type or usage is not None:
        text = f"Sistema de archivos: {esc(fs_type or '—')}"
        if usage is not None:
            text += f" · {fmt_kb(used)} / {fmt_kb(size)} ({usage:.0f}%)"
            text += f"\n{bar(usage)}"
        lines.append(text)

    lines.append(f"Temperatura: {fmt_temp(disk.get('temp'))}")
    rotational = disk.get("rotational")
    kind = "HDD" if rotational else ("SSD" if rotational is False else "—")
    transport = disk.get("transport") or disk.get("format")
    lines.append(f"Tipo: {kind}" + (f" · {esc(transport)}" if transport else ""))
    lines.append(f"Errores de E/S: {disk.get('numErrors', 0)}")
    if disk.get("isSpinning") is not None:
        lines.append(f"En reposo: {'no' if disk.get('isSpinning') else 'sí 💤'}")
    if disk.get("color"):
        lines.append(f"Color: <code>{esc(disk.get('color'))}</code>")
    if disk.get("comment"):
        lines.append(f"Comentario: {esc(shorten(str(disk['comment']), 200))}")
    lines.append("")
    lines.append(
        f"Umbrales configurados: aviso {settings.disk_temp_warning}°C · "
        f"crítico {settings.disk_temp_critical}°C."
    )
    lines.append("<i>El detalle SMART completo está en el WebGUI (Main → disco → SMART).</i>")
    return "\n".join(lines)


def build_physical_disks(
    disks: list[dict[str, Any]], page: int = 0, per_page: int = 10
) -> str:
    sorted_disks = sorted(disks, key=lambda item: str(item.get("device") or ""))
    items, page, pages = paginate(sorted_disks, page, per_page)
    lines = ["🔍 <b>Discos físicos</b>", ""]
    if not disks:
        lines.append("No se han detectado discos físicos.")
        return "\n".join(lines)

    lines.append(f"Total: {len(disks)} · pág. {page + 1}/{pages}")
    lines.append("")
    for disk in items:
        name = disk.get("device") or disk.get("name") or "disco"
        size = fmt_bytes(disk.get("size"))
        temp = fmt_temp(disk.get("temperature"))
        kind = disk.get("type") or "—"
        smart = disk.get("smartStatus") or "UNKNOWN"
        smart_emoji = "🟢" if smart == "OK" else "🟡"
        lines.append(f"{smart_emoji} <b>{esc(name)}</b> · {size} · {temp} · {esc(kind)}")
        model = " ".join(
            part for part in (disk.get("name"), disk.get("vendor")) if part and part != name
        )
        if model:
            lines.append(f"   Modelo: {esc(shorten(model, 90))}")
        details = [f"SMART: {esc(smart)}", f"Interfaz: {esc(disk.get('interfaceType') or '—')}"]
        if disk.get("serialNum"):
            details.append(f"Serie: {esc(disk.get('serialNum'))}")
        lines.append("   " + " · ".join(details))
        if disk.get("isSpinning") is False:
            lines.append("   💤 En reposo")
        lines.append("")

    lines.append("<i>SMART se consulta a la API de Unraid; para atributos completos usa smartctl.</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

def sort_containers(containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"RUNNING": 0, "PAUSED": 1, "EXITED": 2}
    return sorted(
        containers,
        key=lambda item: (order.get(str(item.get("state")), 3), _container_name(item).lower()),
    )


def build_docker_list(containers: list[dict[str, Any]], page: int, per_page: int) -> str:
    sorted_items = sort_containers(containers)
    items, page, pages = paginate(sorted_items, page, per_page)
    running = sum(1 for item in containers if item.get("state") == "RUNNING")
    lines = [
        f"🐳 <b>Docker</b> · {running}/{len(containers)} activos · pág. {page + 1}/{pages}",
        "",
    ]
    if not containers:
        lines.append("No hay contenedores Docker.")
        return "\n".join(lines)

    for container in items:
        name = _container_name(container)
        state = container_emoji(container.get("state"))
        status = shorten(str(container.get("status") or docker_state_text(container.get("state"))), 60)
        update = " ⬆️" if container.get("isUpdateAvailable") else ""
        lines.append(f"{state} <b>{esc(name)}</b>{update}")
        lines.append(f"   <i>{esc(status)}</i>")
    lines.append("")
    lines.append("Toca un contenedor para gestionarlo.")
    return "\n".join(lines)


def build_docker_detail(container: dict[str, Any], logs: list[dict[str, Any]] | None = None) -> str:
    name = _container_name(container)
    state = container.get("state")
    lines = [f"🐳 <b>{esc(name)}</b>  {container_emoji(state)}", ""]
    lines.append(f"Estado: <b>{esc(docker_state_text(state))}</b>")
    if container.get("status"):
        lines.append(f"Detalle: <i>{esc(shorten(str(container['status']), 120))}</i>")
    if container.get("image"):
        lines.append(f"Imagen: <code>{esc(shorten(str(container['image']), 100))}</code>")
    network = _get(container, "hostConfig", "networkMode")
    if network:
        lines.append(f"Red: <code>{esc(network)}</code>")

    ports = []
    for port in container.get("ports") or []:
        if not isinstance(port, dict):
            continue
        private = port.get("privatePort")
        public = port.get("publicPort")
        kind = port.get("type") or "TCP"
        if public and private:
            ports.append(f"{public}→{private}/{kind}")
        elif private:
            ports.append(f"{private}/{kind}")
    if ports:
        lines.append(f"Puertos: <code>{esc(', '.join(ports[:8]))}</code>")
        if len(ports) > 8:
            lines.append(f"… y {len(ports) - 8} más")

    lines.append(f"Autostart: {'sí' if container.get('autoStart') else 'no'}")
    if container.get("isUpdateAvailable"):
        lines.append("Actualización: ⬆️ disponible")
    elif container.get("isUpdateAvailable") is False:
        lines.append("Actualización: al día")
    container_id = str(container.get("id") or "")
    if container_id:
        short = container_id.split(":")[-1][:12]
        lines.append(f"ID: <code>{esc(short)}</code>")

    if logs is not None:
        lines.append("")
        lines.append("<b>Últimas líneas de log</b>")
        lines.append(_format_logs(logs))
    return "\n".join(lines)


def _format_logs(lines: list[dict[str, Any]], limit: int = 2800) -> str:
    if not lines:
        return "<i>Sin líneas de log disponibles.</i>"
    text_parts = []
    for line in lines[-40:]:
        if isinstance(line, dict):
            message = str(line.get("message") or "").rstrip()
        else:
            message = str(line).rstrip()
        if message:
            text_parts.append(message)
    text = "\n".join(text_parts)
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    if len(text) > limit:
        text = "…\n" + text[-limit:]
    return f"<pre>{esc(text)}</pre>"


# ---------------------------------------------------------------------------
# VMs
# ---------------------------------------------------------------------------

def build_vm_list(vms: list[dict[str, Any]]) -> str:
    running = sum(1 for item in vms if item.get("state") in {"RUNNING", "IDLE"})
    lines = [f"🖥️ <b>Máquinas virtuales</b> · {running}/{len(vms)} en marcha", ""]
    if not vms:
        lines.append("No hay máquinas virtuales definidas.")
        return "\n".join(lines)
    for vm in vms:
        lines.append(f"{vm_emoji(vm.get('state'))} <b>{esc(_vm_name(vm))}</b> · {esc(vm_state_text(vm.get('state')))}")
    lines.append("")
    lines.append("Toca una VM para gestionarla.")
    return "\n".join(lines)


def build_vm_detail(vm: dict[str, Any]) -> str:
    lines = [f"🖥️ <b>{esc(_vm_name(vm))}</b> {vm_emoji(vm.get('state'))}", ""]
    lines.append(f"Estado: <b>{esc(vm_state_text(vm.get('state')))}</b>")
    lines.append(f"Estado técnico: <code>{esc(vm.get('state') or '—')}</code>")
    if vm.get("id"):
        raw = str(vm["id"]).split(":")[-1]
        lines.append(f"UUID: <code>{esc(raw)}</code>")
    lines.append("")
    lines.append("<i>El apagado normal envía una señal ACPI. Si la VM no responde, usa «Forzar apagado».</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sistema
# ---------------------------------------------------------------------------

def build_system_menu(snapshot: Snapshot | None) -> str:
    lines = ["⚙️ <b>Sistema</b>", ""]
    if snapshot is not None:
        array = snapshot.array or {}
        state = array.get("state")
        if array:
            lines.append(f"Array: {array_emoji(state)} {esc(ARRAY_STATE_TEXT.get(state or '', state or '—'))}")
        parity = array.get("parityCheckStatus") or {}
        if parity:
            if parity.get("running"):
                lines.append(f"Paridad: {parity.get('progress') or 0}% ({parity.get('errors') or 0} errores)")
            else:
                lines.append(f"Paridad: {esc(str(parity.get('status') or '—'))}")
        if snapshot.ups:
            lines.append(f"UPS: {esc(snapshot.ups[0].get('status') or '—')}")
        unread = _get(snapshot.notifications, "overview", "unread", default={}) or {}
        if unread:
            lines.append(
                f"Notificaciones: {unread.get('alert', 0)} alertas · "
                f"{unread.get('warning', 0)} avisos · {unread.get('info', 0)} info"
            )
        lines.append("")
    lines.append("Elige una sección:")
    return "\n".join(lines)


def build_array(snapshot: Snapshot, settings: Settings) -> str:
    array = snapshot.array or {}
    if not array:
        return "🧱 <b>Array</b>\n\n🔴 No se pudo obtener el estado del array.\n" + (
            _format_error(snapshot.errors.get("array", "")) if snapshot.errors.get("array") else ""
        )

    state = array.get("state")
    capacity = _get(array, "capacity", "kilobytes", default={}) or {}
    used, total = _number(capacity.get("used")), _number(capacity.get("total"))
    usage = pct(used, total)
    lines = ["🧱 <b>Array</b>", ""]
    lines.append(f"Estado: {array_emoji(state)} <b>{esc(ARRAY_STATE_TEXT.get(state or '', state or 'desconocido'))}</b>")
    if usage is not None:
        lines.append(f"Capacidad: {fmt_kb(used)} / {fmt_kb(total)} ({usage:.0f}%)")
        lines.append(bar(usage))
    lines.append(f"Discos de datos: {len(array.get('disks') or [])}")
    lines.append(f"Discos de paridad: {len(array.get('parities') or [])}")
    lines.append(f"Discos de caché: {len(array.get('caches') or [])}")

    parity = array.get("parityCheckStatus") or {}
    lines.append("")
    lines.append("<b>Última paridad</b>")
    lines.append(
        f"Estado: {esc(str(parity.get('status') or '—'))}"
        + (f" · {parity.get('progress')}%" if parity.get("running") else "")
    )
    if parity.get("date"):
        lines.append(f"Fecha: {fmt_timestamp(parity.get('date'), settings.timezone)}")
    if parity.get("duration"):
        lines.append(f"Duración: {fmt_runtime(parity.get('duration'))}")
    lines.append(f"Errores: {parity.get('errors', 0)}")
    return "\n".join(lines)


def build_parity(snapshot: Snapshot, settings: Settings) -> str:
    array = snapshot.array or {}
    parity = array.get("parityCheckStatus") or {}
    lines = ["🧮 <b>Comprobación de paridad</b>", ""]
    if not parity:
        lines.append("No hay información de paridad disponible.")
        return "\n".join(lines)

    running = bool(parity.get("running"))
    paused = bool(parity.get("paused"))
    status = parity.get("status")
    lines.append(f"Estado: <b>{esc(str(status or '—'))}</b>" + (" · pausada" if paused else ""))
    if running or paused:
        progress = _number(parity.get("progress")) or 0
        lines.append(f"Progreso: {progress:.0f}%")
        lines.append(bar(progress))
        if parity.get("speed"):
            lines.append(f"Velocidad: {esc(parity.get('speed'))}")
        lines.append(f"Corrigiendo: {'sí' if parity.get('correcting') else 'no'}")
    if parity.get("errors") is not None:
        lines.append(f"Errores: {parity.get('errors')}")
    if parity.get("date"):
        lines.append(f"Última: {fmt_timestamp(parity.get('date'), settings.timezone)}")
    if parity.get("duration"):
        lines.append(f"Duración: {fmt_runtime(parity.get('duration'))}")
    lines.append("")
    lines.append("<i>Una comprobación correctiva escribe en paridad; la no correctiva solo lee.</i>")
    return "\n".join(lines)


def build_ups(snapshot: Snapshot) -> str:
    lines = ["🔋 <b>UPS</b>", ""]
    if not snapshot.ups:
        lines.append("No hay ningún UPS configurado o visible para la API.")
        lines.append("Puedes configurarlo en <i>Settings → UPS Settings</i>.")
        return "\n".join(lines)

    for unit in snapshot.ups:
        battery = unit.get("battery") or {}
        power = unit.get("power") or {}
        lines.append(f"<b>{esc(unit.get('name') or unit.get('model') or 'UPS')}</b>")
        lines.append(f"Modelo: {esc(unit.get('model') or '—')}")
        lines.append(f"Estado: {esc(unit.get('status') or '—')}")
        charge = battery.get("chargeLevel")
        lines.append(
            f"Batería: {fmt_pct(charge)}"
            + (f" · salud {esc(battery.get('health'))}" if battery.get("health") else "")
        )
        if battery.get("estimatedRuntime") is not None:
            lines.append(f"Autonomía: {fmt_runtime(battery.get('estimatedRuntime'))}")
        load_percentage = _number(power.get("loadPercentage"))
        if load_percentage is not None:
            load = f"Carga: {load_percentage:.0f}%"
            current_power = _number(power.get("currentPower"))
            if current_power is not None:
                load += f" · {current_power:.0f} W"
            lines.append(load)
        input_voltage = _number(power.get("inputVoltage"))
        output_voltage = _number(power.get("outputVoltage"))
        if input_voltage is not None:
            voltage = f"Voltaje: {input_voltage:.1f} V entrada"
            if output_voltage is not None:
                voltage += f" · {output_voltage:.1f} V salida"
            lines.append(voltage)
        lines.append("")
    return "\n".join(lines).rstrip()


def build_notifications(
    snapshot: Snapshot, settings: Settings, page: int = 0, per_page: int = 5
) -> str:
    notifications = snapshot.notifications or {}
    overview = notifications.get("overview") or {}
    unread = overview.get("unread") or {}
    lines = ["🔔 <b>Notificaciones</b>", ""]
    if unread:
        lines.append(
            f"Sin leer: {unread.get('alert', 0)} alertas · "
            f"{unread.get('warning', 0)} avisos · {unread.get('info', 0)} info"
        )
        lines.append("")

    items = notifications.get("warningsAndAlerts") or []
    if not items:
        lines.append("No hay alertas ni avisos pendientes. ✅")
        return "\n".join(lines)

    shown, page, pages = paginate(items, page, per_page)
    lines.append(f"Total: {len(items)} · pág. {page + 1}/{pages}")
    lines.append("")
    for item in shown:
        importance = str(item.get("importance") or "").upper()
        emoji = "🔴" if importance == "ALERT" else "🟠"
        lines.append(f"{emoji} <b>{esc(item.get('subject') or item.get('title') or 'Aviso')}</b>")
        if item.get("description"):
            lines.append(esc(shorten(str(item["description"]), 220)))
        when = fmt_when(str(item.get("timestamp") or ""), settings.timezone)
        if when != "—":
            lines.append(f"<i>{when}</i>")
        lines.append("")

    return "\n".join(lines).rstrip()


def build_shares(shares: list[dict[str, Any]]) -> str:
    lines = ["📚 <b>Shares</b>", ""]
    if not shares:
        lines.append("No se han encontrado shares de usuario.")
        return "\n".join(lines)
    for share in sorted(shares, key=lambda item: str(item.get("name") or "").lower())[:25]:
        used, total = _number(share.get("used")), _number(share.get("size"))
        usage = pct(used, total)
        line = f"<b>{esc(share.get('name') or '—')}</b>"
        if usage is not None:
            line += f" · {fmt_kb(used)} / {fmt_kb(total)} ({usage:.0f}%)"
        if share.get("cache"):
            line += " · caché"
        lines.append(line)
        if usage is not None:
            lines.append(bar(usage, width=8))
    if len(shares) > 25:
        lines.append(f"… y {len(shares) - 25} shares más.")
    return "\n".join(lines)


def build_info(snapshot: Snapshot, settings: Settings) -> str:
    info = snapshot.info or {}
    if not info:
        return "ℹ️ <b>Información</b>\n\nNo se pudo obtener la información del servidor."

    os_info = info.get("os") or {}
    core = _get(info, "versions", "core", default={}) or {}
    packages = _get(info, "versions", "packages", default={}) or {}
    cpu = info.get("cpu") or {}
    board = info.get("baseboard") or {}
    system = info.get("system") or {}
    network = info.get("primaryNetwork") or {}

    lines = ["ℹ️ <b>Información del servidor</b>", ""]
    lines.append(f"Host: <b>{esc(os_info.get('hostname') or '—')}</b>")
    lines.append(f"Unraid: {esc(core.get('unraid') or '—')}")
    lines.append(f"API: {esc(core.get('api') or '—')} · Kernel: {esc(core.get('kernel') or os_info.get('kernel') or '—')}")
    if packages.get("docker"):
        lines.append(f"Docker: {esc(packages.get('docker'))}")
    if system.get("manufacturer") or system.get("model"):
        lines.append(f"Equipo: {esc(system.get('manufacturer') or '')} {esc(system.get('model') or '')}".strip())
    if board.get("manufacturer") or board.get("model"):
        lines.append(f"Placa: {esc(board.get('manufacturer') or '')} {esc(board.get('model') or '')}".strip())
    if cpu.get("brand"):
        cores = cpu.get("cores")
        threads = cpu.get("threads")
        suffix = f" ({cores}C/{threads}T)" if cores and threads else ""
        lines.append(f"CPU: {esc(cpu.get('brand'))}{suffix}")
    memory = (snapshot.metrics or {}).get("memory") or {}
    if memory.get("total"):
        lines.append(f"RAM: {fmt_bytes(memory.get('total'))}")
    if network:
        ip = network.get("ipAddress")
        line = f"Red: {esc(network.get('name') or '—')} · {esc(ip or 'sin IP')}"
        if network.get("speed"):
            line += f" · {fmt_net_speed(network.get('speed'))}"
        lines.append(line)
    uptime = fmt_uptime(os_info.get("uptime"))
    if uptime != "—":
        lines.append(f"Arranque: hace {uptime}")
    if info.get("time"):
        lines.append(f"Hora del servidor: {fmt_timestamp(info.get('time'), settings.timezone)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

def build_alerts(
    settings: Settings,
    subscribed: bool,
    problems: list[Problem],
    muted_until: float | None = None,
) -> str:
    lines = ["🔔 <b>Alertas automáticas</b>", ""]
    lines.append(f"Este chat: {'✅ activadas' if subscribed else '⚪ desactivadas'}")
    if muted_until is not None:
        lines.append(f"🔕 Silenciado hasta el {fmt_epoch(muted_until, settings.timezone)}")
    lines.append(f"Revisión: cada {fmt_runtime(settings.alert_interval_seconds)}")
    lines.append(f"Repetición de un aviso activo: cada {fmt_runtime(settings.alert_repeat_minutes * 60)}")
    lines.append("")
    lines.append("<b>Umbrales</b>")
    lines.append(
        f"• Disco: aviso {settings.disk_temp_warning}°C · crítico {settings.disk_temp_critical}°C"
    )
    lines.append(f"• CPU: {settings.cpu_temp_warning}°C")
    lines.append(f"• RAM: {settings.memory_warning}%")
    lines.append(f"• Array: {settings.array_usage_warning}%")
    lines.append(f"• Shares: {settings.share_usage_warning}%")
    lines.append(f"• Paridad: máximo {settings.parity_max_days} días sin comprobar")
    lines.append("")
    lines.append("<b>Se avisa de</b>")
    lines.append("• API de Unraid inaccesible")
    lines.append("• Array detenido, casi lleno o con problemas")
    lines.append("• Discos en estado rojo/amarillo, con errores, SMART o temperatura alta")
    lines.append("• Shares por encima del umbral de uso")
    lines.append("• Paridad con errores, fallida o demasiado antigua")
    lines.append("• Contenedores caídos, unhealthy o en estado DEAD")
    lines.append("• VMs en estado CRASHED")
    lines.append("• UPS en batería, batería baja o fallo")
    lines.append("• Interfaz de red caída")
    lines.append("• Notificaciones nuevas de Unraid")
    if problems:
        lines.append("")
        lines.append(f"Ahora mismo hay <b>{len(problems)}</b> incidencia(s) detectada(s).")
    return "\n".join(lines)


def build_alert_message(problems: list[Problem], hostname: str) -> str:
    lines = [f"🚨 <b>Alertas · {esc(hostname)}</b>", ""]
    for problem in problems:
        lines.append(f"{severity_emoji(problem.severity)} <b>{esc(problem.title)}</b>")
        if problem.detail:
            lines.append(f"   {esc(problem.detail)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_recovery_message(titles: list[str], hostname: str) -> str:
    lines = [f"✅ <b>Resuelto · {esc(hostname)}</b>", ""]
    for title in titles:
        lines.append(f"• {esc(title)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Búsqueda, historial, rendimiento y resumen
# ---------------------------------------------------------------------------

def build_search(query: str, hits: list[SearchHit], page: int = 0, per_page: int = 8) -> str:
    lines = [f"🔎 <b>Búsqueda</b> · «{esc(shorten(query, 60))}»", ""]
    if not hits:
        lines.append("No se encontraron resultados.")
        lines.append("")
        lines.append("<i>Prueba con otro nombre o abre una sección desde el menú.</i>")
        return "\n".join(lines)

    shown, page, pages = paginate(hits, page, per_page)
    lines.append(f"{len(hits)} resultado(s) · pág. {page + 1}/{pages}")
    lines.append("")
    for hit in shown:
        emoji = KIND_EMOJI.get(hit.kind, "•")
        label = KIND_LABELS.get(hit.kind, hit.kind)
        lines.append(f"{emoji} <b>{esc(hit.title)}</b> · <i>{esc(label)}</i>")
        if hit.detail:
            lines.append(f"   {esc(shorten(hit.detail, 110))}")
    lines.append("")
    lines.append("Toca un resultado para abrirlo.")
    return "\n".join(lines)


def build_history(
    records: list[dict[str, Any]],
    total: int,
    page: int,
    per_page: int,
    query: str,
    settings: Settings,
) -> str:
    pages = max(1, (total + per_page - 1) // per_page)
    lines = ["🗂️ <b>Historial de auditoría</b>", ""]
    if query:
        lines.append(f"Filtro: <code>{esc(query)}</code>")
    lines.append(f"{total} registro(s) · pág. {page + 1}/{pages}")
    lines.append("")
    if not records:
        lines.append("No hay registros que coincidan.")
        return "\n".join(lines)

    for record in records:
        outcome = str(record.get("outcome") or "ok")
        emoji = "✅" if outcome == "ok" else "❌"
        action = str(record.get("action") or "—")
        target = str(record.get("target") or "")
        user = record.get("username") or record.get("user_id") or "—"
        line = f"{emoji} <b>{esc(action)}</b>"
        if target:
            line += f" · {esc(shorten(target, 60))}"
        lines.append(line)
        when = fmt_timestamp(str(record.get("ts") or ""), settings.timezone)
        lines.append(f"   <i>{esc(when)} · {esc(user)}</i>")
    return "\n".join(lines)


def _series_stats(values: list[float]) -> str:
    if not values:
        return "—"
    low = min(values)
    high = max(values)
    average = sum(values) / len(values)
    return f"mín {low:.0f}% · media {average:.0f}% · máx {high:.0f}%"


def build_performance(
    snapshot: Snapshot,
    history: list[dict[str, Any]],
    settings: Settings,
) -> str:
    metrics = snapshot.metrics or {}
    cpu_now = _number(_get(metrics, "cpu", "percentTotal"))
    memory = metrics.get("memory") or {}
    ram_now = _number(memory.get("percentTotal"))
    if ram_now is None:
        ram_now = pct(memory.get("used"), memory.get("total"))

    cpu_values = [
        value
        for value in (_number(entry.get("cpu")) for entry in history if isinstance(entry, dict))
        if value is not None
    ]
    ram_values = [
        value
        for value in (_number(entry.get("ram")) for entry in history if isinstance(entry, dict))
        if value is not None
    ]

    lines = ["📈 <b>Rendimiento</b>", ""]
    lines.append(f"🧠 CPU ahora: <b>{fmt_pct(cpu_now)}</b>")
    if cpu_values:
        lines.append(f"<code>{sparkline(cpu_values, width=32)}</code>")
        lines.append(f"<i>{_series_stats(cpu_values)}</i>")
    else:
        lines.append("<i>Sin historial de CPU todavía.</i>")
    lines.append("")
    lines.append(f"💾 RAM ahora: <b>{fmt_pct(ram_now)}</b>")
    if ram_values:
        lines.append(f"<code>{sparkline(ram_values, width=32)}</code>")
        lines.append(f"<i>{_series_stats(ram_values)}</i>")
    else:
        lines.append("<i>Sin historial de RAM todavía.</i>")
    lines.append("")
    lines.append(
        f"<i>Muestras guardadas: {len(history)} · una cada "
        f"{fmt_runtime(settings.alert_interval_seconds)}.</i>"
    )
    lines.extend(_errors_footer(snapshot))
    return "\n".join(lines)


def build_digest(snapshot: Snapshot, settings: Settings, problems: list[Problem]) -> str:
    hostname = _server_name(snapshot)
    lines = [
        f"📬 <b>Resumen diario · {esc(hostname)}</b>",
        f"<i>{fmt_timestamp(snapshot.fetched_at.isoformat(), settings.timezone)}</i>",
        "",
    ]
    if not snapshot.reachable:
        lines.append("🔴 <b>Sin conexión con la API de Unraid</b>")
        if snapshot.errors:
            lines.append(_format_error(next(iter(snapshot.errors.values()))))
        lines.append("")
        lines.append("Revisa <code>UNRAID_API_URL</code> y el servicio <code>unraid-api</code>.")
        return "\n".join(lines)

    array = snapshot.array or {}
    state = array.get("state")
    capacity = _get(array, "capacity", "kilobytes", default={}) or {}
    used_kb, total_kb = _number(capacity.get("used")), _number(capacity.get("total"))
    usage = pct(used_kb, total_kb)
    array_line = (
        f"{array_emoji(state)} Array "
        f"{esc(ARRAY_STATE_TEXT.get(state or '', state or 'desconocido'))}"
    )
    if usage is not None:
        array_line += f" · {usage:.0f}% ({fmt_kb(used_kb)} / {fmt_kb(total_kb)})"
    lines.append(array_line)

    metrics = snapshot.metrics or {}
    cpu = _number(_get(metrics, "cpu", "percentTotal"))
    memory = metrics.get("memory") or {}
    ram = _number(memory.get("percentTotal"))
    if ram is None:
        ram = pct(memory.get("used"), memory.get("total"))
    lines.append(f"🧠 CPU {fmt_pct(cpu)} · 💾 RAM {fmt_pct(ram)}")

    containers = snapshot.docker
    if containers is not None:
        running = sum(1 for item in containers if item.get("state") == "RUNNING")
        updates = sum(1 for item in containers if item.get("isUpdateAvailable"))
        docker_line = f"🐳 Docker {running}/{len(containers)} activos"
        if updates:
            docker_line += f" · {updates} actualizaciones"
        lines.append(docker_line)

    vms = snapshot.vms
    if vms is not None:
        running_vms = sum(1 for item in vms if item.get("state") in {"RUNNING", "IDLE"})
        lines.append(f"🖥️ VMs {running_vms}/{len(vms)} en marcha")

    ups = snapshot.ups or []
    if ups:
        unit = ups[0]
        battery = unit.get("battery") or {}
        ups_line = f"🔋 UPS {esc(unit.get('status') or 'desconocido')}"
        if battery.get("chargeLevel") is not None:
            ups_line += f" · {battery['chargeLevel']}%"
        lines.append(ups_line)

    notifications = snapshot.notifications or {}
    unread = _get(notifications, "overview", "unread", default={}) or {}
    if unread:
        alerts = int(unread.get("alert") or 0)
        warnings = int(unread.get("warning") or 0)
        if alerts or warnings:
            lines.append(f"🔔 {alerts} alertas · {warnings} avisos sin leer")
        else:
            lines.append("🔔 Sin notificaciones nuevas")

    lines.append("")
    lines.append("<b>Incidencias</b>")
    if problems:
        for problem in problems[:8]:
            lines.append(f"{severity_emoji(problem.severity)} {esc(problem.title)}")
        if len(problems) > 8:
            lines.append(f"… y {len(problems) - 8} más")
    else:
        lines.append("✅ Sin incidencias")

    lines.extend(_errors_footer(snapshot))
    return "\n".join(lines)


def build_help() -> str:
    return (
        "🤖 <b>UnraidBot</b>\n\n"
        "Administra tu servidor Unraid desde Telegram sin abrir puertos: el bot "
        "usa long polling (conexiones salientes) y la API local de Unraid.\n\n"
        "<b>Comandos</b>\n"
        "/estado — estado general\n"
        "/discos — discos y SMART\n"
        "/docker — contenedores\n"
        "/vms — máquinas virtuales\n"
        "/sistema — array, paridad, UPS, shares\n"
        "/alertas — avisos automáticos\n"
        "/menu — menú principal\n"
        "/id — tu ID de Telegram\n\n"
        "<b>Consejos</b>\n"
        "• Las acciones destructivas piden confirmación.\n"
        "• Los botones caducan; si algo falla, vuelve a abrir el menú.\n"
        "• El modo solo lectura se activa con <code>READ_ONLY=true</code>.\n\n"
        "<i>UnraidBot no sustituye al WebGUI: es un mando rápido y un vigilante.</i>"
    )
