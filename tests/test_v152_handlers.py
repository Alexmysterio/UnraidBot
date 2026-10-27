"""Regresiones 1.5.2: errores que no deben dejar al usuario sin navegación."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from telegram.error import BadRequest

from bot.config import Settings
from bot.handlers import common, confirm, system
from bot.i18n import set_language
from bot.security import AuditLog, ConfirmationManager
from bot.state import StateStore
from bot.unraid import Snapshot, UnraidError, UnraidPermissionError


class FakeMessage:
    def __init__(self) -> None:
        self.text = ""
        self.chat_id = 111
        self.message_id = 10
        self.sent: list[tuple[str, object]] = []

    async def reply_text(self, text: str, **kwargs) -> FakeMessage:
        self.sent.append((text, kwargs.get("reply_markup")))
        return FakeMessage()

    async def edit_text(self, text: str, **kwargs) -> None:
        self.sent.append((text, kwargs.get("reply_markup")))


class FakeBot:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object]] = []

    async def edit_message_text(self, **kwargs) -> None:
        self.edits.append((kwargs["text"], kwargs.get("reply_markup")))

    async def send_message(self, **kwargs) -> None:
        self.edits.append((kwargs["text"], kwargs.get("reply_markup")))


class FakeQuery:
    def __init__(self, data: str = "") -> None:
        self.data = data
        self.message = FakeMessage()
        self.from_user = SimpleNamespace(id=111, username="alois", first_name="Alois")
        self.answered: list[str] = []

    async def answer(self, text: str = "", **kwargs) -> None:
        self.answered.append(text)

    async def edit_message_text(self, text: str, **kwargs) -> None:
        self.message.sent.append((text, kwargs.get("reply_markup")))


class FakeClient:
    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot_data = snapshot
        self.ups_error: Exception | None = None
        self.archive_error: Exception | None = None
        self.ups_devices: list[dict] = []

    async def ups(self) -> list[dict]:
        if self.ups_error is not None:
            raise self.ups_error
        return list(self.ups_devices)

    async def archive_all_notifications(self) -> None:
        if self.archive_error is not None:
            raise self.archive_error


class FakeContext:
    def __init__(self, settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
        self.bot = FakeBot()
        self.args: list[str] = []
        self.chat_data: dict = {}
        self.user_data: dict = {}
        self.bot_data: dict = {
            "settings": settings,
            "client": FakeClient(snapshot),
            "confirmations": ConfirmationManager(),
            "audit": AuditLog(tmp_path / "audit.log"),
        }
        self.error: BaseException | None = None

    @property
    def client(self) -> FakeClient:
        return self.bot_data["client"]


def make_update(message: FakeMessage, query: FakeQuery | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=111, username="alois", first_name="Alois"),
        effective_chat=SimpleNamespace(id=111, type="private"),
        effective_message=message,
        callback_query=query,
        update_id=1,
    )


async def make_context(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> FakeContext:
    context = FakeContext(settings, snapshot, tmp_path)
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.set_language(111, "es")
    context.bot_data["store"] = store
    set_language("es")
    return context


def buttons(markup) -> list[list[str]]:
    if markup is None:
        return []
    return [[button.callback_data for button in row] for row in markup.inline_keyboard]


def texts(edits: list[tuple[str, object]]) -> str:
    return "\n".join(text for text, _ in edits)


@pytest.mark.asyncio
async def test_ups_without_device_informs_and_keeps_navigation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.ups_error = UnraidError(
        "Failed to get UPS data: No UPS data returned from apcaccess"
    )
    query = FakeQuery("s:ups")
    update = make_update(query.message, query)

    await system.show_ups(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "No hay ningún UPS configurado o visible para la API" in rendered
    assert "apcaccess" not in rendered
    assert buttons(context.bot.edits[-1][1]) == [["s:ups", "m:sys"], ["m:main"]]


@pytest.mark.asyncio
async def test_ups_with_real_error_shows_detail_and_back_button(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.ups_error = UnraidError("Connection refused by apcupsd")
    query = FakeQuery("s:ups")
    update = make_update(query.message, query)

    await system.show_ups(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "No se pudo consultar el estado del UPS" in rendered
    assert "Connection refused by apcupsd" in rendered
    assert buttons(context.bot.edits[-1][1])[-1] == ["m:main"]


@pytest.mark.asyncio
async def test_ups_with_device_still_renders(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.ups_devices = [
        {
            "name": "Back-UPS",
            "model": "APC 1500",
            "status": "Online",
            "battery": {"chargeLevel": 100},
            "power": {"loadPercentage": 12},
        }
    ]
    query = FakeQuery("s:ups")
    update = make_update(query.message, query)

    await system.show_ups(update, context)  # type: ignore[arg-type]

    assert "APC 1500" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_archive_failure_offers_back_to_notifications(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.archive_error = UnraidPermissionError("Unauthorized: read-only API key")
    item = context.bot_data["confirmations"].create(
        user_id=111,
        chat_id=111,
        action="notifications.archive_all",
        target="notifications",
        args={},
        prompt="¿Continuar?",
        success_text="Archivadas",
        return_callback="s:notif",
    )
    query = FakeQuery(f"c:y:{item.token}")
    update = make_update(query.message, query)

    await confirm.on_confirm(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "no permite esta operación" in rendered
    assert "read-only API key" in rendered
    assert buttons(context.bot.edits[-1][1]) == [["s:notif", "m:main"]]


@pytest.mark.asyncio
async def test_archive_failure_without_return_callback_still_navigates(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.archive_error = UnraidError("boom")
    item = context.bot_data["confirmations"].create(
        user_id=111,
        chat_id=111,
        action="notifications.archive_all",
        target="notifications",
        args={},
        prompt="¿Continuar?",
        success_text="Archivadas",
        return_callback="",
    )
    query = FakeQuery(f"c:y:{item.token}")
    update = make_update(query.message, query)

    await confirm.on_confirm(update, context)  # type: ignore[arg-type]

    assert buttons(context.bot.edits[-1][1]) == [["m:main", "m:main"]]


@pytest.mark.asyncio
async def test_on_error_renders_message_with_menu(
    settings: Settings, snapshot: Snapshot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(common, "Update", SimpleNamespace)
    context = await make_context(settings, snapshot, tmp_path)
    context.error = UnraidError("Failed to get UPS data: No UPS data returned from apcaccess")
    query = FakeQuery("s:ups")
    update = make_update(query.message, query)

    await common.on_error(update, context)  # type: ignore[arg-type]

    rendered = texts(query.message.sent)
    assert "Error de Unraid" in rendered
    assert "apcaccess" in rendered
    assert buttons(query.message.sent[-1][1]) == [["m:main", "m:main"]]


@pytest.mark.asyncio
async def test_on_error_with_permission_issue_explains_api_key(
    settings: Settings, snapshot: Snapshot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(common, "Update", SimpleNamespace)
    context = await make_context(settings, snapshot, tmp_path)
    context.error = UnraidPermissionError("Forbidden")
    query = FakeQuery("s:notifclear")
    update = make_update(query.message, query)

    await common.on_error(update, context)  # type: ignore[arg-type]

    assert "no permite esta operación" in texts(query.message.sent)


@pytest.mark.asyncio
async def test_notify_keeps_a_keyboard_after_processing(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    query = FakeQuery("s:notifclear")
    update = make_update(query.message, query)

    await common.begin_processing(update, context)  # type: ignore[arg-type]
    await common.notify(update, context, "🔒 Tu usuario tiene acceso de solo lectura.")

    assert "solo lectura" in texts(context.bot.edits)
    assert buttons(context.bot.edits[-1][1]) == [["m:main", "m:main"]]


@pytest.mark.asyncio
async def test_render_falls_back_when_processing_message_is_gone(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    query = FakeQuery("s:ups")
    update = make_update(query.message, query)

    async def broken_edit(text: str, **kwargs) -> None:
        raise BadRequest("Message to edit not found")

    query.edit_message_text = broken_edit  # type: ignore[method-assign]

    await common.render(update, context, "hola", None)
    assert query.message.sent


def test_failure_text_distinguishes_permissions() -> None:
    assert "no permite esta operación" in common.failure_text(
        UnraidPermissionError("Unauthorized")
    )
    plain = common.failure_text(UnraidError("timeout"))
    assert "No se pudo completar la operación" in plain
    assert "permisos de escritura" not in plain
