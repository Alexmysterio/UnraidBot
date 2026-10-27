from __future__ import annotations

from dataclasses import replace

from bot import features
from bot.config import Settings, WolDevice
from bot.handlers import register_handlers


class FakeApplication:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def add_handler(self, handler: object) -> None:
        self.handlers.append(handler)


def _patterns(application: FakeApplication) -> list[str]:
    result: list[str] = []
    for handler in application.handlers:
        pattern = getattr(handler, "pattern", None)
        if pattern is not None:
            result.append(str(pattern.pattern))
    return result


def test_noop_and_mute_callbacks_are_registered() -> None:
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    patterns = _patterns(application)
    assert "^d:noop$" in patterns
    assert any("mute" in pattern for pattern in patterns)
    assert any("unmute" in pattern for pattern in patterns)


def test_alert_mute_pattern_accepts_seconds() -> None:
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    mute_patterns = [
        getattr(handler, "pattern")
        for handler in application.handlers
        if getattr(getattr(handler, "pattern", None), "pattern", "").startswith("^a:")
    ]
    assert mute_patterns
    assert any(pattern.match("a:mute:3600") for pattern in mute_patterns)
    assert any(pattern.match("a:unmute") for pattern in mute_patterns)


def test_v14_commands_are_registered() -> None:
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    commands: set[str] = set()
    for handler in application.handlers:
        handler_commands = getattr(handler, "commands", None)
        if handler_commands:
            commands.update(handler_commands)
    for command in ("buscar", "historial", "rendimiento", "resumen", "digest", "docker", "vms"):
        assert command in commands


def test_v14_callbacks_are_registered() -> None:
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    patterns = [
        getattr(handler, "pattern")
        for handler in application.handlers
        if getattr(getattr(handler, "pattern", None), "pattern", "")
    ]

    def matches(data: str) -> bool:
        return any(pattern.match(data) for pattern in patterns)

    for data in ("m:search", "m:perf", "q:p:1", "q:noop", "h:f", "h:noop", "k:p:2", "k:p:noop", "s:notif:1"):
        assert matches(data), data


def test_pagination_patterns_do_not_capture_archive_all() -> None:
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    handlers = [
        handler
        for handler in application.handlers
        if getattr(getattr(handler, "pattern", None), "pattern", "").startswith("^s:notif")
    ]
    assert handlers
    # El primero que casa con s:notifclear debe ser el de archivar, no el paginador.
    first = next(handler for handler in handlers if handler.pattern.match("s:notifclear"))
    assert first.callback.__name__ == "notifications_action"


def test_v15_service_commands_and_callbacks(settings: Settings) -> None:
    enabled = replace(
        settings,
        feature_qbittorrent=True,
        feature_mikrotik=True,
        feature_wol=True,
        wol_devices=(WolDevice(name="NAS", mac="AA:BB:CC:DD:EE:FF"),),
    )
    features.configure(enabled)
    try:
        application = FakeApplication()
        register_handlers(application)  # type: ignore[arg-type]
    finally:
        features.configure(settings)

    commands: set[str] = set()
    for handler in application.handlers:
        handler_commands = getattr(handler, "commands", None)
        if handler_commands:
            commands.update(handler_commands)
    for command in ("qbittorrent", "qb", "mikrotik", "mt", "wol", "encender"):
        assert command in commands, command

    patterns = _patterns(application)
    for pattern in (
        "^qb:l:",
        "^qb:d:",
        "^qb:t:",
        "^qb:x:",
        "^qb:a$",
        "^qb:lim$",
        "^qb:alt$",
        "^qb:cat$",
        "^qb:all:(pause|resume)$",
        "^mt:i:",
        "^mt:l:",
        "^mt:r:",
        "^mt:f:",
        "^mt:g:",
        "^mt:reboot$",
        "^wol:w:",
        "^wol:all$",
        "^(qb|mt|wol):noop$",
    ):
        assert pattern in patterns, pattern


def test_v15_handlers_absent_when_services_disabled(settings: Settings) -> None:
    features.configure(settings)
    application = FakeApplication()
    register_handlers(application)  # type: ignore[arg-type]
    commands: set[str] = set()
    for handler in application.handlers:
        handler_commands = getattr(handler, "commands", None)
        if handler_commands:
            commands.update(handler_commands)
    assert not {"qbittorrent", "mikrotik", "wol"} & commands
    assert "^qb:l:" not in _patterns(application)
