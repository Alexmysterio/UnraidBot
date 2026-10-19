from __future__ import annotations

import pytest

from bot.config import ConfigError, Settings


def base_env() -> dict[str, str]:
    return {
        "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
        "UNRAID_API_KEY": "api-key",
        "ALLOWED_USER_IDS": "111, 222",
    }


def test_valid_settings() -> None:
    settings = Settings.from_env(base_env())
    assert settings.allowed_user_ids == frozenset({111, 222})
    assert settings.unraid_api_url == "http://host.docker.internal/graphql"
    assert settings.alerts_enabled is True
    assert settings.disk_temp_warning == 50


def test_missing_token_raises() -> None:
    env = base_env()
    env.pop("TELEGRAM_BOT_TOKEN")
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        Settings.from_env(env)


def test_empty_allowlist_is_allowed_for_setup_mode() -> None:
    env = base_env()
    env["ALLOWED_USER_IDS"] = ""
    settings = Settings.from_env(env)
    assert settings.allowed_user_ids == frozenset()
    assert settings.is_configured is False


def test_invalid_ids_raise() -> None:
    env = base_env()
    env["ALLOWED_USER_IDS"] = "111, no-es-un-id"
    with pytest.raises(ConfigError, match="ID de Telegram"):
        Settings.from_env(env)


def test_invalid_timezone_raises() -> None:
    env = base_env()
    env["TIMEZONE"] = "Marte/Olympus"
    with pytest.raises(ConfigError, match="TIMEZONE"):
        Settings.from_env(env)


def test_critical_temp_below_warning_raises() -> None:
    env = base_env()
    env["DISK_TEMP_WARNING"] = "60"
    env["DISK_TEMP_CRITICAL"] = "55"
    with pytest.raises(ConfigError, match="DISK_TEMP_CRITICAL"):
        Settings.from_env(env)


def test_socket_disables_default_url_requirement() -> None:
    env = base_env()
    env["UNRAID_API_URL"] = ""
    env["UNRAID_API_SOCKET"] = "/var/run/nginx.sock"
    settings = Settings.from_env(env)
    assert settings.unraid_api_socket == "/var/run/nginx.sock"
