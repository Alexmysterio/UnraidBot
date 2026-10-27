from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from bot.config import Settings
from bot.services import ServiceError
from bot.services.mikrotik import MikroTik
from bot.services.qbittorrent import QBittorrent
from bot.services.wol import _packet, normalize_mac


def test_normalize_mac() -> None:
    assert normalize_mac("aa:bb:cc:dd:ee:ff") == "AABBCCDDEEFF"
    assert normalize_mac("AA-BB-CC-DD-EE-FF") == "AABBCCDDEEFF"


def test_invalid_mac() -> None:
    with pytest.raises(ValueError):
        normalize_mac("no-es-una-mac")


def test_magic_packet() -> None:
    packet = _packet("AA:BB:CC:DD:EE:FF")
    assert len(packet) == 102
    assert packet[:6] == b"\xff" * 6
    assert packet[6:12] == bytes.fromhex("AABBCCDDEEFF")


@pytest.mark.asyncio
async def test_qbittorrent_client(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_qbittorrent=True,
        qbittorrent_url="http://qbittorrent:8080",
        qbittorrent_username="admin",
        qbittorrent_password="secret",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, text="Ok.", request=request)
        if request.url.path.endswith("/transfer/info"):
            return httpx.Response(200, json={"dl_info_speed": 1024, "up_info_speed": 512}, request=request)
        if request.url.path.endswith("/torrents/info"):
            return httpx.Response(
                200,
                json=[{"hash": "abc", "name": "Debian", "progress": 0.5, "state": "downloading"}],
                request=request,
            )
        return httpx.Response(404, request=request)

    client = QBittorrent(settings, transport=httpx.MockTransport(handler))
    try:
        status = await client.status()
        torrents = await client.torrents()
    finally:
        await client.close()
    assert status["dl_info_speed"] == 1024
    assert torrents[0]["name"] == "Debian"


@pytest.mark.asyncio
async def test_mikrotik_client(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_mikrotik=True,
        mikrotik_url="https://192.168.88.1",
        mikrotik_username="admin",
        mikrotik_password="secret",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/system/identity"):
            return httpx.Response(200, json={"name": "router"}, request=request)
        if request.url.path.endswith("/system/resource"):
            return httpx.Response(200, json={"version": "7.15", "cpu-load": "5"}, request=request)
        if request.url.path.endswith("/interface"):
            return httpx.Response(200, json=[{"name": "ether1", "running": "true"}], request=request)
        if request.url.path.endswith("/ip/dhcp-server/lease"):
            return httpx.Response(200, json=[{"address": "192.168.88.10"}], request=request)
        return httpx.Response(404, request=request)

    client = MikroTik(settings, transport=httpx.MockTransport(handler))
    try:
        assert (await client.identity())["name"] == "router"
        assert (await client.resource())["version"] == "7.15"
        assert (await client.interfaces())[0]["name"] == "ether1"
        assert len(await client.leases()) == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_qbittorrent_extended_actions(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_qbittorrent=True,
        qbittorrent_url="http://qbittorrent:8080",
        qbittorrent_username="admin",
        qbittorrent_password="secret",
    )
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/auth/login"):
            return httpx.Response(200, text="Ok.", request=request)
        if path.endswith("/torrents/categories"):
            return httpx.Response(200, json={"Pelis": {"savePath": "/data"}}, request=request)
        if path.endswith("/app/preferences"):
            return httpx.Response(200, json={"dl_limit": 0, "up_limit": 1024}, request=request)
        if path.endswith("/transfer/speedLimitsMode"):
            return httpx.Response(200, text="1", request=request)
        if path.endswith("/torrents/add"):
            return httpx.Response(200, text="Ok.", request=request)
        return httpx.Response(200, text="", request=request)

    client = QBittorrent(settings, transport=httpx.MockTransport(handler))
    try:
        assert "Pelis" in await client.categories()
        assert (await client.preferences())["up_limit"] == 1024
        assert await client.alt_speed_enabled() is True
        await client.add("magnet:?xt=urn:btih:abc", category="Pelis")
        await client.delete("abc", delete_files=True)
        await client.set_paused("abc", True)
        await client.set_category("abc", "Pelis")
        await client.set_download_limit(2048)
        await client.set_upload_limit(1024)
        await client.toggle_alt_speed()
    finally:
        await client.close()
    paths = [path for _, path in calls]
    assert "/api/v2/torrents/delete" in paths
    assert "/api/v2/torrents/stop" in paths
    assert "/api/v2/transfer/setDownloadLimit" in paths
    assert "/api/v2/transfer/toggleSpeedLimitsMode" in paths


@pytest.mark.asyncio
async def test_qbittorrent_reports_connection_errors(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_qbittorrent=True,
        qbittorrent_url="http://qbittorrent:8080",
        qbittorrent_username="admin",
        qbittorrent_password="secret",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = QBittorrent(settings, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ServiceError, match="conectar"):
            await client.status()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_mikrotik_extended_sections(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_mikrotik=True,
        mikrotik_url="https://192.168.88.1",
        mikrotik_username="admin",
        mikrotik_password="secret",
    )
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        path = request.url.path
        if path.endswith("/ip/route"):
            return httpx.Response(200, json=[{"dst-address": "0.0.0.0/0"}], request=request)
        if path.endswith("/ip/firewall/filter"):
            return httpx.Response(200, json=[{"chain": "input"}], request=request)
        if path.endswith("/log"):
            return httpx.Response(200, json=[{"message": "hello"}], request=request)
        if path.endswith("/system/reboot"):
            return httpx.Response(200, json=[], request=request)
        return httpx.Response(404, request=request)

    client = MikroTik(settings, transport=httpx.MockTransport(handler))
    try:
        assert (await client.routes())[0]["dst-address"] == "0.0.0.0/0"
        assert (await client.firewall())[0]["chain"] == "input"
        assert (await client.logs())[0]["message"] == "hello"
        await client.reboot()
    finally:
        await client.close()
    assert "/rest/system/reboot" in calls


@pytest.mark.asyncio
async def test_mikrotik_tolerates_non_list_payloads(settings: Settings) -> None:
    settings = replace(
        settings,
        feature_mikrotik=True,
        mikrotik_url="https://192.168.88.1",
        mikrotik_username="admin",
        mikrotik_password="secret",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/interface"):
            return httpx.Response(200, json={"not": "a list"}, request=request)
        return httpx.Response(200, json={"name": "router"}, request=request)

    client = MikroTik(settings, transport=httpx.MockTransport(handler))
    try:
        assert await client.interfaces() == []
        assert (await client.identity())["name"] == "router"
    finally:
        await client.close()
