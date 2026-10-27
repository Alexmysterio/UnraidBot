from __future__ import annotations

import json

import httpx
import pytest

from bot.config import Settings
from bot.unraid import (
    Snapshot,
    UnraidClient,
    UnraidError,
    UnraidPermissionError,
    normalize_api_url,
)


def _client(settings: Settings, handler) -> UnraidClient:
    return UnraidClient(settings, transport=httpx.MockTransport(handler))


def test_normalize_api_url() -> None:
    assert normalize_api_url("http://host") == "http://host/graphql"
    assert normalize_api_url("http://host/") == "http://host/graphql"
    assert normalize_api_url("http://host/graphql") == "http://host/graphql"
    assert normalize_api_url("https://host:443/graphql/") == "https://host:443/graphql"


@pytest.mark.asyncio
async def test_query_headers_and_url(settings: Settings) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("x-api-key", "")
        seen["url"] = str(request.url)
        body = json.loads(request.content)
        seen["query"] = body["query"]
        return httpx.Response(200, json={"data": {"array": {"state": "STARTED"}}}, request=request)

    client = _client(settings, handler)
    try:
        array = await client.array()
    finally:
        await client.close()

    assert array == {"state": "STARTED"}
    assert seen["key"] == "test-key"
    assert seen["url"] == "http://unraid.local/graphql"
    assert "ArrayInfo" in seen["query"]


@pytest.mark.asyncio
async def test_graphql_error_is_raised(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "Array no disponible"}]},
            request=request,
        )

    client = _client(settings, handler)
    try:
        with pytest.raises(UnraidError, match="Array no disponible"):
            await client.array()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_unauthorized_message(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={}, request=request)

    client = _client(settings, handler)
    try:
        with pytest.raises(UnraidPermissionError, match="rechazó la clave"):
            await client.array()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_graphql_permission_error_is_classified(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "Unauthorized: API key is read-only"}]},
            request=request,
        )

    client = _client(settings, handler)
    try:
        with pytest.raises(UnraidPermissionError, match="read-only"):
            await client.archive_all_notifications()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_graphql_non_permission_error_stays_generic(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "Field 'foo' does not exist"}]},
            request=request,
        )

    client = _client(settings, handler)
    try:
        with pytest.raises(UnraidError) as excinfo:
            await client.array()
        assert not isinstance(excinfo.value, UnraidPermissionError)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_retry_on_server_error(settings: Settings) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(500, text="boom", request=request)
        return httpx.Response(200, json={"data": {"array": {"state": "STARTED"}}}, request=request)

    client = _client(settings, handler)
    try:
        array = await client.array()
    finally:
        await client.close()
    assert array["state"] == "STARTED"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_snapshot_tolerates_partial_failure(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        if "UpsInfo" in query:
            return httpx.Response(200, json={"errors": [{"message": "UPS no soportado"}]}, request=request)
        if "ArrayInfo" in query:
            return httpx.Response(200, json={"data": {"array": {"state": "STARTED"}}}, request=request)
        return httpx.Response(200, json={"data": {}}, request=request)

    client = _client(settings, handler)
    try:
        snapshot = await client.snapshot()
    finally:
        await client.close()

    assert isinstance(snapshot, Snapshot)
    assert snapshot.array == {"state": "STARTED"}
    assert snapshot.ups is None
    assert "UPS no soportado" in snapshot.errors["ups"]
    assert snapshot.reachable is True


@pytest.mark.asyncio
async def test_docker_action_mutation(settings: Settings) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        seen["variables"] = body["variables"]
        return httpx.Response(
            200,
            json={"data": {"docker": {"start": {"id": "abc", "state": "RUNNING"}}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        await client.docker_action("start", "abc")
    finally:
        await client.close()

    assert "start(id: $id)" in str(seen["query"])
    assert seen["variables"] == {"id": "abc"}


@pytest.mark.asyncio
async def test_invalid_action_raises(settings: Settings) -> None:
    client = _client(settings, lambda request: httpx.Response(200, json={"data": {}}, request=request))
    try:
        with pytest.raises(ValueError):
            await client.docker_action("destroy", "abc")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_docker_update_all_mutation(settings: Settings) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        return httpx.Response(
            200,
            json={"data": {"docker": {"updateAllContainers": []}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        await client.docker_update_all()
    finally:
        await client.close()

    assert "updateAllContainers" in str(seen["query"])


@pytest.mark.asyncio
async def test_docker_set_autostart_mutation(settings: Settings) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["query"] = body["query"]
        seen["variables"] = body["variables"]
        return httpx.Response(
            200,
            json={"data": {"docker": {"updateAutostartConfiguration": True}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        await client.docker_set_autostart("abc", True)
    finally:
        await client.close()

    assert "updateAutostartConfiguration" in str(seen["query"])
    assert seen["variables"] == {"entries": [{"id": "abc", "autoStart": True}]}


@pytest.mark.asyncio
async def test_archive_all_notifications(settings: Settings) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = json.loads(request.content)["query"]
        return httpx.Response(
            200,
            json={"data": {"archiveAll": {"unread": {"total": 0}, "archive": {"total": 3}}}},
            request=request,
        )

    client = _client(settings, handler)
    try:
        await client.archive_all_notifications()
    finally:
        await client.close()

    assert "archiveAll" in str(seen["query"])
