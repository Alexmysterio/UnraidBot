"""Cliente de la API REST de RouterOS 7."""

from __future__ import annotations

import httpx

from ..config import Settings
from . import ServiceError


class MikroTik:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.mikrotik_url,
            auth=(settings.mikrotik_username, settings.mikrotik_password),
            timeout=15.0,
            verify=settings.mikrotik_verify_ssl,
            follow_redirects=True,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> object:
        try:
            response = await self._client.get(path)
        except httpx.HTTPError as exc:
            raise ServiceError(f"No se pudo conectar con MikroTik: {exc}") from exc
        if response.status_code in (401, 403):
            raise ServiceError("MikroTik rechazó usuario o contraseña.")
        if response.status_code >= 400:
            raise ServiceError(f"MikroTik devolvió HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _single(value: object) -> dict:
        if isinstance(value, list):
            return value[0] if value and isinstance(value[0], dict) else {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _list(value: object) -> list[dict]:
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    async def identity(self) -> dict:
        return self._single(await self._get("/rest/system/identity"))

    async def resource(self) -> dict:
        return self._single(await self._get("/rest/system/resource"))

    async def interfaces(self) -> list[dict]:
        return self._list(await self._get("/rest/interface"))

    async def leases(self) -> list[dict]:
        return self._list(await self._get("/rest/ip/dhcp-server/lease"))

    async def routes(self) -> list[dict]:
        return self._list(await self._get("/rest/ip/route"))

    async def firewall(self) -> list[dict]:
        return self._list(await self._get("/rest/ip/firewall/filter"))

    async def logs(self) -> list[dict]:
        return self._list(await self._get("/rest/log"))

    async def reboot(self) -> None:
        try:
            response = await self._client.post("/rest/system/reboot")
        except httpx.ReadError:
            return
        except httpx.HTTPError as exc:
            raise ServiceError(f"No se pudo reiniciar MikroTik: {exc}") from exc
        if response.status_code >= 400:
            raise ServiceError(f"MikroTik devolvió HTTP {response.status_code}.")
