"""Diagnóstico de configuración y conectividad con Unraid.

Uso dentro del contenedor:

    python -m bot.doctor

Comprueba la API key contra cada sección que usa el bot y explica qué falla.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from .config import ConfigError, Settings
from .unraid import UnraidClient, UnraidError

CHECKS: tuple[tuple[str, str], ...] = (
    ("Información del sistema", "info"),
    ("Array y discos", "array"),
    ("Discos físicos / SMART", "physical_disks"),
    ("Docker", "docker_containers"),
    ("Máquinas virtuales", "vms"),
    ("UPS", "ups"),
    ("Notificaciones", "notifications"),
    ("Shares", "shares"),
)


def mask(value: str) -> str:
    """Oculta un secreto dejando solo un prefijo y un sufijo."""
    if not value:
        return "—"
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}…{value[-4:]}"


def print_config(settings: Settings) -> None:
    print("⚙️  Configuración")
    print(f"   API URL:        {settings.unraid_api_url}")
    print(f"   Socket:         {settings.unraid_api_socket or '—'}")
    print(f"   API key:        {mask(settings.unraid_api_key)}")
    print(f"   Token Telegram: {mask(settings.telegram_token)}")
    print(f"   Usuarios:       {len(settings.allowed_user_ids)} autorizado(s)")
    print(f"   Solo lectura:   {'sí' if settings.read_only else 'no'}")
    print(f"   Alertas:        {'sí' if settings.alerts_enabled else 'no'}")
    print()


async def diagnose(settings: Settings) -> int:
    print_config(settings)
    client = UnraidClient(settings)
    failures = 0
    try:
        print("🔌 Conectando con la API…")
        try:
            online = await client.ping()
        except UnraidError as exc:
            print(f"   ❌ No se pudo consultar la API: {exc}")
            return 1
        print(f"   {'✅' if online else '⚠️ '} online={str(online).lower()}")
        print()

        print("📋 Permisos y consultas")
        for label, method in CHECKS:
            try:
                result: Any = await getattr(client, method)()
                count = f" ({len(result)})" if isinstance(result, list) else ""
                print(f"   ✅ {label}{count}")
            except UnraidError as exc:
                failures += 1
                print(f"   ❌ {label}: {exc}")
    finally:
        await client.close()

    print()
    if failures:
        print(f"❌ {failures} comprobación(es) fallaron. Revisa la API key y sus permisos.")
        return 1
    print("✅ Todo correcto: la API responde y el bot puede leer todas las secciones.")
    return 0


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print("❌ Configuración inválida:\n")
        print(exc)
        return 2

    try:
        return asyncio.run(diagnose(settings))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
