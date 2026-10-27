"""Registro de funcionalidades opcionales activadas por variables de entorno."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .config import Settings


@dataclass(frozen=True, slots=True)
class Feature:
    key: str
    label: str
    description: str
    callback: str
    flag: str
    env: str = ""


FEATURES: tuple[Feature, ...] = (
    Feature(
        key="qbittorrent",
        label="qBittorrent",
        description="Torrents, detalle, límites y categorías",
        callback="tool:qb",
        flag="feature_qbittorrent",
        env="SERVICE_QBITTORRENT",
    ),
    Feature(
        key="mikrotik",
        label="MikroTik",
        description="Router: interfaces, leases, rutas, firewall y logs",
        callback="tool:mt",
        flag="feature_mikrotik",
        env="SERVICE_MIKROTIK",
    ),
    Feature(
        key="wol",
        label="Wake-on-LAN",
        description="Enciende uno o varios equipos con magic packets",
        callback="tool:wol",
        flag="feature_wol",
        env="SERVICE_WOL",
    ),
)

_enabled: tuple[Feature, ...] = ()


def configure(settings: Settings) -> None:
    global _enabled
    _enabled = tuple(feature for feature in FEATURES if getattr(settings, feature.flag, False))


def enabled() -> tuple[Feature, ...]:
    return _enabled


def is_enabled(key: str) -> bool:
    return any(feature.key == key for feature in _enabled)


def get(key: str) -> Feature | None:
    for feature in _enabled:
        if feature.key == key:
            return feature
    return None


def count() -> int:
    return len(_enabled)


def labels() -> Iterable[str]:
    for feature in _enabled:
        yield feature.label
