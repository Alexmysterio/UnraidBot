from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from telegram.error import Forbidden

from bot.broadcast import broadcast
from bot.config import Settings
from bot.digest import DigestScheduler, scheduler_due
from bot.state import StateStore
from bot.unraid import Snapshot


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


class ForbiddenBot(FakeBot):
    async def send_message(self, **kwargs) -> None:
        raise Forbidden("blocked by user")


class FakeClient:
    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot_data = snapshot

    async def snapshot(self, include_storage: bool = False) -> Snapshot:
        return self.snapshot_data


async def _store(tmp_path: Path) -> StateStore:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    return store


@pytest.mark.asyncio
async def test_digest_waits_for_hour(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    store = await _store(tmp_path)
    await store.subscribe(123)
    bot = FakeBot()
    scheduler = DigestScheduler(settings, FakeClient(snapshot), store, bot)  # type: ignore[arg-type]

    moment = datetime(2026, 10, 27, 8, 59, tzinfo=ZoneInfo(settings.timezone))
    assert await scheduler.send_if_due(moment) is False
    assert bot.messages == []
    assert store.digest_last() is None


@pytest.mark.asyncio
async def test_digest_sends_once_per_day(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    store = await _store(tmp_path)
    await store.subscribe(123)
    await store.set_language(123, "es")
    bot = FakeBot()
    scheduler = DigestScheduler(settings, FakeClient(snapshot), store, bot)  # type: ignore[arg-type]

    moment = datetime(2026, 10, 27, 9, 0, tzinfo=ZoneInfo(settings.timezone))
    assert await scheduler.send_if_due(moment) is True
    assert len(bot.messages) == 1
    assert "Resumen diario" in bot.messages[0]["text"]
    assert store.digest_last() == "2026-10-27"

    assert await scheduler.send_if_due(moment) is False
    assert len(bot.messages) == 1

    next_day = datetime(2026, 10, 28, 9, 0, tzinfo=ZoneInfo(settings.timezone))
    assert await scheduler.send_if_due(next_day) is True
    assert store.digest_last() == "2026-10-28"


@pytest.mark.asyncio
async def test_digest_respects_mute_and_disabled(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    store = await _store(tmp_path)
    await store.subscribe(123)
    await store.mute(123, 3600)
    bot = FakeBot()
    scheduler = DigestScheduler(settings, FakeClient(snapshot), store, bot)  # type: ignore[arg-type]

    moment = datetime(2026, 10, 27, 10, 0, tzinfo=ZoneInfo(settings.timezone))
    assert await scheduler.send_if_due(moment) is False
    assert bot.messages == []
    assert store.digest_last() is None

    disabled = DigestScheduler(
        replace(settings, digest_enabled=False),
        FakeClient(snapshot),
        store,
        bot,  # type: ignore[arg-type]
    )
    assert await disabled.send_if_due(moment) is False


@pytest.mark.asyncio
async def test_scheduler_due_helper(settings: Settings, tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    await store.load()
    moment = datetime(2026, 10, 27, 12, 0, tzinfo=ZoneInfo(settings.timezone))
    assert scheduler_due(settings, store, moment) is True
    await store.set_digest_last("2026-10-27")
    assert scheduler_due(settings, store, moment) is False


@pytest.mark.asyncio
async def test_broadcast_skips_muted_and_unsubscribes_blocked(tmp_path: Path) -> None:
    store = await _store(tmp_path)
    await store.subscribe(1)
    await store.subscribe(2)
    await store.mute(2, 3600)

    bot = FakeBot()
    assert await broadcast(bot, store, [1, 2], "hola") is True  # type: ignore[arg-type]
    assert [message["chat_id"] for message in bot.messages] == [1]

    await store.unmute(2)
    assert await broadcast(ForbiddenBot(), store, [2], "hola") is False  # type: ignore[arg-type]
    assert store.is_subscribed(2) is False
