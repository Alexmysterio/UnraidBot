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
    assert settings.viewer_user_ids == frozenset()
    assert settings.unraid_api_url == "http://host.docker.internal/graphql"
    assert settings.alerts_enabled is True
    assert settings.disk_temp_warning == 50
    assert settings.array_usage_warning == 85
    assert settings.share_usage_warning == 90
    assert settings.parity_max_days == 45
    assert settings.api_offline_alert is True


def test_new_alert_settings_from_env() -> None:
    env = base_env()
    env["ARRAY_USAGE_WARNING"] = "80"
    env["SHARE_USAGE_WARNING"] = "95"
    env["PARITY_MAX_DAYS"] = "60"
    env["API_OFFLINE_ALERT"] = "false"
    settings = Settings.from_env(env)
    assert settings.array_usage_warning == 80
    assert settings.share_usage_warning == 95
    assert settings.parity_max_days == 60
    assert settings.api_offline_alert is False


def test_usage_threshold_above_100_raises() -> None:
    env = base_env()
    env["ARRAY_USAGE_WARNING"] = "101"
    with pytest.raises(ConfigError, match="ARRAY_USAGE_WARNING"):
        Settings.from_env(env)


def test_digest_settings_from_env() -> None:
    env = base_env()
    env["DIGEST_ENABLED"] = "false"
    env["DIGEST_HOUR"] = "21"
    env["DIGEST_MINUTE"] = "30"
    settings = Settings.from_env(env)
    assert settings.digest_enabled is False
    assert settings.digest_hour == 21
    assert settings.digest_minute == 30

    defaults = Settings.from_env(base_env())
    assert defaults.digest_enabled is True
    assert (defaults.digest_hour, defaults.digest_minute) == (9, 0)


@pytest.mark.parametrize("value", ["24", "-1", "abc"])
def test_invalid_digest_hour_raises(value: str) -> None:
    env = base_env()
    env["DIGEST_HOUR"] = value
    with pytest.raises(ConfigError, match="DIGEST_HOUR"):
        Settings.from_env(env)


@pytest.mark.parametrize("value", ["60", "-5", "abc"])
def test_invalid_digest_minute_raises(value: str) -> None:
    env = base_env()
    env["DIGEST_MINUTE"] = value
    with pytest.raises(ConfigError, match="DIGEST_MINUTE"):
        Settings.from_env(env)


def test_viewer_ids_are_parsed() -> None:
    env = base_env()
    env["VIEWER_USER_IDS"] = "333, 444"
    settings = Settings.from_env(env)
    assert settings.viewer_user_ids == frozenset({333, 444})
    assert settings.is_configured is True


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


def test_optional_qbittorrent_requires_credentials() -> None:
    env = base_env()
    env["FEATURE_QBITTORRENT"] = "true"
    with pytest.raises(ConfigError, match="QBITTORRENT_URL"):
        Settings.from_env(env)


def test_optional_wol_requires_mac() -> None:
    env = base_env()
    env["FEATURE_WOL"] = "true"
    env["WOL_MAC"] = "no-es-una-mac"
    with pytest.raises(ConfigError, match="WOL_MAC"):
        Settings.from_env(env)


def test_service_flags_accept_active_and_noactive() -> None:
    env = base_env()
    env["SERVICE_WOL"] = "active"
    env["WOL_DEVICES"] = "NAS=AA:BB:CC:DD:EE:FF,PC=11:22:33:44:55:66@192.168.1.255"
    settings = Settings.from_env(env)
    assert settings.feature_wol is True
    assert [device.name for device in settings.wol_devices] == ["NAS", "PC"]
    assert settings.wol_devices[1].broadcast == "192.168.1.255"

    env["SERVICE_WOL"] = "noactive"
    assert Settings.from_env(env).feature_wol is False


def test_service_flag_takes_precedence_over_legacy_feature() -> None:
    env = base_env()
    env["FEATURE_MIKROTIK"] = "true"
    env["SERVICE_MIKROTIK"] = "noactive"
    settings = Settings.from_env(env)
    assert settings.feature_mikrotik is False


def test_invalid_service_flag_raises() -> None:
    env = base_env()
    env["SERVICE_QBITTORRENT"] = "quizá"
    with pytest.raises(ConfigError, match="SERVICE_QBITTORRENT"):
        Settings.from_env(env)


def test_wol_devices_reject_duplicate_names() -> None:
    env = base_env()
    env["SERVICE_WOL"] = "active"
    env["WOL_DEVICES"] = "NAS=AA:BB:CC:DD:EE:FF,nas=11:22:33:44:55:66"
    with pytest.raises(ConfigError, match="duplicado"):
        Settings.from_env(env)


def test_telegram_proxy_requires_url() -> None:
    env = base_env()
    env["SERVICE_TELEGRAM_PROXY"] = "active"
    with pytest.raises(ConfigError, match="TELEGRAM_PROXY_URL"):
        Settings.from_env(env)

    env["TELEGRAM_PROXY_URL"] = "socks5://127.0.0.1:9050"
    settings = Settings.from_env(env)
    assert settings.telegram_proxy_enabled is True
    assert settings.telegram_proxy_url == "socks5://127.0.0.1:9050"


def test_telegram_rate_limit_can_be_disabled() -> None:
    env = base_env()
    env["TELEGRAM_RATE_LIMIT"] = "noactive"
    assert Settings.from_env(env).telegram_rate_limit is False

