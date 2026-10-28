"""Handlers de las pantallas ampliadas de 1.6.0."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bot.config import Settings
from bot.handlers import confirm, docker, system, system_extra
from bot.i18n import set_language
from bot.security import AuditLog, ConfirmationManager, short_id
from bot.state import StateStore
from bot.unraid import Snapshot


class FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.chat_id = 111
        self.message_id = 10
        self.sent: list[tuple[str, object]] = []
        self.deleted = False

    async def reply_text(self, text: str, **kwargs) -> FakeMessage:
        self.sent.append((text, kwargs.get("reply_markup")))
        return FakeMessage()

    async def edit_text(self, text: str, **kwargs) -> None:
        self.sent.append((text, kwargs.get("reply_markup")))

    async def delete(self) -> None:
        self.deleted = True


class FakeBot:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object]] = []
        self.documents: list[dict] = []

    async def edit_message_text(self, **kwargs) -> None:
        self.edits.append((kwargs["text"], kwargs.get("reply_markup")))

    async def send_message(self, **kwargs) -> None:
        self.edits.append((kwargs["text"], kwargs.get("reply_markup")))

    async def send_document(self, **kwargs) -> None:
        self.documents.append(kwargs)


class FakeQuery:
    def __init__(self, data: str = "", message: FakeMessage | None = None) -> None:
        self.data = data
        self.message = message or FakeMessage()
        self.from_user = SimpleNamespace(id=111, username="alois", first_name="Alois")
        self.answered: list[str] = []

    async def answer(self, text: str = "", **kwargs) -> None:
        self.answered.append(text)

    async def edit_message_text(self, text: str, **kwargs) -> None:
        self.message.sent.append((text, kwargs.get("reply_markup")))


class FakeClient:
    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot_data = snapshot
        self.calls: list[tuple[str, tuple, dict]] = []
        self.snapshot_kwargs: list[dict] = []
        self.parity = [
            {"date": "2026-10-01T03:00:00Z", "status": "COMPLETED", "errors": 0},
            {"date": "2026-09-01T03:00:00Z", "status": "FAILED", "errors": 1},
        ]
        self.plugins_data = [{"name": "x.plg", "version": "1.0"}]
        self.services_data = [{"name": "nginx", "online": True}]
        self.network_data = {
            "interfaces": [{"name": "eth0", "operstate": "up"}],
            "access_urls": [{"type": "LAN", "ipv4": "http://tower"}],
        }
        self.log_files_data = [{"name": "syslog", "path": "/var/log/syslog", "size": 10}]
        self.log_content = {"content": "linea 1\nlinea 2", "totalLines": 2, "path": "/var/log/syslog"}
        self.disks = [
            {
                "id": "disk:d1",
                "name": "disk1",
                "device": "/dev/sdb",
                "smartStatus": "OK",
                "temperature": 30,
            }
        ]
        self.shares_data = [{"name": "media", "used": 1, "size": 2, "cache": True}]
        self.temperatures_data = {
            "temperature": {
                "sensors": [
                    {"name": "CPU", "current": {"value": 40, "unit": "CELSIUS"}}
                ]
            },
            "network": [],
        }
        self.api_keys_data = [{"id": "key:1", "name": "bot", "roles": ["VIEWER"]}]
        self.identity = {"name": "tower", "comment": "salón"}
        self.remotes = [{"name": "backup", "type": "s3"}]
        self.docker = [
            {
                "id": "docker:c1",
                "names": ["/plex"],
                "state": "RUNNING",
                "image": "plex:latest",
                "autoStart": True,
            }
        ]
        self.extras = {
            "containers": [
                {"id": "docker:c1", "names": ["/plex"], "sizeLog": 10, "isOrphaned": False}
            ],
            "updates": [{"name": "plex", "updateStatus": "UPDATE_AVAILABLE"}],
            "conflicts": {},
        }
        self.notifications_view = {
            "overview": {
                "unread": {"alert": 1, "warning": 0, "info": 0, "total": 1},
                "archive": {"alert": 0, "warning": 0, "info": 0, "total": 0},
            },
            "items": [
                {
                    "id": "notif:1",
                    "subject": "Aviso",
                    "importance": "ALERT",
                    "type": "UNREAD",
                }
            ],
        }

    def _record(self, name: str, *args, **kwargs) -> None:
        self.calls.append((name, args, kwargs))

    def calls_named(self, name: str) -> list[tuple[object, dict]]:
        return [
            (args[0] if len(args) == 1 else args, kwargs)
            for called, args, kwargs in self.calls
            if called == name
        ]

    async def snapshot(self, **kwargs) -> Snapshot:
        self.snapshot_kwargs.append(kwargs)
        return self.snapshot_data

    async def array(self) -> dict:
        return self.snapshot_data.array or {}

    async def parity_history(self) -> list[dict]:
        return self.parity

    async def registration(self) -> dict:
        return {"registration": {"state": "BASIC"}, "flash": {"vendor": "SanDisk"}}

    async def plugins(self) -> list[dict]:
        return self.plugins_data

    async def services(self) -> list[dict]:
        return self.services_data

    async def network(self) -> dict:
        return self.network_data

    async def log_files(self) -> list[dict]:
        return self.log_files_data

    async def log_file(self, path: str, *, lines: int = 200) -> dict:
        self._record("log_file", path, lines=lines)
        return dict(self.log_content, path=path)

    async def physical_disks(self) -> list[dict]:
        return self.disks

    async def shares(self) -> list[dict]:
        return self.shares_data

    async def temperatures(self) -> dict:
        return self.temperatures_data

    async def api_keys(self) -> list[dict]:
        return self.api_keys_data

    async def server_identity(self) -> dict:
        return self.identity

    async def set_server_identity(self, name: str, comment: str | None = None) -> dict:
        self._record("set_server_identity", name, comment)
        return {"name": name, "comment": comment}

    async def rclone_remotes(self) -> list[dict]:
        return self.remotes

    async def docker_containers(self) -> list[dict]:
        return self.docker

    async def docker_extras(self) -> dict:
        return self.extras

    async def create_api_key(self, name: str, *, description: str = "") -> dict:
        self._record("create_api_key", name, description=description)
        return {"key": "clave-secreta", "id": "key:2"}

    async def update_temperature_config(self, thresholds: dict) -> bool:
        self._record("update_temperature_config", thresholds)
        return True

    async def create_notification(self, **kwargs) -> None:
        self._record("create_notification", **kwargs)

    async def notifications_filtered(self, **kwargs) -> dict:
        self._record("notifications_filtered", **kwargs)
        return self.notifications_view

    async def archive_notification(self, notification_id: str) -> None:
        self._record("archive_notification", notification_id)

    async def unarchive_notification(self, notification_id: str) -> None:
        self._record("unarchive_notification", notification_id)

    async def mark_notification_unread(self, notification_id: str) -> None:
        self._record("mark_notification_unread", notification_id)

    # Acciones confirmadas
    async def start_array_encrypted(self, password: str | None = None) -> None:
        self._record("start_array_encrypted", password)

    async def mount_array_disk(self, disk_id: str) -> None:
        self._record("mount_array_disk", disk_id)

    async def unmount_array_disk(self, disk_id: str) -> None:
        self._record("unmount_array_disk", disk_id)

    async def parity_action(self, action: str, *, correct: bool = False) -> None:
        self._record("parity_action", action, correct=correct)

    async def install_plugin(self, url: str, name: str | None = None) -> dict:
        self._record("install_plugin", url)
        return {}

    async def flash_backup(self, remote: str, **kwargs) -> dict:
        self._record("flash_backup", remote)
        return {}

    async def delete_api_key(self, key_id: str) -> bool:
        self._record("delete_api_key", key_id)
        return True

    async def delete_notification(self, notification_id: str, *, archived: bool = False) -> None:
        self._record("delete_notification", notification_id, archived=archived)


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


async def make_context(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> FakeContext:
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


def callback(data: str) -> tuple[FakeQuery, SimpleNamespace]:
    query = FakeQuery(data)
    return query, make_update(query.message, query)


@pytest.mark.asyncio
async def test_parity_history_screen(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    _, update = callback("s:ph:1")

    await system_extra.show_parity_history(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "Historial de paridad" in rendered
    assert "Total: 2" in rendered


@pytest.mark.asyncio
async def test_license_screen(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    _, update = callback("s:license")

    await system_extra.show_license(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "Licencia y flash" in rendered
    assert "BASIC" in rendered and "SanDisk" in rendered
    assert buttons(context.bot.edits[-1][1])[-1] == ["m:main"]


@pytest.mark.asyncio
async def test_plugins_screen_and_install_prompt(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    _, update = callback("s:plugins")

    await system_extra.show_plugins(update, context)  # type: ignore[arg-type]
    assert "x.plg" in texts(context.bot.edits)

    _, update = callback("s:plugin:add")
    await system_extra.ask_install_plugin(update, context)  # type: ignore[arg-type]
    assert context.chat_data["pending_input"] == {"kind": "plugin_url"}
    assert buttons(context.bot.edits[-1][1]) == [["s:plugins", "m:main"]]


@pytest.mark.asyncio
async def test_services_and_network_screens(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:services")
    await system_extra.show_services(update, context)  # type: ignore[arg-type]
    assert "nginx" in texts(context.bot.edits)

    _, update = callback("s:network")
    await system_extra.show_network(update, context)  # type: ignore[arg-type]
    assert "eth0" in texts(context.bot.edits)
    assert "http://tower" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_logs_list_content_and_file(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    token = short_id("/var/log/syslog")

    _, update = callback("s:logs")
    await system_extra.show_logs(update, context)  # type: ignore[arg-type]
    assert "syslog" in texts(context.bot.edits)

    _, update = callback(f"s:log:{token}:0")
    await system_extra.show_log(update, context)  # type: ignore[arg-type]
    assert "linea 1" in texts(context.bot.edits)

    _, update = callback(f"s:logfile:{token}")
    await system_extra.send_log_file(update, context)  # type: ignore[arg-type]
    assert context.bot.documents
    assert context.bot.documents[-1]["filename"] == "syslog"


@pytest.mark.asyncio
async def test_log_missing_explains_and_keeps_navigation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    _, update = callback("s:log:inexistente:0")

    await system_extra.show_log(update, context)  # type: ignore[arg-type]

    rendered = texts(context.bot.edits)
    assert "Ese log ya no existe" in rendered
    assert buttons(context.bot.edits[-1][1]) == [["m:main", "m:main"]]


@pytest.mark.asyncio
async def test_smart_and_mount_confirmation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    token = short_id("disk:d1")

    _, update = callback(f"s:smart:{token}")
    await system_extra.show_smart(update, context)  # type: ignore[arg-type]
    assert "SMART: <code>OK</code>" in texts(context.bot.edits)
    assert ["s:disk:mount:" + token, "s:disk:unmount:" + token] in buttons(
        context.bot.edits[-1][1]
    )

    _, update = callback(f"s:disk:mount:{token}")
    await system_extra.disk_action(update, context)  # type: ignore[arg-type]
    rendered = texts(context.bot.edits)
    assert "Montar disk1" in rendered
    assert "c:y:" in buttons(context.bot.edits[-1][1])[0][0]


@pytest.mark.asyncio
async def test_share_detail(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    _, update = callback(f"s:share:{short_id('media')}")

    await system_extra.show_share_detail(update, context)  # type: ignore[arg-type]

    assert "media" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_temperatures_and_thresholds_flow(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:temp")
    await system_extra.show_temperatures(update, context)  # type: ignore[arg-type]
    assert "CPU" in texts(context.bot.edits)

    _, update = callback("s:thresh")
    await system_extra.show_thresholds(update, context)  # type: ignore[arg-type]
    assert "Umbrales de temperatura" in texts(context.bot.edits)

    _, update = callback("s:thresh:set")
    await system_extra.ask_thresholds(update, context)  # type: ignore[arg-type]
    assert context.chat_data["pending_input"] == {"kind": "thresholds"}

    message = FakeMessage("cpu_warning=80 disk_critical=60")
    update = make_update(message)
    assert await system_extra.consume_text(update, context) is True  # type: ignore[arg-type]
    assert context.client.calls_named("update_temperature_config") == [
        ({"cpu_warning": 80, "disk_critical": 60}, {})
    ]
    assert "Umbrales actualizados en Unraid" in texts(message.sent)


@pytest.mark.asyncio
async def test_thresholds_invalid_value_keeps_navigation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.chat_data["pending_input"] = {"kind": "thresholds"}
    message = FakeMessage("cpu_warning=alta")
    update = make_update(message)

    await system_extra.consume_text(update, context)  # type: ignore[arg-type]

    assert "Valor no válido para cpu_warning" in texts(message.sent)
    assert context.client.calls_named("update_temperature_config") == []


@pytest.mark.asyncio
async def test_api_key_create_and_delete_flows(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:key:new")
    await system_extra.ask_new_api_key(update, context)  # type: ignore[arg-type]
    assert context.chat_data["pending_input"] == {"kind": "api_key_name"}

    message = FakeMessage("clave del bot")
    update = make_update(message)
    await system_extra.consume_text(update, context)  # type: ignore[arg-type]
    assert context.client.calls_named("create_api_key") == [
        ("clave del bot", {"description": "Creada desde UnraidBot"})
    ]
    rendered = texts(message.sent)
    assert "clave-secreta" in rendered
    assert "no se volverá a mostrar" in rendered

    _, update = callback(f"s:key:del:{short_id('key:1')}")
    await system_extra.ask_delete_api_key(update, context)  # type: ignore[arg-type]
    assert "Borrar la clave bot" in texts(context.bot.edits)
    assert "c:y:" in buttons(context.bot.edits[-1][1])[0][0]


@pytest.mark.asyncio
async def test_identity_edit_flow(settings: Settings, snapshot: Snapshot, tmp_path: Path) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:identity:edit")
    await system_extra.ask_identity(update, context)  # type: ignore[arg-type]
    assert context.chat_data["pending_input"] == {"kind": "identity"}

    message = FakeMessage("tower | salón")
    update = make_update(message)
    await system_extra.consume_text(update, context)  # type: ignore[arg-type]

    assert context.client.calls_named("set_server_identity") == [
        (("tower", "salón"), {})
    ]
    assert "tower" in texts(message.sent)


@pytest.mark.asyncio
async def test_flash_backup_list_and_confirmation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:flash")
    await system_extra.show_flash_backup(update, context)  # type: ignore[arg-type]
    assert "backup" in texts(context.bot.edits)

    _, update = callback(f"s:flash:{short_id('backup')}")
    await system_extra.ask_flash_backup(update, context)  # type: ignore[arg-type]
    rendered = texts(context.bot.edits)
    assert "Backup del flash a backup" in rendered
    assert "c:y:" in buttons(context.bot.edits[-1][1])[0][0]


@pytest.mark.asyncio
async def test_diagnostics_command_sends_syslog(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.client.log_files_data = [{"name": "syslog", "path": "/var/log/syslog"}]
    message = FakeMessage("/diagnostico")
    update = make_update(message)

    await system_extra.cmd_diagnostics(update, context)  # type: ignore[arg-type]

    assert "Diagnóstico" in texts(context.bot.edits)
    assert context.bot.documents
    assert context.bot.documents[-1]["filename"] == "syslog.txt"


@pytest.mark.asyncio
async def test_consume_text_without_pending_returns_false(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    update = make_update(FakeMessage("hola"))
    assert await system_extra.consume_text(update, context) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_consume_text_without_content_notifies(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.chat_data["pending_input"] = {"kind": "notify"}
    message = FakeMessage("   ")
    update = make_update(message)

    assert await system_extra.consume_text(update, context) is True  # type: ignore[arg-type]
    assert "No he recibido ningún texto" in texts(message.sent)


@pytest.mark.asyncio
async def test_notify_command_creates_notification(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    context.args = ["Aviso", "desde", "el", "bot"]
    message = FakeMessage("/notificar Aviso desde el bot")
    update = make_update(message)

    await system_extra.cmd_notify(update, context)  # type: ignore[arg-type]

    calls = context.client.calls_named("create_notification")
    assert calls and calls[0][1]["subject"] == "Aviso desde el bot"
    assert calls[0][1]["importance"] == "INFO"
    assert "Notificación creada en Unraid" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_encrypted_array_start_asks_password_then_confirms(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:astart:enc")
    await system.array_action(update, context)  # type: ignore[arg-type]
    assert context.chat_data["pending_input"] == {"kind": "array_password"}
    assert "Envía la contraseña del array" in texts(context.bot.edits)

    message = FakeMessage("mi-clave")
    update = make_update(message)
    await system_extra.consume_text(update, context)  # type: ignore[arg-type]

    assert message.deleted is True
    assert "He borrado tu mensaje con la contraseña" in texts(message.sent)
    assert "c:y:" in buttons(message.sent[-1][1])[0][0]


@pytest.mark.asyncio
async def test_parity_choice_creates_correct_confirmation(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:pc:1")
    await system.parity_start_choice(update, context)  # type: ignore[arg-type]
    assert "correctiva" in texts(context.bot.edits)
    token = buttons(context.bot.edits[-1][1])[0][0].split(":")[2]
    item = context.bot_data["confirmations"].pop(token, 111)
    assert item is not None and item.args == {"correct": True}

    _, update = callback("s:pc:0")
    await system.parity_start_choice(update, context)  # type: ignore[arg-type]
    token = buttons(context.bot.edits[-1][1])[0][0].split(":")[2]
    item = context.bot_data["confirmations"].pop(token, 111)
    assert item is not None and item.args == {"correct": False}


@pytest.mark.asyncio
async def test_notifications_filter_and_detail(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("s:notif:f:ALERT:1")
    await system.show_notifications(update, context)  # type: ignore[arg-type]
    calls = context.client.calls_named("notifications_filtered")
    assert calls[0][1] == {"archived": True, "importance": "ALERT", "offset": 0, "limit": 5}
    assert "Archivadas · ALERT" in texts(context.bot.edits)

    context.chat_data["notif_filter"] = {"archived": False, "importance": None}
    _, update = callback(f"s:notif:d:{short_id('notif:1')}")
    await system.notification_detail(update, context)  # type: ignore[arg-type]
    assert "Aviso" in texts(context.bot.edits)
    assert "Importancia: 🔴 ALERT" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_notification_actions(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    token = short_id("notif:1")

    _, update = callback(f"s:notif:a:{token}")
    await system.notification_action(update, context)  # type: ignore[arg-type]
    assert context.client.calls_named("archive_notification") == [("notif:1", {})]

    _, update = callback(f"s:notif:u:{token}")
    await system.notification_action(update, context)  # type: ignore[arg-type]
    assert context.client.calls_named("unarchive_notification") == [("notif:1", {})]

    _, update = callback(f"s:notif:m:{token}")
    await system.notification_action(update, context)  # type: ignore[arg-type]
    assert context.client.calls_named("mark_notification_unread") == [("notif:1", {})]

    _, update = callback(f"s:notif:x:{token}")
    await system.notification_action(update, context)  # type: ignore[arg-type]
    assert "Borrar notificación" in texts(context.bot.edits)
    assert "c:y:" in buttons(context.bot.edits[-1][1])[0][0]


@pytest.mark.asyncio
async def test_docker_maintenance_sizes_and_detail(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)

    _, update = callback("d:maint")
    await docker.show_maintenance(update, context)  # type: ignore[arg-type]
    assert "Actualizaciones pendientes" in texts(context.bot.edits)

    _, update = callback("d:sizes")
    await docker.show_sizes(update, context)  # type: ignore[arg-type]
    assert "Docker · tamaños" in texts(context.bot.edits)

    _, update = callback(f"d:v:{short_id('docker:c1')}:0")
    await docker.show_detail(update, context)  # type: ignore[arg-type]
    assert "Estado de imagen: ⬆️ hay una imagen nueva" in texts(context.bot.edits)


@pytest.mark.asyncio
async def test_system_menu_requests_health_data(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    update = make_update(FakeMessage("/sistema"))

    await system.show_system_menu(update, context)  # type: ignore[arg-type]

    assert context.client.snapshot_kwargs == [{"include_info": False, "include_health": True}]


@pytest.mark.asyncio
async def test_confirmed_actions_dispatch_to_client(
    settings: Settings, snapshot: Snapshot, tmp_path: Path
) -> None:
    context = await make_context(settings, snapshot, tmp_path)
    manager: ConfirmationManager = context.bot_data["confirmations"]

    async def run(action: str, args: dict) -> None:
        item = manager.create(
            user_id=111,
            chat_id=111,
            action=action,
            target="x",
            args=args,
            prompt="¿?",
            success_text="ok",
            return_callback="m:main",
        )
        await confirm._execute(context, item)  # type: ignore[arg-type]

    await run("array.start_encrypted", {"password": "clave"})
    await run("array.mount", {"id": "disk:d1"})
    await run("array.unmount", {"id": "disk:d1"})
    await run("parity.start", {"correct": True})
    await run("plugin.install", {"url": "https://example.test/x.plg"})
    await run("flash.backup", {"remote": "backup"})
    await run("apikey.delete", {"id": "key:1"})
    await run("notification.delete", {"id": "notif:1", "archived": True})

    assert context.client.calls_named("start_array_encrypted") == [("clave", {})]
    assert context.client.calls_named("mount_array_disk") == [("disk:d1", {})]
    assert context.client.calls_named("unmount_array_disk") == [("disk:d1", {})]
    assert context.client.calls_named("parity_action") == [
        ("start", {"correct": True})
    ]
    assert context.client.calls_named("install_plugin") == [("https://example.test/x.plg", {})]
    assert context.client.calls_named("flash_backup") == [("backup", {})]
    assert context.client.calls_named("delete_api_key") == [("key:1", {})]
    assert context.client.calls_named("delete_notification") == [
        ("notif:1", {"archived": True})
    ]
