"""Pantallas y acciones ampliadas del sistema (1.6.0).

Agrupa las funciones específicas de Unraid que no encajan en ``system.py``:
historial de paridad, licencia, plugins, servicios, red, logs, SMART, shares,
temperaturas, claves de API, identidad y diagnóstico.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..formatting import esc
from ..i18n import localize
from ..keyboards import (
    api_keys_keyboard,
    back_menu,
    confirm_keyboard,
    diagnostics_keyboard,
    flash_backup_keyboard,
    identity_keyboard,
    license_keyboard,
    log_content_keyboard,
    logs_keyboard,
    network_keyboard,
    parity_history_keyboard,
    plugins_keyboard,
    services_keyboard,
    share_detail_keyboard,
    shares_keyboard,
    smart_keyboard,
    temperatures_keyboard,
)
from ..security import resolve_short, short_id
from ..unraid import UnraidError
from ..views import build_shares, paginate
from ..views_system import (
    LOG_LINES_PER_PAGE,
    PARITY_PER_PAGE,
    PLUGIN_PER_PAGE,
    build_api_keys,
    build_diagnostics,
    build_identity,
    build_license,
    build_log_content,
    build_log_files,
    build_network,
    build_parity_history,
    build_plugins,
    build_services,
    build_share_detail,
    build_smart,
    build_temperatures,
)
from .common import audit, authorized, ensure_writable, get_settings, notify, render

LOG = logging.getLogger(__name__)

PENDING_KEY = "pending_input"
THRESHOLD_KEYS = ("cpu_warning", "cpu_critical", "disk_warning", "disk_critical")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _array_disks(array: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("parities", "disks", "caches"):
        value = array.get(key)
        if isinstance(value, list):
            result.extend(item for item in value if isinstance(item, dict))
    return result


def _page_from(data: str, index: int = 2) -> int:
    parts = data.split(":")
    if len(parts) > index and parts[index].isdigit():
        return int(parts[index])
    return 0


def _arm(context: ContextTypes.DEFAULT_TYPE, kind: str, **extra: Any) -> None:
    context.chat_data[PENDING_KEY] = {"kind": kind, **extra}


async def _delete_message(update: Update) -> None:
    """Borra el mensaje del usuario, útil para contraseñas."""
    message = update.effective_message
    if message is None:
        return
    try:
        await message.delete()
    except TelegramError:
        pass


async def _syslog_tail(client: Any, lines: int = 200) -> str | None:
    try:
        files = await client.log_files()
    except UnraidError:
        return None
    target = None
    for item in files:
        label = str(item.get("name") or item.get("path") or "").lower()
        if "syslog" in label:
            target = item
            break
    if target is None:
        return None
    try:
        data = await client.log_file(str(target.get("path")), lines=lines)
    except UnraidError:
        return None
    return str(data.get("content") or "") or None


async def _confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    action: str,
    target: str,
    args: dict[str, Any],
    prompt: str,
    success_text: str,
    return_callback: str,
) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    manager = context.bot_data["confirmations"]
    confirmation = manager.create(
        user_id=user.id,
        chat_id=chat.id,
        action=action,
        target=target,
        args=args,
        prompt=prompt,
        success_text=success_text,
        return_callback=return_callback,
    )
    await render(update, context, confirmation.prompt, confirm_keyboard(confirmation.token))


# ---------------------------------------------------------------------------
# Paridad
# ---------------------------------------------------------------------------

async def _render_parity_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0
) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    history = await client.parity_history()
    _, page, pages = paginate(history, page, PARITY_PER_PAGE)
    await render(
        update,
        context,
        build_parity_history(history, settings, page),
        parity_history_keyboard(page, pages),
    )


@authorized
async def show_parity_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = 0
    query = update.callback_query
    if query is not None and query.data.startswith("s:ph:"):
        page = _page_from(query.data)
    await _render_parity_history(update, context, page)


# ---------------------------------------------------------------------------
# Licencia, plugins y servicios
# ---------------------------------------------------------------------------

async def _render_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    data = await client.registration()
    await render(update, context, build_license(data), license_keyboard())


@authorized
async def show_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_license(update, context)


async def _render_plugins(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0
) -> None:
    client = context.bot_data["client"]
    plugins = await client.plugins()
    _, page, pages = paginate(plugins, page, PLUGIN_PER_PAGE)
    await render(
        update, context, build_plugins(plugins, page), plugins_keyboard(page, pages)
    )


@authorized
async def show_plugins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    page = 0
    query = update.callback_query
    if query is not None and query.data.startswith("s:plugins:"):
        page = _page_from(query.data)
    await _render_plugins(update, context, page)


@authorized
async def ask_install_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    _arm(context, "plugin_url")
    await render(
        update,
        context,
        "➕ <b>Instalar plugin</b>\n\n"
        "Envía la URL del archivo <code>.plg</code>. Unraid lo descargará y "
        "ejecutará su instalador; puede pedir un reinicio al terminar.",
        back_menu("s:plugins"),
    )


async def _render_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    services = await client.services()
    await render(update, context, build_services(services), services_keyboard())


@authorized
async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_services(update, context)


async def _render_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    data = await client.network()
    await render(
        update, context, build_network(data), network_keyboard(data.get("access_urls"))
    )


@authorized
async def show_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_network(update, context)


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

async def _render_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    files = await client.log_files()
    await render(update, context, build_log_files(files), logs_keyboard(files))


@authorized
async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_logs(update, context)


def _resolve_log(files: list[dict[str, Any]], token: str) -> dict[str, Any] | None:
    for item in files:
        path = str(item.get("path") or item.get("name") or "")
        if path and short_id(path) == token:
            return item
    return None


@authorized
async def show_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    if token == "noop":
        return
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    client = context.bot_data["client"]
    files = await client.log_files()
    target = _resolve_log(files, token)
    if target is None:
        await notify(update, context, "Ese log ya no existe. Vuelve a abrir la lista.")
        return
    path = str(target.get("path") or target.get("name"))
    data = await client.log_file(path, lines=400)
    total = int(data.get("totalLines") or len(str(data.get("content") or "").splitlines()))
    pages = max(1, (total + LOG_LINES_PER_PAGE - 1) // LOG_LINES_PER_PAGE)
    await render(
        update,
        context,
        build_log_content(data, page=page),
        log_content_keyboard(token, page, pages),
    )


@authorized
async def send_log_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_chat is None:
        return
    parts = query.data.split(":")
    token = parts[2] if len(parts) > 2 else ""
    client = context.bot_data["client"]
    files = await client.log_files()
    target = _resolve_log(files, token)
    if target is None:
        await notify(update, context, "Ese log ya no existe.")
        return
    path = str(target.get("path") or target.get("name"))
    data = await client.log_file(path, lines=1000)
    content = str(data.get("content") or "")
    filename = path.rstrip("/").split("/")[-1] or "log.txt"
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=io.BytesIO(content.encode("utf-8")),
            filename=filename,
            caption=localize(f"📜 Últimas 1000 líneas de {filename}"),
        )
    except TelegramError as exc:
        await notify(update, context, f"❌ No se pudo enviar el archivo: {exc}")


# ---------------------------------------------------------------------------
# Discos y shares
# ---------------------------------------------------------------------------

@authorized
async def show_smart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    token = query.data.split(":")[2] if len(query.data.split(":")) > 2 else ""
    client = context.bot_data["client"]
    disks = await client.physical_disks()
    disk = resolve_short(disks, token)
    if disk is None:
        await notify(update, context, "Ese disco ya no existe. Vuelve a abrir la lista.")
        return
    array = await client.array()
    mountable = any(
        str(item.get("id") or "") == str(disk.get("id") or "") for item in _array_disks(array)
    )
    await render(update, context, build_smart(disk), smart_keyboard(disk, mountable=mountable))


@authorized
async def disk_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    parts = query.data.split(":")
    action = parts[2] if len(parts) > 2 else ""
    token = parts[3] if len(parts) > 3 else ""
    if not await ensure_writable(update, context):
        return
    client = context.bot_data["client"]
    array = await client.array()
    disk = resolve_short(_array_disks(array), token)
    if disk is None:
        await notify(update, context, "Ese disco ya no está en el array.")
        return
    name = str(disk.get("name") or disk.get("device") or "disco")
    mounting = action == "mount"
    await _confirmation(
        update,
        context,
        action=f"array.{action}",
        target=str(disk.get("id")),
        args={"id": disk.get("id")},
        prompt=(
            f"📂 <b>Montar {esc(name)}</b>\n\n¿Continuar?"
            if mounting
            else f"📤 <b>Desmontar {esc(name)}</b>\n\n"
            "El disco dejará de estar disponible hasta que lo vuelvas a montar.\n\n¿Continuar?"
        ),
        success_text=(
            f"✅ <b>Disco {esc(name)} montado.</b>"
            if mounting
            else f"✅ <b>Disco {esc(name)} desmontado.</b>"
        ),
        return_callback="m:disks",
    )


async def _render_shares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    shares = await client.shares()
    await render(update, context, build_shares(shares), shares_keyboard(shares))


@authorized
async def show_shares_extra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_shares(update, context)


@authorized
async def show_share_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    token = query.data.split(":")[2] if len(query.data.split(":")) > 2 else ""
    client = context.bot_data["client"]
    shares = await client.shares()
    share = resolve_short(shares, token, key="name")
    if share is None:
        await notify(update, context, "Ese share ya no existe.")
        return
    await render(
        update,
        context,
        build_share_detail(share),
        share_detail_keyboard(str(share.get("name") or "share")),
    )


# ---------------------------------------------------------------------------
# Temperaturas y umbrales
# ---------------------------------------------------------------------------

async def _render_temperatures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    client = context.bot_data["client"]
    data = await client.temperatures()
    await render(
        update, context, build_temperatures(data, settings), temperatures_keyboard()
    )


@authorized
async def show_temperatures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_temperatures(update, context)


def _thresholds_text(settings) -> str:
    return (
        "⚙️ <b>Umbrales de temperatura</b>\n\n"
        f"CPU: aviso {settings.cpu_temp_warning}°C\n"
        f"Discos: aviso {settings.disk_temp_warning}°C · crítico "
        f"{settings.disk_temp_critical}°C\n\n"
        "<i>Estos son los umbrales que usa el bot. Unraid mantiene los suyos "
        "en Settings → Temperature Settings.</i>"
    )


@authorized
async def show_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    await render(update, context, _thresholds_text(settings), temperatures_keyboard())


@authorized
async def ask_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    settings = get_settings(context)
    _arm(context, "thresholds")
    await render(
        update,
        context,
        "⚙️ <b>Configurar umbrales en Unraid</b>\n\n"
        "Envía los valores como <code>clave=valor</code>, separados por espacios:\n"
        "<code>cpu_warning=80 cpu_critical=90 disk_warning=50 disk_critical=55</code>\n\n"
        f"Ahora mismo: CPU {settings.cpu_temp_warning}°C · discos "
        f"{settings.disk_temp_warning}/{settings.disk_temp_critical}°C.",
        back_menu("s:temp"),
    )


async def _apply_thresholds(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    values: dict[str, int] = {}
    for token in text.replace(",", " ").split():
        key, _, raw = token.partition("=")
        key = key.strip()
        if key not in THRESHOLD_KEYS:
            continue
        try:
            values[key] = int(raw)
        except ValueError:
            await notify(update, context, f"❌ Valor no válido para {key}.")
            return
    if not values:
        await notify(
            update,
            context,
            "❌ No he encontrado valores. Usa por ejemplo "
            "<code>cpu_warning=80 disk_warning=50</code>.",
        )
        return
    client = context.bot_data["client"]
    await client.update_temperature_config(values)
    await audit(update, context, "temperature.thresholds", ",".join(values))
    await render(
        update,
        context,
        "✅ <b>Umbrales actualizados en Unraid</b>\n\n"
        + "\n".join(f"• {key}: {value}°C" for key, value in values.items()),
        back_menu("s:temp"),
    )


# ---------------------------------------------------------------------------
# Claves de API
# ---------------------------------------------------------------------------

async def _render_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    keys = await client.api_keys()
    await render(update, context, build_api_keys(keys), api_keys_keyboard(keys))


@authorized
async def show_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_api_keys(update, context)


@authorized
async def ask_new_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    _arm(context, "api_key_name")
    await render(
        update,
        context,
        "🔑 <b>Crear clave de API</b>\n\n"
        "Envía un nombre para la clave. Se creará con rol <b>VIEWER</b> "
        "(solo lectura), que es lo que necesita el bot.\n\n"
        "La clave se mostrará una sola vez.",
        back_menu("s:keys"),
    )


@authorized
async def ask_delete_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    token = query.data.split(":")[3] if len(query.data.split(":")) > 3 else ""
    if not await ensure_writable(update, context):
        return
    client = context.bot_data["client"]
    keys = await client.api_keys()
    key = resolve_short(keys, token)
    if key is None:
        await notify(update, context, "Esa clave ya no existe.")
        return
    await _confirmation(
        update,
        context,
        action="apikey.delete",
        target=str(key.get("id")),
        args={"id": key.get("id")},
        prompt=(
            f"🗑 <b>Borrar la clave {esc(str(key.get('name') or '—'))}</b>\n\n"
            "Cualquier cliente que la use dejará de funcionar.\n\n¿Continuar?"
        ),
        success_text="🗑 <b>Clave de API borrada.</b>",
        return_callback="s:keys",
    )


async def _apply_api_key_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE, name: str
) -> None:
    name = name[:60]
    client = context.bot_data["client"]
    created = await client.create_api_key(name, description="Creada desde UnraidBot")
    await audit(update, context, "apikey.create", name)
    key = str(created.get("key") or "")
    await render(
        update,
        context,
        "🔑 <b>Clave creada</b>\n\n"
        f"Nombre: <b>{esc(name)}</b>\n"
        "Rol: <code>VIEWER</code>\n\n"
        f"<code>{esc(key)}</code>\n\n"
        "⚠️ Cópiala ahora: no se volverá a mostrar.",
        back_menu("s:keys"),
    )


# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------

async def _render_identity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    server = await client.server_identity()
    await render(update, context, build_identity(server), identity_keyboard())


@authorized
async def show_identity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_identity(update, context)


@authorized
async def ask_identity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    _arm(context, "identity")
    await render(
        update,
        context,
        "🏷️ <b>Editar identidad</b>\n\n"
        "Envía el nombre y, si quieres, un comentario separado por <code>|</code>:\n"
        "<code>MiServidor | Servidor del salón</code>",
        back_menu("s:identity"),
    )


async def _apply_identity(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    name, _, comment = text.partition("|")
    name = name.strip()[:60]
    if not name:
        await notify(update, context, "❌ El nombre no puede estar vacío.")
        return
    client = context.bot_data["client"]
    await client.set_server_identity(name, comment.strip() or None)
    await audit(update, context, "server.identity", name)
    await _render_identity(update, context)


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------

async def _diagnostics_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings(context)
    client = context.bot_data["client"]
    snapshot = await client.snapshot()
    from ..health import detect_problems

    problems = detect_problems(snapshot, settings)
    log_tail = await _syslog_tail(client, lines=200)
    return snapshot, settings, problems, log_tail


@authorized
async def show_diagnostics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot, settings, problems, log_tail = await _diagnostics_parts(update, context)
    await render(
        update,
        context,
        build_diagnostics(
            snapshot, settings, problems, log_tail=(log_tail or "")[-1500:] or None
        ),
        diagnostics_keyboard(),
    )


@authorized
async def cmd_diagnostics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot, settings, problems, log_tail = await _diagnostics_parts(update, context)
    await render(
        update,
        context,
        build_diagnostics(snapshot, settings, problems),
        diagnostics_keyboard(),
    )
    if log_tail and update.effective_chat is not None:
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=io.BytesIO(log_tail.encode("utf-8")),
                filename="syslog.txt",
                caption=localize("🩺 Últimas 200 líneas del syslog"),
            )
        except TelegramError as exc:
            LOG.info("No se pudo enviar el syslog: %s", exc)


# ---------------------------------------------------------------------------
# Backup del flash
# ---------------------------------------------------------------------------

@authorized
async def show_flash_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_flash_backup(update, context)


async def _render_flash_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = context.bot_data["client"]
    remotes = await client.rclone_remotes()
    lines = ["💾 <b>Backup del flash</b>", ""]
    if not remotes:
        lines.append("No hay remotos de rclone configurados.")
        lines.append("")
        lines.append(
            "Crea uno en <i>Settings → Backup/Restore Flash Drive</i> y vuelve aquí."
        )
    else:
        lines.append("Elige el remoto de destino. Se copiará <code>/boot</code>.")
        lines.append("")
        for remote in remotes:
            lines.append(
                f"• <b>{esc(str(remote.get('name') or '—'))}</b> "
                f"({esc(str(remote.get('type') or '—'))})"
            )
    await render(update, context, "\n".join(lines), flash_backup_keyboard(remotes))


@authorized
async def ask_flash_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    token = query.data.split(":")[2] if len(query.data.split(":")) > 2 else ""
    if not await ensure_writable(update, context):
        return
    client = context.bot_data["client"]
    remotes = await client.rclone_remotes()
    remote = next(
        (item for item in remotes if short_id(str(item.get("name") or "")) == token), None
    )
    if remote is None:
        await notify(update, context, "Ese remoto ya no existe.")
        return
    name = str(remote.get("name"))
    await _confirmation(
        update,
        context,
        action="flash.backup",
        target=name,
        args={"remote": name},
        prompt=(
            f"💾 <b>Backup del flash a {esc(name)}</b>\n\n"
            "Se copiará el contenido de <code>/boot</code> al remoto. "
            "Puede tardar varios minutos.\n\n¿Continuar?"
        ),
        success_text=f"✅ <b>Backup del flash lanzado a {esc(name)}.</b>",
        return_callback="s:license",
    )


# ---------------------------------------------------------------------------
# Entrada de texto pendiente
# ---------------------------------------------------------------------------

async def _apply_pending(
    update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str, text: str
) -> None:
    if kind == "array_password":
        await _delete_message(update)
        if not await ensure_writable(update, context):
            return
        await _confirmation(
            update,
            context,
            action="array.start_encrypted",
            target="array",
            args={"password": text},
            prompt=(
                "🔐 <b>Iniciar array cifrado</b>\n\n"
                "Se usará la contraseña una sola vez y no se guardará. "
                "He borrado tu mensaje con la contraseña.\n\n¿Continuar?"
            ),
            success_text="✅ <b>Array cifrado iniciado.</b>",
            return_callback="s:array",
        )
        return

    if not await ensure_writable(update, context):
        return

    if kind == "plugin_url":
        if not text.startswith(("http://", "https://")):
            await notify(update, context, "❌ Envía una URL http(s) al archivo .plg.")
            return
        await _confirmation(
            update,
            context,
            action="plugin.install",
            target=text,
            args={"url": text},
            prompt=(
                f"🔌 <b>Instalar plugin</b>\n\n<code>{esc(text)}</code>\n\n"
                "Unraid descargará y ejecutará el instalador. Algunos plugins "
                "requieren reiniciar el servidor.\n\n¿Continuar?"
            ),
            success_text="✅ <b>Plugin instalado.</b> Revisa si Unraid pide reiniciar.",
            return_callback="s:plugins",
        )
        return

    if kind == "api_key_name":
        await _apply_api_key_name(update, context, text)
        return

    if kind == "identity":
        await _apply_identity(update, context, text)
        return

    if kind == "thresholds":
        await _apply_thresholds(update, context, text)
        return

    if kind == "notify":
        client = context.bot_data["client"]
        await client.create_notification(
            title="UnraidBot",
            subject=text[:60],
            description=text,
            importance="INFO",
        )
        await audit(update, context, "notification.create", text[:60])
        await render(
            update,
            context,
            "✅ <b>Notificación creada en Unraid</b>\n\n"
            "Aparecerá en el centro de notificaciones del WebGUI.",
            back_menu("s:notif"),
        )
        return

    await notify(update, context, "No sé qué hacer con ese texto.")


async def consume_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Consume el siguiente mensaje si hay una entrada pendiente."""
    pending = context.chat_data.get(PENDING_KEY)
    if not isinstance(pending, dict):
        return False
    message = update.effective_message
    text = (message.text or "").strip() if message is not None else ""
    kind = str(pending.get("kind") or "")
    context.chat_data.pop(PENDING_KEY, None)
    if not text:
        await notify(update, context, "No he recibido ningún texto. Vuelve a intentarlo.")
        return True
    await _apply_pending(update, context, kind, text)
    return True


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

@authorized
async def cmd_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from . import system

    await system._render_notifications(update, context)


@authorized
async def cmd_parity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_parity_history(update, context)


@authorized
async def cmd_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_license(update, context)


@authorized
async def cmd_plugins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_plugins(update, context)


@authorized
async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_services(update, context)


@authorized
async def cmd_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_network(update, context)


@authorized
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_logs(update, context)


@authorized
async def cmd_smart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = [arg for arg in context.args if arg.strip()]
    client = context.bot_data["client"]
    disks_list = await client.physical_disks()
    if not args:
        items, page, pages = paginate(disks_list, 0, 10)
        from ..keyboards import physical_disks_keyboard
        from ..views import build_physical_disks

        await render(
            update,
            context,
            build_physical_disks(disks_list, page, 10),
            physical_disks_keyboard(items, page, pages),
        )
        return
    needle = " ".join(args).lower()
    disk = next(
        (
            item
            for item in disks_list
            if needle in str(item.get("name") or item.get("device") or "").lower()
            or needle == str(item.get("id") or "").lower()
        ),
        None,
    )
    if disk is None:
        await notify(update, context, "No encuentro ese disco. Usa /smart sin argumentos.")
        return
    await render(update, context, build_smart(disk), smart_keyboard(disk))


@authorized
async def cmd_temperatures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_temperatures(update, context)


@authorized
async def cmd_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = [arg for arg in context.args if arg.strip()]
    if not args:
        settings = get_settings(context)
        await render(update, context, _thresholds_text(settings), temperatures_keyboard())
        return
    if not await ensure_writable(update, context):
        return
    await _apply_thresholds(update, context, " ".join(args))


@authorized
async def cmd_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_api_keys(update, context)


@authorized
async def cmd_identity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = [arg for arg in context.args if arg.strip()]
    if not args:
        await _render_identity(update, context)
        return
    if not await ensure_writable(update, context):
        return
    await _apply_identity(update, context, " ".join(args))


@authorized
async def cmd_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_writable(update, context):
        return
    args = [arg for arg in context.args if arg.strip()]
    if not args:
        _arm(context, "notify")
        await render(
            update,
            context,
            "📝 <b>Crear notificación en Unraid</b>\n\n"
            "Envía el texto. Aparecerá en el centro de notificaciones del WebGUI "
            "con importancia INFO.",
            back_menu("s:notif"),
        )
        return
    await _apply_pending(update, context, "notify", " ".join(args))


@authorized
async def cmd_flash_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_flash_backup(update, context)
