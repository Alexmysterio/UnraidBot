"""Detección de incidencias a partir de un Snapshot.

Se usa tanto en la pantalla de estado como en el monitor de alertas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .config import Settings
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
    if parity.get("running") and int(parity.get("errors") or 0) > 0:
        problems.append(
            Problem(
                key="parity:errors",
                severity="critical",
                title="Errores durante la comprobación de paridad",
                detail=f"{parity.get('errors')} errores con la comprobación al "
                f"{parity.get('progress') or 0}%.",
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
                    key=f"disk:status:{disk.get('id', name)}",
                    severity=severity,
                    title=f"Disco {name} en estado {status}",
                    detail="Un disco del array no está en estado óptimo.",
                    screen="m:disks",
                )
            )
        elif color and (color.startswith("RED") or color.startswith("YELLOW")):
            problems.append(
                Problem(
                    key=f"disk:color:{disk.get('id', name)}",
                    severity="critical" if color.startswith("RED") else "warning",
                    title=f"Disco {name} marcado en {'rojo' if color.startswith('RED') else 'amarillo'}",
                    detail=f"Color del disco: {color}.",
                    screen="m:disks",
                )
            )

        errors = int(disk.get("numErrors") or 0)
        if errors > 0:
            problems.append(
                Problem(
                    key=f"disk:errors:{disk.get('id', name)}",
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
                        key=f"disk:temp:{disk.get('id', name)}",
                        severity="critical",
                        title=f"Temperatura crítica en {name}",
                        detail=f"{temp:.0f}°C (umbral crítico {settings.disk_temp_critical}°C).",
                        screen="m:disks",
                    )
                )
            elif temp >= settings.disk_temp_warning:
                problems.append(
                    Problem(
                        key=f"disk:temp:{disk.get('id', name)}",
                        severity="warning",
                        title=f"Temperatura alta en {name}",
                        detail=f"{temp:.0f}°C (umbral {settings.disk_temp_warning}°C).",
                        screen="m:disks",
                    )
                )

    # CPU
    cpu_temps = _get(snapshot.info or {}, "cpu", "packages", "temp", default=[]) or []
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

    # Contenedores con autostart que están caídos
    for container in snapshot.docker or []:
        if container.get("autoStart") and container.get("state") == "EXITED":
            problems.append(
                Problem(
                    key=f"docker:{container.get('id', _container_name(container))}",
                    severity="warning",
                    title=f"Contenedor caído: {_container_name(container)}",
                    detail="Tiene autostart activado pero está detenido.",
                    screen="m:docker",
                )
            )

    # VMs bloqueadas
    for vm in snapshot.vms or []:
        if vm.get("state") == "CRASHED":
            problems.append(
                Problem(
                    key=f"vm:{vm.get('id', vm.get('name'))}",
                    severity="critical",
                    title=f"VM bloqueada: {vm.get('name') or 'sin nombre'}",
                    detail="La máquina virtual está en estado CRASHED.",
                    screen="m:vms",
                )
            )

    # UPS
    for ups in snapshot.ups or []:
        status = str(ups.get("status") or "").strip().lower()
        name = ups.get("name") or ups.get("model") or "UPS"
        if "low battery" in status:
            problems.append(
                Problem(
                    key=f"ups:{ups.get('id', name)}",
                    severity="critical",
                    title=f"UPS con batería baja: {name}",
                    detail="El servidor podría apagarse de forma inminente.",
                    screen="s:ups",
                )
            )
        elif "on battery" in status:
            problems.append(
                Problem(
                    key=f"ups:{ups.get('id', name)}",
                    severity="critical",
                    title=f"UPS en batería: {name}",
                    detail=f"Estado: {ups.get('status')}.",
                    screen="s:ups",
                )
            )
        elif "replace" in status or "offline" in status:
            problems.append(
                Problem(
                    key=f"ups:{ups.get('id', name)}",
                    severity="warning",
                    title=f"UPS con problemas: {name}",
                    detail=f"Estado: {ups.get('status')}.",
                    screen="s:ups",
                )
            )

    # Notificaciones nuevas de Unraid (solo alertas/avisos)
    notifications = snapshot.notifications or {}
    for item in (notifications.get("warningsAndAlerts") or [])[:5]:
        importance = str(item.get("importance") or "").upper()
        if importance not in {"ALERT", "WARNING"}:
            continue
        title = item.get("subject") or item.get("title") or "Notificación de Unraid"
        description = item.get("description") or item.get("title") or ""
        problems.append(
            Problem(
                key=f"notif:{item.get('id', title)}",
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
