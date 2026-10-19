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

    await store.mark_alert("array:state", "Array detenido", 1000.0)
    entries = store.alert_entries()
    assert entries["array:state"]["title"] == "Array detenido"

    title = await store.clear_alert("array:state")
    assert title == "Array detenido"
    assert store.alert_entries() == {}

    reloaded = StateStore(path)
    await reloaded.load()
    assert reloaded.is_subscribed(123) is True

    await reloaded.unsubscribe(123)
    assert reloaded.subscribers() == []


@pytest.mark.asyncio
async def test_state_corrupt_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{no es json", encoding="utf-8")
    store = StateStore(path)
    await store.load()
    assert store.subscribers() == []
    assert store.alert_entries() == {}
