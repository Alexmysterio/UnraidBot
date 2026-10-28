"""Cliente GraphQL de las funciones ampliadas de 1.6.0."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from bot.config import Settings
from bot.unraid import UnraidClient


def _client(settings: Settings, handler) -> UnraidClient:
    return UnraidClient(settings, transport=httpx.MockTransport(handler))


def _recorder(data: dict[str, Any], seen: dict[str, Any]):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        seen["variables"] = body.get("variables")
        return httpx.Response(200, json={"data": data}, request=request)

    return handler


@pytest.mark.asyncio
async def test_parity_history(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    history = [{"date": "2026-10-01T03:00:00Z", "status": "COMPLETED", "errors": 0}]
    client = _client(settings, _recorder({"parityHistory": history}, seen))
    try:
        assert await client.parity_history() == history
    finally:
        await client.close()
    assert "parityHistory" in seen["query"]


@pytest.mark.asyncio
async def test_registration_returns_license_and_flash(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    data = {
        "registration": {"state": "BASIC", "type": "BASIC"},
        "flash": {"vendor": "SanDisk", "product": "Cruzer"},
    }
    client = _client(settings, _recorder(data, seen))
    try:
        result = await client.registration()
    finally:
        await client.close()
    assert result == data
    assert "registration" in seen["query"] and "flash" in seen["query"]


@pytest.mark.asyncio
async def test_server_identity_read_and_write(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        if "updateServerIdentity" in body["query"]:
            return httpx.Response(
                200,
                json={"data": {"updateServerIdentity": {"name": "tower"}}},
                request=request,
            )
        return httpx.Response(200, json={"data": {"server": {"name": "tower"}}}, request=request)

    client = _client(settings, handler)
    try:
        assert await client.server_identity() == {"name": "tower"}
        updated = await client.set_server_identity("tower", "salón")
    finally:
        await client.close()

    assert updated == {"name": "tower"}
    assert seen[1]["variables"] == {"name": "tower", "comment": "salón"}


@pytest.mark.asyncio
async def test_plugins_and_install(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        if "installPlugin" in body["query"]:
            return httpx.Response(
                200,
                json={"data": {"unraidPlugins": {"installPlugin": {"name": "x.plg"}}}},
                request=request,
            )
        return httpx.Response(
            200,
            json={"data": {"plugins": [{"name": "x.plg", "version": "1.0"}]}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        assert await client.plugins() == [{"name": "x.plg", "version": "1.0"}]
        result = await client.install_plugin("https://example.test/x.plg")
    finally:
        await client.close()

    assert result == {"name": "x.plg"}
    assert seen[1]["variables"] == {
        "input": {"url": "https://example.test/x.plg", "forced": True}
    }


@pytest.mark.asyncio
async def test_services_and_network(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        seen.append(query)
        if "networkInterfaces" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "networkInterfaces": [{"name": "eth0", "operstate": "up"}],
                        "network": {"accessUrls": [{"type": "LAN", "ipv4": "http://tower"}]},
                    }
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={"data": {"services": [{"name": "nginx", "online": True}]}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        assert await client.services() == [{"name": "nginx", "online": True}]
        network = await client.network()
    finally:
        await client.close()

    assert network["interfaces"] == [{"name": "eth0", "operstate": "up"}]
    assert network["access_urls"] == [{"type": "LAN", "ipv4": "http://tower"}]
    assert any("networkInterfaces" in query for query in seen)


@pytest.mark.asyncio
async def test_log_files_and_content(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        if "logFiles" in body["query"]:
            return httpx.Response(
                200,
                json={"data": {"logFiles": [{"name": "syslog", "path": "/var/log/syslog"}]}},
                request=request,
            )
        return httpx.Response(
            200,
            json={"data": {"logFile": {"content": "hola", "totalLines": 1}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        files = await client.log_files()
        content = await client.log_file("/var/log/syslog", lines=400, start_line=10)
    finally:
        await client.close()

    assert files[0]["name"] == "syslog"
    assert content["content"] == "hola"
    assert seen[1]["variables"] == {
        "path": "/var/log/syslog",
        "lines": 400,
        "startLine": 10,
    }


@pytest.mark.asyncio
async def test_temperatures_reads_metrics(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    data = {
        "metrics": {
            "temperature": {"sensors": [{"name": "CPU", "current": {"value": 40}}]},
            "network": [{"name": "eth0", "bytesReceived": 10}],
        }
    }
    client = _client(settings, _recorder(data, seen))
    try:
        result = await client.temperatures()
    finally:
        await client.close()

    assert result["temperature"]["sensors"][0]["name"] == "CPU"
    assert result["network"][0]["name"] == "eth0"
    assert "temperature" in seen["query"]


@pytest.mark.asyncio
async def test_docker_extras(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    data = {
        "docker": {
            "containers": [{"id": "c1", "names": ["/plex"], "sizeLog": 10}],
            "containerUpdateStatuses": [{"name": "plex", "updateStatus": "UPDATE_AVAILABLE"}],
            "portConflicts": {"containerPorts": [], "lanPorts": []},
        }
    }
    client = _client(settings, _recorder(data, seen))
    try:
        extras = await client.docker_extras()
    finally:
        await client.close()

    assert extras["containers"][0]["names"] == ["/plex"]
    assert extras["updates"][0]["updateStatus"] == "UPDATE_AVAILABLE"
    assert extras["conflicts"] == {"containerPorts": [], "lanPorts": []}
    assert "containerUpdateStatuses" in seen["query"]
    assert "names" in seen["query"]


@pytest.mark.asyncio
async def test_api_keys_create_and_delete(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        if "CreateApiKey" in body["query"]:
            return httpx.Response(
                200,
                json={"data": {"apiKey": {"create": {"key": "secreta", "id": "k1"}}}},
                request=request,
            )
        if "DeleteApiKey" in body["query"]:
            return httpx.Response(
                200, json={"data": {"apiKey": {"delete": True}}}, request=request
            )
        return httpx.Response(
            200,
            json={"data": {"apiKeys": [{"id": "k1", "name": "bot"}]}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        assert await client.api_keys() == [{"id": "k1", "name": "bot"}]
        created = await client.create_api_key("bot", description="desde UnraidBot")
        deleted = await client.delete_api_key("k1")
    finally:
        await client.close()

    assert created == {"key": "secreta", "id": "k1"}
    assert deleted is True
    assert seen[1]["variables"] == {
        "input": {"name": "bot", "description": "desde UnraidBot", "roles": ["VIEWER"]}
    }
    assert seen[2]["variables"] == {"input": {"ids": ["k1"]}}


@pytest.mark.asyncio
async def test_rclone_remotes(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    data = {"rclone": {"remotes": [{"name": "backup", "type": "s3"}]}}
    client = _client(settings, _recorder(data, seen))
    try:
        assert await client.rclone_remotes() == [{"name": "backup", "type": "s3"}]
    finally:
        await client.close()
    assert "remotes" in seen["query"]


@pytest.mark.asyncio
async def test_update_temperature_config(settings: Settings) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        seen["variables"] = body.get("variables")
        return httpx.Response(
            200, json={"data": {"updateTemperatureConfig": True}}, request=request
        )

    client = _client(settings, handler)
    try:
        assert await client.update_temperature_config({"cpu_warning": 80}) is True
    finally:
        await client.close()

    assert seen["variables"] == {"input": {"thresholds": {"cpu_warning": 80}}}


@pytest.mark.asyncio
async def test_flash_backup(settings: Settings) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        seen["variables"] = body.get("variables")
        return httpx.Response(
            200,
            json={"data": {"initiateFlashBackup": {"status": "RUNNING"}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        result = await client.flash_backup("backup")
    finally:
        await client.close()

    assert result == {"status": "RUNNING"}
    assert seen["variables"] == {
        "input": {
            "remoteName": "backup",
            "sourcePath": "/boot",
            "destinationPath": "unraidbot-flash-backup",
        }
    }


@pytest.mark.asyncio
async def test_start_array_encrypted_always_sends_password(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body.get("variables"))
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        await client.start_array_encrypted("secreta")
        await client.start_array_encrypted()
    finally:
        await client.close()

    assert seen == [{"password": "secreta"}, {"password": None}]


@pytest.mark.asyncio
async def test_parity_start_with_correct_flag(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        await client.parity_action("start", correct=True)
        await client.parity_action("start")
    finally:
        await client.close()

    assert seen[0]["variables"] == {"correct": True}
    assert seen[1]["variables"] == {"correct": False}
    assert "StartParity" in seen[0]["query"]


@pytest.mark.asyncio
async def test_mount_and_unmount_array_disk(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        await client.mount_array_disk("disk:d1")
        await client.unmount_array_disk("disk:d1")
    finally:
        await client.close()

    assert "MountArrayDisk" in seen[0]["query"]
    assert "UnmountArrayDisk" in seen[1]["query"]
    assert seen[0]["variables"] == {"id": "disk:d1"}


@pytest.mark.asyncio
async def test_notifications_filtered_builds_filter(settings: Settings) -> None:
    seen: dict[str, Any] = {}
    data = {
        "notifications": {
            "overview": {"unread": {"alert": 1, "warning": 0, "info": 2, "total": 3}},
            "list": [{"id": "notif:1", "subject": "Aviso"}],
        }
    }
    client = _client(settings, _recorder(data, seen))
    try:
        view = await client.notifications_filtered(
            archived=True, importance="ALERT", offset=5, limit=10
        )
    finally:
        await client.close()

    assert view["overview"]["unread"]["total"] == 3
    assert view["items"][0]["subject"] == "Aviso"
    assert seen["variables"] == {
        "filter": {"type": "ARCHIVE", "offset": 5, "limit": 10, "importance": "ALERT"}
    }


@pytest.mark.asyncio
async def test_notification_mutations(settings: Settings) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"query": body["query"], "variables": body.get("variables")})
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        await client.archive_notification("notif:1")
        await client.unarchive_notification("notif:1")
        await client.mark_notification_unread("notif:1")
        await client.delete_notification("notif:1", archived=True)
        await client.create_notification(
            title="UnraidBot", subject="Hola", description="Texto", importance="INFO"
        )
    finally:
        await client.close()

    assert seen[0]["variables"] == {"id": "notif:1"}
    assert seen[1]["variables"] == {"ids": ["notif:1"]}
    assert seen[2]["variables"] == {"id": "notif:1"}
    assert seen[3]["variables"] == {"id": "notif:1", "type": "ARCHIVE"}
    assert seen[4]["variables"] == {
        "input": {
            "title": "UnraidBot",
            "subject": "Hola",
            "description": "Texto",
            "importance": "INFO",
        }
    }


@pytest.mark.asyncio
async def test_snapshot_without_health_does_not_request_extras(settings: Settings) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["query"])
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        snapshot = await client.snapshot(include_info=False)
    finally:
        await client.close()

    assert snapshot.parity_history is None
    assert snapshot.license is None
    assert snapshot.services is None
    assert not any("ParityHistory" in query for query in seen)
    assert not any("RegistrationInfo" in query for query in seen)


@pytest.mark.asyncio
async def test_snapshot_include_health_fills_extra_fields(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        if "ParityHistory" in query:
            return httpx.Response(
                200,
                json={"data": {"parityHistory": [{"status": "COMPLETED"}]}},
                request=request,
            )
        if "RegistrationInfo" in query:
            return httpx.Response(
                200,
                json={"data": {"registration": {"state": "BASIC"}, "flash": None}},
                request=request,
            )
        if "query Services" in query:
            return httpx.Response(
                200,
                json={"data": {"services": [{"name": "nginx", "online": True}]}},
                request=request,
            )
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        snapshot = await client.snapshot(include_info=False, include_health=True)
    finally:
        await client.close()

    assert snapshot.parity_history == [{"status": "COMPLETED"}]
    assert snapshot.license == {"registration": {"state": "BASIC"}, "flash": None}
    assert snapshot.services == [{"name": "nginx", "online": True}]
    assert snapshot.errors == {}


@pytest.mark.asyncio
async def test_snapshot_include_health_tolerates_failure(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        if "query Services" in query:
            return httpx.Response(
                200, json={"errors": [{"message": "Services no soportado"}]}, request=request
            )
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        snapshot = await client.snapshot(include_info=False, include_health=True)
    finally:
        await client.close()

    assert snapshot.services is None
    assert "Services no soportado" in snapshot.errors["services"]
    assert snapshot.parity_history == []
