from __future__ import annotations

import copy

from bot.config import Settings
from bot.search import SearchHit
from bot.unraid import Snapshot
from bot.views import (
    _format_logs,
    build_alert_message,
    build_alerts,
    build_array,
    build_digest,
    build_disk_detail,
    build_disks,
    build_docker_detail,
    build_docker_list,
    build_history,
    build_info,
    build_notifications,
    build_parity,
    build_performance,
    build_physical_disks,
    build_search,
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
    muted = build_alerts(settings, True, [], muted_until=1000000000)
    assert "Silenciado hasta el" in muted
    assert "85%" in muted
    assert "90%" in muted


def test_ups_accepts_numeric_strings(snapshot: Snapshot) -> None:
    changed = copy.deepcopy(snapshot)
    changed.ups[0]["power"] = {
        "inputVoltage": "230.5",
        "outputVoltage": "229.9",
        "loadPercentage": "25",
        "currentPower": "375.4",
    }
    text = build_ups(changed)
    assert "230.5 V entrada" in text
    assert "375 W" in text


def test_logs_preserve_newlines() -> None:
    logs = [{"message": "línea 1"}, {"message": "línea 2"}]
    text = _format_logs(logs)
    assert "línea 1\nlínea 2" in text
    assert "<pre>" in text


def test_search_view_paginates_and_reports_empty() -> None:
    hits = [
        SearchHit("docker", f"cont{index}", "imagen", "d:v:x:0", 1.0) for index in range(10)
    ]
    text = build_search("cont", hits, page=0, per_page=8)
    assert "10 resultado(s) · pág. 1/2" in text
    assert "cont0" in text
    assert "cont9" not in text

    second = build_search("cont", hits, page=1, per_page=8)
    assert "pág. 2/2" in second
    assert "cont9" in second

    empty = build_search("nada", [])
    assert "No se encontraron resultados." in empty


def test_history_view(settings: Settings) -> None:
    records = [
        {
            "ts": "2026-10-27T10:00:00+00:00",
            "action": "docker.stop",
            "target": "plex",
            "username": "alois",
            "outcome": "ok",
        },
        {
            "ts": "2026-10-27T10:05:00+00:00",
            "action": "array.stop",
            "target": "array",
            "user_id": 111,
            "outcome": "error",
        },
    ]
    text = build_history(records, total=2, page=0, per_page=8, query="docker", settings=settings)
    assert "Historial de auditoría" in text
    assert "Filtro: <code>docker</code>" in text
    assert "docker.stop" in text
    assert "array.stop" in text
    assert "❌" in text

    empty = build_history([], total=0, page=0, per_page=8, query="", settings=settings)
    assert "No hay registros que coincidan." in empty


def test_performance_view(snapshot: Snapshot, settings: Settings) -> None:
    history = [
        {"ts": 1, "cpu": 10.0, "ram": 20.0},
        {"ts": 2, "cpu": 30.0, "ram": 40.0},
        {"ts": 3, "cpu": 50.0, "ram": 60.0},
    ]
    text = build_performance(snapshot, history, settings)
    assert "Rendimiento" in text
    assert "CPU ahora: <b>12%</b>" in text
    assert "RAM ahora: <b>25%</b>" in text
    assert "mín 10% · media 30% · máx 50%" in text
    assert "Muestras guardadas: 3" in text

    empty = build_performance(snapshot, [], settings)
    assert "Sin historial de CPU todavía." in empty
    assert "Sin historial de RAM todavía." in empty


def test_digest_view(snapshot: Snapshot, settings: Settings) -> None:
    text = build_digest(snapshot, settings, [])
    assert "Resumen diario · tower" in text
    assert "Array iniciado" in text
    assert "Docker 1/2 activos" in text
    assert "VMs 1/2 en marcha" in text
    assert "Sin incidencias" in text

    changed = Snapshot(errors={"array": "sin conexión"})
    unreachable = build_digest(changed, settings, [])
    assert "Sin conexión con la API de Unraid" in unreachable
    assert "sin conexión" in unreachable


def test_physical_disks_and_notifications_paginate(snapshot: Snapshot, settings: Settings) -> None:
    disks = [
        {"device": f"/dev/sd{letter}", "name": f"disco{index}", "smartStatus": "OK"}
        for index, letter in enumerate("abc")
    ]
    first = build_physical_disks(disks, page=0, per_page=2)
    assert "Total: 3 · pág. 1/2" in first
    assert "/dev/sda" in first
    assert "/dev/sdc" not in first

    second = build_physical_disks(disks, page=1, per_page=2)
    assert "pág. 2/2" in second
    assert "/dev/sdc" in second

    changed = copy.deepcopy(snapshot)
    changed.notifications["warningsAndAlerts"] = [
        {"subject": f"Aviso {index}", "importance": "WARNING"} for index in range(3)
    ]
    page = build_notifications(changed, settings, page=1, per_page=2)
    assert "Total: 3 · pág. 2/2" in page
    assert "Aviso 2" in page
    assert "Aviso 0" not in page
