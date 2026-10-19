"""Carga y validación de la configuración desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(RuntimeError):
    """La configuración es inválida o incompleta."""


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}


def _as_int(value: str | None, default: int, minimum: int | None = None) -> int:
    if value is None or value.strip() == "":
        number = default
    else:
        try:
            number = int(value.strip())
        except ValueError as exc:
            raise ConfigError(f"Se esperaba un número entero, se recibió {value!r}") from exc
    if minimum is not None and number < minimum:
        raise ConfigError(f"El valor {number} es menor que el mínimo permitido ({minimum})")
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
    timezone: str
    log_level: str
    request_timeout: int
    bot_container_name: str

    @property
    def is_configured(self) -> bool:
        """True si hay al menos un usuario autorizado."""
        return bool(self.allowed_user_ids)

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
            alert_interval = _as_int(source.get("ALERT_INTERVAL_SECONDS"), 300, minimum=60)
            repeat = _as_int(source.get("ALERT_REPEAT_MINUTES"), 360, minimum=5)
            disk_warning = _as_int(source.get("DISK_TEMP_WARNING"), 50, minimum=20)
            disk_critical = _as_int(source.get("DISK_TEMP_CRITICAL"), 55, minimum=20)
            cpu_warning = _as_int(source.get("CPU_TEMP_WARNING"), 85, minimum=20)
            memory_warning = _as_int(source.get("MEMORY_WARNING"), 90, minimum=50)
            timeout = _as_int(source.get("REQUEST_TIMEOUT"), 20, minimum=5)
        except ConfigError as exc:
            errors.append(str(exc))
            alert_interval, repeat = 300, 360
            disk_warning, disk_critical, cpu_warning, memory_warning, timeout = 50, 55, 85, 90, 20

        if disk_critical < disk_warning:
            errors.append("DISK_TEMP_CRITICAL no puede ser menor que DISK_TEMP_WARNING.")

        if errors:
            raise ConfigError("\n".join(f"• {error}" for error in errors))

        return cls(
            telegram_token=token,
            unraid_api_url=api_url or "http://host.docker.internal/graphql",
            unraid_api_key=api_key,
            unraid_api_socket=api_socket,
            unraid_verify_ssl=_as_bool(source.get("UNRAID_VERIFY_SSL"), False),
            allowed_user_ids=allowed_users,
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
            timezone=timezone,
            log_level=log_level,
            request_timeout=timeout,
            bot_container_name=(source.get("BOT_CONTAINER_NAME") or "unraidbot").strip(),
        )
