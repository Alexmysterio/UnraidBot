from __future__ import annotations

import hashlib
import shutil
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bot.config import Settings
from bot.unraid import Snapshot


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Sustituye tmp_path: los directorios 0o700 de pytest fallan en este host."""
    digest = hashlib.sha1(request.node.nodeid.encode("utf-8")).hexdigest()[:12]
    path = Path(".test_tmp") / digest
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_token="123456:TEST-TOKEN",
        unraid_api_url="http://unraid.local/graphql",
        unraid_api_key="test-key",
        unraid_api_socket=None,
        unraid_verify_ssl=False,
        allowed_user_ids=frozenset({111}),
        allowed_chat_ids=frozenset(),
        read_only=False,
        data_dir=tmp_path,
        alerts_enabled=True,
        alert_interval_seconds=300,
        alert_repeat_minutes=360,
        disk_temp_warning=50,
        disk_temp_critical=55,
        cpu_temp_warning=85,
        memory_warning=90,
        timezone="Europe/Madrid",
        log_level="INFO",
        request_timeout=20,
        bot_container_name="unraidbot",
    )


@pytest.fixture()
def snapshot() -> Snapshot:
    boot = (datetime.now(timezone.utc) - timedelta(days=12, hours=4)).isoformat()
    return Snapshot(
        array={
            "state": "STARTED",
            "capacity": {
                "kilobytes": {
                    "free": "12000000000",
                    "used": "20000000000",
                    "total": "32000000000",
                },
                "disks": {"free": "2", "used": "6", "total": "8"},
            },
            "parityCheckStatus": {
                "status": "COMPLETED",
                "date": "2026-10-01T03:00:00Z",
                "duration": 29520,
                "speed": "120 MB/s",
                "errors": 0,
                "progress": 100,
                "correcting": False,
                "paused": False,
                "running": False,
            },
            "parities": [
                {
                    "id": "disk:p1",
                    "name": "parity",
                    "device": "/dev/sda",
                    "size": 11721045168,
                    "status": "DISK_OK",
                    "temp": 33,
                    "rotational": True,
                    "color": "GREEN_ON",
                    "isSpinning": True,
                    "numErrors": 0,
                    "fsType": None,
                }
            ],
            "disks": [
                {
                    "id": "disk:d1",
                    "name": "disk1",
                    "device": "/dev/sdb",
                    "size": 11721045168,
                    "status": "DISK_OK",
                    "temp": 34,
                    "rotational": True,
                    "color": "GREEN_ON",
                    "isSpinning": True,
                    "numErrors": 0,
                    "fsType": "xfs",
                    "fsSize": 11721045168,
                    "fsUsed": 7000000000,
                    "transport": "SATA",
                },
                {
                    "id": "disk:d2",
                    "name": "disk2",
                    "device": "/dev/sdc",
                    "size": 11721045168,
                    "status": "DISK_OK",
                    "temp": 35,
                    "rotational": True,
                    "color": "GREEN_ON",
                    "isSpinning": False,
                    "numErrors": 0,
                    "fsType": "xfs",
                    "fsSize": 11721045168,
                    "fsUsed": 5000000000,
                    "transport": "SATA",
                },
            ],
            "caches": [
                {
                    "id": "disk:c1",
                    "name": "cache",
                    "device": "/dev/nvme0n1",
                    "size": 1000204886,
                    "status": "DISK_OK",
                    "temp": 41,
                    "rotational": False,
                    "color": "GREEN_ON",
                    "isSpinning": True,
                    "numErrors": 0,
                    "fsType": "btrfs",
                    "fsSize": 1000204886,
                    "fsUsed": 300000000,
                    "transport": "nvme",
                }
            ],
        },
        metrics={
            "cpu": {"percentTotal": 12.5},
            "memory": {
                "total": 34359738368,
                "used": 8589934592,
                "free": 25769803776,
                "available": 24000000000,
                "percentTotal": 25.0,
                "swapTotal": 0,
                "swapUsed": 0,
                "percentSwapTotal": 0,
            },
        },
        info={
            "time": "2026-10-19T12:00:00Z",
            "os": {
                "hostname": "tower",
                "distro": "Unraid",
                "release": "7.2.0",
                "kernel": "6.12.24-Unraid",
                "arch": "x86_64",
                "uptime": boot,
            },
            "system": {"manufacturer": "Supermicro", "model": "X11"},
            "baseboard": {"manufacturer": "Supermicro", "model": "X11SCA-F"},
            "cpu": {
                "manufacturer": "AMD",
                "brand": "AMD Ryzen 9 5900X 12-Core Processor",
                "cores": 12,
                "threads": 24,
                "speed": 3.7,
                "packages": {"temp": [45.0], "totalPower": 65.0},
            },
            "memory": {
                "layout": [
                    {"size": "17179869184", "type": "DDR4", "clockSpeed": 3200},
                    {"size": "17179869184", "type": "DDR4", "clockSpeed": 3200},
                ]
            },
            "versions": {
                "core": {"unraid": "7.2.0", "api": "4.0.0", "kernel": "6.12.24-Unraid"},
                "packages": {"docker": "27.0.0"},
            },
            "primaryNetwork": {
                "name": "eth0",
                "ipAddress": "192.168.1.10",
                "speed": 1000,
                "operstate": "up",
                "ipv4Addresses": [{"address": "192.168.1.10"}],
            },
        },
        ups=[
            {
                "id": "ups:1",
                "name": "APC Back-UPS",
                "model": "APC Back-UPS Pro 1500",
                "status": "Online",
                "battery": {"chargeLevel": 100, "estimatedRuntime": 2400, "health": "Good"},
                "power": {
                    "inputVoltage": 230.0,
                    "outputVoltage": 230.0,
                    "loadPercentage": 25,
                    "currentPower": 375.0,
                    "nominalPower": 1500,
                },
            }
        ],
        notifications={
            "overview": {
                "unread": {"info": 2, "warning": 1, "alert": 0, "total": 3},
                "archive": {"info": 0, "warning": 0, "alert": 0, "total": 0},
            },
            "warningsAndAlerts": [
                {
                    "id": "notif:1",
                    "title": "Array",
                    "subject": "Aviso de prueba",
                    "description": "Esto es una notificación de prueba",
                    "importance": "WARNING",
                    "timestamp": "2026-10-19T10:00:00Z",
                }
            ],
        },
        docker=[
            {
                "id": "docker:c1",
                "names": ["/plex"],
                "image": "lscr.io/linuxserver/plex:latest",
                "state": "RUNNING",
                "status": "Up 3 days (healthy)",
                "autoStart": True,
                "isUpdateAvailable": False,
                "ports": [{"privatePort": 32400, "publicPort": 32400, "type": "TCP", "ip": "0.0.0.0"}],
                "webUiUrl": "http://192.168.1.10:32400",
                "hostConfig": {"networkMode": "host"},
            },
            {
                "id": "docker:c2",
                "names": ["/autobrr"],
                "image": "ghcr.io/autobrr/autobrr:latest",
                "state": "EXITED",
                "status": "Exited (0) 2 hours ago",
                "autoStart": True,
                "isUpdateAvailable": True,
                "ports": [],
                "webUiUrl": None,
                "hostConfig": {"networkMode": "bridge"},
            },
        ],
        vms=[
            {"id": "vm:1", "name": "Windows 11", "state": "RUNNING"},
            {"id": "vm:2", "name": "Ubuntu", "state": "SHUTOFF"},
        ],
    )


def with_settings(settings: Settings, **changes) -> Settings:
    return replace(settings, **changes)
