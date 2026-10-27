"""Cliente de la WebAPI v2 de qBittorrent."""

from __future__ import annotations

import httpx

from ..config import Settings
from . import ServiceError


class QBittorrent:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.qbittorrent_url,
            timeout=15.0,
            verify=settings.qbittorrent_verify_ssl,
            follow_redirects=True,
            transport=transport,
        )
        self._logged_in = False

    async def close(self) -> None:
        await self._client.aclose()

    async def _login(self) -> None:
        try:
            response = await self._client.post(
                "/api/v2/auth/login",
                data={
                    "username": self.settings.qbittorrent_username,
                    "password": self.settings.qbittorrent_password,
                },
            )
        except httpx.HTTPError as exc:
            raise ServiceError(f"No se pudo conectar con qBittorrent: {exc}") from exc
        if response.status_code != 200 or response.text.strip() != "Ok.":
            raise ServiceError("qBittorrent rechazó usuario o contraseña.")
        self._logged_in = True

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self._login()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        data: dict | None = None,
        raw: bool = False,
    ) -> object:
        await self._ensure_login()
        try:
            response = await self._client.request(method, path, params=params, data=data)
            if response.status_code in (401, 403):
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.request(method, path, params=params, data=data)
        except httpx.HTTPError as exc:
            raise ServiceError(f"No se pudo conectar con qBittorrent: {exc}") from exc
        if response.status_code >= 400:
            raise ServiceError(f"qBittorrent devolvió HTTP {response.status_code}.")
        if raw:
            return response.text
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    async def _post(self, path: str, data: dict | None = None) -> None:
        await self._request("POST", path, data=data or {})

    async def status(self) -> dict:
        value = await self._request("GET", "/api/v2/transfer/info")
        return value if isinstance(value, dict) else {}

    async def torrents(self, filter: str | None = None) -> list[dict]:
        params = {"filter": filter} if filter else None
        value = await self._request("GET", "/api/v2/torrents/info", params=params)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    async def categories(self) -> dict[str, dict]:
        value = await self._request("GET", "/api/v2/torrents/categories")
        return value if isinstance(value, dict) else {}

    async def preferences(self) -> dict:
        value = await self._request("GET", "/api/v2/app/preferences")
        return value if isinstance(value, dict) else {}

    async def alt_speed_enabled(self) -> bool:
        value = await self._request("GET", "/api/v2/transfer/speedLimitsMode", raw=True)
        text = str(value).strip().lower()
        if text in {"1", "true"}:
            return True
        if text in {"0", "false"}:
            return False
        return bool(value)

    async def add(self, url: str, category: str = "", paused: bool = False) -> None:
        data = {"urls": url, "paused": "true" if paused else "false"}
        if category:
            data["category"] = category
        result = str(await self._request("POST", "/api/v2/torrents/add", data=data, raw=True))
        if result.strip().lower().startswith("fail"):
            raise ServiceError(
                "qBittorrent rechazó el torrent (enlace no válido o ya añadido)."
            )

    async def delete(self, torrent_hash: str, delete_files: bool = False) -> None:
        await self._post(
            "/api/v2/torrents/delete",
            {
                "hashes": torrent_hash,
                "deleteFiles": "true" if delete_files else "false",
            },
        )

    async def set_paused(self, torrent_hash: str, paused: bool) -> None:
        endpoint = "/api/v2/torrents/stop" if paused else "/api/v2/torrents/start"
        try:
            await self._post(endpoint, {"hashes": torrent_hash})
        except ServiceError as exc:
            if "404" not in str(exc):
                raise
            # qBittorrent < 5 usa pause/resume en lugar de stop/start.
            fallback = "/api/v2/torrents/pause" if paused else "/api/v2/torrents/resume"
            await self._post(fallback, {"hashes": torrent_hash})

    async def pause_all(self) -> None:
        await self.set_paused("all", True)

    async def resume_all(self) -> None:
        await self.set_paused("all", False)

    async def set_category(self, torrent_hash: str, category: str) -> None:
        await self._post(
            "/api/v2/torrents/setCategory",
            {"hashes": torrent_hash, "category": category},
        )

    async def set_download_limit(self, limit_bytes: int) -> None:
        await self._post(
            "/api/v2/transfer/setDownloadLimit", {"limit": str(max(0, int(limit_bytes)))}
        )

    async def set_upload_limit(self, limit_bytes: int) -> None:
        await self._post(
            "/api/v2/transfer/setUploadLimit", {"limit": str(max(0, int(limit_bytes)))}
        )

    async def toggle_alt_speed(self) -> None:
        await self._post("/api/v2/transfer/toggleSpeedLimitsMode")
