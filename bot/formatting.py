"""Utilidades de formato para los mensajes de Telegram."""

from __future__ import annotations

import html
import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def esc(value: Any) -> str:
    """Escapa texto dinámico para parse_mode=HTML."""
    if value is None:
        return "—"
    return html.escape(str(value), quote=False)


def clamp(text: str, limit: int = 3900) -> str:
    """Recorta un mensaje para no superar el límite de Telegram."""
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n… (recortado)"


def shorten(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def humanize_state(value: str | None) -> str:
    return (value or "").replace("_", " ").strip()


# ---------------------------------------------------------------------------
# Números y tamaños
# ---------------------------------------------------------------------------

_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")


def fmt_bytes(value: float | int | str | None, decimals: int = 1) -> str:
    """Formatea bytes con unidades binarias."""
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(number) or math.isinf(number):
        return "—"
    if number <= 0:
        return "0 B"
    exponent = min(int(math.log(number, 1024)), len(_UNITS) - 1)
    scaled = number / (1024**exponent)
    if exponent == 0:
        return f"{int(scaled)} B"
    return f"{scaled:.{decimals}f} {_UNITS[exponent]}"


def fmt_kb(value: float | int | str | None, decimals: int = 1) -> str:
    if value is None or value == "":
        return "—"
    try:
        return fmt_bytes(float(value) * 1024, decimals)
    except (TypeError, ValueError):
        return "—"


def fmt_array_disk_size(value: float | int | str | None) -> str:
    """Tamaño de un disco del array.

    La API de Unraid expone ``ArrayDisk.size`` en KiB, aunque en algunas
    versiones devuelve bytes. Se detecta por magnitud.
    """
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if number > 1e12:  # bytes (un disco de 1 TB son ~1e9 KiB)
        return fmt_bytes(number)
    return fmt_kb(number)


def fmt_pct(value: float | int | str | None, decimals: int = 0) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def pct(used: float | int | None, total: float | int | None) -> float | None:
    try:
        used_f, total_f = float(used or 0), float(total or 0)
    except (TypeError, ValueError):
        return None
    if total_f <= 0:
        return None
    return max(0.0, min(100.0, used_f / total_f * 100.0))


def bar(percent: float | None, width: int = 10) -> str:
    """Barra de progreso con bloques Unicode."""
    if percent is None:
        return "─" * width
    filled = int(round(max(0.0, min(100.0, percent)) / 100 * width))
    return "█" * filled + "░" * (width - filled)


def fmt_temp(value: float | int | str | None) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(number) or number <= 0:
        return "—"
    return f"{number:.0f}°C"


def fmt_runtime(seconds: float | int | None) -> str:
    if seconds is None:
        return "—"
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "—"
    if total < 0:
        return "—"
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def fmt_timestamp(value: str | None, tz_name: str = "Europe/Madrid") -> str:
    """Convierte un ISO-8601 de la API a hora local legible."""
    parsed = parse_iso(value)
    if parsed is None:
        return "—"
    try:
        from zoneinfo import ZoneInfo

        local = parsed.astimezone(ZoneInfo(tz_name))
    except Exception:  # pragma: no cover - zona inválida ya validada
        local = parsed
    return local.strftime("%d/%m/%Y %H:%M")


def fmt_when(value: str | None, tz_name: str = "Europe/Madrid") -> str:
    """Fecha relativa: 'hace 2 h', 'hace 3 d'."""
    parsed = parse_iso(value)
    if parsed is None:
        return "—"
    now = datetime.now(timezone.utc)
    delta = (now - parsed).total_seconds()
    if delta < 0:
        return fmt_timestamp(value, tz_name)
    if delta < 90:
        return "hace unos segundos"
    if delta < 3600:
        return f"hace {int(delta // 60)} min"
    if delta < 86400:
        return f"hace {int(delta // 3600)} h"
    return f"hace {int(delta // 86400)} d"


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    # Python solo admite 6 dígitos de fracción de segundo.
    match = re.match(r"^(.*\.\d{6})\d+([+-].*)?$", text)
    if match:
        text = match.group(1) + (match.group(2) or "")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def fmt_uptime(boot_time: str | None) -> str:
    parsed = parse_iso(boot_time)
    if parsed is None:
        return "—"
    seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    if seconds <= 0:
        return "—"
    return fmt_runtime(seconds)


def fmt_net_speed(mbps: float | int | None) -> str:
    if not mbps:
        return "—"
    if mbps >= 1000:
        return f"{mbps / 1000:.1f} Gbps"
    return f"{mbps:.0f} Mbps"


def join_nonempty(parts: Iterable[str | None], sep: str = " · ") -> str:
    return sep.join(part for part in parts if part)


# ---------------------------------------------------------------------------
# Emojis de estado
# ---------------------------------------------------------------------------

ARRAY_EMOJI = {
    "STARTED": "🟢",
    "STOPPED": "🔴",
    "NEW_ARRAY": "🟡",
    "RECON_DISK": "🟠",
    "DISABLE_DISK": "🟠",
    "SWAP_DSBL": "🟠",
    "INVALID_EXPANSION": "🔴",
    "PARITY_NOT_BIGGEST": "🟡",
    "TOO_MANY_MISSING_DISKS": "🔴",
    "NEW_DISK_TOO_SMALL": "🔴",
    "NO_DATA_DISKS": "🟡",
}


def array_emoji(state: str | None) -> str:
    return ARRAY_EMOJI.get(state or "", "⚪")


def disk_emoji(status: str | None, color: str | None = None) -> str:
    if color:
        if color.startswith("RED"):
            return "🔴"
        if color.startswith("YELLOW"):
            return "🟡"
        if color.startswith("BLUE"):
            return "🔵"
        if color.startswith("GREEN"):
            return "🟢"
    if status == "DISK_OK":
        return "🟢"
    if status in {"DISK_DSBL", "DISK_INVALID", "DISK_WRONG", "DISK_NP_MISSING"}:
        return "🔴"
    if status in {"DISK_NP", "DISK_NEW", "DISK_DSBL_NEW", "DISK_NP_DSBL"}:
        return "🟡"
    return "⚪"


def container_emoji(state: str | None) -> str:
    return {"RUNNING": "🟢", "PAUSED": "🟡", "EXITED": "⚪"}.get(state or "", "⚪")


def vm_emoji(state: str | None) -> str:
    return {
        "RUNNING": "🟢",
        "IDLE": "🟢",
        "PAUSED": "🟡",
        "PMSUSPENDED": "🟡",
        "SHUTDOWN": "🟠",
        "SHUTOFF": "⚪",
        "CRASHED": "🔴",
        "NOSTATE": "⚪",
    }.get(state or "", "⚪")


def severity_emoji(severity: str) -> str:
    return {"critical": "🔴", "warning": "🟠"}.get(severity, "⚪")


def docker_state_text(state: str | None) -> str:
    return {
        "RUNNING": "En marcha",
        "PAUSED": "Pausado",
        "EXITED": "Detenido",
    }.get(state or "", humanize_state(state) or "Desconocido")


def vm_state_text(state: str | None) -> str:
    return {
        "RUNNING": "En marcha",
        "IDLE": "En marcha (idle)",
        "PAUSED": "Pausada",
        "PMSUSPENDED": "Suspendida",
        "SHUTDOWN": "Apagándose",
        "SHUTOFF": "Apagada",
        "CRASHED": "Bloqueada / crash",
        "NOSTATE": "Sin estado",
    }.get(state or "", humanize_state(state) or "Desconocido")


def parity_status_text(status: str | None, running: bool | None, progress: int | None) -> str:
    if running:
        return f"Comprobando ({progress or 0}%)"
    return {
        "NEVER_RUN": "Nunca ejecutada",
        "COMPLETED": "Completada",
        "PAUSED": "Pausada",
        "CANCELLED": "Cancelada",
        "FAILED": "Fallida",
        "RUNNING": "En ejecución",
    }.get(status or "", humanize_state(status) or "Desconocida")
