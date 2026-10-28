"""Vistas de texto de las pantallas ampliadas de 1.6.0."""

from __future__ import annotations

from bot.config import Settings
from bot.unraid import Snapshot
from bot.views import build_docker_detail, build_system_menu
from bot.views_system import (
    build_api_keys,
    build_diagnostics,
    build_docker_extras,
    build_docker_sizes,
    build_identity,
    build_license,
    build_log_content,
    build_log_files,
    build_network,
    build_notification_detail,
    build_notification_list,
    build_parity_history,
    build_plugins,
    build_services,
    build_share_detail,
    build_smart,
    build_temperatures,
)


def test_parity_history_empty() -> None:
    text = build_parity_history([], None)  # type: ignore[arg-type]
    assert "Historial de paridad" in text
    assert "ninguna comprobación registrada" in text


def test_parity_history_orders_and_marks(settings: Settings) -> None:
    text = build_parity_history(
        [
            {
                "date": "2026-09-01T03:00:00Z",
                "status": "COMPLETED",
                "duration": 3600,
                "speed": "120",
                "correcting": False,
                "errors": 0,
            },
            {
                "date": "2026-10-01T03:00:00Z",
                "status": "FAILED",
                "duration": 7200,
                "speed": "80",
                "correcting": True,
                "errors": 2,
                "paused": True,
            },
        ],
        settings,
    )
    assert "Total: 2" in text
    assert "correctiva" in text and "no correctiva" in text
    assert "❌" in text and "✅" in text
    assert "Errores: 2" in text
    assert "Pausada" in text


def test_notification_list_empty_and_scoped(settings: Settings) -> None:
    overview = {
        "unread": {"alert": 0, "warning": 0, "info": 0},
        "archive": {"alert": 1, "warning": 0, "info": 0},
    }
    text = build_notification_list(
        [], overview, settings, archived=True, importance="ALERT", page=1, pages=3
    )
    assert "Archivadas: 1 alertas" in text
    assert "Archivadas · ALERT" in text
    assert "pág. 2/3" in text
    assert "No hay notificaciones en esta vista" in text


def test_notification_list_items_and_detail(settings: Settings) -> None:
    item = {
        "id": "notif:1",
        "subject": "Aviso de prueba",
        "description": "Algo pasó",
        "importance": "WARNING",
        "timestamp": "2026-10-19T12:00:00Z",
        "type": "UNREAD",
        "link": "https://tower",
    }
    overview = {"unread": {"alert": 0, "warning": 1, "info": 0}, "archive": {}}
    text = build_notification_list([item], overview, settings)
    assert "🟠" in text
    assert "Aviso de prueba" in text
    assert "Algo pasó" in text

    detail = build_notification_detail(item, settings)
    assert "Importancia: 🟠 WARNING" in detail
    assert "Tipo: UNREAD" in detail
    assert "https://tower" in detail


def test_license_empty_and_trial() -> None:
    assert "no ha devuelto información de licencia" in build_license({})

    text = build_license(
        {
            "registration": {
                "state": "TRIAL",
                "type": "TRIAL",
                "expiration": "2026-11-01",
                "updateExpiration": "2027-11-01",
                "keyFile": {"location": "/boot/config/Basic.key"},
            },
            "flash": {"product": "Cruzer", "vendor": "SanDisk", "guid": "ABCD"},
        }
    )
    assert "Estado: ✅ <b>TRIAL</b>" in text
    assert "Caduca: 2026-11-01" in text
    assert "Actualizaciones hasta: 2027-11-01" in text
    assert "periodo de prueba" in text
    assert "Cruzer" in text and "SanDisk" in text and "ABCD" in text


def test_plugins_empty_and_badges() -> None:
    assert "No hay plugins instalados" in build_plugins([])
    text = build_plugins(
        [
            {"name": "z.plg", "version": "2.0", "hasApiModule": True},
            {"name": "a.plg", "version": "1.0", "hasCliModule": True},
        ]
    )
    assert text.index("a.plg") < text.index("z.plg")
    assert "API" in text and "CLI" in text
    assert "Total: 2" in text


def test_services_empty_and_count() -> None:
    assert "no ha devuelto servicios" in build_services([])
    text = build_services(
        [
            {"name": "nginx", "online": True, "version": "1.24"},
            {"name": "smbd", "online": False},
        ]
    )
    assert "Activos: 1/2" in text
    assert "🟢 <b>nginx</b>" in text
    assert "🔴 <b>smbd</b>" in text


def test_network_interfaces_and_urls() -> None:
    assert "no ha devuelto interfaces" in build_network({})
    text = build_network(
        {
            "interfaces": [
                {
                    "name": "eth0",
                    "operstate": "up",
                    "description": "LAN",
                    "speed": 1000,
                    "duplex": "full",
                    "mtu": 1500,
                    "macAddress": "aa:bb",
                    "ipv4Addresses": [{"address": "192.168.1.10", "netmask": "24"}],
                    "ipv6Addresses": [{"address": "fe80::1", "prefixLength": 64}],
                },
                {"name": "eth1", "operstate": "down"},
            ],
            "access_urls": [{"type": "LAN", "ipv4": "http://tower.local"}],
        }
    )
    assert "🟢 <b>eth0</b>" in text and "🔴 <b>eth1</b>" in text
    assert "192.168.1.10" in text and "fe80::1" in text
    assert "aa:bb" in text
    assert "Accesos" in text and "http://tower.local" in text


def test_log_files_and_content(settings: Settings) -> None:
    assert "no ha devuelto archivos de log" in build_log_files([])
    files = build_log_files(
        [{"name": "syslog", "path": "/var/log/syslog", "size": 2048}]
    )
    assert "syslog" in files and "Elige un log" in files

    assert "El log está vacío" in build_log_content({"path": "/x", "content": ""})
    body = "\n".join(f"linea {index}" for index in range(130))
    page = build_log_content(
        {"path": "/var/log/syslog", "content": body, "totalLines": 130}, page=1
    )
    assert "Líneas 61–120 de 130" in page
    assert "pág. 2/3" in page
    assert "linea 60" in page and "linea 119" in page
    assert "linea 0" not in page


def test_smart_and_share_detail() -> None:
    smart = build_smart(
        {
            "name": "disk1",
            "device": "/dev/sdb",
            "type": "HDD",
            "interfaceType": "SATA",
            "size": 12000000000000,
            "serialNum": "ABC",
            "firmwareRevision": "1.0",
            "temperature": 34,
            "smartStatus": "OK",
            "isSpinning": True,
            "partitions": [{"name": "md1p1", "fsType": "xfs", "size": 12000000000000}],
        }
    )
    assert "disk1" in smart
    assert "SMART: <code>OK</code>" in smart
    assert "Girando: <code>sí</code>" in smart
    assert "Particiones" in smart and "xfs" in smart

    share = build_share_detail(
        {
            "name": "media",
            "comment": "Pelis",
            "used": 1000,
            "size": 2000,
            "cache": True,
            "allocator": "highwater",
            "splitLevel": "2",
            "include": ["disk1", "disk2"],
            "exclude": ["disk3"],
        }
    )
    assert "media" in share and "Pelis" in share
    assert "50%" in share
    assert "Caché: sí" in share
    assert "Incluye: disk1, disk2" in share
    assert "Excluye: disk3" in share


def test_temperatures_without_sensors_and_with_traffic(settings: Settings) -> None:
    empty = build_temperatures({}, settings)
    assert "No hay sensores de temperatura configurados" in empty

    text = build_temperatures(
        {
            "temperature": {
                "summary": {
                    "average": 40.5,
                    "hottest": {"name": "CPU", "current": {"value": 55, "unit": "CELSIUS"}},
                    "coolest": {"name": "disco", "current": {"value": 30, "unit": "CELSIUS"}},
                    "warningCount": 1,
                    "criticalCount": 0,
                },
                "sensors": [
                    {
                        "name": "CPU",
                        "current": {"value": 55, "unit": "CELSIUS", "status": "WARNING"},
                        "warning": 50,
                    }
                ],
            },
            "network": [
                {
                    "name": "eth0",
                    "bytesReceived": 1000,
                    "bytesSent": 2000,
                    "receiveErrors": 1,
                    "transmitErrors": 1,
                }
            ],
        },
        settings,
    )
    assert "Media: 40.5°C" in text
    assert "Más caliente: <b>CPU</b> 55.0°C" in text
    assert "Fuera de rango: 1 avisos · 0 críticos" in text
    assert "🟠" in text
    assert "Tráfico de red" in text
    assert "2 errores" in text


def test_api_keys_identity_and_diagnostics(settings: Settings) -> None:
    assert "No hay claves de API creadas" in build_api_keys([])
    keys = build_api_keys(
        [{"name": "bot", "roles": ["VIEWER"], "description": "lectura", "createdAt": "ayer"}]
    )
    assert "bot" in keys and "VIEWER" in keys and "lectura" in keys

    assert "no ha devuelto la identidad" in build_identity({})
    identity = build_identity({"name": "tower", "comment": "salón", "id": "srv:1"})
    assert "tower" in identity and "salón" in identity and "srv:1" in identity

    clean = build_diagnostics(Snapshot(), settings, [])
    assert "No se han detectado incidencias" in clean

    class Problem:
        title = "Array casi lleno"
        detail = "90% en uso"

    dirty = build_diagnostics(
        Snapshot(info={"os": {"hostname": "tower"}}, array={"state": "STARTED"}),
        settings,
        [Problem()],
        log_tail="linea de syslog",
    )
    assert "Incidencias (1)" in dirty
    assert "Array casi lleno" in dirty and "90% en uso" in dirty
    assert "linea de syslog" in dirty


def test_docker_extras_maintenance_and_sizes() -> None:
    text = build_docker_extras(
        {
            "updates": [
                {"name": "plex", "updateStatus": "UPDATE_AVAILABLE"},
                {"name": "sonarr", "updateStatus": "REBUILD_READY"},
                {"name": "radarr", "updateStatus": "UP_TO_DATE"},
            ],
            "conflicts": {
                "containerPorts": [
                    {"privatePort": 80, "containers": [{"name": "nginx"}, {"name": "web"}]}
                ],
                "lanPorts": [
                    {"lanIpPort": "192.168.1.10:8080", "containers": [{"name": "web"}]}
                ],
            },
        }
    )
    assert "Actualizaciones pendientes: <b>2</b>" in text
    assert "⬆️ plex" in text and "🔁 sonarr" in text
    assert "radarr" not in text
    assert "Conflictos de puertos" in text
    assert "Interno 80 · nginx, web" in text
    assert "192.168.1.10:8080" in text

    clean = build_docker_extras({"updates": [], "conflicts": {}})
    assert "Sin conflictos de puertos detectados" in clean

    assert "No hay datos de tamaño disponibles" in build_docker_sizes({})
    sizes = build_docker_sizes(
        {
            "containers": [
                {
                    "names": ["/plex"],
                    "sizeRootFs": 1000,
                    "sizeRw": 200,
                    "sizeLog": 500,
                    "isOrphaned": True,
                    "isRebuildReady": True,
                },
                {"names": ["/sonarr"], "sizeLog": 100},
            ]
        }
    )
    assert sizes.index("plex") < sizes.index("sonarr")
    assert "👻 huérfano" in sizes and "🔁 rebuild" in sizes
    assert "Total de logs" in sizes


def test_docker_detail_with_extras() -> None:
    container = {
        "id": "docker:c1",
        "names": ["/plex"],
        "state": "RUNNING",
        "image": "plex:latest",
        "autoStart": True,
        "status": "Up 2 days",
    }
    text = build_docker_detail(
        container,
        extras={
            "updateStatus": "REBUILD_READY",
            "sizeRootFs": 1000,
            "sizeRw": 200,
            "sizeLog": 300,
            "isOrphaned": True,
            "conflicts": ["interno 80"],
        },
    )
    assert "Estado de imagen: 🔁 hay que reconstruir" in text
    assert "Tamaño:" in text and "imagen" in text and "log" in text
    assert "huérfano" in text
    assert "Conflictos de puertos: interno 80" in text


def test_system_menu_shows_license_and_services() -> None:
    healthy = build_system_menu(
        Snapshot(
            license={"registration": {"state": "BASIC"}},
            services=[{"name": "nginx", "online": True}],
        )
    )
    assert "Licencia: ✅ BASIC" in healthy
    assert "Servicios: ✅ todos activos" in healthy

    broken = build_system_menu(
        Snapshot(
            license={"registration": {"state": "EXPIRED"}},
            services=[
                {"name": "nginx", "online": False},
                {"name": "smbd", "online": False},
            ],
        )
    )
    assert "Licencia: ⚠️ EXPIRED" in broken
    assert "Servicios caídos: ⚠️ nginx, smbd" in broken
