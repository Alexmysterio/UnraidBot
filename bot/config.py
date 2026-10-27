"""Carga y validación de la configuración desde variables de entorno."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(RuntimeError):
    """La configuración es inválida o incompleta."""


@dataclass(frozen=True, slots=True)
class WolDevice:
    """Equipo encendible por Wake-on-LAN."""

    name: str
    mac: str
    broadcast: str = "255.255.255.255"


_SERVICE_ACTIVE = {"active", "on", "true", "yes", "y", "1", "si", "sí"}
_SERVICE_INACTIVE = {"noactive", "inactive", "off", "false", "no", "n", "0"}
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _SERVICE_ACTIVE


def _as_service(value: str | None, default: bool = False, name: str = "") -> bool:
    """Interpreta ``active`` / ``noactive`` (y sinónimos) para un servicio."""
    label = f"{name}: " if name else ""
    if value is None or value.strip() == "":
        return default
    normalized = value.strip().lower()
    if normalized in _SERVICE_ACTIVE:
        return True
    if normalized in _SERVICE_INACTIVE:
        return False
    raise ConfigError(
        f"{label}se esperaba 'active' o 'noactive', se recibió {value!r}"
    )


def _service_flag(
    source: Mapping[str, str],
    service_name: str,
    legacy_name: str,
    default: bool = False,
) -> bool:
    """Lee ``SERVICE_*`` y cae a ``FEATURE_*`` por compatibilidad."""
    raw = source.get(service_name)
    name = service_name
    if raw is None or raw.strip() == "":
        raw = source.get(legacy_name)
        name = legacy_name
    return _as_service(raw, default, name=name)


def _parse_wol_devices(
    raw: str | None,
    legacy_mac: str,
    default_broadcast: str,
    legacy: bool = False,
) -> tuple[WolDevice, ...]:
    """Convierte ``Nombre=MAC[@broadcast],...`` en equipos validados."""
    source_name = "WOL_MAC" if legacy else "WOL_DEVICES"
    entries: list[str] = []
    for line in (raw or "").replace(";", "\n").splitlines():
        entries.extend(part for part in line.split(",") if part.strip())
    if not entries and legacy_mac:
        entries = [f"Equipo={legacy_mac}"]
        source_name = "WOL_MAC"

    devices: list[WolDevice] = []
    names: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        text = entry.strip()
        if not text:
            continue
        if "=" in text:
            name, value = text.split("=", 1)
        else:
            name, value = f"Equipo {index}", text
        name = name.strip() or f"Equipo {index}"
        value = value.strip()
        broadcast = default_broadcast
        if "@" in value:
            value, broadcast = value.rsplit("@", 1)
            broadcast = broadcast.strip() or default_broadcast
        if not _MAC_RE.match(value):
            raise ConfigError(
                f"{source_name}: MAC inválida para {name!r}: {value!r}. "
                "Usa el formato AA:BB:CC:DD:EE:FF."
            )
        if name.casefold() in names:
            raise ConfigError(f"{source_name}: nombre de equipo duplicado {name!r}.")
        names.add(name.casefold())
        devices.append(
            WolDevice(name=name, mac=value.upper().replace("-", ":"), broadcast=broadcast)
        )
    return tuple(devices)


def _as_int(
    value: str | None,
    default: int,
    minimum: int | None = None,
    name: str = "",
) -> int:
    label = f"{name}: " if name else ""
    if value is None or value.strip() == "":
        number = default
    else:
        try:
            number = int(value.strip())
        except ValueError as exc:
            raise ConfigError(f"{label}se esperaba un número entero, se recibió {value!r}") from exc
    if minimum is not None and number < minimum:
        raise ConfigError(f"{label}el valor {number} es menor que el mínimo permitido ({minimum})")
    return number


def _as_id_set(value: str | None) -> frozenset[int]:
    """Convierte '123, 456 789' en un conjunto de enteros."""
    if not value:
        return frozenset()
    result: set[int] = set()
    for chunk in value.replace(";", ",").replace(" ", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            result.add(int(chunk))
        except ValueError as exc:
            raise ConfigError(f"ID de Telegram inválido: {chunk!r}") from exc
    return frozenset(result)


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración inmutable del bot."""

    telegram_token: str
    unraid_api_url: str
    unraid_api_key: str
    unraid_api_socket: str | None
    unraid_verify_ssl: bool
    allowed_user_ids: frozenset[int]
    viewer_user_ids: frozenset[int]
    allowed_chat_ids: frozenset[int]
    read_only: bool
    data_dir: Path
    alerts_enabled: bool
    alert_interval_seconds: int
    alert_repeat_minutes: int
    disk_temp_warning: int
    disk_temp_critical: int
    cpu_temp_warning: int
    memory_warning: int
    array_usage_warning: int
    share_usage_warning: int
    parity_max_days: int
    api_offline_alert: bool
    digest_enabled: bool
    digest_hour: int
    digest_minute: int
    timezone: str
    log_level: str
    request_timeout: int
    bot_container_name: str
    feature_qbittorrent: bool
    qbittorrent_url: str
    qbittorrent_username: str
    qbittorrent_password: str
    qbittorrent_verify_ssl: bool
    feature_mikrotik: bool
    mikrotik_url: str
    mikrotik_username: str
    mikrotik_password: str
    mikrotik_verify_ssl: bool
    feature_wol: bool
    wol_mac: str
    wol_broadcast: str
    wol_devices: tuple[WolDevice, ...]
    telegram_proxy_enabled: bool
    telegram_proxy_url: str
    telegram_rate_limit: bool
    telegram_rate_limit_max_retries: int
    user_rate_limit_actions: int
    user_rate_limit_window: int

    @property
    def is_configured(self) -> bool:
        """True si hay al menos un usuario (admin o de solo lectura)."""
        return bool(self.allowed_user_ids or self.viewer_user_ids)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env
        errors: list[str] = []

        token = (source.get("TELEGRAM_BOT_TOKEN") or "").strip()
        if not token:
            errors.append("Falta TELEGRAM_BOT_TOKEN (token de @BotFather).")
        elif ":" not in token or not token.split(":", 1)[0].isdigit():
            errors.append("TELEGRAM_BOT_TOKEN no tiene el formato esperado (123456:ABC...).")

        api_key = (source.get("UNRAID_API_KEY") or "").strip()
        if not api_key:
            errors.append("Falta UNRAID_API_KEY (Settings → Management Access → API Keys).")

        api_socket = (source.get("UNRAID_API_SOCKET") or "").strip() or None
        api_url = (source.get("UNRAID_API_URL") or "").strip()
        if not api_url and not api_socket:
            api_url = "http://host.docker.internal/graphql"
        if api_url and not api_url.startswith(("http://", "https://")):
            errors.append("UNRAID_API_URL debe empezar por http:// o https://.")

        try:
            allowed_users = _as_id_set(source.get("ALLOWED_USER_IDS"))
        except ConfigError as exc:
            errors.append(str(exc))
            allowed_users = frozenset()
        try:
            viewer_users = _as_id_set(source.get("VIEWER_USER_IDS"))
        except ConfigError as exc:
            errors.append(str(exc))
            viewer_users = frozenset()
        try:
            allowed_chats = _as_id_set(source.get("ALLOWED_CHAT_IDS"))
        except ConfigError as exc:
            errors.append(str(exc))
            allowed_chats = frozenset()

        timezone = (source.get("TIMEZONE") or "Europe/Madrid").strip()
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            errors.append(f"TIMEZONE no es una zona IANA válida: {timezone!r}.")

        data_dir = Path((source.get("DATA_DIR") or "/data").strip()).expanduser()

        log_level = (source.get("LOG_LEVEL") or "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            errors.append(f"LOG_LEVEL inválido: {log_level!r}.")

        try:
            alert_interval = _as_int(source.get("ALERT_INTERVAL_SECONDS"), 300, minimum=60, name="ALERT_INTERVAL_SECONDS")
            repeat = _as_int(source.get("ALERT_REPEAT_MINUTES"), 360, minimum=5, name="ALERT_REPEAT_MINUTES")
            disk_warning = _as_int(source.get("DISK_TEMP_WARNING"), 50, minimum=20, name="DISK_TEMP_WARNING")
            disk_critical = _as_int(source.get("DISK_TEMP_CRITICAL"), 55, minimum=20, name="DISK_TEMP_CRITICAL")
            cpu_warning = _as_int(source.get("CPU_TEMP_WARNING"), 85, minimum=20, name="CPU_TEMP_WARNING")
            memory_warning = _as_int(source.get("MEMORY_WARNING"), 90, minimum=50, name="MEMORY_WARNING")
            array_usage = _as_int(source.get("ARRAY_USAGE_WARNING"), 85, minimum=50, name="ARRAY_USAGE_WARNING")
            share_usage = _as_int(source.get("SHARE_USAGE_WARNING"), 90, minimum=50, name="SHARE_USAGE_WARNING")
            parity_days = _as_int(source.get("PARITY_MAX_DAYS"), 45, minimum=1, name="PARITY_MAX_DAYS")
            digest_hour = _as_int(source.get("DIGEST_HOUR"), 9, minimum=0, name="DIGEST_HOUR")
            digest_minute = _as_int(source.get("DIGEST_MINUTE"), 0, minimum=0, name="DIGEST_MINUTE")
            timeout = _as_int(source.get("REQUEST_TIMEOUT"), 20, minimum=5, name="REQUEST_TIMEOUT")
            telegram_retries = _as_int(
                source.get("TELEGRAM_RATE_LIMIT_MAX_RETRIES"),
                2,
                minimum=0,
                name="TELEGRAM_RATE_LIMIT_MAX_RETRIES",
            )
            user_actions = _as_int(
                source.get("USER_RATE_LIMIT_ACTIONS"),
                30,
                minimum=1,
                name="USER_RATE_LIMIT_ACTIONS",
            )
            user_window = _as_int(
                source.get("USER_RATE_LIMIT_WINDOW"),
                60,
                minimum=1,
                name="USER_RATE_LIMIT_WINDOW",
            )
        except ConfigError as exc:
            errors.append(str(exc))
            alert_interval, repeat = 300, 360
            disk_warning, disk_critical, cpu_warning, memory_warning, timeout = 50, 55, 85, 90, 20
            array_usage, share_usage, parity_days = 85, 90, 45
            digest_hour, digest_minute = 9, 0
            telegram_retries, user_actions, user_window = 2, 30, 60

        if disk_critical < disk_warning:
            errors.append("DISK_TEMP_CRITICAL no puede ser menor que DISK_TEMP_WARNING.")
        if array_usage > 100 or share_usage > 100:
            errors.append("ARRAY_USAGE_WARNING y SHARE_USAGE_WARNING deben estar entre 50 y 100.")
        if digest_hour > 23:
            errors.append("DIGEST_HOUR debe estar entre 0 y 23.")
        if digest_minute > 59:
            errors.append("DIGEST_MINUTE debe estar entre 0 y 59.")

        try:
            feature_qbittorrent = _service_flag(
                source, "SERVICE_QBITTORRENT", "FEATURE_QBITTORRENT"
            )
            feature_mikrotik = _service_flag(source, "SERVICE_MIKROTIK", "FEATURE_MIKROTIK")
            feature_wol = _service_flag(source, "SERVICE_WOL", "FEATURE_WOL")
            telegram_proxy_enabled = _as_service(
                source.get("SERVICE_TELEGRAM_PROXY"),
                False,
                name="SERVICE_TELEGRAM_PROXY",
            )
            telegram_rate_limit = _as_service(
                source.get("TELEGRAM_RATE_LIMIT"),
                True,
                name="TELEGRAM_RATE_LIMIT",
            )
        except ConfigError as exc:
            errors.append(str(exc))
            feature_qbittorrent = feature_mikrotik = feature_wol = False
            telegram_proxy_enabled, telegram_rate_limit = False, True

        qbittorrent_url = (source.get("QBITTORRENT_URL") or "").strip().rstrip("/")
        qbittorrent_username = (source.get("QBITTORRENT_USERNAME") or "").strip()
        qbittorrent_password = source.get("QBITTORRENT_PASSWORD") or ""
        if feature_qbittorrent:
            if not qbittorrent_url or not qbittorrent_username or not qbittorrent_password:
                errors.append(
                    "SERVICE_QBITTORRENT=active (o FEATURE_QBITTORRENT=true) requiere "
                    "QBITTORRENT_URL, QBITTORRENT_USERNAME y QBITTORRENT_PASSWORD."
                )
            if qbittorrent_url and not qbittorrent_url.startswith(("http://", "https://")):
                errors.append("QBITTORRENT_URL debe empezar por http:// o https://.")

        mikrotik_url = (source.get("MIKROTIK_URL") or "").strip().rstrip("/")
        mikrotik_username = (source.get("MIKROTIK_USERNAME") or "").strip()
        mikrotik_password = source.get("MIKROTIK_PASSWORD") or ""
        if feature_mikrotik:
            if not mikrotik_url or not mikrotik_username or not mikrotik_password:
                errors.append(
                    "SERVICE_MIKROTIK=active (o FEATURE_MIKROTIK=true) requiere MIKROTIK_URL, "
                    "MIKROTIK_USERNAME y MIKROTIK_PASSWORD."
                )
            if mikrotik_url and not mikrotik_url.startswith(("http://", "https://")):
                errors.append("MIKROTIK_URL debe empezar por http:// o https://.")

        wol_mac = (source.get("WOL_MAC") or "").strip()
        wol_broadcast = (source.get("WOL_BROADCAST") or "255.255.255.255").strip()
        try:
            wol_devices = _parse_wol_devices(
                source.get("WOL_DEVICES"),
                wol_mac,
                wol_broadcast,
                legacy=not (source.get("WOL_DEVICES") or "").strip(),
            )
        except ConfigError as exc:
            errors.append(str(exc))
            wol_devices = ()
        if feature_wol and not wol_devices:
            errors.append(
                "SERVICE_WOL=active (o FEATURE_WOL=true) requiere WOL_DEVICES o WOL_MAC "
                "con formato AA:BB:CC:DD:EE:FF."
            )

        telegram_proxy_url = (source.get("TELEGRAM_PROXY_URL") or "").strip()
        if telegram_proxy_enabled:
            if not telegram_proxy_url:
                errors.append(
                    "SERVICE_TELEGRAM_PROXY=active requiere TELEGRAM_PROXY_URL."
                )
            elif not telegram_proxy_url.startswith(
                ("http://", "https://", "socks4://", "socks5://", "socks5h://")
            ):
                errors.append(
                    "TELEGRAM_PROXY_URL debe empezar por http://, https:// o socks5://."
                )

        if errors:
            raise ConfigError("\n".join(f"• {error}" for error in errors))

        return cls(
            telegram_token=token,
            unraid_api_url=api_url or "http://host.docker.internal/graphql",
            unraid_api_key=api_key,
            unraid_api_socket=api_socket,
            unraid_verify_ssl=_as_bool(source.get("UNRAID_VERIFY_SSL"), False),
            allowed_user_ids=allowed_users,
            viewer_user_ids=viewer_users,
            allowed_chat_ids=allowed_chats,
            read_only=_as_bool(source.get("READ_ONLY"), False),
            data_dir=data_dir,
            alerts_enabled=_as_bool(source.get("ALERTS_ENABLED"), True),
            alert_interval_seconds=alert_interval,
            alert_repeat_minutes=repeat,
            disk_temp_warning=disk_warning,
            disk_temp_critical=disk_critical,
            cpu_temp_warning=cpu_warning,
            memory_warning=memory_warning,
            array_usage_warning=array_usage,
            share_usage_warning=share_usage,
            parity_max_days=parity_days,
            api_offline_alert=_as_bool(source.get("API_OFFLINE_ALERT"), True),
            digest_enabled=_as_bool(source.get("DIGEST_ENABLED"), True),
            digest_hour=digest_hour,
            digest_minute=digest_minute,
            timezone=timezone,
            log_level=log_level,
            request_timeout=timeout,
            bot_container_name=(source.get("BOT_CONTAINER_NAME") or "unraidbot").strip(),
            feature_qbittorrent=feature_qbittorrent,
            qbittorrent_url=qbittorrent_url,
            qbittorrent_username=qbittorrent_username,
            qbittorrent_password=qbittorrent_password,
            qbittorrent_verify_ssl=_as_bool(source.get("QBITTORRENT_VERIFY_SSL"), False),
            feature_mikrotik=feature_mikrotik,
            mikrotik_url=mikrotik_url,
            mikrotik_username=mikrotik_username,
            mikrotik_password=mikrotik_password,
            mikrotik_verify_ssl=_as_bool(source.get("MIKROTIK_VERIFY_SSL"), False),
            feature_wol=feature_wol,
            wol_mac=wol_mac,
            wol_broadcast=wol_broadcast,
            wol_devices=wol_devices,
            telegram_proxy_enabled=telegram_proxy_enabled,
            telegram_proxy_url=telegram_proxy_url,
            telegram_rate_limit=telegram_rate_limit,
            telegram_rate_limit_max_retries=telegram_retries,
            user_rate_limit_actions=user_actions,
            user_rate_limit_window=user_window,
        )
