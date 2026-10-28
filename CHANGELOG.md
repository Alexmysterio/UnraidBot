# Changelog

Todas las novedades relevantes de este proyecto se documentan aquí. El formato
sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

## [1.6.0] - 2026-10-28

### Añadido

- **Historial de paridad** (`/paridad`): comprobaciones paginadas con estado, duración, velocidad, errores y tipo (correctiva o no correctiva).
- **Array cifrado desde el bot**: al iniciar un array cifrado se pide la contraseña, se borra el mensaje del chat y se usa una sola vez.
- **Paridad correctiva o no correctiva**: antes de arrancar la comprobación se elige el tipo y se confirma.
- **Notificaciones ampliadas**: filtros por importancia y por archivo, paginación, ficha de cada aviso y acciones para archivar, desarchivar, marcar como no leída o borrar. `/notificar` crea una notificación `INFO` en Unraid.
- **Licencia y flash** (`/licencia`): estado, tipo, caducidad, actualizaciones y datos del dispositivo flash.
- **Plugins** (`/plugins`): lista paginada e instalación desde una URL `.plg` con confirmación.
- **Servicios internos** (`/servicios`): estado y versión de los servicios de Unraid.
- **Red** (`/red`): interfaces, estado, velocidad, MTU, VLAN, IPv4/IPv6, MAC y accesos al WebGUI.
- **Logs** (`/logs`): lista de archivos, últimas líneas paginadas y envío del log como archivo.
- **SMART y discos** (`/smart`): ficha completa, particiones y montaje/desmontaje de discos del array con confirmación.
- **Detalle de shares**: uso, caché, asignador, split level, COW, LUKS e inclusiones/exclusiones.
- **Temperaturas y tráfico** (`/temperaturas`): sensores, resumen, avisos y tráfico de red.
- **Umbrales** (`/umbrales`): consulta los del bot y actualiza los de Unraid (`cpu_warning`, `cpu_critical`, `disk_warning`, `disk_critical`).
- **Claves de API** (`/claves`): lista, creación con rol `VIEWER` (se muestra una sola vez) y borrado con confirmación.
- **Identidad del servidor** (`/servidor`): nombre y comentario editables.
- **Diagnóstico** (`/diagnostico`): resumen del sistema, incidencias detectadas y envío del syslog.
- **Backup del flash** (`/backupflash`): copia de `/boot` a un remoto de rclone con confirmación.
- **Docker ampliado**: mantenimiento con actualizaciones pendientes y conflictos de puertos; tamaños de imagen, capa escribible y logs; ficha con estado de imagen, tamaños, contenedores huérfanos y conflictos.
- **Alertas nuevas**: última comprobación de paridad fallida, licencia caducada o a punto de caducar, estado de licencia inválido y servicios caídos.
- Menú **Sistema** con resumen de licencia y servicios, y 14 botones de acceso directo.
- Traducciones nuevas en inglés, francés e italiano para todas las pantallas.

### Cambiado

- `snapshot(include_health=True)` añade historial de paridad, licencia y servicios; solo lo piden el monitor y el menú Sistema.
- Las consultas nuevas son independientes para que un campo no soportado en versiones antiguas de Unraid no rompa las pantallas existentes.
- `SHARES_QUERY` incorpora los campos ampliados del share (asignador, split level, COW, LUKS, include/exclude).
- El cliente envía siempre `password` al iniciar un array cifrado y acepta `correct` en la comprobación de paridad.

### Corregido

- Si la API no soporta historial de paridad, licencia o servicios, esas pantallas lo explican y el resto sigue funcionando.

## [1.5.2] - 2026-10-27

### Corregido

- La pantalla **UPS** ya no muestra un error cuando el servidor no tiene UPS: informa, explica cómo configurarlo y mantiene los botones para volver.
- Un error inesperado ya no deja el mensaje en «Procesando…» sin botones: el manejador global responde con el detalle y un teclado de vuelta al menú.
- Al archivar notificaciones con una API key de solo lectura se explica el motivo y se mantiene la navegación a Notificaciones.
- Los avisos que sustituyen el mensaje de proceso conservan siempre un teclado de vuelta.

### Añadido

- Detección específica de errores de permisos de la API (`UnraidPermissionError`), con un mensaje claro y el detalle original para diagnosticar.

## [1.5.1] - 2026-10-27

### Seguridad

- `python-dotenv` 1.2.4 corrige la escritura arbitraria de archivos mediante enlaces simbólicos en `set_key` ([GHSA-mf9w-mj56-hr94](https://github.com/advisories/GHSA-mf9w-mj56-hr94)).
- `pytest` 9.1.1 corrige el manejo de directorios temporales ([GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g)).

### Cambiado

- `pytest-asyncio` 1.4.1, `ruff` 0.17.3 y `tzdata` 2026.5.
- `requirements-dev.txt` fija las herramientas de desarrollo compatibles con pytest 9.

## [1.5.0] - 2026-10-27

### Añadido

- **qBittorrent a fondo**: `/qbittorrent [list|add|pause|resume|delete|limit|limits|alt|categories]`, lista paginada con filtros (todos, descargando, sembrando, pausados), ficha del torrent, añadir magnet/URL, borrado con confirmación y opción de borrar archivos, límites de descarga/subida, modo de velocidad alternativa y categorías.
- **MikroTik a fondo**: `/mikrotik [resumen|interfaces|leases|rutas|firewall|logs|reboot]` con pantallas paginadas de interfaces, leases DHCP, rutas, reglas de firewall y registros, además de reinicio con confirmación.
- **Wake-on-LAN multi-equipo**: `WOL_DEVICES=Nombre=MAC[@broadcast],...`, encendido individual desde el teclado, botón **⚡ Encender todos** y `/wol <nombre|all>`. `WOL_MAC` sigue funcionando como equipo «Equipo».
- **Proxy de Telegram**: `SERVICE_TELEGRAM_PROXY=active` + `TELEGRAM_PROXY_URL` enruta las conexiones salientes (SOCKS5/HTTP) sin abrir puertos.
- **Limitador global de Telegram** con `AIORateLimiter` y reintentos configurables (`TELEGRAM_RATE_LIMIT`, `TELEGRAM_RATE_LIMIT_MAX_RETRIES`).
- **Límite por usuario configurable**: `USER_RATE_LIMIT_ACTIONS` y `USER_RATE_LIMIT_WINDOW`.
- **Activación por compose** con `SERVICE_QBITTORRENT`, `SERVICE_MIKROTIK`, `SERVICE_WOL` y `SERVICE_TELEGRAM_PROXY` en formato `active`/`noactive`.

### Cambiado

- Los antiguos `FEATURE_QBITTORRENT`, `FEATURE_MIKROTIK` y `FEATURE_WOL` se mantienen como alias, pero `SERVICE_*` tiene prioridad.
- El menú **🧰 Herramientas**, `/help` y los comandos publicados del bot incluyen las integraciones activas.
- El cliente de qBittorrent reintenta el login ante `401/403`, usa `stop/start` con caída a `pause/resume` y traduce errores de conexión.
- El cliente de MikroTik tolera respuestas que no son listas y añade rutas, firewall, registros y reinicio.
- `doctor` muestra el estado de cada servicio extra, del proxy y de los límites.

### Corregido

- El borrado de torrents pasa por `ConfirmationManager` y nunca elimina archivos salvo que se pida explícitamente.
- El texto libre del chat solo se interpreta como torrent cuando el usuario pulsó «Añadir».

### Documentación

- README, `.env.example`, `docker-compose.yml` y `scripts/setup.sh` documentan los servicios `SERVICE_*` y sus credenciales.
- Traducciones nuevas en inglés, francés e italiano para las pantallas de integraciones.

## [1.4.0] - 2026-10-27

### Añadido

- Comandos con argumentos: `/docker start|stop|restart|pause|unpause|update|logs <nombre>` y `/vms start|stop|reboot|pause|resume|force_stop|reset <nombre>`, con resolución tolerante de nombres y desambiguación.
- Búsqueda global (`/buscar` y botón **🔎 Buscar**) en Docker, VMs, discos, shares, UPS y notificaciones, con resultados paginados y accesos directos.
- Historial de auditoría (`/historial`) con filtro, paginación y acceso restringido a administradores.
- Paginación en discos físicos, notificaciones y resultados de búsqueda.
- Pantalla de rendimiento (`/rendimiento` y **📈 Rendimiento**) con sparklines de CPU y RAM a partir del historial persistido (máximo 288 muestras).
- Resumen diario programado con `DIGEST_ENABLED`, `DIGEST_HOUR` y `DIGEST_MINUTE`, y envío inmediato con `/resumen`.
- Operaciones largas en segundo plano con progreso editado en el mensaje, resultado final y duración: actualizar contenedores, iniciar/detener el array y reiniciar/resetear VMs.

### Cambiado

- El menú principal incorpora **🔎 Buscar** y **📈 Rendimiento**.
- El monitor y las pantallas de estado/rendimiento guardan muestras de CPU y RAM en `state.json`.
- El envío a varios chats se centraliza en un `broadcast()` compartido que respeta el silencio y desuscribe chats que bloquean el bot.
- Los textos de éxito de las operaciones largas usan tiempo pasado («Array iniciado», «VM reiniciada»).

### Corregido

- El uso de `/docker` y `/vms` escapa `<nombre>` para que Telegram no rechace el mensaje en modo HTML.
- El paginador de notificaciones ya no captura el botón «Archivar todas».

### Documentación

- README, `.env.example` y `doctor` actualizados con los comandos, la búsqueda, el historial, el rendimiento y el resumen diario.
- Traducciones de las nuevas cadenas en inglés, francés e italiano.

## [1.3.0] - 2026-10-27

### Añadido

- Alerta cuando la API de Unraid lleva dos ciclos consecutivos sin responder, con aviso de recuperación al volver la conexión.
- Alertas de uso: array casi lleno (`ARRAY_USAGE_WARNING`) y shares casi llenos (`SHARE_USAGE_WARNING`).
- Alerta de paridad antigua (`PARITY_MAX_DAYS`) y detección de errores de paridad fuera de una comprobación en curso.
- Alerta de estado SMART distinto de `OK` en discos físicos.
- Detección de contenedores `unhealthy` y en estado `DEAD`.
- Alerta de interfaz de red principal caída.
- Silencio temporal de alertas por chat: 1 h, 8 h o 24 h, con botón para quitarlo.
- Reenvío inmediato cuando una incidencia empeora de `warning` a `critical`.

### Cambiado

- El monitor consulta también discos físicos y shares para evaluar SMART y uso.
- Las alertas de recuperación solo borran la incidencia guardada si el mensaje se entregó.
- Los botones decorativos (`d:noop`) ya no muestran el aviso de «Procesando…».
- Los avisos de error de VMs y qBittorrent se traducen al idioma del chat.
- El uptime de MikroTik se interpreta en formato RouterOS (`1w2d03:04:05`).
- Los valores numéricos de UPS y temperatura de CPU se aceptan también como texto o escalares.
- La marca de «Procesando…» se guarda por mensaje de origen para evitar colisiones entre pulsaciones rápidas.

### Corregido

- Lectura de `id` nulos en discos, VMs, UPS y notificaciones sin generar claves `None`.
- Errores de formato en temperaturas y voltajes cuando la API devuelve cadenas.
- El estado de UPS en formato diccionario ya no se muestra como `{'value': ...}`.

### Documentación

- Nuevas variables en `.env.example` y en la tabla de configuración del README.
- Sección de alertas actualizada con los nuevos avisos y el silencio temporal.

## [1.2.0] - 2026-10-20

### Añadido

- Interfaz multiidioma: inglés, español, francés e italiano, con selección en el primer `/start` y cambio desde el menú.
- Mensaje «Procesando…» mientras se consultan los datos.
- Sistema de herramientas opcionales activables desde Docker Compose: qBittorrent, MikroTik (RouterOS 7 REST) y Wake-on-LAN.
- Menú «Herramientas» que solo aparece si hay alguna funcionalidad activada.

### Cambiado

- El archivo `.env.example` documenta todas las variables de las herramientas opcionales.
- El compose permite activar cada herramienta sin tocar código.

## [1.1.0] - 2026-10-19

### Añadido

- Usuarios de solo lectura con `VIEWER_USER_IDS`.
- Actualización de todos los contenedores Docker desde el botón «Actualizar todo».
- Activar/desactivar el autostart de cada contenedor desde su ficha.
- Archivado de todas las notificaciones de Unraid.
- Instalación sin clonar el repositorio usando la imagen publicada en GHCR.
- README centrado en el usuario, con un `docker-compose.yml` listo para copiar.

### Cambiado

- La imagen por defecto de Compose ahora es `ghcr.io/alexmysterio/unraidbot:latest`.
- El build local se hace con `docker-compose.build.yml`.

## [1.0.0] - 2026-10-19

### Añadido

- Estado general del servidor: array, capacidad, paridad, CPU, RAM, red, Docker,
  VMs, UPS y notificaciones.
- Discos del array y pools con estado, temperatura, uso, errores y detalle.
- Discos físicos con SMART, modelo, interfaz y número de serie.
- Gestión de Docker: listar, arrancar, parar, reiniciar, pausar, logs y
  actualizar imágenes.
- Gestión de VMs: arrancar, apagar, reiniciar, pausar, reanudar, resetear y
  forzar apagado.
- Control del array y de las comprobaciones de paridad.
- Alertas automáticas con deduplicación, repetición y aviso de resolución.
- Suscripciones por chat y persistencia en `data/state.json`.
- Allowlist de usuarios y chats, modo solo lectura, confirmaciones con caducidad,
  límite de acciones y auditoría JSONL.
- Contenedor sin puertos, sin privilegios, con rootfs de solo lectura.
- Healthcheck, latido y diagnóstico `python -m bot.doctor`.
- Configurador interactivo `scripts/setup.sh`.
- CI con lint, tests y build de la imagen; publicación en GHCR por tags.
- Documentación de instalación, seguridad, contribución y solución de problemas.
