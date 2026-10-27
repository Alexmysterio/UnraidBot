"""Extracción y registro de muestras de CPU/RAM para las sparklines."""

from __future__ import annotations

from typing import Any

from telegram.ext import ContextTypes

from .unraid import Snapshot


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def sample_usage(snapshot: Snapshot) -> tuple[float | None, float | None]:
    """Devuelve ``(cpu, ram)`` en porcentaje a partir de las métricas."""
    metrics = snapshot.metrics or {}
    cpu = metrics.get("cpu") or {}
    memory = metrics.get("memory") or {}
    cpu_value = _number(cpu.get("percentTotal"))
    ram_value = _number(memory.get("percentTotal"))
    if ram_value is None:
        total = _number(memory.get("total"))
        used = _number(memory.get("used"))
        if total and used is not None and total > 0:
            ram_value = used / total * 100
    return cpu_value, ram_value


async def record_metric(context: ContextTypes.DEFAULT_TYPE, snapshot: Snapshot) -> None:
    """Guarda una muestra si la API devolvió métricas."""
    store = context.bot_data.get("store")
    if store is None:
        return
    cpu, ram = sample_usage(snapshot)
    if cpu is None and ram is None:
        return
    await store.record_metric(cpu, ram)
