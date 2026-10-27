"""Búsqueda difusa de recursos del servidor y resolución de nombres."""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .security import short_id
from .unraid import Snapshot

KIND_LABELS = {
    "docker": "Docker",
    "vm": "VM",
    "disk": "Disco",
    "physical_disk": "Disco físico",
    "share": "Share",
    "notification": "Notificación",
    "ups": "UPS",
}

KIND_EMOJI = {
    "docker": "🐳",
    "vm": "🖥️",
    "disk": "💾",
    "physical_disk": "🔍",
    "share": "📚",
    "notification": "🔔",
    "ups": "🔋",
}


@dataclass(frozen=True, slots=True)
class SearchHit:
    """Resultado de búsqueda con el callback que abre su pantalla."""

    kind: str
    title: str
    detail: str
    callback: str
    score: float = 0.0


def normalize(value: Any) -> str:
    """Minúsculas y sin acentos para comparar de forma tolerante."""
    text = str(value or "").strip().lstrip("/")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _fields(item: dict[str, Any], keys: Sequence[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = item.get(key)
        if isinstance(raw, (list, tuple)):
            values.extend(str(part) for part in raw if part is not None)
        elif raw is not None:
            values.append(str(raw))
    return values


def score_match(query: str, fields: Iterable[Any]) -> float:
    """Puntúa 0..1; acepta coincidencia exacta, parcial o difusa."""
    needle = normalize(query)
    if not needle:
        return 0.0
    candidates = [normalize(field) for field in fields if normalize(field)]
    if not candidates:
        return 0.0

    best = 0.0
    tokens = needle.split()
    for candidate in candidates:
        if candidate == needle:
            return 1.0
        if candidate.startswith(needle):
            best = max(best, 0.95)
        elif needle in candidate:
            best = max(best, 0.85)
        elif tokens and all(token in candidate for token in tokens):
            best = max(best, 0.8)
        else:
            ratio = difflib.SequenceMatcher(None, needle, candidate).ratio()
            best = max(best, ratio * 0.75)
    return best


def _container_name(container: dict[str, Any]) -> str:
    names = container.get("names") or []
    return str(names[0]).lstrip("/") if names else "contenedor"


def _array_disks(array: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("parities", "disks", "caches"):
        value = array.get(key)
        if isinstance(value, list):
            result.extend(item for item in value if isinstance(item, dict))
    return result


def search_snapshot(snapshot: Snapshot, query: str) -> list[SearchHit]:
    """Busca en Docker, VMs, discos, shares, UPS y notificaciones."""
    needle = query.strip()
    if not needle:
        return []
    hits: list[SearchHit] = []

    def add(
        kind: str,
        title: str,
        detail: str,
        callback: str,
        fields: Iterable[Any],
        threshold: float = 0.5,
    ) -> None:
        score = score_match(needle, fields)
        if score >= threshold:
            hits.append(SearchHit(kind, title, detail, callback, score))

    for container in snapshot.docker or []:
        name = _container_name(container)
        add(
            "docker",
            name,
            f"{container.get('image') or 'imagen desconocida'} · {container.get('state') or '—'}",
            f"d:v:{short_id(str(container.get('id') or name))}:0",
            [name, container.get("image"), container.get("status")],
        )

    for vm in snapshot.vms or []:
        name = str(vm.get("name") or vm.get("id") or "VM")
        add(
            "vm",
            name,
            f"Estado: {vm.get('state') or '—'}",
            f"v:v:{short_id(str(vm.get('id') or name))}",
            [name, vm.get("state")],
        )

    for disk in _array_disks(snapshot.array or {}):
        name = str(disk.get("name") or disk.get("device") or "disco")
        add(
            "disk",
            name,
            f"{disk.get('device') or '—'} · {disk.get('status') or '—'}",
            f"k:v:{short_id(str(disk.get('id') or name))}",
            [name, disk.get("device"), disk.get("fsType"), disk.get("comment")],
        )

    for disk in snapshot.physical_disks or []:
        name = str(disk.get("device") or disk.get("name") or "disco")
        add(
            "physical_disk",
            name,
            f"{disk.get('smartStatus') or 'SMART ?'} · {disk.get('interfaceType') or '—'}",
            "k:p",
            [name, disk.get("name"), disk.get("serialNum"), disk.get("vendor")],
        )

    for share in snapshot.shares or []:
        name = str(share.get("name") or "share")
        add(
            "share",
            name,
            str(share.get("comment") or "Share de usuario"),
            "s:shares",
            [name, share.get("comment")],
        )

    for unit in snapshot.ups or []:
        name = str(unit.get("name") or unit.get("model") or "UPS")
        add(
            "ups",
            name,
            str(unit.get("status") or "—"),
            "s:ups",
            [name, unit.get("model"), unit.get("status")],
        )

    notifications = (snapshot.notifications or {}).get("warningsAndAlerts") or []
    for item in notifications:
        title = str(item.get("subject") or item.get("title") or "Notificación")
        add(
            "notification",
            title,
            str(item.get("description") or ""),
            "s:notif",
            [title, item.get("description"), item.get("importance")],
        )

    hits.sort(key=lambda hit: (-hit.score, KIND_LABELS.get(hit.kind, hit.kind), hit.title.lower()))
    return hits


def find_named(
    items: Sequence[dict[str, Any]],
    query: str,
    keys: Sequence[str] = ("name",),
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Resuelve un nombre: exacto, prefijo, contenido o difuso.

    Devuelve ``(elemento, candidatos)``. Si hay ambigüedad, el elemento es
    ``None`` y los candidatos permiten explicar la elección al usuario.
    """
    needle = normalize(query)
    if not needle or not items:
        return None, []

    def matches(predicate) -> list[dict[str, Any]]:
        return [
            item
            for item in items
            if any(predicate(normalize(value)) for value in _fields(item, keys))
        ]

    exact = matches(lambda value: value == needle)
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        return None, exact

    prefix = matches(lambda value: value.startswith(needle))
    if len(prefix) == 1:
        return prefix[0], []
    if len(prefix) > 1:
        return None, prefix

    contains = matches(lambda value: needle in value)
    if len(contains) == 1:
        return contains[0], []
    if len(contains) > 1:
        return None, contains

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        best = max(
            (
                difflib.SequenceMatcher(None, needle, normalize(value)).ratio()
                for value in _fields(item, keys)
            ),
            default=0.0,
        )
        scored.append((best, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return None, []
    best_score, best_item = scored[0]
    if best_score < 0.62:
        return None, []
    close = [item for score, item in scored if score >= max(0.62, best_score - 0.05)]
    if len(close) == 1:
        return best_item, []
    return None, close[:8]
