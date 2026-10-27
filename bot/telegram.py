"""Construcción del cliente de Telegram con proxy y limitador de frecuencia."""

from __future__ import annotations

import logging

from telegram.ext import AIORateLimiter, ApplicationBuilder

from .config import Settings

LOG = logging.getLogger(__name__)


def configure_telegram(builder: ApplicationBuilder, settings: Settings) -> ApplicationBuilder:
    """Aplica proxy de salida y limitador global de Telegram si están activos."""
    if settings.telegram_proxy_enabled and settings.telegram_proxy_url:
        builder = builder.proxy(settings.telegram_proxy_url).get_updates_proxy(
            settings.telegram_proxy_url
        )
        LOG.info("Proxy de Telegram activo: %s", _safe_url(settings.telegram_proxy_url))

    if settings.telegram_rate_limit:
        try:
            limiter = AIORateLimiter(max_retries=settings.telegram_rate_limit_max_retries)
        except RuntimeError as exc:
            LOG.warning("Limitador de Telegram no disponible: %s", exc)
        else:
            builder = builder.rate_limiter(limiter)
            LOG.info(
                "Limitador de Telegram activo (reintentos: %s)",
                settings.telegram_rate_limit_max_retries,
            )
    return builder


def _safe_url(url: str) -> str:
    """Oculta usuario y contraseña al registrar la URL del proxy."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}"
