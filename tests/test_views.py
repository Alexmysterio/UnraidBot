from __future__ import annotations

import copy

from bot.config import Settings
from bot.unraid import Snapshot
from bot.views import (
    _format_logs,
    build_alert_message,
    build_alerts,
    build_array,
    build_disk_detail,
    build_disks,
    build_docker_detail,
    build_docker_list,
    build_info,
    build_notifications,
    build_parity,
    build_physical_disks,
    build_status,
    build_system_menu,
    build_ups,
    build_vm_detail,
    build_vm_list,
)


def test_status_contains_key_sections(snapshot: Snapshot, settings: Settings) -> None:
    text = build_status(snapshot, settings, [])
    assert "tower" in text
    assert "Unraid 7.2.0" in text
    assert "Array iniciado" in text
    assert "Docker 1/2 activos" in text
    assert "VMs 1/2 en marcha" in text
    assert "APC Back-UPS" in text
    assert "192.168.1.10" in text


def test_status_escapes_html(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.info["os"]["hostname"] = "<tower>"
    text = build_status(changed, settings, [])
    assert "&lt;tower&gt;" in text
    assert "<tower>" not in text


def test_status_without_connection(settings: Settings) -> None:
    text = build_status(Snapshot(errors={"array": "connection refused"}), settings, [])
    assert "Sin conexión" in text


def test_disks_view(snapshot: Snapshot) -> None:
    text = build_disks(snapshot)
    assert "disk1" in text
    assert "cache" in text
    assert "Paridad" in text
    assert "💤" in text


def test_disk_detail(snapshot: Snapshot, settings: Settings) -> None:
    text = build_disk_detail(snapshot.array["disks"][0], settings)
    assert "Errores de E/S: 0" in text
    assert "xfs" in text
    assert "50°C" in text


def test_physical_disks() -> None:
    text = build_physical_disks(
        [
            {
                "device": "/dev/sda",
                "name": "WDC WD120",
                "vendor": "Western Digital",
                "size": 12000000000000,
                "temperature": 34.0,
                "smartStatus": "OK",
                "type": "HDD",
                "interfaceType": "SATA",
                "serialNum": "ABC123",
            }
        ]
    )
    assert "/dev/sda" in text
    assert "SMART: OK" in text


def test_docker_list_and_detail(snapshot: Snapshot) -> None:
    listing = build_docker_list(snapshot.docker, page=0, per_page=8)
    assert "plex" in listing
    assert "autobrr" in listing

    detail = build_docker_detail(snapshot.docker[0])
    assert "lscr.io/linuxserver/plex" in detail
    assert "32400" in detail
    assert "Autostart: sí" in detail

    updates = build_docker_detail(snapshot.docker[1])
    assert "Actualización: ⬆️ disponible" in updates


def test_vm_views(snapshot: Snapshot) -> None:
    listing = build_vm_list(snapshot.vms)
    assert "Windows 11" in listing
    assert "1/2 en marcha" in listing
    assert "En marcha" in build_vm_detail(snapshot.vms[0])


def test_array_parity_ups_notifications(snapshot: Snapshot, settings: Settings) -> None:
    assert "Array" in build_array(snapshot, settings)
    assert "Comprobación de paridad" in build_parity(snapshot, settings)
    assert "APC" in build_ups(snapshot)
    assert "Aviso de prueba" in build_notifications(snapshot, settings)
    assert "Array" in build_system_menu(snapshot)


def test_info(snapshot: Snapshot, settings: Settings) -> None:
    text = build_info(snapshot, settings)
    assert "AMD Ryzen" in text
    assert "34.4 GB" in text or "32.0 GiB" in text


def test_alerts_views(settings: Settings) -> None:
    assert "desactivadas" in build_alerts(settings, False, [])
    text = build_alert_message([], "tower")
    assert "Alertas" in text


def test_logs_preserve_newlines() -> None:
    logs = [{"message": "línea 1"}, {"message": "línea 2"}]
    text = _format_logs(logs)
    assert "línea 1\nlínea 2" in text
    assert "<pre>" in text
