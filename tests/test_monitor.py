from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from bot.config import Settings
from bot.monitor import AlertMonitor
from bot.state import StateStore
from bot.unraid import Snapshot


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


class FakeClient:
    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot_data = snapshot

    async def snapshot(self, include_info: bool = True) -> Snapshot:
        return self.snapshot_data


@pytest.mark.asyncio
async def test_monitor_dedup_and_recovery(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    settings = replace(settings, alerts_enabled=True)
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)

    bot = FakeBot()
    client = FakeClient(snapshot)
    monitor = AlertMonitor(settings, client, store, bot)  # type: ignore[arg-type]

    await monitor.tick()
    assert len(bot.messages) == 1
    text = bot.messages[0]["text"]
    assert "Alertas" in text
    assert "autobrr" in text

    # Sin cambios: no se repite
    await monitor.tick()
    assert len(bot.messages) == 1

    # Una consulta caída no debe resolver las incidencias de esa sección
    partial = replace(
        snapshot,
        array={"state": "STARTED"},
        metrics={},
        info=snapshot.info,
        ups=[],
        notifications=None,
        docker=None,
        vms=[],
    )
    client.snapshot_data = partial
    await monitor.tick()
    assert len(bot.messages) == 1

    # Se resuelven las incidencias: mensaje de recuperación
    healthy = replace(
        snapshot,
        array={"state": "STARTED"},
        metrics={},
        info=snapshot.info,
        ups=[],
        notifications={},
        docker=[],
        vms=[],
    )
    client.snapshot_data = healthy
    await monitor.tick()
    assert len(bot.messages) == 2
    assert "Resuelto" in bot.messages[1]["text"]


@pytest.mark.asyncio
async def test_monitor_without_subscribers_does_nothing(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    bot = FakeBot()
    monitor = AlertMonitor(settings, FakeClient(snapshot), store, bot)  # type: ignore[arg-type]
    await monitor.tick()
    assert bot.messages == []
