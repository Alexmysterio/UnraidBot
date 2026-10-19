"""Registro centralizado de handlers."""

from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from . import alerts, common, confirm, disks, docker, status, system, vms


def register_handlers(application: Application) -> None:
    # Comandos
    application.add_handler(CommandHandler(["start", "inicio"], common.cmd_start))
    application.add_handler(CommandHandler(["menu"], common.cmd_menu))
    application.add_handler(CommandHandler(["ayuda", "help"], common.cmd_help))
    application.add_handler(CommandHandler(["id"], common.cmd_id))
    application.add_handler(CommandHandler(["estado", "status"], status.show_status))
    application.add_handler(CommandHandler(["discos", "disks"], disks.show_disks))
    application.add_handler(CommandHandler(["docker"], docker.show_list))
    application.add_handler(CommandHandler(["vms", "vm"], vms.show_list))
    application.add_handler(CommandHandler(["sistema", "system"], system.show_system_menu))
    application.add_handler(CommandHandler(["alertas", "alerts"], alerts.show_alerts))

    # Menú
    application.add_handler(CallbackQueryHandler(common.on_menu, pattern=r"^m:(main|help|noop)$"))
    application.add_handler(CallbackQueryHandler(status.show_status, pattern=r"^m:status$"))
    application.add_handler(CallbackQueryHandler(disks.show_disks, pattern=r"^m:disks$"))
    application.add_handler(CallbackQueryHandler(docker.show_list, pattern=r"^d:l:"))
    application.add_handler(CallbackQueryHandler(docker.show_list, pattern=r"^m:docker$"))
    application.add_handler(CallbackQueryHandler(vms.show_list, pattern=r"^m:vms$"))
    application.add_handler(CallbackQueryHandler(system.show_system_menu, pattern=r"^m:sys$"))
    application.add_handler(CallbackQueryHandler(alerts.show_alerts, pattern=r"^m:alerts$"))

    # Discos
    application.add_handler(CallbackQueryHandler(disks.show_disk_detail, pattern=r"^k:v:"))
    application.add_handler(CallbackQueryHandler(disks.show_physical_disks, pattern=r"^k:p$"))

    # Docker
    application.add_handler(CallbackQueryHandler(docker.show_detail, pattern=r"^d:v:"))
    application.add_handler(CallbackQueryHandler(docker.show_logs, pattern=r"^d:log:"))
    application.add_handler(CallbackQueryHandler(docker.ask_update, pattern=r"^d:update:"))
    application.add_handler(CallbackQueryHandler(docker.ask_update_all, pattern=r"^d:updateall$"))
    application.add_handler(CallbackQueryHandler(docker.toggle_autostart, pattern=r"^d:autostart:"))
    application.add_handler(
        CallbackQueryHandler(docker.container_action, pattern=r"^d:(start|stop|restart|pause|unpause):")
    )

    # VMs
    application.add_handler(CallbackQueryHandler(vms.show_detail, pattern=r"^v:v:"))
    application.add_handler(CallbackQueryHandler(vms.vm_action, pattern=r"^v:a:"))

    # Sistema
    application.add_handler(CallbackQueryHandler(system.show_array, pattern=r"^s:array$"))
    application.add_handler(CallbackQueryHandler(system.show_parity, pattern=r"^s:parity$"))
    application.add_handler(CallbackQueryHandler(system.show_ups, pattern=r"^s:ups$"))
    application.add_handler(CallbackQueryHandler(system.show_notifications, pattern=r"^s:notif$"))
    application.add_handler(CallbackQueryHandler(system.notifications_action, pattern=r"^s:notifclear$"))
    application.add_handler(CallbackQueryHandler(system.show_shares, pattern=r"^s:shares$"))
    application.add_handler(CallbackQueryHandler(system.show_info, pattern=r"^s:info$"))
    application.add_handler(CallbackQueryHandler(system.array_action, pattern=r"^s:(astart|astop)$"))
    application.add_handler(
        CallbackQueryHandler(system.parity_action, pattern=r"^s:(pstart|ppause|presume|pcancel)$")
    )

    # Alertas y confirmaciones
    application.add_handler(CallbackQueryHandler(alerts.alerts_action, pattern=r"^a:(on|off|test)$"))
    application.add_handler(CallbackQueryHandler(confirm.on_confirm, pattern=r"^c:[yn]:"))

    # Texto libre y comandos desconocidos
    application.add_handler(MessageHandler(filters.COMMAND, common.unknown_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, common.fallback_text)
    )
