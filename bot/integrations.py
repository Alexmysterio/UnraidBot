"""Utilidades compartidas por las integraciones opcionales."""

from __future__ import annotations

from typing import Any, Iterable

from .formatting import fmt_elapsed

QB_FILTERS: dict[str, str] = {
    "all": "Todos",
    "downloading": "Descargando",
    "seeding": "Sembrando",
    "paused": "Pausados",
}

QB_STATE_TEXT: dict[str, str] = {
    "error": "Error",
    "missingFiles": "Faltan archivos",
    "uploading": "Subiendo",
    "pausedUP": "Pausado (completo)",
    "stoppedUP": "Detenido (completo)",
    "queuedUP": "En cola (subida)",
    "stalledUP": "Estancado (subida)",
    "checkingUP": "Comprobando (subida)",
    "forcedUP": "Forzado (subida)",
    "allocating": "Reservando espacio",
    "downloading": "Descargando",
    "metaDL": "Obteniendo metadatos",
    "pausedDL": "Pausado",
    "stoppedDL": "Detenido",
    "queuedDL": "En cola (descarga)",
    "stalledDL": "Estancado (descarga)",
    "checkingDL": "Comprobando (descarga)",
    "forcedDL": "Forzado (descarga)",
    "checkingResumeData": "Comprobando datos",
    "moving": "Moviendo",
    "unknown": "Desconocido",
}

_DOWNLOADING = {
    "downloading",
    "metaDL",
    "stalledDL",
    "forcedDL",
    "queuedDL",
    "checkingDL",
    "allocating",
}
_SEEDING = {
    "uploading",
    "stalledUP",
    "forcedUP",
    "queuedUP",
    "checkingUP",
}


def number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_paused(torrent: dict[str, Any]) -> bool:
    state = str(torrent.get("state") or "")
    return state.startswith("paused") or state.startswith("stopped") or state in {
        "stopped",
        "stoppedDL",
        "stoppedUP",
    }


def is_downloading(torrent: dict[str, Any]) -> bool:
    return str(torrent.get("state") or "") in _DOWNLOADING


def is_seeding(torrent: dict[str, Any]) -> bool:
    return str(torrent.get("state") or "") in _SEEDING


def torrent_state(torrent: dict[str, Any]) -> str:
    state = str(torrent.get("state") or "")
    return QB_STATE_TEXT.get(state, state or "Desconocido")


def filter_torrents(torrents: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    items = list(torrents)
    if key == "downloading":
        return [item for item in items if is_downloading(item)]
    if key == "seeding":
        return [item for item in items if is_seeding(item)]
    if key == "paused":
        return [item for item in items if is_paused(item)]
    return items


def format_eta(seconds: Any) -> str:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "—"
    if value < 0 or value >= 8_640_000:
        return "∞"
    return fmt_elapsed(value)
