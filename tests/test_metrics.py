from __future__ import annotations

from bot.metrics import sample_usage
from bot.unraid import Snapshot


def test_sample_usage_reads_percentages(snapshot: Snapshot) -> None:
    cpu, ram = sample_usage(snapshot)
    assert cpu == 12.5
    assert ram == 25.0


def test_sample_usage_computes_ram_from_bytes() -> None:
    snapshot = Snapshot(
        metrics={
            "cpu": {"percentTotal": "40"},
            "memory": {"total": 1000, "used": 250},
        }
    )
    cpu, ram = sample_usage(snapshot)
    assert cpu == 40.0
    assert ram == 25.0


def test_sample_usage_handles_missing_data() -> None:
    assert sample_usage(Snapshot()) == (None, None)
    assert sample_usage(Snapshot(metrics={"memory": {"total": 0, "used": 10}})) == (None, None)
    assert sample_usage(Snapshot(metrics={"cpu": {"percentTotal": "n/a"}})) == (None, None)
