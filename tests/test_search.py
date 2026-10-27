from __future__ import annotations

from bot.search import find_named, normalize, score_match, search_snapshot
from bot.unraid import Snapshot


def test_normalize_strips_accents_and_slashes() -> None:
    assert normalize("/Plex") == "plex"
    assert normalize("Máquina Virtual") == "maquina virtual"


def test_score_match_prefers_exact() -> None:
    assert score_match("plex", ["plex"]) == 1.0
    assert score_match("ple", ["plex"]) >= 0.9
    assert score_match("lex", ["plex"]) >= 0.8
    assert score_match("", ["plex"]) == 0.0
    assert score_match("zzzz", ["plex"]) < 0.5


def test_search_snapshot_finds_every_kind(snapshot: Snapshot) -> None:
    hits = search_snapshot(snapshot, "plex")
    assert hits
    assert hits[0].kind == "docker"
    assert hits[0].title == "plex"
    assert hits[0].callback.startswith("d:v:")

    assert search_snapshot(snapshot, "windows")[0].kind == "vm"
    assert search_snapshot(snapshot, "disk1")[0].kind == "disk"
    assert search_snapshot(snapshot, "apc")[0].kind == "ups"
    assert search_snapshot(snapshot, "prueba")[0].kind == "notification"


def test_search_snapshot_empty_or_unknown(snapshot: Snapshot) -> None:
    assert search_snapshot(snapshot, "   ") == []
    assert search_snapshot(snapshot, "zzzz-no-existe") == []


def test_find_named_exact_prefix_and_contains() -> None:
    items = [{"name": "Plex"}, {"name": "Plexamp"}, {"name": "autobrr"}]
    item, candidates = find_named(items, "plex")
    assert item == {"name": "Plex"}
    assert candidates == []

    item, candidates = find_named(items, "plexam")
    assert item == {"name": "Plexamp"}
    assert candidates == []

    item, candidates = find_named(items, "brr")
    assert item == {"name": "autobrr"}
    assert candidates == []


def test_find_named_ambiguous_returns_candidates() -> None:
    items = [{"name": "Plex"}, {"name": "Plexamp"}]
    item, candidates = find_named(items, "ple")
    assert item is None
    assert len(candidates) == 2


def test_find_named_fuzzy_and_missing() -> None:
    items = [{"name": "autobrr"}, {"name": "sonarr"}]
    item, _ = find_named(items, "sonar")
    assert item == {"name": "sonarr"}

    item, candidates = find_named(items, "qqqqqq")
    assert item is None
    assert candidates == []

    assert find_named([], "plex") == (None, [])
