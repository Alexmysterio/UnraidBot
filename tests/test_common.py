from __future__ import annotations

from dataclasses import replace

from bot.config import Settings
from bot.handlers.common import is_writable, role_for


def test_roles(settings: Settings) -> None:
    assert role_for(settings, 111) == "admin"
    assert role_for(settings, 999) is None

    with_viewer = replace(settings, viewer_user_ids=frozenset({222}))
    assert role_for(with_viewer, 222) == "viewer"
    assert is_writable(with_viewer, 111) is True
    assert is_writable(with_viewer, 222) is False

    read_only = replace(settings, read_only=True)
    assert is_writable(read_only, 111) is False
