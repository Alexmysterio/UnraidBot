from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from bot.security import AuditLog, ConfirmationManager, RateLimiter, resolve_short, short_id


def test_short_id_is_stable_and_short() -> None:
    token = short_id("server:abcdef1234567890")
    assert token == short_id("server:abcdef1234567890")
    assert len(token) == 10
    assert token != short_id("server:otro")


def test_resolve_short() -> None:
    items = [{"id": "a"}, {"id": "b"}]
    token = short_id("b")
    assert resolve_short(items, token) == {"id": "b"}
    assert resolve_short(items, "no-existe") is None


def test_rate_limiter() -> None:
    limiter = RateLimiter(actions=2, window=60)
    assert limiter.allow(1) is True
    assert limiter.allow(1) is True
    assert limiter.allow(1) is False
    assert limiter.allow(2) is True


def test_confirmation_lifecycle() -> None:
    manager = ConfirmationManager(ttl_seconds=60)
    item = manager.create(
        user_id=1,
        chat_id=2,
        action="array.stop",
        target="array",
        args={},
        prompt="¿Seguro?",
        success_text="Hecho",
        return_callback="s:array",
    )
    assert manager.pop(item.token, 999) is None
    assert manager.pop(item.token, 1) is item
    assert manager.pop(item.token, 1) is None


def test_confirmation_expires() -> None:
    manager = ConfirmationManager(ttl_seconds=0)
    item = manager.create(
        user_id=1,
        chat_id=2,
        action="x",
        target="x",
        args={},
        prompt="p",
        success_text="s",
        return_callback="m:main",
    )
    time.sleep(0.01)
    assert manager.pop(item.token, 1) is None


@pytest.mark.asyncio
async def test_audit_log_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.log"
    log = AuditLog(path, max_bytes=1000)
    await log.write(user_id=1, username="alois", chat_id=2, action="docker.stop", target="plex")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["action"] == "docker.stop"
    assert record["target"] == "plex"
    assert record["user_id"] == 1
