"""Internacionalización ligera (es, en, fr, it).

El español es el idioma base del código. ``localize`` traduce los textos ya
construidos y ``t`` resuelve claves estables (ayuda, bienvenida, etc.).
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
}
DEFAULT_LANGUAGE = "en"

_current: ContextVar[str] = ContextVar("unraidbot_language", default=DEFAULT_LANGUAGE)


def set_language(language: str | None) -> None:
    _current.set(language if language in LANGUAGES else DEFAULT_LANGUAGE)


def get_language() -> str:
    return _current.get()


def language_name(code: str) -> str:
    return LANGUAGES.get(code, code)


DEFAULTS: dict[str, str] = {
    "help": (
        "🤖 <b>UnraidBot</b>\n\n"
        "Administra tu servidor Unraid desde Telegram sin abrir puertos: el bot usa "
        "long polling (conexiones salientes) y la API local de Unraid.\n\n"
        "<b>Comandos</b>\n"
        "/estado — estado general\n"
        "/discos — discos y SMART\n"
        "/docker — contenedores\n"
        "/vms — máquinas virtuales\n"
        "/sistema — array, paridad, UPS, shares\n"
        "/alertas — avisos automáticos\n"
        "/buscar — buscar recursos\n"
        "/historial — historial de auditoría (admin)\n"
        "/rendimiento — CPU y RAM\n"
        "/resumen — resumen diario ahora\n"
        "/qbittorrent · /mikrotik · /wol — servicios extra (si están activos)\n"
        "/menu — menú principal\n"
        "/id — tu ID de Telegram\n\n"
        "<b>Consejos</b>\n"
        "• Las acciones destructivas piden confirmación.\n"
        "• /docker y /vms aceptan acciones: <code>/docker stop nombre</code>.\n"
        "• Los botones caducan; si algo falla, vuelve a abrir el menú.\n"
        "• El modo solo lectura se activa con <code>READ_ONLY=true</code>.\n\n"
        "<i>UnraidBot no sustituye al WebGUI: es un mando rápido y un vigilante.</i>"
    ),
    "start_welcome": (
        "👋 Hola, {name}.\n\n"
        "Este bot administra tu servidor Unraid sin exponerlo a Internet: "
        "todo el tráfico con Telegram es saliente y las órdenes van a la API local.\n\n"
        "Elige una opción:"
    ),
    "lang_choose": (
        "🌐 <b>Idioma · Language · Langue · Lingua</b>\n\n"
        "Elige abajo · Choose below · Choisissez ci-dessous · Scegli sotto\n"
        "<i>Puedes cambiarlo luego en el menú.</i>"
    ),
    "processing": "⏳ Procesando…",
    "tools_title": "🧰 <b>Herramientas</b>",
    "tools_choose": "Servicios opcionales activados en este bot:",
    "tools_empty": "No hay herramientas opcionales activadas.",
    "language_saved": "✅ Idioma actualizado.",
}

CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "help": (
            "🤖 <b>UnraidBot</b>\n\n"
            "Manage your Unraid server from Telegram without opening ports: the bot uses "
            "long polling (outbound connections) and the local Unraid API.\n\n"
            "<b>Commands</b>\n"
            "/estado — overview\n"
            "/discos — disks and SMART\n"
            "/docker — containers\n"
            "/vms — virtual machines\n"
            "/sistema — array, parity, UPS, shares\n"
            "/alertas — automatic alerts\n"
            "/buscar — search resources\n"
            "/historial — audit history (admin)\n"
            "/rendimiento — CPU and RAM\n"
            "/resumen — daily summary now\n"
            "/qbittorrent · /mikrotik · /wol — extra services (when enabled)\n"
            "/menu — main menu\n"
            "/id — your Telegram ID\n\n"
            "<b>Tips</b>\n"
            "• Destructive actions ask for confirmation.\n"
            "• /docker and /vms accept actions: <code>/docker stop name</code>.\n"
            "• Buttons expire; if something fails, reopen the menu.\n"
            "• Read-only mode is enabled with <code>READ_ONLY=true</code>.\n\n"
            "<i>UnraidBot does not replace the WebGUI: it is a quick remote and a watchdog.</i>"
        ),
        "start_welcome": (
            "👋 Hi, {name}.\n\n"
            "This bot manages your Unraid server without exposing it to the Internet: "
            "all Telegram traffic is outbound and commands go to the local API.\n\n"
            "Choose an option:"
        ),
        "lang_choose": (
            "🌐 <b>Language · Idioma · Langue · Lingua</b>\n\n"
            "Choose below · Elige abajo · Choisissez ci-dessous · Scegli sotto\n"
            "<i>You can change it later from the menu.</i>"
        ),
        "processing": "⏳ Processing…",
        "tools_title": "🧰 <b>Tools</b>",
        "tools_choose": "Optional services enabled on this bot:",
        "tools_empty": "No optional tools are enabled.",
        "language_saved": "✅ Language updated.",
        "Estado": "Status",
        "Discos": "Disks",
        "Sistema": "System",
        "Alertas": "Alerts",
        "Ayuda": "Help",
        "Idioma": "Language",
        "Herramientas": "Tools",
        "Menú": "Menu",
        "Volver": "Back",
        "Actualizar": "Refresh",
        "Cerrar": "Close",
        "Actualizar todo": "Update all",
        "Iniciar": "Start",
        "Detener": "Stop",
        "Reiniciar": "Restart",
        "Pausar": "Pause",
        "Reanudar": "Resume",
        "Forzar apagado": "Force stop",
        "Reset": "Reset",
        "Logs": "Logs",
        "Archivar todas": "Archive all",
        "Enviar prueba": "Send test",
        "Activar aquí": "Enable here",
        "Desactivar aquí": "Disable here",
        "Autostart: Sí": "Autostart: Yes",
        "Autostart: No": "Autostart: No",
        "Array iniciado": "Array started",
        "Array detenido": "Array stopped",
        "Array nuevo": "New array",
        "Paridad: OK ": "Parity: OK ",
        "Paridad: nunca comprobada": "Parity: never checked",
        "Comprobando": "Checking",
        "Completada": "Completed",
        "Pausada": "Paused",
        "Cancelada": "Cancelled",
        "Fallida": "Failed",
        "Nunca ejecutada": "Never run",
        "Sin conexión con la API de Unraid": "No connection to the Unraid API",
        "Revisa ": "Check ",
        "Incidencias": "Issues",
        "Sin notificaciones nuevas": "No new notifications",
        "En marcha desde hace ": "Running for ",
        "Sin datos de: ": "No data from: ",
        "actualizaciones": "updates",
        "activos": "active",
        "en marcha": "running",
        "alertas": "alerts",
        "avisos": "warnings",
        "Red": "Network",
        "Discos y almacenamiento": "Disks and storage",
        "Capacidad": "Capacity",
        "Paridad": "Parity",
        "Datos": "Data",
        "Caché / pools": "Cache / pools",
        "Total": "Total",
        "dispositivos · toca un disco para ver el detalle.": "devices · tap a disk for details.",
        "Estado: ": "Status: ",
        "Dispositivo: ": "Device: ",
        "Tamaño: ": "Size: ",
        "Sistema de archivos: ": "Filesystem: ",
        "Temperatura: ": "Temperature: ",
        "Tipo: ": "Type: ",
        "Errores de E/S: ": "I/O errors: ",
        "En reposo: ": "Sleeping: ",
        "Color: ": "Color: ",
        "Comentario: ": "Comment: ",
        "Umbrales configurados: aviso ": "Configured thresholds: warning ",
        "°C · crítico ": "°C · critical ",
        "El detalle SMART completo está en el WebGUI (Main → disco → SMART).": "Full SMART details are in the WebGUI (Main → disk → SMART).",
        "Discos físicos": "Physical disks",
        "No se han detectado discos físicos.": "No physical disks detected.",
        "Modelo: ": "Model: ",
        "SMART: ": "SMART: ",
        "Interfaz: ": "Interface: ",
        "Serie: ": "Serial: ",
        "Mostrando 20 de ": "Showing 20 of ",
        " discos.": " disks.",
        "No hay contenedores Docker.": "No Docker containers.",
        "Toca un contenedor para gestionarlo.": "Tap a container to manage it.",
        "Detalle: ": "Detail: ",
        "Imagen: ": "Image: ",
        "Red: ": "Network: ",
        "Puertos: ": "Ports: ",
        "Autostart: ": "Autostart: ",
        "Actualización: ⬆️ disponible": "Update: ⬆️ available",
        "Actualización: al día": "Update: up to date",
        "ID: ": "ID: ",
        "Últimas líneas de log": "Latest log lines",
        "Sin líneas de log disponibles.": "No log lines available.",
        "No hay actualizaciones pendientes.": "No pending updates.",
        "Máquinas virtuales": "Virtual machines",
        "No hay máquinas virtuales definidas.": "No virtual machines defined.",
        "Toca una VM para gestionarla.": "Tap a VM to manage it.",
        "Estado técnico: ": "Technical state: ",
        "UUID: ": "UUID: ",
        "El apagado normal envía una señal ACPI. Si la VM no responde, usa «Forzar apagado».": "Normal shutdown sends an ACPI signal. If the VM does not respond, use “Force stop”.",
        "Elige una sección:": "Choose a section:",
        "Última paridad": "Last parity check",
        "Fecha: ": "Date: ",
        "Duración: ": "Duration: ",
        "Errores: ": "Errors: ",
        "Discos de datos: ": "Data disks: ",
        "Discos de paridad: ": "Parity disks: ",
        "Discos de caché: ": "Cache disks: ",
        "No hay información de paridad disponible.": "No parity information available.",
        "No hay ningún UPS configurado o visible para la API.": "No UPS configured or visible to the API.",
        "Puedes configurarlo en <i>Settings → UPS Settings</i>.": "You can configure it in <i>Settings → UPS Settings</i>.",
        "Batería: ": "Battery: ",
        "Autonomía: ": "Runtime: ",
        "Carga: ": "Load: ",
        "Voltaje: ": "Voltage: ",
        "Sin leer: ": "Unread: ",
        "No hay alertas ni avisos pendientes. ✅": "No pending alerts or warnings. ✅",
        "No se han encontrado shares de usuario.": "No user shares found.",
        " · caché": " · cache",
        " · Kernel: ": " · Kernel: ",
        "Información del servidor": "Server information",
        "Alertas automáticas": "Automatic alerts",
        "Este chat: ": "This chat: ",
        "activadas": "enabled",
        "desactivadas": "disabled",
        "Revisión: cada ": "Check: every ",
        "Repetición de un aviso activo: cada ": "Repeat an active warning: every ",
        "Umbrales": "Thresholds",
        "Se avisa de": "Alerts for",
        "• Array detenido o con problemas": "• Array stopped or with problems",
        "• Discos en estado rojo/amarillo, con errores o temperatura alta": "• Disks red/yellow, with errors or high temperature",
        "• Contenedores con autostart que estén caídos": "• Containers with autostart that are down",
        "• VMs en estado CRASHED": "• VMs in CRASHED state",
        "• UPS en batería, batería baja o fallo": "• UPS on battery, low battery or failure",
        "• Notificaciones nuevas de Unraid": "• New Unraid notifications",
        "Ahora mismo hay ": "Right now there are ",
        " incidencia(s) detectada(s).": " issue(s) detected.",
        "Sin incidencias": "No issues",
        "Resuelto": "Resolved",
        "Alertas · ": "Alerts · ",
        "El array está en estado ": "The array is in state ",
        "Errores durante la comprobación de paridad": "Errors during parity check",
        "La última comprobación de paridad falló": "The last parity check failed",
        "Disco ": "Disk ",
        " en estado ": " in state ",
        " marcado en rojo": " marked red",
        " marcado en amarillo": " marked yellow",
        "Errores de E/S en ": "I/O errors on ",
        "Temperatura crítica en ": "Critical temperature on ",
        "Temperatura alta en ": "High temperature on ",
        "Temperatura de CPU alta": "High CPU temperature",
        "Memoria RAM al límite": "Memory running out",
        "Contenedor caído: ": "Container down: ",
        "VM bloqueada: ": "VM stuck: ",
        "UPS con batería baja: ": "UPS low battery: ",
        "UPS en batería: ": "UPS on battery: ",
        "UPS con problemas: ": "UPS problem: ",
        "Tiene autostart activado pero está detenido.": "Autostart is enabled but it is stopped.",
        "La máquina virtual está en estado CRASHED.": "The virtual machine is in CRASHED state.",
        "El servidor podría apagarse de forma inminente.": "The server may shut down imminently.",
        "Pausar todo": "Pause all",
        "Reanudar todo": "Resume all",
        "pausados": "paused",
        "torrents": "torrents",
        "Interfaces": "Interfaces",
        "Interfaces: ": "Interfaces: ",
        "Leases DHCP": "DHCP leases",
        "Leases DHCP: ": "DHCP leases: ",
        "libres de": "free of",
        "usada": "used",
        "Encender": "Power on",
        "Magic packet enviado.": "Magic packet sent.",
        "No se pudo enviar el magic packet: ": "Could not send the magic packet: ",
        "Torrents, velocidades y pausa global": "Torrents, speeds and global pause",
        "Router: recursos, interfaces y leases": "Router: resources, interfaces and leases",
        "Encender un equipo con un magic packet": "Power on a device with a magic packet",
        "Uptime: ": "Uptime: ",
        "pág. ": "page ",
        "Array: ": "Array: ",
        "Paridad: ": "Parity: ",
        "UPS: ": "UPS: ",
        "Notificaciones: ": "Notifications: ",
        "Comprobación de paridad": "Parity check",
        "¿Continuar?": "Continue?",
        "¿Seguro?": "Are you sure?",
        "Iniciando": "Starting",
        "Deteniendo": "Stopping",
        "Reiniciando": "Restarting",
        "Pausando": "Pausing",
        "Reanudando": "Resuming",
        "Notificaciones archivadas.": "Notifications archived.",
        "Prueba enviada.": "Test sent.",
        "Idioma no válido.": "Invalid language.",
        "Identificadores de Telegram": "Telegram identifiers",
        "Usuario: ": "User: ",
        "Estás autorizado como ": "You are authorized as ",
        "administrador": "administrator",
        "Estás autorizado en ": "You are authorized in ",
        "solo lectura": "read-only",
        "No autorizado": "Not authorized",
        "Bot sin configurar": "Bot not configured",
        "Tu ID de Telegram es ": "Your Telegram ID is ",
        "Añádelo a ": "Add it to ",
        "Tu usuario tiene acceso de solo lectura.": "Your user has read-only access.",
        "El bot está en modo solo lectura (READ_ONLY=true).": "The bot is in read-only mode (READ_ONLY=true).",
        "Demasiadas acciones seguidas. Espera un minuto.": "Too many actions in a row. Wait a minute.",
        "La API no confirmó la acción": "The API did not confirm the action",
        "Confirmar": "Confirm",
        "Cancelar": "Cancel",
        "Ficha": "Details",
        "Volver a discos": "Back to disks",
    },
    "fr": {
        "help": (
            "🤖 <b>UnraidBot</b>\n\n"
            "Gérez votre serveur Unraid depuis Telegram sans ouvrir de ports : le bot "
            "utilise le long polling (connexions sortantes) et l'API locale d'Unraid.\n\n"
            "<b>Commandes</b>\n"
            "/estado — vue d'ensemble\n"
            "/discos — disques et SMART\n"
            "/docker — conteneurs\n"
            "/vms — machines virtuelles\n"
            "/sistema — array, parité, UPS, partages\n"
            "/alertas — alertes automatiques\n"
            "/buscar — rechercher des ressources\n"
            "/historial — historique d'audit (admin)\n"
            "/rendimiento — CPU et RAM\n"
            "/resumen — résumé quotidien maintenant\n"
            "/qbittorrent · /mikrotik · /wol — services extra (si activés)\n"
            "/menu — menu principal\n"
            "/id — votre ID Telegram\n\n"
            "<b>Conseils</b>\n"
            "• Les actions destructrices demandent confirmation.\n"
            "• /docker et /vms acceptent des actions : <code>/docker stop nom</code>.\n"
            "• Les boutons expirent ; en cas d'échec, rouvrez le menu.\n"
            "• Le mode lecture seule s'active avec <code>READ_ONLY=true</code>.\n\n"
            "<i>UnraidBot ne remplace pas le WebGUI : c'est une télécommande rapide et une surveillance.</i>"
        ),
        "start_welcome": (
            "👋 Bonjour, {name}.\n\n"
            "Ce bot gère votre serveur Unraid sans l'exposer à Internet : tout le trafic "
            "Telegram est sortant et les commandes passent par l'API locale.\n\n"
            "Choisissez une option :"
        ),
        "lang_choose": (
            "🌐 <b>Langue · Idioma · Language · Lingua</b>\n\n"
            "Choisissez ci-dessous · Elige abajo · Choose below · Scegli sotto\n"
            "<i>Vous pourrez la changer plus tard dans le menu.</i>"
        ),
        "processing": "⏳ Traitement…",
        "tools_title": "🧰 <b>Outils</b>",
        "tools_choose": "Services optionnels activés sur ce bot :",
        "tools_empty": "Aucun outil optionnel activé.",
        "language_saved": "✅ Langue mise à jour.",
        "Estado": "État",
        "Discos": "Disques",
        "Sistema": "Système",
        "Alertas": "Alertes",
        "Ayuda": "Aide",
        "Idioma": "Langue",
        "Herramientas": "Outils",
        "Menú": "Menu",
        "Volver": "Retour",
        "Actualizar": "Actualiser",
        "Cerrar": "Fermer",
        "Actualizar todo": "Tout mettre à jour",
        "Iniciar": "Démarrer",
        "Detener": "Arrêter",
        "Reiniciar": "Relancer",
        "Pausar": "Pause",
        "Reanudar": "Reprendre",
        "Forzar apagado": "Forcer l'arrêt",
        "Reset": "Réinitialiser",
        "Logs": "Journaux",
        "Archivar todas": "Tout archiver",
        "Enviar prueba": "Envoyer un test",
        "Activar aquí": "Activer ici",
        "Desactivar aquí": "Désactiver ici",
        "Autostart: Sí": "Autostart : Oui",
        "Autostart: No": "Autostart : Non",
        "Array iniciado": "Array démarré",
        "Array detenido": "Array arrêté",
        "Array nuevo": "Nouvel array",
        "Paridad: OK ": "Parité : OK ",
        "Paridad: nunca comprobada": "Parité : jamais vérifiée",
        "Comprobando": "Vérification",
        "Completada": "Terminée",
        "Pausada": "En pause",
        "Cancelada": "Annulée",
        "Fallida": "Échouée",
        "Nunca ejecutada": "Jamais exécutée",
        "Sin conexión con la API de Unraid": "Pas de connexion à l'API Unraid",
        "Revisa ": "Vérifiez ",
        "Incidencias": "Incidents",
        "Sin notificaciones nuevas": "Aucune nouvelle notification",
        "En marcha desde hace ": "En marche depuis ",
        "Sin datos de: ": "Données indisponibles : ",
        "actualizaciones": "mises à jour",
        "activos": "actifs",
        "en marcha": "en marche",
        "alertas": "alertes",
        "avisos": "avertissements",
        "Red": "Réseau",
        "Discos y almacenamiento": "Disques et stockage",
        "Capacidad": "Capacité",
        "Paridad": "Parité",
        "Datos": "Données",
        "Caché / pools": "Cache / pools",
        "Total": "Total",
        "dispositivos · toca un disco para ver el detalle.": "appareils · touchez un disque pour les détails.",
        "Estado: ": "État : ",
        "Dispositivo: ": "Périphérique : ",
        "Tamaño: ": "Taille : ",
        "Sistema de archivos: ": "Système de fichiers : ",
        "Temperatura: ": "Température : ",
        "Tipo: ": "Type : ",
        "Errores de E/S: ": "Erreurs E/S : ",
        "En reposo: ": "En veille : ",
        "Color: ": "Couleur : ",
        "Comentario: ": "Commentaire : ",
        "Umbrales configurados: aviso ": "Seuils configurés : alerte ",
        "°C · crítico ": "°C · critique ",
        "El detalle SMART completo está en el WebGUI (Main → disco → SMART).": "Les détails SMART complets sont dans le WebGUI (Main → disque → SMART).",
        "Discos físicos": "Disques physiques",
        "No se han detectado discos físicos.": "Aucun disque physique détecté.",
        "Modelo: ": "Modèle : ",
        "SMART: ": "SMART : ",
        "Interfaz: ": "Interface : ",
        "Serie: ": "Série : ",
        "Mostrando 20 de ": "Affichage de 20 sur ",
        " discos.": " disques.",
        "No hay contenedores Docker.": "Aucun conteneur Docker.",
        "Toca un contenedor para gestionarlo.": "Touchez un conteneur pour le gérer.",
        "Detalle: ": "Détail : ",
        "Imagen: ": "Image : ",
        "Red: ": "Réseau : ",
        "Puertos: ": "Ports : ",
        "Autostart: ": "Démarrage auto : ",
        "Actualización: ⬆️ disponible": "Mise à jour : ⬆️ disponible",
        "Actualización: al día": "Mise à jour : à jour",
        "ID: ": "ID : ",
        "Últimas líneas de log": "Dernières lignes de log",
        "Sin líneas de log disponibles.": "Aucune ligne de log disponible.",
        "No hay actualizaciones pendientes.": "Aucune mise à jour en attente.",
        "Máquinas virtuales": "Machines virtuelles",
        "No hay máquinas virtuales definidas.": "Aucune machine virtuelle définie.",
        "Toca una VM para gestionarla.": "Touchez une VM pour la gérer.",
        "Estado técnico: ": "État technique : ",
        "UUID: ": "UUID : ",
        "El apagado normal envía una señal ACPI. Si la VM no responde, usa «Forzar apagado».": "L'arrêt normal envoie un signal ACPI. Si la VM ne répond pas, utilisez « Forcer l'arrêt ».",
        "Elige una sección:": "Choisissez une section :",
        "Última paridad": "Dernière parité",
        "Fecha: ": "Date : ",
        "Duración: ": "Durée : ",
        "Errores: ": "Erreurs : ",
        "Discos de datos: ": "Disques de données : ",
        "Discos de paridad: ": "Disques de parité : ",
        "Discos de caché: ": "Disques de cache : ",
        "No hay información de paridad disponible.": "Aucune information de parité disponible.",
        "No hay ningún UPS configurado o visible para la API.": "Aucun UPS configuré ou visible pour l'API.",
        "Puedes configurarlo en <i>Settings → UPS Settings</i>.": "Vous pouvez le configurer dans <i>Settings → UPS Settings</i>.",
        "Batería: ": "Batterie : ",
        "Autonomía: ": "Autonomie : ",
        "Carga: ": "Charge : ",
        "Voltaje: ": "Tension : ",
        "Sin leer: ": "Non lues : ",
        "No hay alertas ni avisos pendientes. ✅": "Aucune alerte ou avertissement en attente. ✅",
        "No se han encontrado shares de usuario.": "Aucun partage utilisateur trouvé.",
        " · caché": " · cache",
        " · Kernel: ": " · Noyau : ",
        "Información del servidor": "Informations du serveur",
        "Alertas automáticas": "Alertes automatiques",
        "Este chat: ": "Ce chat : ",
        "activadas": "activées",
        "desactivadas": "désactivées",
        "Revisión: cada ": "Vérification : toutes les ",
        "Repetición de un aviso activo: cada ": "Répétition d'un avertissement actif : toutes les ",
        "Umbrales": "Seuils",
        "Se avisa de": "Alertes pour",
        "• Array detenido o con problemas": "• Array arrêté ou problématique",
        "• Discos en estado rojo/amarillo, con errores o temperatura alta": "• Disques en rouge/jaune, avec erreurs ou température élevée",
        "• Contenedores con autostart que estén caídos": "• Conteneurs avec autostart arrêtés",
        "• VMs en estado CRASHED": "• VM en état CRASHED",
        "• UPS en batería, batería baja o fallo": "• UPS sur batterie, batterie faible ou panne",
        "• Notificaciones nuevas de Unraid": "• Nouvelles notifications Unraid",
        "Ahora mismo hay ": "En ce moment, il y a ",
        " incidencia(s) detectada(s).": " incident(s) détecté(s).",
        "Sin incidencias": "Aucun incident",
        "Resuelto": "Résolu",
        "Alertas · ": "Alertes · ",
        "El array está en estado ": "L'array est en état ",
        "Errores durante la comprobación de paridad": "Erreurs pendant la vérification de parité",
        "La última comprobación de paridad falló": "La dernière vérification de parité a échoué",
        "Disco ": "Disque ",
        " en estado ": " en état ",
        " marcado en rojo": " marqué en rouge",
        " marcado en amarillo": " marqué en jaune",
        "Errores de E/S en ": "Erreurs E/S sur ",
        "Temperatura crítica en ": "Température critique sur ",
        "Temperatura alta en ": "Température élevée sur ",
        "Temperatura de CPU alta": "Température CPU élevée",
        "Memoria RAM al límite": "Mémoire presque saturée",
        "Contenedor caído: ": "Conteneur arrêté : ",
        "VM bloqueada: ": "VM bloquée : ",
        "UPS con batería baja: ": "UPS batterie faible : ",
        "UPS en batería: ": "UPS sur batterie : ",
        "UPS con problemas: ": "UPS en problème : ",
        "Tiene autostart activado pero está detenido.": "L'autostart est activé mais le conteneur est arrêté.",
        "La máquina virtual está en estado CRASHED.": "La machine virtuelle est en état CRASHED.",
        "El servidor podría apagarse de forma inminente.": "Le serveur pourrait s'éteindre imminemment.",
        "Pausar todo": "Tout mettre en pause",
        "Reanudar todo": "Tout reprendre",
        "pausados": "en pause",
        "torrents": "torrents",
        "Interfaces": "Interfaces",
        "Interfaces: ": "Interfaces : ",
        "Leases DHCP": "Baux DHCP",
        "Leases DHCP: ": "Baux DHCP : ",
        "libres de": "libres sur",
        "usada": "utilisée",
        "Encender": "Allumer",
        "Magic packet enviado.": "Magic packet envoyé.",
        "No se pudo enviar el magic packet: ": "Impossible d'envoyer le magic packet : ",
        "Torrents, velocidades y pausa global": "Torrents, vitesses et pause globale",
        "Router: recursos, interfaces y leases": "Routeur : ressources, interfaces et baux",
        "Encender un equipo con un magic packet": "Allumer un appareil avec un magic packet",
        "Uptime: ": "Uptime : ",
        "pág. ": "p. ",
        "Array: ": "Array : ",
        "Paridad: ": "Parité : ",
        "UPS: ": "UPS : ",
        "Notificaciones: ": "Notifications : ",
        "Comprobación de paridad": "Vérification de parité",
        "¿Continuar?": "Continuer ?",
        "¿Seguro?": "Êtes-vous sûr ?",
        "Iniciando": "Démarrage",
        "Deteniendo": "Arrêt",
        "Reiniciando": "Relance",
        "Pausando": "Mise en pause",
        "Reanudando": "Reprise",
        "Notificaciones archivadas.": "Notifications archivées.",
        "Prueba enviada.": "Test envoyé.",
        "Idioma no válido.": "Langue invalide.",
        "Identificadores de Telegram": "Identifiants Telegram",
        "Usuario: ": "Utilisateur : ",
        "Estás autorizado como ": "Vous êtes autorisé comme ",
        "administrador": "administrateur",
        "Estás autorizado en ": "Vous êtes autorisé en ",
        "solo lectura": "lecture seule",
        "No autorizado": "Non autorisé",
        "Bot sin configurar": "Bot non configuré",
        "Tu ID de Telegram es ": "Votre ID Telegram est ",
        "Añádelo a ": "Ajoutez-le à ",
        "Tu usuario tiene acceso de solo lectura.": "Votre utilisateur a un accès en lecture seule.",
        "El bot está en modo solo lectura (READ_ONLY=true).": "Le bot est en mode lecture seule (READ_ONLY=true).",
        "Demasiadas acciones seguidas. Espera un minuto.": "Trop d'actions à la suite. Attendez une minute.",
        "La API no confirmó la acción": "L'API n'a pas confirmé l'action",
        "Confirmar": "Confirmer",
        "Cancelar": "Annuler",
        "Ficha": "Détails",
        "Volver a discos": "Retour aux disques",
    },
    "it": {
        "help": (
            "🤖 <b>UnraidBot</b>\n\n"
            "Gestisci il tuo server Unraid da Telegram senza aprire porte: il bot usa "
            "long polling (connessioni in uscita) e l'API locale di Unraid.\n\n"
            "<b>Comandi</b>\n"
            "/estado — panoramica\n"
            "/discos — dischi e SMART\n"
            "/docker — container\n"
            "/vms — macchine virtuali\n"
            "/sistema — array, parità, UPS, condivisioni\n"
            "/alertas — avvisi automatici\n"
            "/buscar — cerca risorse\n"
            "/historial — cronologia di audit (admin)\n"
            "/rendimiento — CPU e RAM\n"
            "/resumen — riepilogo giornaliero ora\n"
            "/qbittorrent · /mikrotik · /wol — servizi extra (se attivi)\n"
            "/menu — menu principale\n"
            "/id — il tuo ID Telegram\n\n"
            "<b>Consigli</b>\n"
            "• Le azioni distruttive chiedono conferma.\n"
            "• /docker e /vms accettano azioni: <code>/docker stop nome</code>.\n"
            "• I pulsanti scadono; se qualcosa non funziona, riapri il menu.\n"
            "• La modalità sola lettura si attiva con <code>READ_ONLY=true</code>.\n\n"
            "<i>UnraidBot non sostituisce il WebGUI: è un telecomando rapido e un watchdog.</i>"
        ),
        "start_welcome": (
            "👋 Ciao, {name}.\n\n"
            "Questo bot gestisce il tuo server Unraid senza esporlo a Internet: tutto il "
            "traffico Telegram è in uscita e i comandi passano dall'API locale.\n\n"
            "Scegli un'opzione:"
        ),
        "lang_choose": (
            "🌐 <b>Lingua · Idioma · Language · Langue</b>\n\n"
            "Scegli sotto · Elige abajo · Choose below · Choisissez ci-dessous\n"
            "<i>Puoi cambiarla in seguito dal menu.</i>"
        ),
        "processing": "⏳ Elaborazione…",
        "tools_title": "🧰 <b>Strumenti</b>",
        "tools_choose": "Servizi opzionali attivati su questo bot:",
        "tools_empty": "Nessuno strumento opzionale attivato.",
        "language_saved": "✅ Lingua aggiornata.",
        "Estado": "Stato",
        "Discos": "Dischi",
        "Sistema": "Sistema",
        "Alertas": "Avvisi",
        "Ayuda": "Aiuto",
        "Idioma": "Lingua",
        "Herramientas": "Strumenti",
        "Menú": "Menu",
        "Volver": "Indietro",
        "Actualizar": "Aggiorna",
        "Cerrar": "Chiudi",
        "Actualizar todo": "Aggiorna tutto",
        "Iniciar": "Avvia",
        "Detener": "Ferma",
        "Reiniciar": "Riavvia",
        "Pausar": "Pausa",
        "Reanudar": "Riprendi",
        "Forzar apagado": "Spegnimento forzato",
        "Reset": "Reset",
        "Logs": "Log",
        "Archivar todas": "Archivia tutto",
        "Enviar prueba": "Invia test",
        "Activar aquí": "Attiva qui",
        "Desactivar aquí": "Disattiva qui",
        "Autostart: Sí": "Avvio automatico: Sì",
        "Autostart: No": "Avvio automatico: No",
        "Array iniciado": "Array avviato",
        "Array detenido": "Array fermato",
        "Array nuevo": "Nuovo array",
        "Paridad: OK ": "Parità: OK ",
        "Paridad: nunca comprobada": "Parità: mai verificata",
        "Comprobando": "Verifica",
        "Completada": "Completata",
        "Pausada": "In pausa",
        "Cancelada": "Annullata",
        "Fallida": "Fallita",
        "Nunca ejecutada": "Mai eseguita",
        "Sin conexión con la API de Unraid": "Nessuna connessione all'API Unraid",
        "Revisa ": "Controlla ",
        "Incidencias": "Problemi",
        "Sin notificaciones nuevas": "Nessuna nuova notifica",
        "En marcha desde hace ": "In esecuzione da ",
        "Sin datos de: ": "Dati non disponibili: ",
        "actualizaciones": "aggiornamenti",
        "activos": "attivi",
        "en marcha": "in esecuzione",
        "alertas": "avvisi",
        "avisos": "avvisi",
        "Red": "Rete",
        "Discos y almacenamiento": "Dischi e archiviazione",
        "Capacidad": "Capacità",
        "Paridad": "Parità",
        "Datos": "Dati",
        "Caché / pools": "Cache / pool",
        "Total": "Totale",
        "dispositivos · toca un disco para ver el detalle.": "dispositivi · tocca un disco per i dettagli.",
        "Estado: ": "Stato: ",
        "Dispositivo: ": "Dispositivo: ",
        "Tamaño: ": "Dimensione: ",
        "Sistema de archivos: ": "Filesystem: ",
        "Temperatura: ": "Temperatura: ",
        "Tipo: ": "Tipo: ",
        "Errores de E/S: ": "Errori I/O: ",
        "En reposo: ": "In riposo: ",
        "Color: ": "Colore: ",
        "Comentario: ": "Commento: ",
        "Umbrales configurados: aviso ": "Soglie configurate: avviso ",
        "°C · crítico ": "°C · critico ",
        "El detalle SMART completo está en el WebGUI (Main → disco → SMART).": "I dettagli SMART completi sono nel WebGUI (Main → disco → SMART).",
        "Discos físicos": "Dischi fisici",
        "No se han detectado discos físicos.": "Nessun disco fisico rilevato.",
        "Modelo: ": "Modello: ",
        "SMART: ": "SMART: ",
        "Interfaz: ": "Interfaccia: ",
        "Serie: ": "Seriale: ",
        "Mostrando 20 de ": "Visualizzazione di 20 su ",
        " discos.": " dischi.",
        "No hay contenedores Docker.": "Nessun container Docker.",
        "Toca un contenedor para gestionarlo.": "Tocca un container per gestirlo.",
        "Detalle: ": "Dettaglio: ",
        "Imagen: ": "Immagine: ",
        "Red: ": "Rete: ",
        "Puertos: ": "Porte: ",
        "Autostart: ": "Avvio automatico: ",
        "Actualización: ⬆️ disponible": "Aggiornamento: ⬆️ disponibile",
        "Actualización: al día": "Aggiornamento: aggiornato",
        "ID: ": "ID: ",
        "Últimas líneas de log": "Ultime righe di log",
        "Sin líneas de log disponibles.": "Nessuna riga di log disponibile.",
        "No hay actualizaciones pendientes.": "Nessun aggiornamento in sospeso.",
        "Máquinas virtuales": "Macchine virtuali",
        "No hay máquinas virtuales definidas.": "Nessuna macchina virtuale definita.",
        "Toca una VM para gestionarla.": "Tocca una VM per gestirla.",
        "Estado técnico: ": "Stato tecnico: ",
        "UUID: ": "UUID: ",
        "El apagado normal envía una señal ACPI. Si la VM no responde, usa «Forzar apagado».": "Lo spegnimento normale invia un segnale ACPI. Se la VM non risponde, usa «Spegnimento forzato».",
        "Elige una sección:": "Scegli una sezione:",
        "Última paridad": "Ultima parità",
        "Fecha: ": "Data: ",
        "Duración: ": "Durata: ",
        "Errores: ": "Errori: ",
        "Discos de datos: ": "Dischi dati: ",
        "Discos de paridad: ": "Dischi di parità: ",
        "Discos de caché: ": "Dischi cache: ",
        "No hay información de paridad disponible.": "Nessuna informazione sulla parità disponibile.",
        "No hay ningún UPS configurado o visible para la API.": "Nessun UPS configurato o visibile all'API.",
        "Puedes configurarlo en <i>Settings → UPS Settings</i>.": "Puoi configurarlo in <i>Settings → UPS Settings</i>.",
        "Batería: ": "Batteria: ",
        "Autonomía: ": "Autonomia: ",
        "Carga: ": "Carico: ",
        "Voltaje: ": "Tensione: ",
        "Sin leer: ": "Non lette: ",
        "No hay alertas ni avisos pendientes. ✅": "Nessun avviso o allerta in sospeso. ✅",
        "No se han encontrado shares de usuario.": "Nessuna condivisione utente trovata.",
        " · caché": " · cache",
        " · Kernel: ": " · Kernel: ",
        "Información del servidor": "Informazioni sul server",
        "Alertas automáticas": "Avvisi automatici",
        "Este chat: ": "Questa chat: ",
        "activadas": "attivati",
        "desactivadas": "disattivati",
        "Revisión: cada ": "Controllo: ogni ",
        "Repetición de un aviso activo: cada ": "Ripetizione di un avviso attivo: ogni ",
        "Umbrales": "Soglie",
        "Se avisa de": "Avvisi per",
        "• Array detenido o con problemas": "• Array fermato o con problemi",
        "• Discos en estado rojo/amarillo, con errores o temperatura alta": "• Dischi rossi/gialli, con errori o temperatura alta",
        "• Contenedores con autostart que estén caídos": "• Container con autostart non attivi",
        "• VMs en estado CRASHED": "• VM in stato CRASHED",
        "• UPS en batería, batería baja o fallo": "• UPS a batteria, batteria scarica o guasto",
        "• Notificaciones nuevas de Unraid": "• Nuove notifiche Unraid",
        "Ahora mismo hay ": "Al momento ci sono ",
        " incidencia(s) detectada(s).": " problema(i) rilevato(i).",
        "Sin incidencias": "Nessun problema",
        "Resuelto": "Risolto",
        "Alertas · ": "Avvisi · ",
        "El array está en estado ": "L'array è in stato ",
        "Errores durante la comprobación de paridad": "Errori durante il controllo di parità",
        "La última comprobación de paridad falló": "L'ultimo controllo di parità non è riuscito",
        "Disco ": "Disco ",
        " en estado ": " in stato ",
        " marcado en rojo": " contrassegnato in rosso",
        " marcado en amarillo": " contrassegnato in giallo",
        "Errores de E/S en ": "Errori I/O su ",
        "Temperatura crítica en ": "Temperatura critica su ",
        "Temperatura alta en ": "Temperatura alta su ",
        "Temperatura de CPU alta": "Temperatura CPU alta",
        "Memoria RAM al límite": "Memoria quasi esaurita",
        "Contenedor caído: ": "Container fermo: ",
        "VM bloqueada: ": "VM bloccata: ",
        "UPS con batería baja: ": "UPS batteria scarica: ",
        "UPS en batería: ": "UPS a batteria: ",
        "UPS con problemas: ": "UPS con problemi: ",
        "Tiene autostart activado pero está detenido.": "L'autostart è attivo ma il container è fermo.",
        "La máquina virtual está en estado CRASHED.": "La macchina virtuale è in stato CRASHED.",
        "El servidor podría apagarse de forma inminente.": "Il server potrebbe spegnersi a breve.",
        "Pausar todo": "Pausa tutto",
        "Reanudar todo": "Riprendi tutto",
        "pausados": "in pausa",
        "torrents": "torrent",
        "Interfaces": "Interfacce",
        "Interfaces: ": "Interfacce: ",
        "Leases DHCP": "Lease DHCP",
        "Leases DHCP: ": "Lease DHCP: ",
        "libres de": "liberi di",
        "usada": "usata",
        "Encender": "Accendi",
        "Magic packet enviado.": "Magic packet inviato.",
        "No se pudo enviar el magic packet: ": "Impossibile inviare il magic packet: ",
        "Torrents, velocidades y pausa global": "Torrent, velocità e pausa globale",
        "Router: recursos, interfaces y leases": "Router: risorse, interfacce e lease",
        "Encender un equipo con un magic packet": "Accendi un dispositivo con un magic packet",
        "Uptime: ": "Uptime: ",
        "pág. ": "pag. ",
        "Array: ": "Array: ",
        "Paridad: ": "Parità: ",
        "UPS: ": "UPS: ",
        "Notificaciones: ": "Notifiche: ",
        "Comprobación de paridad": "Controllo di parità",
        "¿Continuar?": "Continuare?",
        "¿Seguro?": "Sei sicuro?",
        "Iniciando": "Avvio",
        "Deteniendo": "Arresto",
        "Reiniciando": "Riavvio",
        "Pausando": "Pausa",
        "Reanudando": "Ripresa",
        "Notificaciones archivadas.": "Notifiche archiviate.",
        "Prueba enviada.": "Test inviato.",
        "Idioma no válido.": "Lingua non valida.",
        "Identificadores de Telegram": "Identificatori Telegram",
        "Usuario: ": "Utente: ",
        "Estás autorizado como ": "Sei autorizzato come ",
        "administrador": "amministratore",
        "Estás autorizado en ": "Sei autorizzato in ",
        "solo lectura": "sola lettura",
        "No autorizado": "Non autorizzato",
        "Bot sin configurar": "Bot non configurato",
        "Tu ID de Telegram es ": "Il tuo ID Telegram è ",
        "Añádelo a ": "Aggiungilo a ",
        "Tu usuario tiene acceso de solo lectura.": "Il tuo utente ha accesso in sola lettura.",
        "El bot está en modo solo lectura (READ_ONLY=true).": "Il bot è in modalità sola lettura (READ_ONLY=true).",
        "Demasiadas acciones seguidas. Espera un minuto.": "Troppe azioni consecutive. Attendi un minuto.",
        "La API no confirmó la acción": "L'API non ha confermato l'azione",
        "Confirmar": "Conferma",
        "Cancelar": "Annulla",
        "Ficha": "Dettagli",
        "Volver a discos": "Torna ai dischi",
    },
}


# Traducciones añadidas en 1.3.0 y cadenas cortas de los handlers.
EXTRA_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "Array casi lleno": "Array almost full",
        "• Disco: aviso ": "• Disk: warning ",
        " en uso (umbral ": " in use (threshold ",
        " casi lleno": " almost full",
        "La última comprobación registró ": "The last check recorded ",
        " errores.": " errors.",
        "errores con la comprobación al ": "errors during the check at ",
        "Comprobación de paridad antigua": "Old parity check",
        "La última comprobación fue hace ": "The last check was ",
        " días (máximo recomendado ": " days ago (recommended maximum ",
        "SMART con problemas en ": "SMART problems on ",
        "Estado SMART: ": "SMART status: ",
        "Interfaz de red caída": "Network interface down",
        "La interfaz ": "The interface ",
        " está DOWN.": " is DOWN.",
        "Contenedor muerto: ": "Container dead: ",
        "Docker lo marca como DEAD. Revisa sus logs.": "Docker marks it as DEAD. Check its logs.",
        "Contenedor unhealthy: ": "Unhealthy container: ",
        "El healthcheck de Docker está fallando.": "The Docker healthcheck is failing.",
        "desconocido": "unknown",
        "El bot no puede contactar con la API local. Revisa que Unraid esté encendido, la URL y la conectividad de la red Docker.": (
            "The bot cannot reach the local API. Check that Unraid is on, the URL and "
            "Docker network connectivity."
        ),
        "API de Unraid inaccesible": "Unraid API unreachable",
        "• API de Unraid inaccesible": "• Unraid API unreachable",
        "• Array detenido, casi lleno o con problemas": "• Array stopped, almost full or with problems",
        "• Discos en estado rojo/amarillo, con errores, SMART o temperatura alta": (
            "• Disks red/yellow, with errors, SMART or high temperature"
        ),
        "• Shares por encima del umbral de uso": "• Shares above the usage threshold",
        "• Paridad con errores, fallida o demasiado antigua": "• Parity with errors, failed or too old",
        "• Contenedores caídos, unhealthy o en estado DEAD": "• Containers down, unhealthy or DEAD",
        "• Interfaz de red caída": "• Network interface down",
        "🔕 Silenciado hasta el ": "🔕 Muted until ",
        "Quitar silencio": "Unmute",
        "🔕 Silenciar 8 h": "🔕 Mute 8 h",
        "🔕 1 h": "🔕 1 h",
        "🔕 8 h": "🔕 8 h",
        "🔕 24 h": "🔕 24 h",
        "🔄 Reintentar": "🔄 Retry",
        "🔕 Alertas silenciadas hasta el ": "🔕 Alerts muted until ",
        "🔔 Silencio desactivado.": "🔔 Mute disabled.",
        "ℹ️ Este chat no estaba silenciado.": "ℹ️ This chat was not muted.",
        "Duración de silencio no válida.": "Invalid mute duration.",
        "❌ No se pudo enviar la prueba.": "❌ Could not send the test.",
        "⏸ Todos los torrents pausados": "⏸ All torrents paused",
        "▶️ Todos los torrents reanudados": "▶️ All torrents resumed",
        "Ese torrent ya no existe.": "That torrent no longer exists.",
        "Ese contenedor ya no existe.": "That container no longer exists.",
        "Acción no válida.": "Invalid action.",
        "Autostart activado": "Autostart enabled",
        "Autostart desactivado": "Autostart disabled",
        "🛑 No puedo detener ni reiniciar el contenedor del propio bot. Hazlo desde el WebGUI o con docker compose.": (
            "🛑 I cannot stop or restart the bot's own container. Use the WebGUI or docker compose."
        ),
        "🛑 No puedo actualizar el contenedor del propio bot desde aquí.": (
            "🛑 I cannot update the bot's own container from here."
        ),
        "❌ No se pudo aplicar «": "❌ Could not apply “",
        "»: ": "”: ",
        "❌ No se pudieron leer los logs: ": "❌ Could not read the logs: ",
        "❌ No se pudo cambiar el autostart: ": "❌ Could not change autostart: ",
        "Ese disco ya no existe. Vuelve a abrir la lista.": "That disk no longer exists. Reopen the list.",
        "Esa VM ya no existe.": "That VM no longer exists.",
        "Acción de paridad no válida.": "Invalid parity action.",
        "⏸ Comprobación pausada": "⏸ Parity check paused",
        "▶️ Comprobación reanudada": "▶️ Parity check resumed",
        "❓ Comando no reconocido. Usa /menu para ver las opciones.": (
            "❓ Unknown command. Use /menu to see the options."
        ),
        "❌ Ha ocurrido un error inesperado. Revisa los logs del contenedor.": (
            "❌ An unexpected error occurred. Check the container logs."
        ),
        "⏳ Esta confirmación ha caducado. Vuelve a intentarlo.": (
            "⏳ This confirmation has expired. Please try again."
        ),
        "❌ <b>Operación cancelada.</b>": "❌ <b>Operation cancelled.</b>",
        "❌ <b>No se pudo completar la operación</b>": "❌ <b>The operation could not be completed</b>",
        "• Shares: ": "• Shares: ",
        "• Paridad: máximo ": "• Parity: maximum ",
        " días sin comprobar": " days without checking",
        "✅ Alertas activadas en este chat.": "✅ Alerts enabled in this chat.",
        "🔕 Alertas desactivadas en este chat.": "🔕 Alerts disabled in this chat.",
        "El servidor no presenta problemas según los umbrales configurados.": (
            "The server has no problems according to the configured thresholds."
        ),
        "🔎 Buscar": "🔎 Search",
        "📈 Rendimiento": "📈 Performance",
        "🔎 <b>Búsqueda</b> · «": "🔎 <b>Search</b> · «",
        "Escribe el nombre de un contenedor, VM, disco, share, UPS o notificación.": (
            "Type the name of a container, VM, disk, share, UPS or notification."
        ),
        "También puedes usar /buscar texto directamente.": "You can also use /buscar text directly.",
        "No se encontraron resultados.": "No results found.",
        "Prueba con otro nombre o abre una sección desde el menú.": (
            "Try another name or open a section from the menu."
        ),
        "resultado(s) · pág. ": "result(s) · page ",
        "Toca un resultado para abrirlo.": "Tap a result to open it.",
        "La búsqueda ha caducado. Vuelve a empezar.": "The search expired. Please start again.",
        "🔎 Nueva búsqueda": "🔎 New search",
        "🔄 Repetir": "🔄 Repeat",
        "🔎 Filtrar": "🔎 Filter",
        "🧹 Quitar filtro": "🧹 Clear filter",
        "🗂️ <b>Historial de auditoría</b>": "🗂️ <b>Audit history</b>",
        "Filtro: ": "Filter: ",
        "registro(s) · pág. ": "record(s) · page ",
        "No hay registros que coincidan.": "No matching records.",
        "🔒 El historial de auditoría es solo para administradores.": (
            "🔒 Audit history is for administrators only."
        ),
        "🗂️ <b>Filtrar historial</b>": "🗂️ <b>Filter history</b>",
        "Escribe un texto para filtrar por acción, objetivo o usuario.": (
            "Type text to filter by action, target or user."
        ),
        "Ejemplos: ": "Examples: ",
        "La auditoría no está disponible.": "The audit log is not available.",
        "📈 <b>Rendimiento</b>": "📈 <b>Performance</b>",
        "🧠 CPU ahora: ": "🧠 CPU now: ",
        "💾 RAM ahora: ": "💾 RAM now: ",
        "Sin historial de CPU todavía.": "No CPU history yet.",
        "Sin historial de RAM todavía.": "No RAM history yet.",
        "Muestras guardadas: ": "Stored samples: ",
        "una cada ": "one every ",
        "mín ": "min ",
        "media ": "avg ",
        "máx ": "max ",
        "📬 <b>Resumen diario · ": "📬 <b>Daily summary · ",
        "avisos sin leer": "unread warnings",
        "sin leer": "unread",
        "Sin leer: ": "Unread: ",
        "Operación en curso… ": "Operation in progress… ",
        "⏱️ Duración: ": "⏱️ Duration: ",
        "Duración: ": "Duration: ",
        "Actualizando contenedor": "Updating container",
        "Actualizando contenedores": "Updating containers",
        "Iniciando el array": "Starting the array",
        "Deteniendo el array": "Stopping the array",
        "Reiniciando la VM": "Rebooting the VM",
        "Forzando el apagado de la VM": "Force stopping the VM",
        "Reseteando la VM": "Resetting the VM",
        "Uso de /docker": "Usage of /docker",
        "Uso de /vms": "Usage of /vms",
        "lista de contenedores": "container list",
        "lista de máquinas virtuales": "virtual machine list",
        "Hay varias coincidencias: ": "Multiple matches: ",
        "Sé más específico.": "Be more specific.",
        "No encontré ningún contenedor llamado «": "No container found named «",
        "No encontré ninguna VM llamada «": "No VM found named «",
        "✅ <b>Actualización completada</b>": "✅ <b>Update completed</b>",
        "La imagen se ha descargado y el contenedor se ha recreado.": (
            "The image was downloaded and the container recreated."
        ),
        " contenedores completada</b>": " containers completed</b>",
        "Las imágenes se han descargado y los contenedores se han recreado. ": (
            "The images were downloaded and the containers recreated. "
        ),
        "✅ <b>Array iniciado</b>": "✅ <b>Array started</b>",
        "Los discos están montados y los servicios disponibles. ": (
            "Disks are mounted and services are available. "
        ),
        "✅ <b>Array detenido</b>": "✅ <b>Array stopped</b>",
        "Los discos están desmontados y los shares ya no están disponibles.": (
            "Disks are unmounted and shares are no longer available."
        ),
        "🔄 VM reiniciada": "🔄 VM rebooted",
        "⏏ VM apagada a la fuerza": "⏏ VM force stopped",
        "↩️ VM reseteada": "↩️ VM reset",
        "✅ Acción completada": "✅ Action completed",
        "🔒 Solo los administradores pueden enviar el resumen.": (
            "🔒 Only administrators can send the summary."
        ),
        "📬 Enviado a ": "📬 Sent to ",
        "⚠️ No se pudo entregar el resumen.": "⚠️ The summary could not be delivered.",
        "No hay chats suscritos; no se ha enviado nada.": "There are no subscribed chats; nothing was sent.",
        # --- 1.5.0 · Integraciones ---
        "🐳 <b>qBittorrent</b>": "🐳 <b>qBittorrent</b>",
        "📡 <b>MikroTik · ": "📡 <b>MikroTik · ",
        "⚙️ <b>Límites de velocidad</b>": "⚙️ <b>Speed limits</b>",
        "📚 <b>Categorías</b>": "📚 <b>Categories</b>",
        "📚 Categorías": "📚 Categories",
        "⚙️ Límites": "⚙️ Limits",
        "🖧 <b>Interfaces</b>": "🖧 <b>Interfaces</b>",
        "🖧 Interfaces": "🖧 Interfaces",
        "📋 <b>Leases DHCP</b>": "📋 <b>DHCP leases</b>",
        "📋 Leases": "📋 Leases",
        "🧭 <b>Rutas</b>": "🧭 <b>Routes</b>",
        "🧭 Rutas": "🧭 Routes",
        "🛡 <b>Firewall</b>": "🛡 <b>Firewall</b>",
        "🛡 Firewall": "🛡 Firewall",
        "📜 <b>Registros</b>": "📜 <b>Logs</b>",
        "📜 Registros": "📜 Logs",
        "⚡ <b>Wake-on-LAN</b>": "⚡ <b>Wake-on-LAN</b>",
        "⚡ Encender todos": "⚡ Wake all",
        "🧰 Herramientas": "🧰 Tools",
        "🔁 Reiniciar": "🔁 Reboot",
        "🗑 Borrar": "🗑 Delete",
        "➕ Añadir": "➕ Add",
        "⏸ Pausar todo": "⏸ Pause all",
        "▶️ Reanudar todo": "▶️ Resume all",
        "⚡ Activar alternativa": "⚡ Enable alternative",
        "⚡ Desactivar alternativa": "⚡ Disable alternative",
        "No hay torrents con este filtro.": "No torrents with this filter.",
        "No hay interfaces.": "No interfaces.",
        "No hay leases DHCP.": "No DHCP leases.",
        "No hay rutas.": "No routes.",
        "No hay reglas de firewall.": "No firewall rules.",
        "No hay registros.": "No logs.",
        "No hay equipos configurados.": "No devices configured.",
        "No hay equipos configurados en WOL_DEVICES.": "No devices configured in WOL_DEVICES.",
        "Pulsa un equipo para enviar su magic packet.": "Tap a device to send its magic packet.",
        "Equipos configurados: <b>": "Configured devices: <b>",
        "Ese equipo ya no está configurado.": "That device is no longer configured.",
        "No encontré ningún equipo llamado «": "No device found named «",
        "No encontré ningún torrent llamado «": "No torrent found named «",
        "✅ Torrent añadido": "✅ Torrent added",
        "⚙️ Límites actualizados": "⚙️ Limits updated",
        "❌ Envía un enlace magnet o una URL http(s).": "❌ Send a magnet link or an http(s) URL.",
        "➕ <b>Añadir torrent</b>": "➕ <b>Add torrent</b>",
        "🔁 <b>Reiniciar MikroTik</b>": "🔁 <b>Reboot MikroTik</b>",
        "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?": (
            "The router will reboot and the network will drop for a few seconds. Continue?"
        ),
        "🔁 <b>Reinicio de MikroTik enviado.</b>": "🔁 <b>MikroTik reboot sent.</b>",
        "Se eliminará el torrent, pero no los archivos descargados.": (
            "The torrent will be removed, but not the downloaded files."
        ),
        "🗑 <b>Torrent eliminado</b>": "🗑 <b>Torrent deleted</b>",
        "Uso de /qbittorrent": "Usage of /qbittorrent",
        "Uso de /mikrotik": "Usage of /mikrotik",
        "Uso de /wol": "Usage of /wol",
        "⚡ Magic packet enviado a <b>": "⚡ Magic packet sent to <b>",
        "Magic packets enviados: <b>": "Magic packets sent: <b>",
        "Alternativa: ": "Alternative: ",
        "Velocidad alternativa: <b>": "Alternative speed: <b>",
        "Límites alternativa: ": "Alternative limits: ",
        "Broadcast: <code>": "Broadcast: <code>",
        "Descarga: <b>": "Download: <b>",
        "Subida: <b>": "Upload: <b>",
        # --- 1.5.0 · fragmentos de pantalla ---
        "Todos": "All",
        "Pausados": "Paused",
        "Descargando": "Downloading",
        "Sembrando": "Seeding",
        "Información": "Information",
        "ilimitado": "unlimited",
        "⚡ alternativa activa": "⚡ alternative active",
        "⚡ alternativa inactiva": "⚡ alternative inactive",
        "Velocidad alternativa: <b>activada</b>": "Alternative speed: <b>enabled</b>",
        "Velocidad alternativa: <b>desactivada</b>": "Alternative speed: <b>disabled</b>",
        "Progreso: ": "Progress: ",
        "Semillas: ": "Seeds: ",
        "Pares: ": "Peers: ",
        "Categoría: <code>": "Category: <code>",
        "Ruta: <code>": "Path: <code>",
        "Añadido: ": "Added: ",
        "Sin categoría": "Uncategorized",
        "No hay categorías definidas.": "No categories defined.",
        "Para cambiarlos: ": "To change them: ",
        "(KB/s; 0 = ilimitado).": "(KB/s; 0 = unlimited).",
        " más en total": " more in total",
        " libres de ": " free of ",
        "% usada)": "% used)",
        "Rutas: ": "Routes: ",
        "activas": "active",
        " reglas activas": " active rules",
        "dinámica": "dynamic",
        "estática": "static",
        "deshabilitada": "disabled",
        " paquetes · ": " packets · ",
        "⏸ Torrent pausado": "⏸ Torrent paused",
        "▶️ Torrent reanudado": "▶️ Torrent resumed",
        "❌ No se pudo añadir el torrent: ": "❌ The torrent could not be added: ",
        "Se eliminará el torrent y también los archivos descargados.": (
            "The torrent and its downloaded files will be deleted."
        ),
        "🗑 <b>Borrar ": "🗑 <b>Delete ",
        "⚡ Magic packet enviado a ": "⚡ Magic packet sent to ",
    },
    "fr": {
        "Array casi lleno": "Array presque plein",
        "• Disco: aviso ": "• Disque : alerte ",
        " en uso (umbral ": " utilisé (seuil ",
        " casi lleno": " presque plein",
        "La última comprobación registró ": "La dernière vérification a enregistré ",
        " errores.": " erreurs.",
        "errores con la comprobación al ": "erreurs pendant la vérification à ",
        "Comprobación de paridad antigua": "Vérification de parité ancienne",
        "La última comprobación fue hace ": "La dernière vérification date de ",
        " días (máximo recomendado ": " jours (maximum recommandé ",
        "SMART con problemas en ": "Problème SMART sur ",
        "Estado SMART: ": "État SMART : ",
        "Interfaz de red caída": "Interface réseau hors service",
        "La interfaz ": "L'interface ",
        " está DOWN.": " est DOWN.",
        "Contenedor muerto: ": "Conteneur mort : ",
        "Docker lo marca como DEAD. Revisa sus logs.": "Docker le marque comme DEAD. Consultez ses logs.",
        "Contenedor unhealthy: ": "Conteneur unhealthy : ",
        "El healthcheck de Docker está fallando.": "Le healthcheck Docker échoue.",
        "desconocido": "inconnu",
        "El bot no puede contactar con la API local. Revisa que Unraid esté encendido, la URL y la conectividad de la red Docker.": (
            "Le bot ne peut pas joindre l'API locale. Vérifiez qu'Unraid est allumé, l'URL et "
            "la connectivité réseau Docker."
        ),
        "API de Unraid inaccesible": "API Unraid inaccessible",
        "• API de Unraid inaccesible": "• API Unraid inaccessible",
        "• Array detenido, casi lleno o con problemas": "• Array arrêté, presque plein ou problématique",
        "• Discos en estado rojo/amarillo, con errores, SMART o temperatura alta": (
            "• Disques en rouge/jaune, avec erreurs, SMART ou température élevée"
        ),
        "• Shares por encima del umbral de uso": "• Partages au-dessus du seuil d'utilisation",
        "• Paridad con errores, fallida o demasiado antigua": "• Parité avec erreurs, échouée ou trop ancienne",
        "• Contenedores caídos, unhealthy o en estado DEAD": "• Conteneurs arrêtés, unhealthy ou DEAD",
        "• Interfaz de red caída": "• Interface réseau hors service",
        "🔕 Silenciado hasta el ": "🔕 Silencieux jusqu'au ",
        "Quitar silencio": "Réactiver",
        "🔕 Silenciar 8 h": "🔕 Silencieux 8 h",
        "🔕 1 h": "🔕 1 h",
        "🔕 8 h": "🔕 8 h",
        "🔕 24 h": "🔕 24 h",
        "🔄 Reintentar": "🔄 Réessayer",
        "🔕 Alertas silenciadas hasta el ": "🔕 Alertes en silencieux jusqu'au ",
        "🔔 Silencio desactivado.": "🔔 Silencieux désactivé.",
        "ℹ️ Este chat no estaba silenciado.": "ℹ️ Ce chat n'était pas en silencieux.",
        "Duración de silencio no válida.": "Durée de silencieux invalide.",
        "❌ No se pudo enviar la prueba.": "❌ Impossible d'envoyer le test.",
        "⏸ Todos los torrents pausados": "⏸ Tous les torrents en pause",
        "▶️ Todos los torrents reanudados": "▶️ Tous les torrents repris",
        "Ese torrent ya no existe.": "Ce torrent n'existe plus.",
        "Ese contenedor ya no existe.": "Ce conteneur n'existe plus.",
        "Acción no válida.": "Action invalide.",
        "Autostart activado": "Autostart activé",
        "Autostart desactivado": "Autostart désactivé",
        "🛑 No puedo detener ni reiniciar el contenedor del propio bot. Hazlo desde el WebGUI o con docker compose.": (
            "🛑 Je ne peux pas arrêter ou redémarrer le conteneur du bot. Utilisez le WebGUI ou docker compose."
        ),
        "🛑 No puedo actualizar el contenedor del propio bot desde aquí.": (
            "🛑 Je ne peux pas mettre à jour le conteneur du bot depuis ici."
        ),
        "❌ No se pudo aplicar «": "❌ Impossible d'appliquer « ",
        "»: ": " » : ",
        "❌ No se pudieron leer los logs: ": "❌ Impossible de lire les logs : ",
        "❌ No se pudo cambiar el autostart: ": "❌ Impossible de modifier l'autostart : ",
        "Ese disco ya no existe. Vuelve a abrir la lista.": "Ce disque n'existe plus. Rouvrez la liste.",
        "Esa VM ya no existe.": "Cette VM n'existe plus.",
        "Acción de paridad no válida.": "Action de parité invalide.",
        "⏸ Comprobación pausada": "⏸ Vérification en pause",
        "▶️ Comprobación reanudada": "▶️ Vérification reprise",
        "❓ Comando no reconocido. Usa /menu para ver las opciones.": (
            "❓ Commande inconnue. Utilisez /menu pour voir les options."
        ),
        "❌ Ha ocurrido un error inesperado. Revisa los logs del contenedor.": (
            "❌ Une erreur inattendue s'est produite. Consultez les logs du conteneur."
        ),
        "⏳ Esta confirmación ha caducado. Vuelve a intentarlo.": (
            "⏳ Cette confirmation a expiré. Réessayez."
        ),
        "❌ <b>Operación cancelada.</b>": "❌ <b>Opération annulée.</b>",
        "❌ <b>No se pudo completar la operación</b>": "❌ <b>L'opération n'a pas pu être terminée</b>",
        "• Shares: ": "• Partages : ",
        "• Paridad: máximo ": "• Parité : maximum ",
        " días sin comprobar": " jours sans vérification",
        "✅ Alertas activadas en este chat.": "✅ Alertes activées dans ce chat.",
        "🔕 Alertas desactivadas en este chat.": "🔕 Alertes désactivées dans ce chat.",
        "El servidor no presenta problemas según los umbrales configurados.": (
            "Le serveur ne présente aucun problème selon les seuils configurés."
        ),
        "🔎 Buscar": "🔎 Rechercher",
        "📈 Rendimiento": "📈 Performance",
        "🔎 <b>Búsqueda</b> · «": "🔎 <b>Recherche</b> · «",
        "Escribe el nombre de un contenedor, VM, disco, share, UPS o notificación.": (
            "Saisissez le nom d'un conteneur, VM, disque, partage, UPS ou notification."
        ),
        "También puedes usar /buscar texto directamente.": (
            "Vous pouvez aussi utiliser /buscar texte directement."
        ),
        "No se encontraron resultados.": "Aucun résultat trouvé.",
        "Prueba con otro nombre o abre una sección desde el menú.": (
            "Essayez un autre nom ou ouvrez une section depuis le menu."
        ),
        "resultado(s) · pág. ": "résultat(s) · page ",
        "Toca un resultado para abrirlo.": "Touchez un résultat pour l'ouvrir.",
        "La búsqueda ha caducado. Vuelve a empezar.": "La recherche a expiré. Recommencez.",
        "🔎 Nueva búsqueda": "🔎 Nouvelle recherche",
        "🔄 Repetir": "🔄 Répéter",
        "🔎 Filtrar": "🔎 Filtrer",
        "🧹 Quitar filtro": "🧹 Retirer le filtre",
        "🗂️ <b>Historial de auditoría</b>": "🗂️ <b>Historique d'audit</b>",
        "Filtro: ": "Filtre : ",
        "registro(s) · pág. ": "enregistrement(s) · page ",
        "No hay registros que coincidan.": "Aucun enregistrement correspondant.",
        "🔒 El historial de auditoría es solo para administradores.": (
            "🔒 L'historique d'audit est réservé aux administrateurs."
        ),
        "🗂️ <b>Filtrar historial</b>": "🗂️ <b>Filtrer l'historique</b>",
        "Escribe un texto para filtrar por acción, objetivo o usuario.": (
            "Saisissez un texte pour filtrer par action, cible ou utilisateur."
        ),
        "Ejemplos: ": "Exemples : ",
        "La auditoría no está disponible.": "L'audit n'est pas disponible.",
        "📈 <b>Rendimiento</b>": "📈 <b>Performance</b>",
        "🧠 CPU ahora: ": "🧠 CPU maintenant : ",
        "💾 RAM ahora: ": "💾 RAM maintenant : ",
        "Sin historial de CPU todavía.": "Pas encore d'historique CPU.",
        "Sin historial de RAM todavía.": "Pas encore d'historique RAM.",
        "Muestras guardadas: ": "Échantillons stockés : ",
        "una cada ": "un toutes les ",
        "mín ": "min ",
        "media ": "moy ",
        "máx ": "max ",
        "📬 <b>Resumen diario · ": "📬 <b>Résumé quotidien · ",
        "avisos sin leer": "avertissements non lus",
        "sin leer": "non lus",
        "Sin leer: ": "Non lus : ",
        "Operación en curso… ": "Opération en cours… ",
        "⏱️ Duración: ": "⏱️ Durée : ",
        "Duración: ": "Durée : ",
        "Actualizando contenedor": "Mise à jour du conteneur",
        "Actualizando contenedores": "Mise à jour des conteneurs",
        "Iniciando el array": "Démarrage de l'array",
        "Deteniendo el array": "Arrêt de l'array",
        "Reiniciando la VM": "Relance de la VM",
        "Forzando el apagado de la VM": "Arrêt forcé de la VM",
        "Reseteando la VM": "Réinitialisation de la VM",
        "Uso de /docker": "Utilisation de /docker",
        "Uso de /vms": "Utilisation de /vms",
        "lista de contenedores": "liste des conteneurs",
        "lista de máquinas virtuales": "liste des machines virtuelles",
        "Hay varias coincidencias: ": "Plusieurs correspondances : ",
        "Sé más específico.": "Soyez plus précis.",
        "No encontré ningún contenedor llamado «": "Aucun conteneur nommé «",
        "No encontré ninguna VM llamada «": "Aucune VM nommée «",
        "✅ <b>Actualización completada</b>": "✅ <b>Mise à jour terminée</b>",
        "La imagen se ha descargado y el contenedor se ha recreado.": (
            "L'image a été téléchargée et le conteneur recréé."
        ),
        " contenedores completada</b>": " conteneurs terminée</b>",
        "Las imágenes se han descargado y los contenedores se han recreado. ": (
            "Les images ont été téléchargées et les conteneurs recréés. "
        ),
        "✅ <b>Array iniciado</b>": "✅ <b>Array démarré</b>",
        "Los discos están montados y los servicios disponibles. ": (
            "Les disques sont montés et les services disponibles. "
        ),
        "✅ <b>Array detenido</b>": "✅ <b>Array arrêté</b>",
        "Los discos están desmontados y los shares ya no están disponibles.": (
            "Les disques sont démontés et les partages ne sont plus disponibles."
        ),
        "🔄 VM reiniciada": "🔄 VM redémarrée",
        "⏏ VM apagada a la fuerza": "⏏ VM arrêtée de force",
        "↩️ VM reseteada": "↩️ VM réinitialisée",
        "✅ Acción completada": "✅ Action terminée",
        "🔒 Solo los administradores pueden enviar el resumen.": (
            "🔒 Seuls les administrateurs peuvent envoyer le résumé."
        ),
        "📬 Enviado a ": "📬 Envoyé à ",
        "⚠️ No se pudo entregar el resumen.": "⚠️ Le résumé n'a pas pu être livré.",
        "No hay chats suscritos; no se ha enviado nada.": (
            "Aucun chat abonné ; rien n'a été envoyé."
        ),
        # --- 1.5.0 · Integraciones ---
        "🐳 <b>qBittorrent</b>": "🐳 <b>qBittorrent</b>",
        "📡 <b>MikroTik · ": "📡 <b>MikroTik · ",
        "⚙️ <b>Límites de velocidad</b>": "⚙️ <b>Limites de vitesse</b>",
        "📚 <b>Categorías</b>": "📚 <b>Catégories</b>",
        "📚 Categorías": "📚 Catégories",
        "⚙️ Límites": "⚙️ Limites",
        "🖧 <b>Interfaces</b>": "🖧 <b>Interfaces</b>",
        "🖧 Interfaces": "🖧 Interfaces",
        "📋 <b>Leases DHCP</b>": "📋 <b>Baux DHCP</b>",
        "📋 Leases": "📋 Baux",
        "🧭 <b>Rutas</b>": "🧭 <b>Routes</b>",
        "🧭 Rutas": "🧭 Routes",
        "🛡 <b>Firewall</b>": "🛡 <b>Pare-feu</b>",
        "🛡 Firewall": "🛡 Pare-feu",
        "📜 <b>Registros</b>": "📜 <b>Journaux</b>",
        "📜 Registros": "📜 Journaux",
        "⚡ <b>Wake-on-LAN</b>": "⚡ <b>Wake-on-LAN</b>",
        "⚡ Encender todos": "⚡ Allumer tout",
        "🧰 Herramientas": "🧰 Outils",
        "🔁 Reiniciar": "🔁 Relancer",
        "🗑 Borrar": "🗑 Supprimer",
        "➕ Añadir": "➕ Ajouter",
        "⏸ Pausar todo": "⏸ Tout mettre en pause",
        "▶️ Reanudar todo": "▶️ Tout reprendre",
        "⚡ Activar alternativa": "⚡ Activer l'alternative",
        "⚡ Desactivar alternativa": "⚡ Désactiver l'alternative",
        "No hay torrents con este filtro.": "Aucun torrent avec ce filtre.",
        "No hay interfaces.": "Aucune interface.",
        "No hay leases DHCP.": "Aucun bail DHCP.",
        "No hay rutas.": "Aucune route.",
        "No hay reglas de firewall.": "Aucune règle de pare-feu.",
        "No hay registros.": "Aucun journal.",
        "No hay equipos configurados.": "Aucun appareil configuré.",
        "No hay equipos configurados en WOL_DEVICES.": (
            "Aucun appareil configuré dans WOL_DEVICES."
        ),
        "Pulsa un equipo para enviar su magic packet.": (
            "Touchez un appareil pour envoyer son magic packet."
        ),
        "Equipos configurados: <b>": "Appareils configurés : <b>",
        "Ese equipo ya no está configurado.": "Cet appareil n'est plus configuré.",
        "No encontré ningún equipo llamado «": "Aucun appareil trouvé nommé «",
        "No encontré ningún torrent llamado «": "Aucun torrent trouvé nommé «",
        "✅ Torrent añadido": "✅ Torrent ajouté",
        "⚙️ Límites actualizados": "⚙️ Limites mis à jour",
        "❌ Envía un enlace magnet o una URL http(s).": (
            "❌ Envoyez un lien magnet ou une URL http(s)."
        ),
        "➕ <b>Añadir torrent</b>": "➕ <b>Ajouter un torrent</b>",
        "🔁 <b>Reiniciar MikroTik</b>": "🔁 <b>Relancer MikroTik</b>",
        "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?": (
            "Le routeur va relancer et le réseau sera coupé quelques secondes. Continuer ?"
        ),
        "🔁 <b>Reinicio de MikroTik enviado.</b>": "🔁 <b>Relance de MikroTik envoyée.</b>",
        "Se eliminará el torrent, pero no los archivos descargados.": (
            "Le torrent sera supprimé, mais pas les fichiers téléchargés."
        ),
        "🗑 <b>Torrent eliminado</b>": "🗑 <b>Torrent supprimé</b>",
        "Uso de /qbittorrent": "Utilisation de /qbittorrent",
        "Uso de /mikrotik": "Utilisation de /mikrotik",
        "Uso de /wol": "Utilisation de /wol",
        "⚡ Magic packet enviado a <b>": "⚡ Magic packet envoyé à <b>",
        "Magic packets enviados: <b>": "Magic packets envoyés : <b>",
        "Alternativa: ": "Alternative : ",
        "Velocidad alternativa: <b>": "Vitesse alternative : <b>",
        "Límites alternativa: ": "Limites alternative : ",
        "Broadcast: <code>": "Broadcast : <code>",
        "Descarga: <b>": "Téléchargement : <b>",
        "Subida: <b>": "Envoi : <b>",
        # --- 1.5.0 · fragmentos de pantalla ---
        "Todos": "Tous",
        "Pausados": "En pause",
        "Descargando": "Téléchargement",
        "Sembrando": "En partage",
        "Información": "Informations",
        "ilimitado": "illimité",
        "⚡ alternativa activa": "⚡ alternative active",
        "⚡ alternativa inactiva": "⚡ alternative inactive",
        "Velocidad alternativa: <b>activada</b>": "Vitesse alternative : <b>activée</b>",
        "Velocidad alternativa: <b>desactivada</b>": "Vitesse alternative : <b>désactivée</b>",
        "Progreso: ": "Progression : ",
        "Semillas: ": "Sources : ",
        "Pares: ": "Pairs : ",
        "Categoría: <code>": "Catégorie : <code>",
        "Ruta: <code>": "Chemin : <code>",
        "Añadido: ": "Ajouté : ",
        "Sin categoría": "Sans catégorie",
        "No hay categorías definidas.": "Aucune catégorie définie.",
        "Para cambiarlos: ": "Pour les modifier : ",
        "(KB/s; 0 = ilimitado).": "(Ko/s ; 0 = illimité).",
        " más en total": " de plus au total",
        " libres de ": " libres sur ",
        "% usada)": "% utilisée)",
        "Rutas: ": "Routes : ",
        "activas": "actives",
        " reglas activas": " règles actives",
        "dinámica": "dynamique",
        "estática": "statique",
        "deshabilitada": "désactivée",
        " paquetes · ": " paquets · ",
        "⏸ Torrent pausado": "⏸ Torrent en pause",
        "▶️ Torrent reanudado": "▶️ Torrent repris",
        "❌ No se pudo añadir el torrent: ": "❌ Impossible d'ajouter le torrent : ",
        "Se eliminará el torrent y también los archivos descargados.": (
            "Le torrent et les fichiers téléchargés seront supprimés."
        ),
        "🗑 <b>Borrar ": "🗑 <b>Supprimer ",
        "⚡ Magic packet enviado a ": "⚡ Magic packet envoyé à ",
    },
    "it": {
        "Array casi lleno": "Array quasi pieno",
        "• Disco: aviso ": "• Disco: avviso ",
        " en uso (umbral ": " in uso (soglia ",
        " casi lleno": " quasi pieno",
        "La última comprobación registró ": "L'ultimo controllo ha registrato ",
        " errores.": " errori.",
        "errores con la comprobación al ": "errori durante il controllo al ",
        "Comprobación de paridad antigua": "Controllo di parità vecchio",
        "La última comprobación fue hace ": "L'ultimo controllo risale a ",
        " días (máximo recomendado ": " giorni (massimo consigliato ",
        "SMART con problemas en ": "Problema SMART su ",
        "Estado SMART: ": "Stato SMART: ",
        "Interfaz de red caída": "Interfaccia di rete inattiva",
        "La interfaz ": "L'interfaccia ",
        " está DOWN.": " è DOWN.",
        "Contenedor muerto: ": "Container morto: ",
        "Docker lo marca como DEAD. Revisa sus logs.": "Docker lo segnala come DEAD. Controlla i log.",
        "Contenedor unhealthy: ": "Container unhealthy: ",
        "El healthcheck de Docker está fallando.": "L'healthcheck di Docker sta fallendo.",
        "desconocido": "sconosciuto",
        "El bot no puede contactar con la API local. Revisa que Unraid esté encendido, la URL y la conectividad de la red Docker.": (
            "Il bot non riesce a contattare l'API locale. Controlla che Unraid sia acceso, l'URL e "
            "la connettività di rete Docker."
        ),
        "API de Unraid inaccesible": "API Unraid irraggiungibile",
        "• API de Unraid inaccesible": "• API Unraid irraggiungibile",
        "• Array detenido, casi lleno o con problemas": "• Array fermato, quasi pieno o con problemi",
        "• Discos en estado rojo/amarillo, con errores, SMART o temperatura alta": (
            "• Dischi rossi/gialli, con errori, SMART o temperatura alta"
        ),
        "• Shares por encima del umbral de uso": "• Condivisioni sopra la soglia di utilizzo",
        "• Paridad con errores, fallida o demasiado antigua": "• Parità con errori, fallita o troppo vecchia",
        "• Contenedores caídos, unhealthy o en estado DEAD": "• Container fermi, unhealthy o DEAD",
        "• Interfaz de red caída": "• Interfaccia di rete inattiva",
        "🔕 Silenciado hasta el ": "🔕 Silenziato fino al ",
        "Quitar silencio": "Riattiva",
        "🔕 Silenciar 8 h": "🔕 Silenzia 8 h",
        "🔕 1 h": "🔕 1 h",
        "🔕 8 h": "🔕 8 h",
        "🔕 24 h": "🔕 24 h",
        "🔄 Reintentar": "🔄 Riprova",
        "🔕 Alertas silenciadas hasta el ": "🔕 Avvisi silenziati fino al ",
        "🔔 Silencio desactivado.": "🔔 Silenzio disattivato.",
        "ℹ️ Este chat no estaba silenciado.": "ℹ️ Questa chat non era silenziata.",
        "Duración de silencio no válida.": "Durata del silenzio non valida.",
        "❌ No se pudo enviar la prueba.": "❌ Impossibile inviare il test.",
        "⏸ Todos los torrents pausados": "⏸ Tutti i torrent in pausa",
        "▶️ Todos los torrents reanudados": "▶️ Tutti i torrent ripresi",
        "Ese torrent ya no existe.": "Quel torrent non esiste più.",
        "Ese contenedor ya no existe.": "Quel container non esiste più.",
        "Acción no válida.": "Azione non valida.",
        "Autostart activado": "Avvio automatico attivato",
        "Autostart desactivado": "Avvio automatico disattivato",
        "🛑 No puedo detener ni reiniciar el contenedor del propio bot. Hazlo desde el WebGUI o con docker compose.": (
            "🛑 Non posso fermare o riavviare il container del bot. Usa il WebGUI o docker compose."
        ),
        "🛑 No puedo actualizar el contenedor del propio bot desde aquí.": (
            "🛑 Non posso aggiornare il container del bot da qui."
        ),
        "❌ No se pudo aplicar «": "❌ Impossibile applicare «",
        "»: ": "»: ",
        "❌ No se pudieron leer los logs: ": "❌ Impossibile leggere i log: ",
        "❌ No se pudo cambiar el autostart: ": "❌ Impossibile modificare l'autostart: ",
        "Ese disco ya no existe. Vuelve a abrir la lista.": "Quel disco non esiste più. Riapri la lista.",
        "Esa VM ya no existe.": "Quella VM non esiste più.",
        "Acción de paridad no válida.": "Azione di parità non valida.",
        "⏸ Comprobación pausada": "⏸ Controllo in pausa",
        "▶️ Comprobación reanudada": "▶️ Controllo ripreso",
        "❓ Comando no reconocido. Usa /menu para ver las opciones.": (
            "❓ Comando sconosciuto. Usa /menu per vedere le opzioni."
        ),
        "❌ Ha ocurrido un error inesperado. Revisa los logs del contenedor.": (
            "❌ Si è verificato un errore imprevisto. Controlla i log del container."
        ),
        "⏳ Esta confirmación ha caducado. Vuelve a intentarlo.": (
            "⏳ Questa conferma è scaduta. Riprova."
        ),
        "❌ <b>Operación cancelada.</b>": "❌ <b>Operazione annullata.</b>",
        "❌ <b>No se pudo completar la operación</b>": "❌ <b>Impossibile completare l'operazione</b>",
        "• Shares: ": "• Condivisioni: ",
        "• Paridad: máximo ": "• Parità: massimo ",
        " días sin comprobar": " giorni senza controllo",
        "✅ Alertas activadas en este chat.": "✅ Avvisi attivati in questa chat.",
        "🔕 Alertas desactivadas en este chat.": "🔕 Avvisi disattivati in questa chat.",
        "El servidor no presenta problemas según los umbrales configurados.": (
            "Il server non presenta problemi secondo le soglie configurate."
        ),
        "🔎 Buscar": "🔎 Cerca",
        "📈 Rendimiento": "📈 Prestazioni",
        "🔎 <b>Búsqueda</b> · «": "🔎 <b>Ricerca</b> · «",
        "Escribe el nombre de un contenedor, VM, disco, share, UPS o notificación.": (
            "Scrivi il nome di un container, VM, disco, condivisione, UPS o notifica."
        ),
        "También puedes usar /buscar texto directamente.": (
            "Puoi anche usare /buscar testo direttamente."
        ),
        "No se encontraron resultados.": "Nessun risultato trovato.",
        "Prueba con otro nombre o abre una sección desde el menú.": (
            "Prova un altro nome o apri una sezione dal menu."
        ),
        "resultado(s) · pág. ": "risultato/i · pag. ",
        "Toca un resultado para abrirlo.": "Tocca un risultato per aprirlo.",
        "La búsqueda ha caducado. Vuelve a empezar.": "La ricerca è scaduta. Ricomincia.",
        "🔎 Nueva búsqueda": "🔎 Nuova ricerca",
        "🔄 Repetir": "🔄 Ripeti",
        "🔎 Filtrar": "🔎 Filtra",
        "🧹 Quitar filtro": "🧹 Rimuovi filtro",
        "🗂️ <b>Historial de auditoría</b>": "🗂️ <b>Cronologia di audit</b>",
        "Filtro: ": "Filtro: ",
        "registro(s) · pág. ": "record · pag. ",
        "No hay registros que coincidan.": "Nessun record corrispondente.",
        "🔒 El historial de auditoría es solo para administradores.": (
            "🔒 La cronologia di audit è riservata agli amministratori."
        ),
        "🗂️ <b>Filtrar historial</b>": "🗂️ <b>Filtra cronologia</b>",
        "Escribe un texto para filtrar por acción, objetivo o usuario.": (
            "Scrivi un testo per filtrare per azione, obiettivo o utente."
        ),
        "Ejemplos: ": "Esempi: ",
        "La auditoría no está disponible.": "L'audit non è disponibile.",
        "📈 <b>Rendimiento</b>": "📈 <b>Prestazioni</b>",
        "🧠 CPU ahora: ": "🧠 CPU ora: ",
        "💾 RAM ahora: ": "💾 RAM ora: ",
        "Sin historial de CPU todavía.": "Nessuna cronologia CPU.",
        "Sin historial de RAM todavía.": "Nessuna cronologia RAM.",
        "Muestras guardadas: ": "Campioni salvati: ",
        "una cada ": "uno ogni ",
        "mín ": "min ",
        "media ": "media ",
        "máx ": "max ",
        "📬 <b>Resumen diario · ": "📬 <b>Riepilogo giornaliero · ",
        "avisos sin leer": "avvisi non letti",
        "sin leer": "non letti",
        "Sin leer: ": "Non letti: ",
        "Operación en curso… ": "Operazione in corso… ",
        "⏱️ Duración: ": "⏱️ Durata: ",
        "Duración: ": "Durata: ",
        "Actualizando contenedor": "Aggiornamento container",
        "Actualizando contenedores": "Aggiornamento container",
        "Iniciando el array": "Avvio dell'array",
        "Deteniendo el array": "Arresto dell'array",
        "Reiniciando la VM": "Riavvio della VM",
        "Forzando el apagado de la VM": "Arresto forzato della VM",
        "Reseteando la VM": "Reset della VM",
        "Uso de /docker": "Uso di /docker",
        "Uso de /vms": "Uso di /vms",
        "lista de contenedores": "elenco container",
        "lista de máquinas virtuales": "elenco macchine virtuali",
        "Hay varias coincidencias: ": "Più corrispondenze: ",
        "Sé más específico.": "Sii più specifico.",
        "No encontré ningún contenedor llamado «": "Nessun container trovato con nome «",
        "No encontré ninguna VM llamada «": "Nessuna VM trovata con nome «",
        "✅ <b>Actualización completada</b>": "✅ <b>Aggiornamento completato</b>",
        "La imagen se ha descargado y el contenedor se ha recreado.": (
            "L'immagine è stata scaricata e il container ricreato."
        ),
        " contenedores completada</b>": " container completato</b>",
        "Las imágenes se han descargado y los contenedores se han recreado. ": (
            "Le immagini sono state scaricate e i container ricreati. "
        ),
        "✅ <b>Array iniciado</b>": "✅ <b>Array avviato</b>",
        "Los discos están montados y los servicios disponibles. ": (
            "I dischi sono montati e i servizi disponibili. "
        ),
        "✅ <b>Array detenido</b>": "✅ <b>Array arrestato</b>",
        "Los discos están desmontados y los shares ya no están disponibles.": (
            "I dischi sono smontati e le condivisioni non sono più disponibili."
        ),
        "🔄 VM reiniciada": "🔄 VM riavviata",
        "⏏ VM apagada a la fuerza": "⏏ VM arrestata forzatamente",
        "↩️ VM reseteada": "↩️ VM resettata",
        "✅ Acción completada": "✅ Azione completata",
        "🔒 Solo los administradores pueden enviar el resumen.": (
            "🔒 Solo gli amministratori possono inviare il riepilogo."
        ),
        "📬 Enviado a ": "📬 Inviato a ",
        "⚠️ No se pudo entregar el resumen.": "⚠️ Impossibile consegnare il riepilogo.",
        "No hay chats suscritos; no se ha enviado nada.": (
            "Nessuna chat iscritta; non è stato inviato nulla."
        ),
        # --- 1.5.0 · Integraciones ---
        "🐳 <b>qBittorrent</b>": "🐳 <b>qBittorrent</b>",
        "📡 <b>MikroTik · ": "📡 <b>MikroTik · ",
        "⚙️ <b>Límites de velocidad</b>": "⚙️ <b>Limiti di velocità</b>",
        "📚 <b>Categorías</b>": "📚 <b>Categorie</b>",
        "📚 Categorías": "📚 Categorie",
        "⚙️ Límites": "⚙️ Limiti",
        "🖧 <b>Interfaces</b>": "🖧 <b>Interfacce</b>",
        "🖧 Interfaces": "🖧 Interfacce",
        "📋 <b>Leases DHCP</b>": "📋 <b>Lease DHCP</b>",
        "📋 Leases": "📋 Lease",
        "🧭 <b>Rutas</b>": "🧭 <b>Rotte</b>",
        "🧭 Rutas": "🧭 Rotte",
        "🛡 <b>Firewall</b>": "🛡 <b>Firewall</b>",
        "🛡 Firewall": "🛡 Firewall",
        "📜 <b>Registros</b>": "📜 <b>Log</b>",
        "📜 Registros": "📜 Log",
        "⚡ <b>Wake-on-LAN</b>": "⚡ <b>Wake-on-LAN</b>",
        "⚡ Encender todos": "⚡ Accendi tutti",
        "🧰 Herramientas": "🧰 Strumenti",
        "🔁 Reiniciar": "🔁 Riavvia",
        "🗑 Borrar": "🗑 Elimina",
        "➕ Añadir": "➕ Aggiungi",
        "⏸ Pausar todo": "⏸ Metti in pausa tutto",
        "▶️ Reanudar todo": "▶️ Riprendi tutto",
        "⚡ Activar alternativa": "⚡ Attiva alternativa",
        "⚡ Desactivar alternativa": "⚡ Disattiva alternativa",
        "No hay torrents con este filtro.": "Nessun torrent con questo filtro.",
        "No hay interfaces.": "Nessuna interfaccia.",
        "No hay leases DHCP.": "Nessun lease DHCP.",
        "No hay rutas.": "Nessuna rotta.",
        "No hay reglas de firewall.": "Nessuna regola di firewall.",
        "No hay registros.": "Nessun log.",
        "No hay equipos configurados.": "Nessun dispositivo configurato.",
        "No hay equipos configurados en WOL_DEVICES.": (
            "Nessun dispositivo configurato in WOL_DEVICES."
        ),
        "Pulsa un equipo para enviar su magic packet.": (
            "Tocca un dispositivo per inviare il suo magic packet."
        ),
        "Equipos configurados: <b>": "Dispositivi configurati: <b>",
        "Ese equipo ya no está configurado.": "Quel dispositivo non è più configurato.",
        "No encontré ningún equipo llamado «": "Nessun dispositivo trovato con nome «",
        "No encontré ningún torrent llamado «": "Nessun torrent trovato con nome «",
        "✅ Torrent añadido": "✅ Torrent aggiunto",
        "⚙️ Límites actualizados": "⚙️ Limiti aggiornati",
        "❌ Envía un enlace magnet o una URL http(s).": (
            "❌ Invia un link magnet o un URL http(s)."
        ),
        "➕ <b>Añadir torrent</b>": "➕ <b>Aggiungi torrent</b>",
        "🔁 <b>Reiniciar MikroTik</b>": "🔁 <b>Riavvia MikroTik</b>",
        "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?": (
            "Il router si riavvierà e la rete cadrà per alcuni secondi. Continuare?"
        ),
        "🔁 <b>Reinicio de MikroTik enviado.</b>": "🔁 <b>Riavvio di MikroTik inviato.</b>",
        "Se eliminará el torrent, pero no los archivos descargados.": (
            "Il torrent verrà rimosso, ma non i file scaricati."
        ),
        "🗑 <b>Torrent eliminado</b>": "🗑 <b>Torrent eliminato</b>",
        "Uso de /qbittorrent": "Uso di /qbittorrent",
        "Uso de /mikrotik": "Uso di /mikrotik",
        "Uso de /wol": "Uso di /wol",
        "⚡ Magic packet enviado a <b>": "⚡ Magic packet inviato a <b>",
        "Magic packets enviados: <b>": "Magic packet inviati: <b>",
        "Alternativa: ": "Alternativa: ",
        "Velocidad alternativa: <b>": "Velocità alternativa: <b>",
        "Límites alternativa: ": "Limiti alternativi: ",
        "Broadcast: <code>": "Broadcast: <code>",
        "Descarga: <b>": "Download: <b>",
        "Subida: <b>": "Upload: <b>",
        # --- 1.5.0 · fragmentos de pantalla ---
        "Todos": "Tutti",
        "Pausados": "In pausa",
        "Descargando": "In download",
        "Sembrando": "In seed",
        "Información": "Informazioni",
        "ilimitado": "illimitato",
        "⚡ alternativa activa": "⚡ alternativa attiva",
        "⚡ alternativa inactiva": "⚡ alternativa inattiva",
        "Velocidad alternativa: <b>activada</b>": "Velocità alternativa: <b>attiva</b>",
        "Velocidad alternativa: <b>desactivada</b>": "Velocità alternativa: <b>disattivata</b>",
        "Progreso: ": "Avanzamento: ",
        "Semillas: ": "Semi: ",
        "Pares: ": "Peer: ",
        "Categoría: <code>": "Categoria: <code>",
        "Ruta: <code>": "Percorso: <code>",
        "Añadido: ": "Aggiunto: ",
        "Sin categoría": "Senza categoria",
        "No hay categorías definidas.": "Nessuna categoria definita.",
        "Para cambiarlos: ": "Per modificarli: ",
        "(KB/s; 0 = ilimitado).": "(KB/s; 0 = illimitato).",
        " más en total": " in più in totale",
        " libres de ": " liberi su ",
        "% usada)": "% usata)",
        "Rutas: ": "Rotte: ",
        "activas": "attive",
        " reglas activas": " regole attive",
        "dinámica": "dinamica",
        "estática": "statica",
        "deshabilitada": "disattivata",
        " paquetes · ": " pacchetti · ",
        "⏸ Torrent pausado": "⏸ Torrent in pausa",
        "▶️ Torrent reanudado": "▶️ Torrent ripreso",
        "❌ No se pudo añadir el torrent: ": "❌ Impossibile aggiungere il torrent: ",
        "Se eliminará el torrent y también los archivos descargados.": (
            "Il torrent e i file scaricati verranno eliminati."
        ),
        "🗑 <b>Borrar ": "🗑 <b>Elimina ",
        "⚡ Magic packet enviado a ": "⚡ Magic packet inviato a ",
    },
}

for _language, _extra in EXTRA_TRANSLATIONS.items():
    CATALOG.setdefault(_language, {}).update(_extra)


def t(key: str, **kwargs: Any) -> str:
    """Texto estable (ayuda, bienvenida...) en el idioma actual."""
    language = get_language()
    template = CATALOG.get(language, {}).get(key) or DEFAULTS.get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def localize(text: str) -> str:
    """Traduce fragmentos españoles dentro de un texto ya construido."""
    language = get_language()
    if language == "es" or not text:
        return text
    catalog = CATALOG.get(language)
    if not catalog:
        return text
    for source, translated in _SORTED.get(language, ()):
        if source in text:
            text = text.replace(source, translated)
    return text


def _sorted_catalog(language: str) -> tuple[tuple[str, str], ...]:
    catalog = CATALOG.get(language, {})
    return tuple(sorted(catalog.items(), key=lambda item: len(item[0]), reverse=True))


_SORTED = {language: _sorted_catalog(language) for language in CATALOG}


def localize_keyboard(keyboard: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup | None:
    if keyboard is None:
        return None
    rows = []
    for row in keyboard.inline_keyboard:
        buttons = []
        for button in row:
            buttons.append(
                InlineKeyboardButton(
                    text=localize(button.text),
                    callback_data=button.callback_data,
                    url=button.url,
                )
            )
        rows.append(buttons)
    return InlineKeyboardMarkup(rows)
