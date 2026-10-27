from __future__ import annotations

from pathlib import Path

import pytest

from bot.state import StateStore


@pytest.mark.asyncio
async def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    await store.load()

    await store.subscribe(123)
    assert store.is_subscribed(123) is True
    assert store.subscribers() == [123]

    await store.set_language(123, "fr")
    assert store.get_language(123) == "fr"

    await store.mark_alert("array:state", "Array detenido", 1000.0)
    entries = store.alert_entries()
    assert entries["array:state"]["title"] == "Array detenido"

    title = await store.clear_alert("array:state")
    assert title == "Array detenido"
    assert store.alert_entries() == {}

    reloaded = StateStore(path)
    await reloaded.load()
    assert reloaded.is_subscribed(123) is True
    assert reloaded.get_language(123) == "fr"

    await reloaded.unsubscribe(123)
    assert reloaded.subscribers() == []


@pytest.mark.asyncio
async def test_state_mute_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    await store.load()
    await store.subscribe(123)

    assert store.is_muted(123) is False
    until = await store.mute(123, 3600)
    assert store.is_muted(123) is True
    assert store.muted_until(123) == pytest.approx(until)

    reloaded = StateStore(path)
    await reloaded.load()
    assert reloaded.is_muted(123) is True

    assert await reloaded.unmute(123) is True
    assert reloaded.is_muted(123) is False
    assert await reloaded.unmute(123) is False


@pytest.mark.asyncio
async def test_state_alert_severity(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.mark_alert("disk:temp:d1", "Temperatura alta", 1000.0, severity="critical")
    entry = store.alert_entries()["disk:temp:d1"]
    assert entry["severity"] == "critical"


@pytest.mark.asyncio
async def test_state_corrupt_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{no es json", encoding="utf-8")
    store = StateStore(path)
    await store.load()
    assert store.subscribers() == []
    assert store.alert_entries() == {}


@pytest.mark.asyncio
async def test_state_metrics_history_is_capped_and_persisted(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    await store.load()

    await store.record_metric(None, None)
    assert store.metric_history() == []

    for index in range(5):
        await store.record_metric(float(index), float(index * 2), ts=float(index), limit=3)
    history = store.metric_history()
    assert [entry["cpu"] for entry in history] == [2.0, 3.0, 4.0]
    assert store.metric_history(limit=1)[0]["ram"] == 8.0

    reloaded = StateStore(path)
    await reloaded.load()
    assert len(reloaded.metric_history()) == 3


@pytest.mark.asyncio
async def test_state_digest_marker_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    await store.load()
    assert store.digest_last() is None

    await store.set_digest_last("2026-10-27")
    assert store.digest_last() == "2026-10-27"

    reloaded = StateStore(path)
    await reloaded.load()
    assert reloaded.digest_last() == "2026-10-27"
