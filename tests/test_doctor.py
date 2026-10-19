from __future__ import annotations

from bot.doctor import mask


def test_mask_hides_secrets() -> None:
    assert mask("") == "—"
    assert mask("short") == "••••"
    assert mask("123456789:ABCDEFGHIJ") == "1234…GHIJ"
    assert "ABCDEFGHIJ" not in mask("123456789:ABCDEFGHIJ")
