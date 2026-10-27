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

    async def snapshot(
        self, include_info: bool = True, include_storage: bool = False
    ) -> Snapshot:
        return self.snapshot_data


class FailingBot(FakeBot):
    async def send_message(self, **kwargs) -> None:
        from telegram.error import TelegramError

        raise TelegramError("boom")


@pytest.mark.asyncio
async def test_monitor_dedup_and_recovery(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    settings = replace(settings, alerts_enabled=True)
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)
    await store.set_language(123, "es")

    bot = FakeBot()
    client = FakeClient(snapshot)
    monitor = AlertMonitor(settings, client, store, bot)  # type: ignore[arg-type]

    await monitor.tick()
    assert len(bot.messages) == 1
    text = bot.messages[0]["text"]
    assert "Alertas" in text
    assert "autobrr" in text
    assert store.metric_history()[0]["cpu"] == 12.5

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


def _healthy(snapshot: Snapshot) -> Snapshot:
    return replace(
        snapshot,
        array={"state": "STARTED"},
        metrics={},
        ups=[],
        notifications={"warningsAndAlerts": []},
        docker=[],
        vms=[],
    )


@pytest.mark.asyncio
async def test_monitor_offline_alert_after_two_cycles(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)
    await store.set_language(123, "es")

    bot = FakeBot()
    client = FakeClient(Snapshot(errors={"array": "connection refused"}))
    monitor = AlertMonitor(settings, client, store, bot)  # type: ignore[arg-type]

    await monitor.tick()
    assert bot.messages == []

    await monitor.tick()
    assert len(bot.messages) == 1
    assert "Sin conexión con la API" in bot.messages[0]["text"]

    client.snapshot_data = _healthy(snapshot)
    await monitor.tick()
    assert len(bot.messages) == 2
    assert "Resuelto" in bot.messages[1]["text"]


@pytest.mark.asyncio
async def test_monitor_skips_muted_chats(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)
    await store.set_language(123, "es")
    await store.mute(123, 3600)

    bot = FakeBot()
    monitor = AlertMonitor(settings, FakeClient(snapshot), store, bot)  # type: ignore[arg-type]
    await monitor.tick()
    assert bot.messages == []

    await store.unmute(123)
    await monitor.tick()
    assert len(bot.messages) == 1


@pytest.mark.asyncio
async def test_monitor_escalates_severity(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)
    await store.set_language(123, "es")

    warning = replace(snapshot)
    warning.array = {**snapshot.array, "disks": [dict(snapshot.array["disks"][0])]}
    warning.array["disks"][0]["temp"] = 51

    bot = FakeBot()
    client = FakeClient(warning)
    monitor = AlertMonitor(settings, client, store, bot)  # type: ignore[arg-type]
    await monitor.tick()
    assert len(bot.messages) == 1

    critical = replace(snapshot)
    critical.array = {**snapshot.array, "disks": [dict(snapshot.array["disks"][0])]}
    critical.array["disks"][0]["temp"] = 56
    client.snapshot_data = critical
    await monitor.tick()
    assert len(bot.messages) == 2
    assert "crítica" in bot.messages[1]["text"]


@pytest.mark.asyncio
async def test_monitor_keeps_alert_until_recovery_is_delivered(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.subscribe(123)
    await store.set_language(123, "es")

    bot = FakeBot()
    client = FakeClient(snapshot)
    monitor = AlertMonitor(settings, client, store, bot)  # type: ignore[arg-type]
    await monitor.tick()
    assert len(bot.messages) == 1
    assert store.alert_entries()

    monitor.bot = FailingBot()  # type: ignore[assignment]
    client.snapshot_data = _healthy(snapshot)
    await monitor.tick()
    assert store.alert_entries()

    monitor.bot = bot  # type: ignore[assignment]
    await monitor.tick()
    assert len(bot.messages) == 2
    assert "Resuelto" in bot.messages[1]["text"]
    assert store.alert_entries() == {}
