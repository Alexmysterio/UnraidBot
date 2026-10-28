"""Alertas nuevas de 1.6.0: paridad histórica, licencia y servicios."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

from bot.config import Settings
from bot.health import detect_problems
from bot.unraid import Snapshot


def _problems(snapshot: Snapshot, settings: Settings) -> dict[str, str]:
    return {problem.key: problem.severity for problem in detect_problems(snapshot, settings)}


def test_license_expired_state(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.license = {"registration": {"state": "EXPIRED"}, "flash": None}
    assert _problems(changed, settings)["license:state"] == "critical"


def test_trial_expired_is_a_warning(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.license = {"registration": {"state": "TRIAL_EXPIRED"}, "flash": None}
    assert _problems(changed, settings)["license:state"] == "warning"


def test_license_expiring_soon(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    expiration = datetime.now(timezone.utc) + timedelta(days=10)
    changed.license = {
        "registration": {"state": "BASIC", "expiration": expiration.isoformat()},
        "flash": None,
    }
    problems = _problems(changed, settings)
    assert problems["license:expiry"] == "warning"
    assert "license:expired" not in problems


def test_license_already_expired(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    expiration = datetime.now(timezone.utc) - timedelta(days=5)
    changed.license = {
        "registration": {"state": "BASIC", "expiration": expiration.isoformat()},
        "flash": None,
    }
    assert _problems(changed, settings)["license:expired"] == "critical"


def test_service_down(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.services = [
        {"name": "nginx", "online": True},
        {"name": "smbd", "online": False},
    ]
    problems = _problems(changed, settings)
    assert problems["service:smbd"] == "warning"
    assert "service:nginx" not in problems


def test_parity_history_failure_alert(snapshot: Snapshot, settings: Settings) -> None:
    changed = copy.deepcopy(snapshot)
    changed.parity_history = [
        {
            "date": "2026-08-01T03:00:00Z",
            "status": "FAILED",
            "errors": 3,
        }
    ]
    assert _problems(changed, settings)["parity:history"] == "warning"


def test_parity_history_failure_matching_current_is_not_repeated(
    snapshot: Snapshot, settings: Settings
) -> None:
    changed = copy.deepcopy(snapshot)
    current = str(changed.array["parityCheckStatus"]["date"])
    changed.array["parityCheckStatus"]["status"] = "FAILED"
    changed.array["parityCheckStatus"]["errors"] = 2
    changed.parity_history = [{"date": current, "status": "FAILED", "errors": 2}]
    assert "parity:history" not in _problems(changed, settings)


def test_parity_history_without_failures_is_quiet(
    snapshot: Snapshot, settings: Settings
) -> None:
    changed = copy.deepcopy(snapshot)
    changed.parity_history = [
        {"date": "2026-08-01T03:00:00Z", "status": "COMPLETED", "errors": 0}
    ]
    assert "parity:history" not in _problems(changed, settings)

