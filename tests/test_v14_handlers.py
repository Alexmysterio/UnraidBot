from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bot.config import Settings
from bot.handlers import common, docker, search, vms
from bot.security import AuditLog, ConfirmationManager
from bot.state import StateStore
from bot.unraid import Snapshot


class FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.chat_id = 111
        self.message_id = 10
        self.sent: list[str] = []

    async def reply_text(self, text: str, **kwargs) -> FakeMessage:
        self.sent.append(text)
        return FakeMessage()

    async def edit_text(self, text: str, **kwargs) -> None:
        self.sent.append(text)


class FakeBot:
    def __init__(self) -> None:
        self.edits: list[str] = []

    async def edit_message_text(self, **kwargs) -> None:
        self.edits.append(kwargs["text"])

    async def send_message(self, **kwargs) -> None:
        self.edits.append(kwargs["text"])


class FakeClient:
    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot_data = snapshot
        self.calls: list[tuple[str, tuple]] = []

    async def snapshot(self, include_storage: bool = False) -> Snapshot:
        return self.snapshot_data

    async def docker_containers(self) -> list[dict]:
        return list(self.snapshot_data.docker or [])

    async def docker_logs(self, container_id: str, tail: int = 40) -> list[dict]:
        self.calls.append(("logs", (container_id, tail)))
        return [{"message": "línea de log"}]

    async def docker_action(self, action: str, container_id: str) -> None:
        self.calls.append((action, (container_id,)))

    async def vms(self) -> list[dict]:
        return list(self.snapshot_data.vms or [])

    async def vm_action(self, action: str, vm_id: str) -> bool:
        self.calls.append((action, (vm_id,)))
        return True

    async def set_array_state(self, state: str) -> None:
        self.calls.append((state, ()))


class FakeContext:
    def __init__(self, settings: Settings, snapshot: Snapshot, tmp_path: Path, args: list[str]) -> None:
        self.bot = FakeBot()
        self.args = args
        self.chat_data: dict = {}
        self.bot_data: dict = {
            "settings": settings,
            "client": FakeClient(snapshot),
            "confirmations": ConfirmationManager(),
            "audit": AuditLog(tmp_path / "audit.log"),
        }
        self.user_data: dict = {}

    @property
    def client(self) -> FakeClient:
        return self.bot_data["client"]


def make_update(message: FakeMessage) -> SimpleNamespace:
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=111, username="alois", first_name="Alois"),
        effective_chat=SimpleNamespace(id=111, type="private"),
        effective_message=message,
        callback_query=None,
        update_id=1,
    )


async def make_context(
    settings: Settings, snapshot: Snapshot, tmp_path: Path, args: list[str] | None = None
) -> FakeContext:
    context = FakeContext(settings, snapshot, tmp_path, args or [])
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.set_language(111, "es")
    context.bot_data["store"] = store
    return context


@pytest.mark.asyncio
async def test_docker_command_logs(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path, ["logs", "plex"])
    message = FakeMessage()
    await docker.cmd_docker(make_update(message), context)  # type: ignore[arg-type]
    assert context.client.calls == [("logs", ("docker:c1", 40))]
    assert any("línea de log" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_docker_command_unknown_action_shows_usage(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path, ["bogus"])
    message = FakeMessage()
    await docker.cmd_docker(make_update(message), context)  # type: ignore[arg-type]
    assert any("Uso de /docker" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_docker_command_unknown_container(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path, ["stop", "inexistente"])
    message = FakeMessage()
    await docker.cmd_docker(make_update(message), context)  # type: ignore[arg-type]
    assert any("No encontré ningún contenedor" in text for text in context.bot.edits)
    assert context.client.calls == []


@pytest.mark.asyncio
async def test_vms_command_unknown_action_shows_usage(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path, ["bogus"])
    message = FakeMessage()
    await vms.cmd_vms(make_update(message), context)  # type: ignore[arg-type]
    assert any("Uso de /vms" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_fallback_text_consumes_search(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.chat_data["search_armed"] = True
    message = FakeMessage("plex")
    await common.fallback_text(make_update(message), context)  # type: ignore[arg-type]
    assert context.chat_data["search"]["query"] == "plex"
    assert any("Búsqueda" in text for text in context.bot.edits)
    assert any("plex" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_fallback_text_without_capture_shows_menu(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    message = FakeMessage("hola")
    await common.fallback_text(make_update(message), context)  # type: ignore[arg-type]
    assert any("Menú principal" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_fallback_text_consumes_history_filter(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    log: AuditLog = context.bot_data["audit"]
    await log.write(user_id=111, username="alois", chat_id=111, action="docker.stop", target="plex")

    context.chat_data["history_armed"] = True
    message = FakeMessage("docker")
    await common.fallback_text(make_update(message), context)  # type: ignore[arg-type]
    assert context.chat_data["history_query"] == "docker"
    assert any("Historial de auditoría" in text for text in context.bot.edits)
    assert any("docker.stop" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_history_is_admin_only(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    from dataclasses import replace

    from bot.handlers import history

    viewer = replace(settings, allowed_user_ids=frozenset(), viewer_user_ids=frozenset({111}))
    context = await make_context(viewer, snapshot, tmp_path)
    message = FakeMessage()
    await history.cmd_history(make_update(message), context)  # type: ignore[arg-type]
    assert any("solo para administradores" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_search_command_without_query_arms_prompt(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    message = FakeMessage()
    await search.cmd_search(make_update(message), context)  # type: ignore[arg-type]
    assert context.chat_data["search_armed"] is True
    assert any("Buscar" in text for text in context.bot.edits)


class FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.message = FakeMessage()
        self.from_user = SimpleNamespace(id=111, username="alois", first_name="Alois")
        self.answered = False

    async def answer(self, *args, **kwargs) -> None:
        self.answered = True

    async def edit_message_text(self, text: str, **kwargs) -> None:
        self.message.sent.append(text)


@pytest.mark.asyncio
async def test_long_operation_reports_result_and_duration(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    import asyncio

    from bot.handlers import confirm

    context = await make_context(settings, snapshot, tmp_path)
    query = FakeQuery("")
    confirmation = context.bot_data["confirmations"].create(
        user_id=111,
        chat_id=111,
        action="array.start",
        target="array",
        args={},
        prompt="¿Continuar?",
        success_text="✅ <b>Array iniciado</b>",
        return_callback="s:array",
    )
    query.data = f"c:y:{confirmation.token}"
    update = make_update(query.message)
    update.callback_query = query

    await confirm.on_confirm(update, context)  # type: ignore[arg-type]
    tasks = context.bot_data["background"]
    assert len(tasks) == 1
    await asyncio.gather(*tasks)

    assert any("Operación en curso" in text for text in context.bot.edits)
    assert any("Array iniciado" in text and "Duración" in text for text in context.bot.edits)
    assert context.client.calls == [("START", ())]


@pytest.mark.asyncio
async def test_digest_command_broadcasts_to_subscribers(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    from bot.handlers import digest

    context = await make_context(settings, snapshot, tmp_path)
    store: StateStore = context.bot_data["store"]
    await store.subscribe(111)
    await store.set_language(111, "es")

    await digest.cmd_digest(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert any("Resumen diario" in text for text in context.bot.edits)
    assert any("Enviado a 1 chat(s)" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_digest_command_is_admin_only(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    from dataclasses import replace

    from bot.handlers import digest

    viewer = replace(settings, allowed_user_ids=frozenset(), viewer_user_ids=frozenset({111}))
    context = await make_context(viewer, snapshot, tmp_path)
    await digest.cmd_digest(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert any("Solo los administradores" in text for text in context.bot.edits)
