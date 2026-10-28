"""Detección de incidencias a partir de un Snapshot.

Se usa tanto en la pantalla de estado como en el monitor de alertas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from .config import Settings
from .formatting import parse_iso
from .unraid import Snapshot

Severity = Literal["critical", "warning"]


@dataclass(frozen=True, slots=True)
class Problem:
    key: str
    severity: Severity
    title: str
    detail: str
    screen: str = "m:status"


def _get(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _container_name(container: dict[str, Any]) -> str:
    names = container.get("names") or []
    if names:
        return str(names[0]).lstrip("/")
    return "contenedor"


def _temp(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:  # NaN o valor ausente
        return None
    return number


def _as_list(value: Any) -> list[Any]:
    """Normaliza escalares y listas: la API a veces devuelve un solo valor."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _disk_key(disk: dict[str, Any], name: str) -> str:
    """Clave estable aunque ``id`` exista con valor nulo."""
    return str(disk.get("id") or name)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _usage(used: Any, total: Any) -> float | None:
    try:
        used_f, total_f = float(used or 0), float(total or 0)
    except (TypeError, ValueError):
        return None
    if total_f <= 0:
        return None
    return max(0.0, min(100.0, used_f / total_f * 100.0))


def detect_problems(snapshot: Snapshot, settings: Settings) -> list[Problem]:
    """Devuelve incidencias ordenadas por gravedad.

    Si el snapshot no tiene datos (API inaccesible), devuelve una lista vacía:
    de la conectividad ya se encarga la pantalla de estado y el log.
    """
    problems: list[Problem] = []

    array = snapshot.array or {}
    state = array.get("state")
    if array and state != "STARTED":
        problems.append(
            Problem(
                key="array:state",
                severity="critical",
                title="Array detenido",
                detail=f"El array está en estado {state or 'desconocido'}.",
                screen="s:array",
            )
        )

    parity = array.get("parityCheckStatus") or {}
    try:
        parity_errors = int(parity.get("errors") or 0)
    except (TypeError, ValueError):
        parity_errors = 0
    if parity_errors > 0:
        problems.append(
            Problem(
                key="parity:errors",
                severity="critical",
                title="Errores durante la comprobación de paridad",
                detail=(
                    f"{parity_errors} errores con la comprobación al "
                    f"{parity.get('progress') or 0}%."
                    if parity.get("running")
                    else f"La última comprobación registró {parity_errors} errores."
                ),
                screen="s:parity",
            )
        )
    if parity.get("status") == "FAILED":
        problems.append(
            Problem(
                key="parity:failed",
                severity="warning",
                title="La última comprobación de paridad falló",
                detail="Revisa el historial de paridad en el WebGUI.",
                screen="s:parity",
            )
        )
    if parity.get("status") == "COMPLETED" and parity.get("date"):
        last_run = parse_iso(parity.get("date"))
        if last_run is not None:
            age_days = (datetime.now(timezone.utc) - last_run).days
            if age_days >= settings.parity_max_days:
                problems.append(
                    Problem(
                        key="parity:age",
                        severity="warning",
                        title="Comprobación de paridad antigua",
                        detail=(
                            f"La última comprobación fue hace {age_days} días "
                            f"(máximo recomendado {settings.parity_max_days})."
                        ),
                        screen="s:parity",
                    )
                )

    # Historial de paridad: incidencias que el estado actual ya no refleja.
    history = [item for item in (snapshot.parity_history or []) if isinstance(item, dict)]
    if history:
        failing = [
            item
            for item in history
            if str(item.get("status") or "").upper() in {"FAILED", "ERROR"}
            or _int(item.get("errors")) > 0
        ]
        if failing:
            latest = max(failing, key=lambda item: str(item.get("date") or ""))
            same_as_current = str(latest.get("date") or "") == str(parity.get("date") or "")
            if not same_as_current:
                errors = _int(latest.get("errors"))
                when = str(latest.get("date") or "sin fecha")
                problems.append(
                    Problem(
                        key="parity:history",
                        severity="warning",
                        title="La última comprobación de paridad registrada falló",
                        detail=(
                            f"{when}: {errors} errores."
                            if errors
                            else f"{when}: estado {latest.get('status') or 'desconocido'}."
                        ),
                        screen="s:ph",
                    )
                )

    # Licencia
    registration = (snapshot.license or {}).get("registration") or {}
    if registration:
        license_state = str(registration.get("state") or "").upper()
        if license_state in {"EXPIRED", "TRIAL_EXPIRED", "INVALID", "NOT_FOUND"}:
            problems.append(
                Problem(
                    key="license:state",
                    severity="critical" if license_state != "TRIAL_EXPIRED" else "warning",
                    title="Licencia de Unraid no válida",
                    detail=f"Estado: {license_state}.",
                    screen="s:license",
                )
            )
        expiration = parse_iso(registration.get("expiration"))
        if expiration is not None:
            days_left = (expiration - datetime.now(timezone.utc)).days
            if days_left < 0:
                problems.append(
                    Problem(
                        key="license:expired",
                        severity="critical",
                        title="Licencia de Unraid caducada",
                        detail=f"Caducó hace {abs(days_left)} días.",
                        screen="s:license",
                    )
                )
            elif days_left <= 30:
                problems.append(
                    Problem(
                        key="license:expiry",
                        severity="warning",
                        title="Licencia de Unraid a punto de caducar",
                        detail=f"Quedan {days_left} días.",
                        screen="s:license",
                    )
                )

    # Servicios internos de Unraid
    for service in snapshot.services or []:
        if not isinstance(service, dict) or service.get("online"):
            continue
        service_name = str(service.get("name") or service.get("id") or "servicio")
        problems.append(
            Problem(
                key=f"service:{service_name}",
                severity="warning",
                title=f"Servicio caído: {service_name}",
                detail="Unraid lo marca como no disponible.",
                screen="s:services",
            )
        )

    capacity = _get(array, "capacity", "kilobytes", default={}) or {}
    array_usage = _usage(capacity.get("used"), capacity.get("total"))
    if array_usage is not None and array_usage >= settings.array_usage_warning:
        problems.append(
            Problem(
                key="array:usage",
                severity="warning",
                title="Array casi lleno",
                detail=(
                    f"{array_usage:.0f}% en uso "
                    f"(umbral {settings.array_usage_warning}%)."
                ),
                screen="s:array",
            )
        )

    for share in snapshot.shares or []:
        if not isinstance(share, dict):
            continue
        share_name = share.get("name") or "share"
        share_usage = _usage(share.get("used"), share.get("size"))
        if share_usage is not None and share_usage >= settings.share_usage_warning:
            problems.append(
                Problem(
                    key=f"share:usage:{share_name}",
                    severity="warning",
                    title=f"Share {share_name} casi lleno",
                    detail=(
                        f"{share_usage:.0f}% en uso "
                        f"(umbral {settings.share_usage_warning}%)."
                    ),
                    screen="s:shares",
                )
            )

    for disk in _all_disks(array):
        name = disk.get("name") or disk.get("device") or "disco"
        status = disk.get("status")
        color = disk.get("color")

        if status and status != "DISK_OK":
            severity: Severity = "critical" if status in {
                "DISK_DSBL",
                "DISK_INVALID",
                "DISK_WRONG",
                "DISK_NP_MISSING",
            } else "warning"
            problems.append(
                Problem(
                    key=f"disk:status:{_disk_key(disk, name)}",
                    severity=severity,
                    title=f"Disco {name} en estado {status}",
                    detail="Un disco del array no está en estado óptimo.",
                    screen="m:disks",
                )
            )
        elif color and (color.startswith("RED") or color.startswith("YELLOW")):
            problems.append(
                Problem(
                    key=f"disk:color:{_disk_key(disk, name)}",
                    severity="critical" if color.startswith("RED") else "warning",
                    title=f"Disco {name} marcado en {'rojo' if color.startswith('RED') else 'amarillo'}",
                    detail=f"Color del disco: {color}.",
                    screen="m:disks",
                )
            )

        try:
            errors = int(disk.get("numErrors") or 0)
        except (TypeError, ValueError):
            errors = 0
        if errors > 0:
            problems.append(
                Problem(
                    key=f"disk:errors:{_disk_key(disk, name)}",
                    severity="warning",
                    title=f"Errores de E/S en {name}",
                    detail=f"{errors} errores acumulados. Revisa el SMART del disco.",
                    screen="m:disks",
                )
            )

        temp = _temp(disk.get("temp"))
        if temp is not None:
            if temp >= settings.disk_temp_critical:
                problems.append(
                    Problem(
                        key=f"disk:temp:{_disk_key(disk, name)}",
                        severity="critical",
                        title=f"Temperatura crítica en {name}",
                        detail=f"{temp:.0f}°C (umbral crítico {settings.disk_temp_critical}°C).",
                        screen="m:disks",
                    )
                )
            elif temp >= settings.disk_temp_warning:
                problems.append(
                    Problem(
                        key=f"disk:temp:{_disk_key(disk, name)}",
                        severity="warning",
                        title=f"Temperatura alta en {name}",
                        detail=f"{temp:.0f}°C (umbral {settings.disk_temp_warning}°C).",
                        screen="m:disks",
                    )
                )

    # Discos físicos: la API solo expone OK/UNKNOWN, pero toleramos estados futuros.
    for disk in snapshot.physical_disks or []:
        if not isinstance(disk, dict):
            continue
        smart = str(disk.get("smartStatus") or "").strip().upper()
        if not smart or smart in {"OK", "UNKNOWN"}:
            continue
        name = disk.get("device") or disk.get("name") or "disco"
        problems.append(
            Problem(
                key=f"smart:{disk.get('id') or name}",
                severity="warning",
                title=f"SMART con problemas en {name}",
                detail=f"Estado SMART: {smart}.",
                screen="m:disks",
            )
        )

    # CPU
    cpu_temps = _as_list(_get(snapshot.info or {}, "cpu", "packages", "temp", default=[]))
    valid_temps = [value for value in (_temp(item) for item in cpu_temps) if value is not None]
    if valid_temps:
        hottest = max(valid_temps)
        if hottest >= settings.cpu_temp_warning:
            problems.append(
                Problem(
                    key="cpu:temp",
                    severity="warning",
                    title="Temperatura de CPU alta",
                    detail=f"{hottest:.0f}°C (umbral {settings.cpu_temp_warning}°C).",
                    screen="m:status",
                )
            )

    memory = snapshot.metrics or {}
    mem_pct = _temp(_get(memory, "memory", "percentTotal"))
    if mem_pct is not None and mem_pct >= settings.memory_warning:
        problems.append(
            Problem(
                key="memory:usage",
                severity="warning",
                title="Memoria RAM al límite",
                detail=f"{mem_pct:.0f}% en uso (umbral {settings.memory_warning}%).",
                screen="m:status",
            )
        )

    # Red primaria caída
    network = _get(snapshot.info or {}, "primaryNetwork", default={}) or {}
    operstate = str(network.get("operstate") or "").strip().lower()
    if operstate == "down":
        problems.append(
            Problem(
                key="network:down",
                severity="critical",
                title="Interfaz de red caída",
                detail=f"La interfaz {network.get('name') or 'principal'} está DOWN.",
                screen="s:info",
            )
        )

    # Contenedores caídos, muertos o unhealthy
    for container in snapshot.docker or []:
        if not isinstance(container, dict):
            continue
        container_name = _container_name(container)
        container_id = container.get("id") or container_name
        state = container.get("state")
        status_text = str(container.get("status") or "").lower()
        if state == "DEAD":
            problems.append(
                Problem(
                    key=f"docker:dead:{container_id}",
                    severity="critical",
                    title=f"Contenedor muerto: {container_name}",
                    detail="Docker lo marca como DEAD. Revisa sus logs.",
                    screen="m:docker",
                )
            )
        elif "unhealthy" in status_text:
            problems.append(
                Problem(
                    key=f"docker:unhealthy:{container_id}",
                    severity="warning",
                    title=f"Contenedor unhealthy: {container_name}",
                    detail="El healthcheck de Docker está fallando.",
                    screen="m:docker",
                )
            )
        if container.get("autoStart") and state == "EXITED":
            problems.append(
                Problem(
                    key=f"docker:{container_id}",
                    severity="warning",
                    title=f"Contenedor caído: {container_name}",
                    detail="Tiene autostart activado pero está detenido.",
                    screen="m:docker",
                )
            )

    # VMs bloqueadas
    for vm in snapshot.vms or []:
        if vm.get("state") == "CRASHED":
            problems.append(
                Problem(
                    key=f"vm:{vm.get('id') or vm.get('name') or 'vm'}",
                    severity="critical",
                    title=f"VM bloqueada: {vm.get('name') or 'sin nombre'}",
                    detail="La máquina virtual está en estado CRASHED.",
                    screen="m:vms",
                )
            )

    # UPS
    for ups in snapshot.ups or []:
        if not isinstance(ups, dict):
            continue
        raw_status = ups.get("status")
        if isinstance(raw_status, dict):
            raw_status = raw_status.get("value") or raw_status.get("status")
        status = str(raw_status or "").strip().lower().replace("_", " ")
        name = ups.get("name") or ups.get("model") or "UPS"
        ups_id = ups.get("id") or name
        if "low battery" in status:
            problems.append(
                Problem(
                    key=f"ups:{ups_id}",
                    severity="critical",
                    title=f"UPS con batería baja: {name}",
                    detail="El servidor podría apagarse de forma inminente.",
                    screen="s:ups",
                )
            )
        elif "on battery" in status:
            problems.append(
                Problem(
                    key=f"ups:{ups_id}",
                    severity="critical",
                    title=f"UPS en batería: {name}",
                    detail=f"Estado: {raw_status or 'desconocido'}.",
                    screen="s:ups",
                )
            )
        elif any(word in status for word in ("replace", "offline", "communication", "no battery")):
            problems.append(
                Problem(
                    key=f"ups:{ups_id}",
                    severity="warning",
                    title=f"UPS con problemas: {name}",
                    detail=f"Estado: {raw_status or 'desconocido'}.",
                    screen="s:ups",
                )
            )

    # Notificaciones nuevas de Unraid (solo alertas/avisos)
    notifications = snapshot.notifications or {}
    for item in (notifications.get("warningsAndAlerts") or [])[:5]:
        if not isinstance(item, dict):
            continue
        importance = str(item.get("importance") or "").upper()
        if importance not in {"ALERT", "WARNING"}:
            continue
        title = item.get("subject") or item.get("title") or "Notificación de Unraid"
        description = item.get("description") or item.get("title") or ""
        problems.append(
            Problem(
                key=f"notif:{item.get('id') or title}",
                severity="critical" if importance == "ALERT" else "warning",
                title=str(title),
                detail=str(description)[:300],
                screen="s:notif",
            )
        )

    order = {"critical": 0, "warning": 1}
    problems.sort(key=lambda item: (order.get(item.severity, 2), item.title))
    return problems


def _all_disks(array: dict[str, Any]) -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    for key in ("parities", "disks", "caches"):
        value = array.get(key)
        if isinstance(value, list):
            disks.extend(item for item in value if isinstance(item, dict))
    return disks
