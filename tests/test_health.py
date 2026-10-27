from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

from bot.config import Settings
from bot.health import detect_problems
from bot.unraid import Snapshot


def _problems(snapshot: Snapshot, settings: Settings) -> dict[str, str]:
    return {problem.key: problem.severity for problem in detect_problems(snapshot, settings)}


def test_healthy_snapshot_has_no_problems(snapshot: Snapshot, settings: Settings) -> None:
    clean = copy.deepcopy(snapshot)
    clean.docker = []
    clean.notifications = {"overview": {"unread": {"info": 0, "warning": 0, "alert": 0, "total": 0}}, "warningsAndAlerts": []}
    assert detect_problems(clean, settings) == []


def test_array_stopped(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["state"] = "STOPPED"
    problems = _problems(changed, settings)
    assert problems["array:state"] == "critical"


def test_disk_temperature_critical(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["disks"][0]["temp"] = 56
    problems = _problems(changed, settings)
    assert problems["disk:temp:disk:d1"] == "critical"


def test_disk_temperature_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["disks"][0]["temp"] = 51
    assert _problems(changed, settings)["disk:temp:disk:d1"] == "warning"


def test_disk_disabled(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["disks"][0]["status"] = "DISK_DSBL"
    problems = _problems(changed, settings)
    assert problems["disk:status:disk:d1"] == "critical"


def test_container_down_with_autostart(snapshot: Snapshot, settings: Settings) -> None:
    problems = _problems(snapshot, settings)
    assert problems["docker:docker:c2"] == "warning"


def test_ups_on_battery(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.ups[0]["status"] = "On Battery"
    assert _problems(changed, settings)["ups:ups:1"] == "critical"


def test_cpu_and_memory_thresholds(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.info["cpu"]["packages"]["temp"] = [91.0]
    changed.metrics["memory"]["percentTotal"] = 95.0
    problems = _problems(changed, settings)
    assert problems["cpu:temp"] == "warning"
    assert problems["memory:usage"] == "warning"


def test_notification_alert(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.notifications["warningsAndAlerts"][0]["importance"] = "ALERT"
    assert _problems(changed, settings)["notif:notif:1"] == "critical"


def test_missing_array_does_not_crash(settings: Settings) -> None:
    assert detect_problems(Snapshot(), settings) == []


def test_array_usage_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["capacity"]["kilobytes"]["used"] = "30000000000"
    assert _problems(changed, settings)["array:usage"] == "warning"


def test_share_usage_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.shares = [{"name": "media", "used": 95, "size": 100}]
    assert _problems(changed, settings)["share:usage:media"] == "warning"


def test_parity_age_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    old = datetime.now(timezone.utc) - timedelta(days=60)
    changed.array["parityCheckStatus"]["date"] = old.isoformat()
    assert _problems(changed, settings)["parity:age"] == "warning"


def test_parity_errors_without_running(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["parityCheckStatus"]["errors"] = 3
    assert _problems(changed, settings)["parity:errors"] == "critical"


def test_physical_disk_smart_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.physical_disks = [
        {"id": "disk:x", "device": "/dev/sdx", "smartStatus": "FAILED"},
        {"id": "disk:y", "device": "/dev/sdy", "smartStatus": "UNKNOWN"},
    ]
    problems = _problems(changed, settings)
    assert problems["smart:disk:x"] == "warning"
    assert "smart:disk:y" not in problems


def test_docker_unhealthy_and_dead(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.docker = [
        {
            "id": "docker:c3",
            "names": ["/web"],
            "state": "RUNNING",
            "status": "Up 2 hours (unhealthy)",
            "autoStart": False,
        },
        {
            "id": "docker:c4",
            "names": ["/dead"],
            "state": "DEAD",
            "status": "Dead",
            "autoStart": False,
        },
    ]
    problems = _problems(changed, settings)
    assert problems["docker:unhealthy:docker:c3"] == "warning"
    assert problems["docker:dead:docker:c4"] == "critical"


def test_network_down(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.info["primaryNetwork"]["operstate"] = "down"
    assert _problems(changed, settings)["network:down"] == "critical"


def test_null_disk_id_uses_name(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.array["disks"][0]["id"] = None
    changed.array["disks"][0]["temp"] = 56
    assert _problems(changed, settings)["disk:temp:disk1"] == "critical"


def test_cpu_temp_scalar_is_accepted(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.info["cpu"]["packages"]["temp"] = 91
    assert _problems(changed, settings)["cpu:temp"] == "warning"
