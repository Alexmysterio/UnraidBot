from __future__ import annotations

from dataclasses import replace

from bot import features
from bot.config import Settings
from bot.keyboards import main_menu


def test_features_disabled_by_default(settings: Settings) -> None:
    features.configure(settings)
    assert features.enabled() == ()
    callbacks = [button.callback_data for row in main_menu().inline_keyboard for button in row]
    assert "m:tools" not in callbacks


def test_feature_enables_tools_menu(settings: Settings) -> None:
    enabled = replace(
        settings,
        feature_qbittorrent=True,
        qbittorrent_url="http://qbittorrent:8080",
        qbittorrent_username="admin",
        qbittorrent_password="secret",
    )
    features.configure(enabled)
    assert [feature.key for feature in features.enabled()] == ["qbittorrent"]
    callbacks = [button.callback_data for row in main_menu().inline_keyboard for button in row]
    assert "m:tools" in callbacks
    features.configure(settings)
