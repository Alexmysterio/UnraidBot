from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot.config import Settings, WolDevice
from bot.handlers import mikrotik, qbittorrent, wol
from bot.security import AuditLog, ConfirmationManager
from bot.state import StateStore

TORRENTS = [
    {"hash": "aaaaaaaaaaaa", "name": "Debian ISO", "state": "downloading", "progress": 0.4},
    {"hash": "bbbbbbbbbbbb", "name": "Arch Linux", "state": "pausedDL", "progress": 0.1},
]


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


class FakeQbittorrent:
    """Cliente qBittorrent falso: registra llamadas y no toca la red."""

    instances: list[FakeQbittorrent] = []

    def __init__(self, settings: Settings) -> None:
        self.calls: list[tuple[str, tuple]] = []
        FakeQbittorrent.instances.append(self)

    async def status(self) -> dict:
        return {"dl_info_speed": 2048, "up_info_speed": 1024}

    async def torrents(self) -> list[dict]:
        return [dict(item) for item in TORRENTS]

    async def alt_speed_enabled(self) -> bool:
        return False

    async def preferences(self) -> dict:
        return {"dl_limit": 0, "up_limit": 0}

    async def categories(self) -> dict:
        return {"Pelis": {"savePath": "/data"}}

    async def add(self, url: str, category: str = "") -> None:
        self.calls.append(("add", (url, category)))

    async def delete(self, hash_: str, delete_files: bool = False) -> None:
        self.calls.append(("delete", (hash_, delete_files)))

    async def set_paused(self, hash_: str, paused: bool) -> None:
        self.calls.append(("set_paused", (hash_, paused)))

    async def set_download_limit(self, limit: int) -> None:
        self.calls.append(("set_download_limit", (limit,)))

    async def set_upload_limit(self, limit: int) -> None:
        self.calls.append(("set_upload_limit", (limit,)))

    async def toggle_alt_speed(self) -> None:
        self.calls.append(("toggle_alt_speed", ()))

    async def pause_all(self) -> None:
        self.calls.append(("pause_all", ()))

    async def resume_all(self) -> None:
        self.calls.append(("resume_all", ()))

    async def close(self) -> None:
        self.calls.append(("close", ()))


class FakeContext:
    def __init__(self, settings: Settings, tmp_path: Path, args: list[str]) -> None:
        self.bot = FakeBot()
        self.args = args
        self.chat_data: dict = {}
        self.user_data: dict = {}
        self.bot_data: dict = {
            "settings": settings,
            "confirmations": ConfirmationManager(),
            "audit": AuditLog(tmp_path / "audit.log"),
        }


def make_update(message: FakeMessage) -> SimpleNamespace:
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=111, username="alois", first_name="Alois"),
        effective_chat=SimpleNamespace(id=111, type="private"),
        effective_message=message,
        callback_query=None,
        update_id=1,
    )


async def make_context(
    settings: Settings, tmp_path: Path, args: list[str] | None = None
) -> FakeContext:
    context = FakeContext(settings, tmp_path, args or [])
    store = StateStore(tmp_path / "state.json")
    await store.load()
    await store.set_language(111, "es")
    context.bot_data["store"] = store
    return context


def wol_settings(settings: Settings) -> Settings:
    return replace(
        settings,
        feature_wol=True,
        wol_devices=(
            WolDevice(name="NAS", mac="AA:BB:CC:DD:EE:FF"),
            WolDevice(name="PC", mac="11:22:33:44:55:66", broadcast="192.168.1.255"),
        ),
    )


@pytest.fixture()
def sent_packets(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    packets: list[tuple[str, str]] = []

    async def fake_wake(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
        packets.append((mac, broadcast))

    monkeypatch.setattr(wol, "wake", fake_wake)
    return packets


@pytest.fixture()
def qb_client(monkeypatch: pytest.MonkeyPatch) -> type[FakeQbittorrent]:
    FakeQbittorrent.instances = []
    monkeypatch.setattr(qbittorrent, "QBittorrent", FakeQbittorrent)
    return FakeQbittorrent


@pytest.mark.asyncio
async def test_wol_without_args_lists_devices(
    settings: Settings, tmp_path: Path, sent_packets: list[tuple[str, str]]
) -> None:
    context = await make_context(wol_settings(settings), tmp_path)
    await wol.cmd_wol(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert sent_packets == []
    assert any("Wake-on-LAN" in text and "NAS" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_wol_all_wakes_every_device(
    settings: Settings, tmp_path: Path, sent_packets: list[tuple[str, str]]
) -> None:
    context = await make_context(wol_settings(settings), tmp_path, ["all"])
    await wol.cmd_wol(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert sent_packets == [
        ("AA:BB:CC:DD:EE:FF", "255.255.255.255"),
        ("11:22:33:44:55:66", "192.168.1.255"),
    ]
    assert any("Magic packets enviados: 2/2" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_wol_named_device_uses_its_broadcast(
    settings: Settings, tmp_path: Path, sent_packets: list[tuple[str, str]]
) -> None:
    context = await make_context(wol_settings(settings), tmp_path, ["PC"])
    await wol.cmd_wol(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert sent_packets == [("11:22:33:44:55:66", "192.168.1.255")]
    assert any("Magic packet enviado a <b>PC</b>" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_wol_unknown_device_reports(
    settings: Settings, tmp_path: Path, sent_packets: list[tuple[str, str]]
) -> None:
    context = await make_context(wol_settings(settings), tmp_path, ["Inexistente"])
    await wol.cmd_wol(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert sent_packets == []
    assert any("No encontré ningún equipo" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_wol_is_blocked_in_read_only_mode(
    settings: Settings, tmp_path: Path, sent_packets: list[tuple[str, str]]
) -> None:
    context = await make_context(replace(wol_settings(settings), read_only=True), tmp_path, ["NAS"])
    await wol.cmd_wol(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert sent_packets == []
    assert any("modo solo lectura" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_mikrotik_reboot_asks_for_confirmation(settings: Settings, tmp_path: Path) -> None:
    context = await make_context(settings, tmp_path, ["reboot"])
    await mikrotik.cmd_mikrotik(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    manager: ConfirmationManager = context.bot_data["confirmations"]
    assert len(manager._items) == 1
    confirmation = next(iter(manager._items.values()))
    assert confirmation.action == "mikrotik.reboot"
    assert confirmation.return_callback == "tool:mt"
    assert any("Reiniciar MikroTik" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_mikrotik_unknown_action_shows_usage(settings: Settings, tmp_path: Path) -> None:
    context = await make_context(settings, tmp_path, ["bogus"])
    await mikrotik.cmd_mikrotik(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert any("Uso de /mikrotik" in text for text in context.bot.edits)
    assert context.bot_data["confirmations"]._items == {}


@pytest.mark.asyncio
async def test_qbittorrent_unknown_action_shows_usage(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["bogus"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert any("Uso de /qbittorrent" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_delete_asks_confirmation_without_files(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["delete", "Debian"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    confirmation = next(iter(context.bot_data["confirmations"]._items.values()))
    assert confirmation.action == "qbittorrent.delete"
    assert confirmation.args == {"hash": "aaaaaaaaaaaa", "delete_files": False}
    assert any("no los archivos descargados" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_delete_accepts_files_flag(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["delete", "Debian", "files"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    confirmation = next(iter(context.bot_data["confirmations"]._items.values()))
    assert confirmation.args["delete_files"] is True
    assert any("también los archivos descargados" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_limit_sets_download_limit(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["limit", "down", "500"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    calls = [call for client in qb_client.instances for call in client.calls]
    assert ("set_download_limit", (500 * 1024,)) in calls
    assert not any(call[0] == "set_upload_limit" for call in calls)
    assert any("Límites actualizados" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_limit_rejects_bad_value(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["limit", "down", "mucho"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    calls = [call for client in qb_client.instances for call in client.calls]
    assert not any(call[0].startswith("set_") for call in calls)
    assert any("Uso de /qbittorrent" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_pause_resolves_torrent_by_name(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["pause", "Debian"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    calls = [call for client in qb_client.instances for call in client.calls]
    assert ("set_paused", ("aaaaaaaaaaaa", True)) in calls
    assert any("Torrent pausado" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_add_without_argument_arms_capture(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path, ["add"])
    await qbittorrent.cmd_qbittorrent(make_update(FakeMessage()), context)  # type: ignore[arg-type]
    assert context.chat_data["qb_add_armed"] is True
    assert any("Añadir torrent" in text for text in context.bot.edits)


@pytest.mark.asyncio
async def test_qbittorrent_consume_text_rejects_invalid_link(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path)
    context.chat_data["qb_add_armed"] = True
    message = FakeMessage("no-es-un-enlace")
    consumed = await qbittorrent.consume_text(  # type: ignore[arg-type]
        make_update(message), context
    )
    assert consumed is True
    assert any("magnet" in text for text in message.sent)
    calls = [call for client in qb_client.instances for call in client.calls]
    assert not any(call[0] == "add" for call in calls)


@pytest.mark.asyncio
async def test_qbittorrent_consume_text_adds_magnet(
    settings: Settings, tmp_path: Path, qb_client: type[FakeQbittorrent]
) -> None:
    context = await make_context(settings, tmp_path)
    context.chat_data["qb_add_armed"] = True
    consumed = await qbittorrent.consume_text(  # type: ignore[arg-type]
        make_update(FakeMessage("magnet:?xt=urn:btih:abc")), context
    )
    assert consumed is True
    assert "qb_add_armed" not in context.chat_data
    calls = [call for client in qb_client.instances for call in client.calls]
    assert ("add", ("magnet:?xt=urn:btih:abc", "")) in calls
