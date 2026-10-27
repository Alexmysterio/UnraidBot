from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.formatting import (
    bar,
    clamp,
    esc,
    fmt_array_disk_size,
    fmt_bytes,
    fmt_epoch,
    fmt_kb,
    fmt_pct,
    fmt_routeros_uptime,
    fmt_runtime,
    fmt_temp,
    fmt_uptime,
    parse_iso,
    pct,
    sparkline,
    fmt_elapsed,
)


def test_fmt_bytes() -> None:
    assert fmt_bytes(0) == "0 B"
    assert fmt_bytes(1024) == "1.0 KiB"
    assert fmt_bytes(1536) == "1.5 KiB"
    assert fmt_bytes(1024**3) == "1.0 GiB"
    assert fmt_bytes("invalid") == "—"


def test_fmt_kb() -> None:
    assert fmt_kb(1024) == "1.0 MiB"
    assert fmt_kb(None) == "—"


def test_fmt_array_disk_size_kib_and_bytes() -> None:
    # 12 TB en KiB
    assert fmt_array_disk_size(11721045168) == "10.9 TiB"
    # El mismo disco en bytes
    assert fmt_array_disk_size(12000000000000) == "10.9 TiB"


def test_fmt_epoch() -> None:
    assert fmt_epoch(0) == "01/01/1970 01:00"
    assert fmt_epoch(None) == "—"
    assert fmt_epoch("invalid") == "—"


def test_fmt_routeros_uptime() -> None:
    assert fmt_routeros_uptime("1w2d03:04:05") == "9d 3h"
    assert fmt_routeros_uptime("04:05:06") == "4h 5m"
    assert fmt_routeros_uptime("3600") == "1h 0m"
    assert fmt_routeros_uptime(None) == "—"
    assert fmt_routeros_uptime("no-es-uptime") == "—"


def test_pct_and_bar() -> None:
    assert pct(50, 200) == 25.0
    assert pct(0, 0) is None
    assert bar(0, width=4) == "░░░░"
    assert bar(100, width=4) == "████"
    assert bar(50, width=4) == "██░░"


def test_fmt_temp() -> None:
    assert fmt_temp(34.4) == "34°C"
    assert fmt_temp(None) == "—"
    assert fmt_temp(0) == "—"


def test_fmt_runtime() -> None:
    assert fmt_runtime(90) == "1m"
    assert fmt_runtime(3700) == "1h 1m"
    assert fmt_runtime(90000) == "1d 1h"


def test_parse_iso_with_z_and_nanoseconds() -> None:
    parsed = parse_iso("2026-10-19T12:34:56.123456789Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.tzinfo is not None


def test_fmt_uptime() -> None:
    boot = (datetime.now(timezone.utc) - timedelta(days=2, hours=3)).isoformat()
    assert fmt_uptime(boot).startswith("2d")
    assert fmt_uptime(None) == "—"


def test_esc_and_clamp() -> None:
    assert esc("<b>hola</b>") == "&lt;b&gt;hola&lt;/b&gt;"
    assert len(clamp("x" * 5000, limit=100)) <= 100


def test_fmt_pct() -> None:
    assert fmt_pct(12.6) == "13%"
    assert fmt_pct(None) == "—"


def test_sparkline() -> None:
    assert sparkline([]) == "—"
    assert sparkline([None, "x"]) == "—"
    assert sparkline([0, 50, 100], width=3) == "▁▅█"
    assert len(sparkline(range(100), width=10)) == 10
    assert sparkline([5, 5, 5]) == "▁▁▁"


def test_fmt_elapsed() -> None:
    assert fmt_elapsed(0) == "0 s"
    assert fmt_elapsed(45) == "45 s"
    assert fmt_elapsed(65) == "1 min 5 s"
    assert fmt_elapsed(120) == "2 min"
    assert fmt_elapsed(3660) == "1 h 1 min"
    assert fmt_elapsed(None) == "—"
