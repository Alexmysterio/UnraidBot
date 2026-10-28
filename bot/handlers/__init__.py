"""Registro centralizado de handlers."""

from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .. import features
from . import (
    alerts,
    common,
    confirm,
    digest,
    disks,
    docker,
    history,
    mikrotik,
    perf,
    qbittorrent,
    search,
    status,
    system,
    system_extra,
    tools,
    vms,
    wol,
)


def register_handlers(application: Application) -> None:
    # Comandos
    application.add_handler(CommandHandler(["start", "inicio"], common.cmd_start))
    application.add_handler(CommandHandler(["menu"], common.cmd_menu))
    application.add_handler(CommandHandler(["ayuda", "help"], common.cmd_help))
    application.add_handler(CommandHandler(["id"], common.cmd_id))
    application.add_handler(CommandHandler(["estado", "status"], status.show_status))
    application.add_handler(CommandHandler(["discos", "disks"], disks.show_disks))
    application.add_handler(CommandHandler(["docker"], docker.cmd_docker))
    application.add_handler(CommandHandler(["vms", "vm"], vms.cmd_vms))
    application.add_handler(CommandHandler(["sistema", "system"], system.show_system_menu))
    application.add_handler(CommandHandler(["alertas", "alerts"], alerts.show_alerts))
    application.add_handler(CommandHandler(["buscar", "search"], search.cmd_search))
    application.add_handler(CommandHandler(["historial", "history"], history.cmd_history))
    application.add_handler(CommandHandler(["rendimiento", "perf"], perf.show_performance))
    application.add_handler(CommandHandler(["resumen", "digest"], digest.cmd_digest))
    application.add_handler(CommandHandler(["paridad", "parity"], system_extra.cmd_parity))
    application.add_handler(
        CommandHandler(["notificaciones", "notifications"], system_extra.cmd_notifications)
    )
    application.add_handler(CommandHandler(["licencia", "license"], system_extra.cmd_license))
    application.add_handler(CommandHandler(["plugins"], system_extra.cmd_plugins))
    application.add_handler(CommandHandler(["servicios", "services"], system_extra.cmd_services))
    application.add_handler(CommandHandler(["red", "network"], system_extra.cmd_network))
    application.add_handler(CommandHandler(["logs"], system_extra.cmd_logs))
    application.add_handler(CommandHandler(["smart"], system_extra.cmd_smart))
    application.add_handler(
        CommandHandler(["temperaturas", "temps"], system_extra.cmd_temperatures)
    )
    application.add_handler(CommandHandler(["umbrales", "thresholds"], system_extra.cmd_thresholds))
    application.add_handler(CommandHandler(["claves", "apikeys"], system_extra.cmd_api_keys))
    application.add_handler(CommandHandler(["servidor", "server"], system_extra.cmd_identity))
    application.add_handler(
        CommandHandler(["diagnostico", "diagnostics"], system_extra.cmd_diagnostics)
    )
    application.add_handler(CommandHandler(["notificar", "notify"], system_extra.cmd_notify))
    application.add_handler(
        CommandHandler(["backupflash", "flashbackup"], system_extra.cmd_flash_backup)
    )

    # Menú
    application.add_handler(CallbackQueryHandler(common.on_menu, pattern=r"^m:(main|help|noop)$"))
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^d:noop$"))
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^(q|h):noop$"))
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^(k:p|s:notif):noop$"))
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^(qb|mt|wol):noop$"))
    application.add_handler(CallbackQueryHandler(common.show_language, pattern=r"^m:lang$"))
    application.add_handler(CallbackQueryHandler(common.set_language_callback, pattern=r"^lang:set:(en|es|fr|it)$"))
    application.add_handler(CallbackQueryHandler(tools.show_tools, pattern=r"^m:tools$"))
    application.add_handler(CallbackQueryHandler(status.show_status, pattern=r"^m:status$"))
    application.add_handler(CallbackQueryHandler(disks.show_disks, pattern=r"^m:disks$"))
    application.add_handler(CallbackQueryHandler(docker.show_list, pattern=r"^d:l:"))
    application.add_handler(CallbackQueryHandler(docker.show_list, pattern=r"^m:docker$"))
    application.add_handler(CallbackQueryHandler(docker.show_maintenance, pattern=r"^d:maint$"))
    application.add_handler(CallbackQueryHandler(docker.show_sizes, pattern=r"^d:sizes$"))
    application.add_handler(CallbackQueryHandler(vms.show_list, pattern=r"^m:vms$"))
    application.add_handler(CallbackQueryHandler(system.show_system_menu, pattern=r"^m:sys$"))
    application.add_handler(CallbackQueryHandler(alerts.show_alerts, pattern=r"^m:alerts$"))
    application.add_handler(CallbackQueryHandler(search.on_search_menu, pattern=r"^m:search$"))
    application.add_handler(CallbackQueryHandler(perf.show_performance, pattern=r"^m:perf$"))

    # Búsqueda e historial
    application.add_handler(CallbackQueryHandler(search.on_search_callback, pattern=r"^q:"))
    application.add_handler(CallbackQueryHandler(history.on_history_callback, pattern=r"^h:"))

    # Discos
    application.add_handler(CallbackQueryHandler(disks.show_disk_detail, pattern=r"^k:v:"))
    application.add_handler(CallbackQueryHandler(disks.show_physical_disks, pattern=r"^k:p"))

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
    application.add_handler(CallbackQueryHandler(system.show_shares, pattern=r"^s:shares$"))
    application.add_handler(CallbackQueryHandler(system.show_info, pattern=r"^s:info$"))
    application.add_handler(CallbackQueryHandler(system.array_action, pattern=r"^s:(astart|astop)$"))
    application.add_handler(
        CallbackQueryHandler(system.parity_action, pattern=r"^s:(pstart|ppause|presume|pcancel)$")
    )
    application.add_handler(CallbackQueryHandler(system.parity_start_choice, pattern=r"^s:pc:"))

    # Notificaciones: detalle y acciones antes que la lista genérica
    application.add_handler(CallbackQueryHandler(system.notification_detail, pattern=r"^s:notif:d:"))
    application.add_handler(
        CallbackQueryHandler(system.notification_action, pattern=r"^s:notif:(a|u|m|x):")
    )
    application.add_handler(
        CallbackQueryHandler(system.notifications_action, pattern=r"^s:notifclear$")
    )
    application.add_handler(CallbackQueryHandler(system.show_notifications, pattern=r"^s:notif(:|$)"))

    # Sistema ampliado (1.6.0)
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^s:ph:noop$"))
    application.add_handler(
        CallbackQueryHandler(system_extra.show_parity_history, pattern=r"^s:ph(:|$)")
    )
    application.add_handler(CallbackQueryHandler(system_extra.show_license, pattern=r"^s:license$"))
    application.add_handler(CallbackQueryHandler(common.on_noop, pattern=r"^s:plugins:noop$"))
    application.add_handler(CallbackQueryHandler(system_extra.show_plugins, pattern=r"^s:plugins"))
    application.add_handler(
        CallbackQueryHandler(system_extra.ask_install_plugin, pattern=r"^s:plugin:add$")
    )
    application.add_handler(CallbackQueryHandler(system_extra.show_services, pattern=r"^s:services$"))
    application.add_handler(CallbackQueryHandler(system_extra.show_network, pattern=r"^s:network$"))
    application.add_handler(CallbackQueryHandler(system_extra.show_logs, pattern=r"^s:logs$"))
    application.add_handler(CallbackQueryHandler(system_extra.send_log_file, pattern=r"^s:logfile:"))
    application.add_handler(CallbackQueryHandler(system_extra.show_log, pattern=r"^s:log:"))
    application.add_handler(CallbackQueryHandler(system_extra.show_smart, pattern=r"^s:smart:"))
    application.add_handler(CallbackQueryHandler(system_extra.disk_action, pattern=r"^s:disk:"))
    application.add_handler(CallbackQueryHandler(system_extra.show_share_detail, pattern=r"^s:share:"))
    application.add_handler(CallbackQueryHandler(system_extra.show_temperatures, pattern=r"^s:temp$"))
    application.add_handler(CallbackQueryHandler(system_extra.show_thresholds, pattern=r"^s:thresh$"))
    application.add_handler(
        CallbackQueryHandler(system_extra.ask_thresholds, pattern=r"^s:thresh:set$")
    )
    application.add_handler(CallbackQueryHandler(system_extra.show_api_keys, pattern=r"^s:keys$"))
    application.add_handler(CallbackQueryHandler(system_extra.ask_new_api_key, pattern=r"^s:key:new$"))
    application.add_handler(
        CallbackQueryHandler(system_extra.ask_delete_api_key, pattern=r"^s:key:del:")
    )
    application.add_handler(CallbackQueryHandler(system_extra.show_identity, pattern=r"^s:identity$"))
    application.add_handler(
        CallbackQueryHandler(system_extra.ask_identity, pattern=r"^s:identity:edit$")
    )
    application.add_handler(CallbackQueryHandler(system_extra.show_diagnostics, pattern=r"^s:diag$"))
    application.add_handler(
        CallbackQueryHandler(system_extra.ask_flash_backup, pattern=r"^s:flash:")
    )
    application.add_handler(
        CallbackQueryHandler(system_extra.show_flash_backup, pattern=r"^s:flash$")
    )

    # Alertas y confirmaciones
    application.add_handler(
        CallbackQueryHandler(alerts.alerts_action, pattern=r"^a:(on|off|test|mute:\d+|unmute)$")
    )
    application.add_handler(CallbackQueryHandler(confirm.on_confirm, pattern=r"^c:[yn]:"))

    # Herramientas opcionales
    if features.is_enabled("qbittorrent"):
        application.add_handler(CommandHandler(["qbittorrent", "qb"], qbittorrent.cmd_qbittorrent))
        application.add_handler(CallbackQueryHandler(qbittorrent.show, pattern=r"^tool:qb$"))
        application.add_handler(CallbackQueryHandler(qbittorrent.on_list, pattern=r"^qb:l:"))
        application.add_handler(CallbackQueryHandler(qbittorrent.show_detail, pattern=r"^qb:d:"))
        application.add_handler(CallbackQueryHandler(qbittorrent.toggle, pattern=r"^qb:t:"))
        application.add_handler(CallbackQueryHandler(qbittorrent.ask_delete, pattern=r"^qb:x:"))
        application.add_handler(CallbackQueryHandler(qbittorrent.arm_add, pattern=r"^qb:a$"))
        application.add_handler(CallbackQueryHandler(qbittorrent.show_limits, pattern=r"^qb:lim$"))
        application.add_handler(CallbackQueryHandler(qbittorrent.toggle_alt, pattern=r"^qb:alt$"))
        application.add_handler(
            CallbackQueryHandler(qbittorrent.show_categories, pattern=r"^qb:cat$")
        )
        application.add_handler(
            CallbackQueryHandler(qbittorrent.action, pattern=r"^qb:all:(pause|resume)$")
        )
    if features.is_enabled("mikrotik"):
        application.add_handler(CommandHandler(["mikrotik", "mt"], mikrotik.cmd_mikrotik))
        application.add_handler(CallbackQueryHandler(mikrotik.show, pattern=r"^tool:mt$"))
        application.add_handler(CallbackQueryHandler(mikrotik.on_interfaces, pattern=r"^mt:i:"))
        application.add_handler(CallbackQueryHandler(mikrotik.on_leases, pattern=r"^mt:l:"))
        application.add_handler(CallbackQueryHandler(mikrotik.on_routes, pattern=r"^mt:r:"))
        application.add_handler(CallbackQueryHandler(mikrotik.on_firewall, pattern=r"^mt:f:"))
        application.add_handler(CallbackQueryHandler(mikrotik.on_logs, pattern=r"^mt:g:"))
        application.add_handler(CallbackQueryHandler(mikrotik.ask_reboot, pattern=r"^mt:reboot$"))
    if features.is_enabled("wol"):
        application.add_handler(CommandHandler(["wol", "encender"], wol.cmd_wol))
        application.add_handler(CallbackQueryHandler(wol.show, pattern=r"^tool:wol$"))
        application.add_handler(CallbackQueryHandler(wol.on_wake, pattern=r"^wol:w:"))
        application.add_handler(CallbackQueryHandler(wol.wake_all, pattern=r"^wol:all$"))

    # Texto libre y comandos desconocidos
    application.add_handler(MessageHandler(filters.COMMAND, common.unknown_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, common.fallback_text)
    )
