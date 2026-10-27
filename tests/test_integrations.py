from __future__ import annotations

from dataclasses import replace

import pytest

from bot import features
from bot.config import Settings, WolDevice
from bot.integrations import (
    filter_torrents,
    format_eta,
    is_downloading,
    is_paused,
    is_seeding,
    number,
    torrent_state,
    truthy,
)
from bot.keyboards import (
    mikrotik_main_keyboard,
    mikrotik_paged_keyboard,
    qb_detail_keyboard,
    qb_limits_keyboard,
    qb_list_keyboard,
    wol_keyboard,
)
from bot.telegram import _safe_url, configure_telegram
from bot.views_integrations import (
    build_mikrotik_firewall,
    build_mikrotik_interfaces,
    build_mikrotik_leases,
    build_mikrotik_logs,
    build_mikrotik_main,
    build_mikrotik_routes,
    build_qb_categories,
    build_qb_detail,
    build_qb_limits,
    build_qb_list,
    build_wol,
)

TORRENTS = [
    {"hash": "a", "name": "Debian", "state": "downloading", "progress": 0.5, "dlspeed": 2048},
    {"hash": "b", "name": "Arch", "state": "uploading", "progress": 1.0, "upspeed": 1024},
    {"hash": "c", "name": "Ubuntu", "state": "pausedDL", "progress": 0.1},
]


def test_torrent_helpers() -> None:
    assert number("2.5") == 2.5
    assert number(None) == 0.0
    assert truthy("true") and truthy(True) and not truthy("0")
    assert is_downloading(TORRENTS[0])
    assert is_seeding(TORRENTS[1])
    assert is_paused(TORRENTS[2])
    assert torrent_state(TORRENTS[2]) == "Pausado"
    assert format_eta(90) == "1 min 30 s"
    assert format_eta(-1) == "∞"


def test_filter_torrents() -> None:
    assert [item["name"] for item in filter_torrents(TORRENTS, "downloading")] == ["Debian"]
    assert [item["name"] for item in filter_torrents(TORRENTS, "seeding")] == ["Arch"]
    assert [item["name"] for item in filter_torrents(TORRENTS, "paused")] == ["Ubuntu"]
    assert len(filter_torrents(TORRENTS, "all")) == 3


def test_build_qb_list_marks_filter_and_page(settings: Settings) -> None:
    text = build_qb_list(
        {"dl_info_speed": 2048, "up_info_speed": 1024},
        TORRENTS,
        0,
        6,
        "downloading",
        False,
    )
    assert "qBittorrent" in text
    assert "Filtro: Descargando" in text
    assert "Debian" in text
    assert "Arch" not in text


def test_build_qb_detail_and_limits(settings: Settings) -> None:
    detail = build_qb_detail(TORRENTS[0], settings)
    assert "Debian" in detail
    assert "Estado: <b>Descargando</b>" in detail
    limits = build_qb_limits({"dl_limit": 0, "up_limit": 1024}, True)
    assert "ilimitado" in limits
    assert "activada" in limits


def test_build_qb_categories_counts_torrents() -> None:
    text = build_qb_categories({"Pelis": {"savePath": "/data/pelis"}}, TORRENTS)
    assert "Pelis" in text
    assert "0 torrents" in text
    assert "Sin categoría" in text


def test_build_mikrotik_main() -> None:
    text = build_mikrotik_main(
        {"name": "router"},
        {"board-name": "hEX", "version": "7.15", "uptime": "1d", "cpu-load": "5",
         "total-memory": 1024, "free-memory": 512},
        [{"name": "ether1", "running": "true"}],
        [{"status": "bound"}],
        [{"active": "true"}],
        [{"disabled": "false"}],
    )
    assert "MikroTik · router" in text
    assert "Interfaces: 1/1" in text
    assert "Leases DHCP: 1/1" in text


def test_build_mikrotik_sections() -> None:
    interfaces = [{"name": "ether1", "running": "true", "type": "ether", "mtu": "1500"}]
    assert "ether1" in build_mikrotik_interfaces(interfaces, 0)
    leases = [{"address": "192.168.88.10", "status": "bound", "host-name": "nas"}]
    assert "nas" in build_mikrotik_leases(leases, 0)
    routes = [{"dst-address": "0.0.0.0/0", "gateway": "192.168.88.1", "active": "true"}]
    assert "0.0.0.0/0" in build_mikrotik_routes(routes, 0)
    rules = [{"chain": "input", "action": "accept", "packets": 3, "bytes": 128}]
    assert "input" in build_mikrotik_firewall(rules, 0)
    logs = [{"time": "12:00:00", "topics": "system,info", "message": "logged in"}]
    assert "logged in" in build_mikrotik_logs(logs, 0)


def test_build_mikrotik_empty_sections() -> None:
    assert "No hay interfaces." in build_mikrotik_interfaces([], 0)
    assert "No hay leases DHCP." in build_mikrotik_leases([], 0)
    assert "No hay rutas." in build_mikrotik_routes([], 0)
    assert "No hay reglas de firewall." in build_mikrotik_firewall([], 0)
    assert "No hay registros." in build_mikrotik_logs([], 0)


def test_build_wol_lists_devices() -> None:
    devices = [
        WolDevice(name="NAS", mac="AA:BB:CC:DD:EE:FF"),
        WolDevice(name="PC", mac="11:22:33:44:55:66", broadcast="192.168.1.255"),
    ]
    text = build_wol(devices)
    assert "NAS" in text
    assert "192.168.1.255" in text
    assert "Equipos configurados: <b>2</b>" in text
    assert "No hay equipos configurados." in build_wol([])


def test_qb_keyboards_include_actions() -> None:
    list_markup = qb_list_keyboard(TORRENTS, 0, 2, "all", False)
    data = [button.callback_data for row in list_markup.inline_keyboard for button in row]
    assert "qb:all:pause" in data
    assert "qb:l:downloading:0" in data
    assert "qb:noop" in data
    detail = qb_detail_keyboard(TORRENTS[0], "all", 0)
    detail_data = [button.callback_data for row in detail.inline_keyboard for button in row]
    assert any(item.startswith("qb:t:") for item in detail_data)
    assert any(item.startswith("qb:x:") for item in detail_data)
    limits = qb_limits_keyboard(True)
    assert limits.inline_keyboard[0][0].callback_data == "qb:alt"


def test_mikrotik_and_wol_keyboards() -> None:
    main = [button.callback_data for row in mikrotik_main_keyboard().inline_keyboard for button in row]
    assert "mt:i:0" in main
    assert "mt:reboot" in main
    paged = mikrotik_paged_keyboard("mt:l", 1, 3)
    paged_data = [button.callback_data for row in paged.inline_keyboard for button in row]
    assert "mt:l:0" in paged_data
    assert "mt:l:2" in paged_data
    assert "mt:l:noop" in paged_data

    devices = [WolDevice(name="NAS", mac="AA:BB:CC:DD:EE:FF"), WolDevice(name="PC", mac="11:22:33:44:55:66")]
    wol = [button.callback_data for row in wol_keyboard(devices).inline_keyboard for button in row]
    assert "wol:all" in wol
    assert any(item.startswith("wol:w:") for item in wol)


def test_safe_url_masks_credentials() -> None:
    assert _safe_url("socks5://user:pass@127.0.0.1:9050") == "socks5://***@127.0.0.1:9050"
    assert _safe_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"


def test_configure_telegram_applies_proxy_and_rate_limiter(settings: Settings) -> None:
    from telegram.ext import AIORateLimiter, ApplicationBuilder

    configured = replace(
        settings,
        telegram_proxy_enabled=True,
        telegram_proxy_url="http://127.0.0.1:8080",
        telegram_rate_limit=True,
    )
    builder = ApplicationBuilder().token(configured.telegram_token)
    result = configure_telegram(builder, configured)
    assert result is builder
    assert isinstance(builder._rate_limiter, AIORateLimiter)
    assert builder._proxy is not None
    assert builder._get_updates_proxy is not None


def test_configure_telegram_skips_when_disabled(settings: Settings) -> None:
    from telegram.ext import AIORateLimiter, ApplicationBuilder

    configured = replace(settings, telegram_proxy_enabled=False, telegram_rate_limit=False)
    builder = ApplicationBuilder().token(configured.telegram_token)
    assert configure_telegram(builder, configured) is builder
    assert not isinstance(builder._rate_limiter, AIORateLimiter)


def test_features_expose_service_env(settings: Settings) -> None:
    enabled = replace(
        settings,
        feature_qbittorrent=True,
        feature_mikrotik=True,
        feature_wol=True,
        wol_devices=(WolDevice(name="NAS", mac="AA:BB:CC:DD:EE:FF"),),
    )
    features.configure(enabled)
    try:
        assert features.is_enabled("qbittorrent")
        assert features.is_enabled("mikrotik")
        assert features.is_enabled("wol")
        assert {feature.env for feature in features.enabled()} == {
            "SERVICE_QBITTORRENT",
            "SERVICE_MIKROTIK",
            "SERVICE_WOL",
        }
    finally:
        features.configure(settings)


@pytest.mark.parametrize(
    "state,expected",
    [
        ("downloading", "Descargando"),
        ("stalledUP", "Estancado (subida)"),
        ("pausedUP", "Pausado (completo)"),
        ("raro", "raro"),
    ],
)
def test_torrent_state_labels(state: str, expected: str) -> None:
    assert torrent_state({"state": state}) == expected


@pytest.mark.asyncio
async def test_qb_consume_text_ignores_unarmed_chat() -> None:
    from bot.handlers.qbittorrent import consume_text

    class FakeContext:
        chat_data: dict[str, object] = {}
        bot_data: dict[str, object] = {}

    assert await consume_text(None, FakeContext()) is False  # type: ignore[arg-type]
