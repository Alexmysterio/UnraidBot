from __future__ import annotations

import copy

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
