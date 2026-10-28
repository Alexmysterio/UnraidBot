"""Cliente asíncrono para la API GraphQL de Unraid.

La API se sirve por HTTP(S) en ``/graphql`` o por el socket Unix de nginx.
Todas las peticiones salen del contenedor: no hace falta abrir puertos.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import Settings

LOG = logging.getLogger(__name__)


class UnraidError(RuntimeError):
    """Error controlado de la API de Unraid."""


class UnraidConnectionError(UnraidError):
    """No se pudo contactar con la API."""


class UnraidPermissionError(UnraidError):
    """La clave de API no tiene permisos para la operación solicitada."""


_PERMISSION_HINTS = (
    "unauthorized",
    "forbidden",
    "not authorized",
    "permission",
    "access denied",
    "insufficient",
    "read-only",
    "read only",
    "not allowed",
    "requires write",
)


def _looks_like_permission_error(message: str) -> bool:
    lowered = message.lower()
    return any(hint in lowered for hint in _PERMISSION_HINTS)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

ARRAY_QUERY = """
query ArrayInfo {
  array {
    state
    capacity {
      kilobytes { free used total }
      disks { free used total }
    }
    parityCheckStatus {
      date duration speed status errors progress correcting paused running
    }
    parities {
      id idx name device size status temp rotational color isSpinning numErrors fsType
    }
    disks {
      id idx name device size status temp rotational color isSpinning numErrors
      fsType fsSize fsFree fsUsed transport format comment
    }
    caches {
      id idx name device size status temp rotational color isSpinning numErrors
      fsType fsSize fsFree fsUsed transport format comment
    }
  }
}
"""

DOCKER_QUERY = """
query DockerList {
  docker {
    containers {
      id names image state status autoStart isUpdateAvailable
      ports { privatePort publicPort type ip }
      webUiUrl hostConfig { networkMode }
    }
  }
}
"""

VMS_QUERY = """
query VmList {
  vms { domains { id name state } }
}
"""

METRICS_QUERY = """
query SystemMetrics {
  metrics {
    cpu { percentTotal }
    memory {
      total used free available percentTotal
      swapTotal swapUsed percentSwapTotal
    }
  }
}
"""

INFO_QUERY = """
query SystemInfo {
  info {
    time
    os { hostname distro release kernel arch uptime }
    system { manufacturer model }
    baseboard { manufacturer model version }
    cpu { manufacturer brand cores threads speed packages { temp totalPower } }
    memory { layout { size type clockSpeed manufacturer } }
    versions { core { unraid api kernel } packages { docker } }
    primaryNetwork { name ipAddress speed operstate ipv4Addresses { address } }
  }
}
"""

UPS_QUERY = """
query UpsInfo {
  upsDevices {
    id name model status
    battery { chargeLevel estimatedRuntime health }
    power { inputVoltage outputVoltage loadPercentage currentPower nominalPower }
  }
}
"""

NOTIFICATIONS_QUERY = """
query NotificationsInfo {
  notifications {
    overview {
      unread { info warning alert total }
      archive { info warning alert total }
    }
    warningsAndAlerts {
      id title subject description importance timestamp
    }
  }
}
"""

SHARES_QUERY = """
query SharesInfo {
  shares {
    name used free size cache comment nameOrig allocator splitLevel floor cow luksStatus
    include exclude
  }
}
"""

PHYSICAL_DISKS_QUERY = """
query PhysicalDisks {
  disks {
    id device name type size temperature smartStatus isSpinning
    interfaceType serialNum firmwareRevision
    partitions { name fsType size }
  }
}
"""

PING_QUERY = """
query Ping { online }
"""

PARITY_HISTORY_QUERY = """
query ParityHistory {
  parityHistory { date duration speed status errors progress correcting paused running }
}
"""

NOTIFICATIONS_LIST_QUERY = """
query NotificationsList($filter: NotificationFilter!) {
  notifications {
    overview {
      unread { info warning alert total }
      archive { info warning alert total }
    }
    list(filter: $filter) {
      id title subject description importance link type timestamp
    }
  }
}
"""

REGISTRATION_QUERY = """
query RegistrationInfo {
  registration { type state expiration updateExpiration keyFile { location } }
  flash { id guid vendor product }
}
"""

SERVER_QUERY = """
query ServerInfo {
  server { id name comment }
}
"""

PLUGINS_QUERY = """
query Plugins {
  plugins { name version hasApiModule hasCliModule }
}
"""

SERVICES_QUERY = """
query Services {
  services { id name online version uptime { timestamp } }
}
"""

NETWORK_QUERY = """
query NetworkInfo {
  networkInterfaces {
    id name description macAddress mtu speed duplex internal virtual operstate type vlanId
    ipv4Addresses { address netmask }
    ipv6Addresses { address prefixLength }
  }
  network { accessUrls { type name ipv4 ipv6 } }
}
"""

LOG_FILES_QUERY = """
query LogFiles {
  logFiles { name path size modifiedAt }
}
"""

LOG_FILE_QUERY = """
query LogFile($path: String!, $lines: Int, $startLine: Int) {
  logFile(path: $path, lines: $lines, startLine: $startLine) {
    path content totalLines startLine
  }
}
"""

TEMPERATURES_QUERY = """
query Temperatures {
  metrics {
    temperature {
      summary {
        average warningCount criticalCount
        hottest { name current { value unit } }
        coolest { name current { value unit } }
      }
      sensors {
        id name type location
        current { value unit status }
        min { value unit }
        max { value unit }
        warning critical
      }
    }
    network {
      id name operstate bytesReceived bytesSent packetsReceived packetsSent
      receiveErrors transmitErrors
    }
  }
}
"""

API_KEYS_QUERY = """
query ApiKeys {
  apiKeys { id name description roles createdAt }
}
"""

RCLONE_REMOTES_QUERY = """
query RcloneRemotes {
  rclone { remotes { name type } }
}
"""

DOCKER_EXTRAS_QUERY = """
query DockerExtras {
  docker {
    containers { id names sizeRootFs sizeRw sizeLog isOrphaned isRebuildReady }
    containerUpdateStatuses { name updateStatus }
    portConflicts {
      containerPorts { privatePort type containers { id name } }
      lanPorts { lanIpPort publicPort type containers { id name } }
    }
  }
}
"""

DOCKER_LOGS_QUERY = """
query DockerLogs($id: PrefixedID!, $tail: Int) {
  docker {
    logs(id: $id, tail: $tail) {
      lines { timestamp message }
    }
  }
}
"""

DOCKER_UPDATE_ALL = """
mutation UpdateAllContainers {
  docker { updateAllContainers { id state } }
}
"""

DOCKER_SET_AUTOSTART = """
mutation SetAutostart($entries: [DockerAutostartEntryInput!]!) {
  docker {
    updateAutostartConfiguration(entries: $entries, persistUserPreferences: true)
  }
}
"""

ARCHIVE_ALL_NOTIFICATIONS = """
mutation ArchiveAllNotifications {
  archiveAll {
    unread { total }
    archive { total }
  }
}
"""

ARCHIVE_NOTIFICATION = """
mutation ArchiveNotification($id: PrefixedID!) {
  archiveNotification(id: $id) { id type }
}
"""

UNARCHIVE_NOTIFICATIONS = """
mutation UnarchiveNotifications($ids: [PrefixedID!]!) {
  unarchiveNotifications(ids: $ids) {
    unread { total }
    archive { total }
  }
}
"""

UNREAD_NOTIFICATION = """
mutation UnreadNotification($id: PrefixedID!) {
  unreadNotification(id: $id) { id type }
}
"""

DELETE_NOTIFICATION = """
mutation DeleteNotification($id: PrefixedID!, $type: NotificationType!) {
  deleteNotification(id: $id, type: $type) {
    unread { total }
    archive { total }
  }
}
"""

CREATE_NOTIFICATION = """
mutation CreateNotification($input: NotificationData!) {
  createNotification(input: $input) { id }
}
"""

ARRAY_SET_STATE = """
mutation SetArrayState($state: ArrayStateInputState!) {
  array { setState(input: { desiredState: $state }) { state } }
}
"""

ARRAY_START_WITH_PASSWORD = """
mutation StartArrayEncrypted($password: String) {
  array {
    setState(input: { desiredState: START, decryptionPassword: $password }) { state }
  }
}
"""

PARITY_START = """
mutation StartParity($correct: Boolean!) {
  parityCheck { start(correct: $correct) }
}
"""

PARITY_MUTATIONS = {
    "pause": "mutation { parityCheck { pause } }",
    "resume": "mutation { parityCheck { resume } }",
    "cancel": "mutation { parityCheck { cancel } }",
}

MOUNT_ARRAY_DISK = """
mutation MountArrayDisk($id: PrefixedID!) {
  array { mountArrayDisk(id: $id) { id name } }
}
"""

UNMOUNT_ARRAY_DISK = """
mutation UnmountArrayDisk($id: PrefixedID!) {
  array { unmountArrayDisk(id: $id) { id name } }
}
"""

INSTALL_PLUGIN = """
mutation InstallPlugin($input: InstallPluginInput!) {
  unraidPlugins {
    installPlugin(input: $input) { id status name url output }
  }
}
"""

FLASH_BACKUP = """
mutation FlashBackup($input: InitiateFlashBackupInput!) {
  initiateFlashBackup(input: $input) { status jobId }
}
"""

TEMPERATURE_CONFIG = """
mutation TemperatureConfig($input: TemperatureConfigInput!) {
  updateTemperatureConfig(input: $input)
}
"""

API_KEY_CREATE = """
mutation CreateApiKey($input: CreateApiKeyInput!) {
  apiKey {
    create(input: $input) { id key name description roles createdAt }
  }
}
"""

API_KEY_DELETE = """
mutation DeleteApiKey($input: DeleteApiKeyInput!) {
  apiKey { delete(input: $input) }
}
"""

SERVER_IDENTITY = """
mutation ServerIdentity($name: String!, $comment: String) {
  updateServerIdentity(name: $name, comment: $comment) { id name comment }
}
"""

DOCKER_ACTIONS = {
    "start": "start",
    "stop": "stop",
    "restart": "restart",
    "pause": "pause",
    "unpause": "unpause",
    "update": "updateContainer",
}

VM_ACTIONS = {
    "start": "start",
    "stop": "stop",
    "force_stop": "forceStop",
    "pause": "pause",
    "resume": "resume",
    "reboot": "reboot",
    "reset": "reset",
}


def normalize_api_url(url: str) -> str:
    """Acepta ``http://host`` o ``http://host/graphql``."""
    clean = url.strip().rstrip("/")
    if clean.endswith("/graphql"):
        return clean
    return clean + "/graphql"


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Snapshot:
    """Fotografía del servidor con errores parciales tolerados."""

    array: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    info: dict[str, Any] | None = None
    ups: list[dict[str, Any]] | None = None
    notifications: dict[str, Any] | None = None
    docker: list[dict[str, Any]] | None = None
    vms: list[dict[str, Any]] | None = None
    physical_disks: list[dict[str, Any]] | None = None
    shares: list[dict[str, Any]] | None = None
    parity_history: list[dict[str, Any]] | None = None
    license: dict[str, Any] | None = None
    services: list[dict[str, Any]] | None = None
    errors: dict[str, str] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def reachable(self) -> bool:
        values = (
            self.array,
            self.metrics,
            self.info,
            self.ups,
            self.notifications,
            self.docker,
            self.vms,
            self.physical_disks,
            self.shares,
        )
        return any(value is not None for value in values)


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class UnraidClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        headers = {
            "x-api-key": settings.unraid_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "unraidbot/1.0",
        }
        timeout = httpx.Timeout(settings.request_timeout, connect=10.0)

        if transport is not None:
            self._http = httpx.AsyncClient(transport=transport, timeout=timeout, headers=headers)
            self._endpoint = normalize_api_url(settings.unraid_api_url)
        elif settings.unraid_api_socket:
            socket_transport = httpx.AsyncHTTPTransport(uds=settings.unraid_api_socket, retries=0)
            self._http = httpx.AsyncClient(
                transport=socket_transport,
                timeout=timeout,
                headers=headers,
            )
            self._endpoint = "http://localhost/graphql"
        else:
            self._http = httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                verify=settings.unraid_verify_ssl,
                follow_redirects=True,
            )
            self._endpoint = normalize_api_url(settings.unraid_api_url)

    async def close(self) -> None:
        await self._http.aclose()

    # -- transporte ---------------------------------------------------------

    async def _execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        retry: bool = True,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        attempts = 2 if retry else 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            kwargs: dict[str, Any] = {"json": payload}
            if timeout is not None:
                kwargs["timeout"] = timeout
            try:
                response = await self._http.post(self._endpoint, **kwargs)
            except httpx.HTTPError as exc:
                last_error = exc
                LOG.warning("Fallo de red con Unraid (intento %s): %s", attempt + 1, exc)
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.5)
                    continue
                raise UnraidConnectionError(
                    "No se pudo contactar con la API de Unraid. Revisa UNRAID_API_URL, "
                    "que el servidor esté encendido y la conectividad de la red Docker."
                ) from exc

            if response.status_code in (401, 403):
                raise UnraidPermissionError(
                    f"La API de Unraid rechazó la clave (HTTP {response.status_code}). "
                    "Comprueba UNRAID_API_KEY y que tenga permisos de administración."
                )

            body: Any = None
            try:
                body = response.json()
            except ValueError:
                body = None

            if isinstance(body, dict) and body.get("errors"):
                messages = []
                for item in body["errors"][:3]:
                    if isinstance(item, dict):
                        messages.append(str(item.get("message") or "error"))
                detail = "; ".join(messages) or "Error GraphQL desconocido"
                if _looks_like_permission_error(detail):
                    raise UnraidPermissionError(detail)
                raise UnraidError(detail)

            if response.status_code >= 500:
                last_error = UnraidError(f"La API de Unraid devolvió HTTP {response.status_code}.")
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.5)
                    continue
                raise UnraidError(
                    f"La API de Unraid devolvió HTTP {response.status_code}. "
                    "Revisa el estado del servicio con `unraid-api status`."
                )

            if not isinstance(body, dict):
                raise UnraidError(f"Respuesta no válida de la API (HTTP {response.status_code}).")

            if response.status_code >= 400:
                raise UnraidError(f"La API de Unraid devolvió HTTP {response.status_code}.")

            data = body.get("data")
            if not isinstance(data, dict):
                raise UnraidError("La API de Unraid devolvió una respuesta vacía.")
            return data

        raise UnraidConnectionError(str(last_error or "Error de conexión desconocido"))

    # -- lecturas -----------------------------------------------------------

    async def ping(self) -> bool:
        data = await self._execute(PING_QUERY)
        return bool(data.get("online"))

    async def array(self) -> dict[str, Any]:
        data = await self._execute(ARRAY_QUERY)
        return data.get("array") or {}

    async def docker_containers(self) -> list[dict[str, Any]]:
        data = await self._execute(DOCKER_QUERY)
        return ((data.get("docker") or {}).get("containers")) or []

    async def vms(self) -> list[dict[str, Any]]:
        data = await self._execute(VMS_QUERY)
        return ((data.get("vms") or {}).get("domains")) or []

    async def metrics(self) -> dict[str, Any]:
        data = await self._execute(METRICS_QUERY)
        return data.get("metrics") or {}

    async def info(self) -> dict[str, Any]:
        data = await self._execute(INFO_QUERY)
        return data.get("info") or {}

    async def ups(self) -> list[dict[str, Any]]:
        data = await self._execute(UPS_QUERY)
        return data.get("upsDevices") or []

    async def notifications(self) -> dict[str, Any]:
        data = await self._execute(NOTIFICATIONS_QUERY)
        return data.get("notifications") or {}

    async def shares(self) -> list[dict[str, Any]]:
        data = await self._execute(SHARES_QUERY)
        return data.get("shares") or []

    async def physical_disks(self) -> list[dict[str, Any]]:
        data = await self._execute(PHYSICAL_DISKS_QUERY)
        return data.get("disks") or []

    async def docker_logs(self, container_id: str, tail: int = 40) -> list[dict[str, Any]]:
        data = await self._execute(DOCKER_LOGS_QUERY, {"id": container_id, "tail": tail})
        return ((data.get("docker") or {}).get("logs") or {}).get("lines") or []

    async def snapshot(
        self,
        *,
        include_info: bool = True,
        include_storage: bool = False,
        include_health: bool = False,
    ) -> Snapshot:
        """Lanza las consultas en paralelo y tolera fallos parciales.

        ``include_storage`` añade discos físicos (SMART) y shares. Solo se usa
        en las pantallas y en el monitor que necesitan esos datos.
        ``include_health`` añade el historial de paridad, la licencia y los
        servicios; solo lo pide el monitor de alertas.
        """
        jobs: dict[str, Any] = {
            "array": self.array(),
            "metrics": self.metrics(),
            "ups": self.ups(),
            "notifications": self.notifications(),
            "docker": self.docker_containers(),
            "vms": self.vms(),
        }
        if include_info:
            jobs["info"] = self.info()
        if include_storage:
            jobs["physical_disks"] = self.physical_disks()
            jobs["shares"] = self.shares()
        if include_health:
            jobs["parity_history"] = self.parity_history()
            jobs["license"] = self.registration()
            jobs["services"] = self.services()

        results = await asyncio.gather(*jobs.values(), return_exceptions=True)
        snapshot = Snapshot()
        for name, result in zip(jobs, results):
            if isinstance(result, Exception):
                snapshot.errors[name] = str(result)
                LOG.warning("Consulta %s falló: %s", name, result)
            else:
                setattr(snapshot, name, result)
        return snapshot

    # -- mutaciones ---------------------------------------------------------

    async def docker_action(self, action: str, container_id: str) -> None:
        field = DOCKER_ACTIONS.get(action)
        if field is None:
            raise ValueError(f"Acción Docker desconocida: {action}")
        query = f"mutation($id: PrefixedID!) {{ docker {{ {field}(id: $id) {{ id state }} }} }}"
        # Una actualización puede tardar minutos (pull + recreate).
        timeout = 300.0 if action == "update" else None
        await self._execute(query, {"id": container_id}, retry=False, timeout=timeout)

    async def vm_action(self, action: str, vm_id: str) -> bool:
        field = VM_ACTIONS.get(action)
        if field is None:
            raise ValueError(f"Acción de VM desconocida: {action}")
        query = f"mutation($id: PrefixedID!) {{ vm {{ {field}(id: $id) }} }}"
        data = await self._execute(query, {"id": vm_id}, retry=False)
        return bool((data.get("vm") or {}).get(field))

    async def set_array_state(self, state: str) -> None:
        if state not in {"START", "STOP"}:
            raise ValueError(f"Estado de array inválido: {state}")
        await self._execute(ARRAY_SET_STATE, {"state": state}, retry=False, timeout=180.0)

    async def parity_action(self, action: str, *, correct: bool = False) -> None:
        if action == "start":
            await self._execute(PARITY_START, {"correct": correct}, retry=False)
            return
        query = PARITY_MUTATIONS.get(action)
        if query is None:
            raise ValueError(f"Acción de paridad desconocida: {action}")
        await self._execute(query, retry=False)

    async def docker_update_all(self) -> None:
        """Actualiza todos los contenedores con imagen nueva."""
        await self._execute(DOCKER_UPDATE_ALL, retry=False, timeout=900.0)

    async def docker_set_autostart(self, container_id: str, auto_start: bool) -> None:
        await self._execute(
            DOCKER_SET_AUTOSTART,
            {
                "entries": [
                    {
                        "id": container_id,
                        "autoStart": auto_start,
                    }
                ]
            },
            retry=False,
        )

    async def archive_all_notifications(self) -> None:
        """Archiva todas las notificaciones no leídas."""
        await self._execute(ARCHIVE_ALL_NOTIFICATIONS, retry=False)

    # -- notificaciones -----------------------------------------------------

    async def notifications_page(
        self,
        *,
        archived: bool = False,
        importance: str | None = None,
        offset: int = 0,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Lista notificaciones leídas o archivadas, con filtro opcional."""
        view = await self.notifications_filtered(
            archived=archived, importance=importance, offset=offset, limit=limit
        )
        return view["items"]

    async def notifications_filtered(
        self,
        *,
        archived: bool = False,
        importance: str | None = None,
        offset: int = 0,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Devuelve el resumen y la página de notificaciones en una sola consulta."""
        filter_data: dict[str, Any] = {
            "type": "ARCHIVE" if archived else "UNREAD",
            "offset": max(0, offset),
            "limit": max(1, limit),
        }
        if importance:
            filter_data["importance"] = importance
        data = await self._execute(NOTIFICATIONS_LIST_QUERY, {"filter": filter_data})
        notifications = data.get("notifications") or {}
        return {
            "overview": notifications.get("overview") or {},
            "items": notifications.get("list") or [],
        }

    async def archive_notification(self, notification_id: str) -> None:
        await self._execute(ARCHIVE_NOTIFICATION, {"id": notification_id}, retry=False)

    async def unarchive_notification(self, notification_id: str) -> None:
        await self._execute(
            UNARCHIVE_NOTIFICATIONS, {"ids": [notification_id]}, retry=False
        )

    async def mark_notification_unread(self, notification_id: str) -> None:
        await self._execute(UNREAD_NOTIFICATION, {"id": notification_id}, retry=False)

    async def delete_notification(
        self, notification_id: str, *, archived: bool = False
    ) -> None:
        await self._execute(
            DELETE_NOTIFICATION,
            {"id": notification_id, "type": "ARCHIVE" if archived else "UNREAD"},
            retry=False,
        )

    async def create_notification(
        self,
        *,
        title: str,
        subject: str,
        description: str,
        importance: str = "INFO",
        link: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "title": title,
            "subject": subject,
            "description": description,
            "importance": importance,
        }
        if link:
            payload["link"] = link
        await self._execute(CREATE_NOTIFICATION, {"input": payload}, retry=False)

    # -- sistema ampliado ---------------------------------------------------

    async def parity_history(self) -> list[dict[str, Any]]:
        data = await self._execute(PARITY_HISTORY_QUERY)
        return data.get("parityHistory") or []

    async def registration(self) -> dict[str, Any]:
        data = await self._execute(REGISTRATION_QUERY)
        return {
            "registration": data.get("registration"),
            "flash": data.get("flash"),
        }

    async def server_identity(self) -> dict[str, Any]:
        data = await self._execute(SERVER_QUERY)
        return data.get("server") or {}

    async def set_server_identity(self, name: str, comment: str | None = None) -> dict[str, Any]:
        data = await self._execute(
            SERVER_IDENTITY, {"name": name, "comment": comment}, retry=False
        )
        return data.get("updateServerIdentity") or {}

    async def plugins(self) -> list[dict[str, Any]]:
        data = await self._execute(PLUGINS_QUERY)
        return data.get("plugins") or []

    async def install_plugin(self, url: str, name: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url, "forced": True}
        if name:
            payload["name"] = name
        data = await self._execute(
            INSTALL_PLUGIN, {"input": payload}, retry=False, timeout=600.0
        )
        return ((data.get("unraidPlugins") or {}).get("installPlugin")) or {}

    async def services(self) -> list[dict[str, Any]]:
        data = await self._execute(SERVICES_QUERY)
        return data.get("services") or []

    async def network(self) -> dict[str, Any]:
        data = await self._execute(NETWORK_QUERY)
        return {
            "interfaces": data.get("networkInterfaces") or [],
            "access_urls": ((data.get("network") or {}).get("accessUrls")) or [],
        }

    async def log_files(self) -> list[dict[str, Any]]:
        data = await self._execute(LOG_FILES_QUERY)
        return data.get("logFiles") or []

    async def log_file(self, path: str, *, lines: int = 200, start_line: int | None = None) -> dict[str, Any]:
        variables: dict[str, Any] = {"path": path, "lines": max(1, lines)}
        if start_line is not None:
            variables["startLine"] = max(0, start_line)
        data = await self._execute(LOG_FILE_QUERY, variables)
        return data.get("logFile") or {}

    async def temperatures(self) -> dict[str, Any]:
        data = await self._execute(TEMPERATURES_QUERY)
        metrics = data.get("metrics") or {}
        return {
            "temperature": metrics.get("temperature") or {},
            "network": metrics.get("network") or [],
        }

    async def docker_extras(self) -> dict[str, Any]:
        data = await self._execute(DOCKER_EXTRAS_QUERY)
        docker = data.get("docker") or {}
        return {
            "containers": docker.get("containers") or [],
            "updates": docker.get("containerUpdateStatuses") or [],
            "conflicts": docker.get("portConflicts") or {},
        }

    async def api_keys(self) -> list[dict[str, Any]]:
        data = await self._execute(API_KEYS_QUERY)
        return data.get("apiKeys") or []

    async def rclone_remotes(self) -> list[dict[str, Any]]:
        data = await self._execute(RCLONE_REMOTES_QUERY)
        return ((data.get("rclone") or {}).get("remotes")) or []

    async def create_api_key(self, name: str, *, description: str = "") -> dict[str, Any]:
        data = await self._execute(
            API_KEY_CREATE,
            {
                "input": {
                    "name": name,
                    "description": description,
                    "roles": ["VIEWER"],
                }
            },
            retry=False,
        )
        return ((data.get("apiKey") or {}).get("create")) or {}

    async def delete_api_key(self, key_id: str) -> bool:
        data = await self._execute(
            API_KEY_DELETE, {"input": {"ids": [key_id]}}, retry=False
        )
        return bool((data.get("apiKey") or {}).get("delete"))

    async def update_temperature_config(self, thresholds: dict[str, Any]) -> bool:
        data = await self._execute(
            TEMPERATURE_CONFIG, {"input": {"thresholds": thresholds}}, retry=False
        )
        return bool(data.get("updateTemperatureConfig"))

    async def flash_backup(
        self,
        remote: str,
        *,
        source: str = "/boot",
        destination: str = "unraidbot-flash-backup",
    ) -> dict[str, Any]:
        data = await self._execute(
            FLASH_BACKUP,
            {
                "input": {
                    "remoteName": remote,
                    "sourcePath": source,
                    "destinationPath": destination,
                }
            },
            retry=False,
            timeout=600.0,
        )
        return data.get("initiateFlashBackup") or {}

    async def start_array_encrypted(self, password: str | None = None) -> None:
        await self._execute(
            ARRAY_START_WITH_PASSWORD,
            {"password": password},
            retry=False,
            timeout=180.0,
        )

    async def mount_array_disk(self, disk_id: str) -> None:
        await self._execute(MOUNT_ARRAY_DISK, {"id": disk_id}, retry=False)

    async def unmount_array_disk(self, disk_id: str) -> None:
        await self._execute(UNMOUNT_ARRAY_DISK, {"id": disk_id}, retry=False)

