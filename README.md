# 🤖 UnraidBot

Administra tu servidor **Unraid** desde **Telegram** sin abrir puertos ni exponer el WebGUI a Internet.

El bot usa **long polling** contra Telegram (solo conexiones salientes) y la **API GraphQL local de Unraid**. No hay puertos de entrada, webhook público ni reverse proxy.

```
 Tu móvil / Telegram  ──saliente──▶  UnraidBot (contenedor)  ──HTTP local──▶  Unraid API
```

---

## ⚡ Instalación fácil (recomendada)

Solo necesitas Docker Compose y estos datos:

- Token del bot de [@BotFather](https://t.me/BotFather).
- API key de Unraid: *Settings → Management Access → API Keys*.
- Tu ID de Telegram (te lo dice el bot con `/id`, o [@userinfobot](https://t.me/userinfobot)).

### 1. Crea la carpeta

```bash
mkdir -p /mnt/user/appdata/unraidbot
cd /mnt/user/appdata/unraidbot
```

### 2. Crea `docker-compose.yml`

Copia **todo** este bloque en un archivo llamado `docker-compose.yml`:

```yaml
services:
  unraidbot:
    image: ghcr.io/alexmysterio/unraidbot:latest
    container_name: unraidbot
    restart: unless-stopped
    stop_grace_period: 30s

    environment:
      # Cambia estos dos valores
      TELEGRAM_BOT_TOKEN: "PEGA_AQUI_TU_TOKEN"
      UNRAID_API_KEY: "PEGA_AQUI_TU_API_KEY"

      # Déjalo vacío en el primer arranque y usa /id para obtener el tuyo
      ALLOWED_USER_IDS: ""
      VIEWER_USER_IDS: ""

      UNRAID_API_URL: "http://host.docker.internal/graphql"
      TZ: "Europe/Madrid"
      TIMEZONE: "Europe/Madrid"
      PUID: "99"
      PGID: "100"

      # Servicios extra: cambia a "active" y rellena sus datos.
      # SERVICE_QBITTORRENT: "active"
      # QBITTORRENT_URL: "http://192.168.1.20:8080"
      # QBITTORRENT_USERNAME: "admin"
      # QBITTORRENT_PASSWORD: "tu-password"
      # SERVICE_MIKROTIK: "active"
      # MIKROTIK_URL: "https://192.168.1.1"
      # MIKROTIK_USERNAME: "admin"
      # MIKROTIK_PASSWORD: "tu-password"
      # SERVICE_WOL: "active"
      # WOL_DEVICES: "NAS=AA:BB:CC:DD:EE:FF,PC=11:22:33:44:55:66@192.168.1.255"
      # SERVICE_TELEGRAM_PROXY: "active"
      # TELEGRAM_PROXY_URL: "socks5://192.168.1.30:1080"

    volumes:
      - ./data:/data

    extra_hosts:
      - "host.docker.internal:host-gateway"

    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=32m,mode=1777
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
      - FOWNER

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. Arranca

```bash
docker compose up -d
docker compose logs -f unraidbot
```

Habla con el bot y envía `/id`. Copia tu ID y ponlo en `ALLOWED_USER_IDS`:

```yaml
      ALLOWED_USER_IDS: "123456789"
```

Recrea el contenedor:

```bash
docker compose up -d --force-recreate
```

Envía `/start`. Listo.

La primera vez `/start` te pedirá el idioma: **inglés, español, francés o italiano**. Después puedes cambiarlo en **🌐 Idioma**.

> Si tu Unraid usa HTTPS, cambia `UNRAID_API_URL` a `https://IP-DE-UNRAID/graphql`.
> Si `host.docker.internal` no funciona, usa `http://IP-DE-UNRAID/graphql`.

### Instalación desde el repositorio

Si prefieres clonar el proyecto y usar el asistente:

```bash
git clone https://github.com/Alexmysterio/UnraidBot.git
cd UnraidBot
bash scripts/setup.sh
```

El asistente crea `.env`, descarga la imagen publicada y arranca el contenedor.

---

## ⚙️ Configuración

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Token de @BotFather. **Obligatorio**. |
| `UNRAID_API_KEY` | — | API key de Unraid. **Obligatoria**. |
| `ALLOWED_USER_IDS` | vacío | IDs con permisos de administración, separados por comas. Vacío = modo configuración. |
| `VIEWER_USER_IDS` | vacío | IDs con acceso de **solo lectura**: ven todo, pero no arrancan/paran nada. |
| `ALLOWED_CHAT_IDS` | vacío | Grupos permitidos. Los privados de usuarios autorizados siempre se permiten. |
| `UNRAID_API_URL` | `http://host.docker.internal/graphql` | URL de la API de Unraid. |
| `UNRAID_VERIFY_SSL` | `false` | Verificar certificado TLS (Unraid suele usar autofirmado). |
| `READ_ONLY` | `false` | Convierte todo el bot en solo lectura. |
| `ALERTS_ENABLED` | `true` | Activa las alertas automáticas. |
| `ALERT_INTERVAL_SECONDS` | `300` | Cada cuánto revisa el servidor. |
| `ALERT_REPEAT_MINUTES` | `360` | Cada cuánto recuerda una incidencia activa. |
| `DISK_TEMP_WARNING` | `50` | Aviso de temperatura de disco (°C). |
| `DISK_TEMP_CRITICAL` | `55` | Crítico de temperatura de disco (°C). |
| `CPU_TEMP_WARNING` | `85` | Aviso de temperatura de CPU (°C). |
| `MEMORY_WARNING` | `90` | Aviso de RAM (%). |
| `ARRAY_USAGE_WARNING` | `85` | Aviso de array casi lleno (%). |
| `SHARE_USAGE_WARNING` | `90` | Aviso de share casi lleno (%). |
| `PARITY_MAX_DAYS` | `45` | Días máximos sin comprobar la paridad. |
| `API_OFFLINE_ALERT` | `true` | Avisa cuando la API de Unraid lleva dos ciclos sin responder. |
| `DIGEST_ENABLED` | `true` | Envía un resumen diario a los chats suscritos. |
| `DIGEST_HOUR` | `9` | Hora local (0–23) del resumen diario. |
| `DIGEST_MINUTE` | `0` | Minuto (0–59) del resumen diario. |
| `TIMEZONE` | `Europe/Madrid` | Zona horaria de las fechas. |
| `PUID` / `PGID` | `99` / `100` | Usuario/grupo de Unraid para `./data`. |
| `UNRAIDBOT_IMAGE` | `ghcr.io/alexmysterio/unraidbot:latest` | Imagen a usar (solo Compose). |
| `SERVICE_QBITTORRENT` | `noactive` | `active` activa la integración qBittorrent. |
| `SERVICE_MIKROTIK` | `noactive` | `active` activa la integración MikroTik. |
| `SERVICE_WOL` | `noactive` | `active` activa Wake-on-LAN multi-equipo. |
| `SERVICE_TELEGRAM_PROXY` | `noactive` | `active` enruta Telegram por `TELEGRAM_PROXY_URL`. |
| `TELEGRAM_PROXY_URL` | vacío | Proxy SOCKS5/HTTP para Telegram (p. ej. `socks5://host:1080`). |
| `TELEGRAM_RATE_LIMIT` | `active` | Limitador global de Telegram con reintentos ante `429`. |
| `TELEGRAM_RATE_LIMIT_MAX_RETRIES` | `2` | Reintentos del limitador global. |
| `USER_RATE_LIMIT_ACTIONS` | `30` | Acciones por usuario permitidas en la ventana. |
| `USER_RATE_LIMIT_WINDOW` | `60` | Ventana del límite por usuario (segundos). |

Los servicios extra usan `active` / `noactive`. Los antiguos `FEATURE_QBITTORRENT`,
`FEATURE_MIKROTIK` y `FEATURE_WOL` (`true`/`false`) siguen funcionando como alias,
pero `SERVICE_*` tiene prioridad. Las credenciales (`QBITTORRENT_*`, `MIKROTIK_*`,
`WOL_*`) están documentadas en `.env.example` y solo se leen si el servicio está activo.

---

## 🎮 Uso

Menú principal:

```
📊 Estado     💾 Discos
🐳 Docker     🖥️ VMs
⚙️ Sistema    🔔 Alertas
🔎 Buscar     📈 Rendimiento
🌐 Idioma     ❓ Ayuda
🧰 Herramientas (si hay alguna activada)
```

| Comando | Acción |
|---|---|
| `/estado` | Estado general: array, CPU, RAM, Docker, VMs, UPS y avisos. |
| `/discos` | Discos del array, pools y discos físicos con SMART. |
| `/docker` | Contenedores: lista, o `start/stop/restart/pause/unpause/update/logs <nombre>`. |
| `/vms` | VMs: lista, o `start/stop/reboot/pause/resume/force_stop/reset <nombre>`. |
| `/sistema` | Array, paridad, UPS, notificaciones y shares. |
| `/buscar` | Busca contenedores, VMs, discos, shares, UPS y notificaciones. |
| `/historial` | Historial de auditoría con filtro y paginación (solo administradores). |
| `/rendimiento` | CPU y RAM actuales con sparklines del historial guardado. |
| `/resumen` | Envía ahora el resumen diario a los chats suscritos. |
| `/qbittorrent` | Torrents: `list`, `add`, `pause`, `resume`, `delete`, `limit`, `limits`, `alt`, `categories`. |
| `/mikrotik` | Router: `interfaces`, `leases`, `rutas`, `firewall`, `logs`, `reboot`. |
| `/wol` | Enciende un equipo (`/wol nombre`) o todos (`/wol all`). |
| `/alertas` | Activar o desactivar alertas en ese chat. |
| `/id` | Tu ID de usuario y de chat. |
| `/menu` | Menú principal. |
| `/help` | Ayuda. |

### Docker

- **Actualizar todo**: actualiza de una vez todos los contenedores con imagen nueva.
- **Autostart**: activa o desactiva el arranque automático desde la ficha del contenedor.
- **Logs**: últimas 40 líneas.
- El bot bloquea las acciones directas sobre su propio contenedor; «Actualizar todo» avisa si incluye al propio bot.

### Discos

- Estado, temperatura, uso, errores y si el disco está en reposo.
- Lista de discos físicos con modelo, SMART, interfaz y número de serie.
- Para atributos SMART completos usa el WebGUI o `smartctl`.

### Array y paridad

- Iniciar/detener el array y controlar la comprobación de paridad.
- Si el array está cifrado, inícialo desde el WebGUI: el bot no pide contraseñas.

### Notificaciones

- Ver alertas y avisos de Unraid.
- **Archivar todas** las notificaciones no leídas.

### Búsqueda e historial

- **🔎 Buscar** (o `/buscar texto`) busca en contenedores, VMs, discos, shares, UPS y notificaciones; los resultados se abren con un toque y se paginan.
- **`/historial`** muestra la auditoría de acciones con filtro por acción, objetivo o usuario. Es **solo para administradores**, incluso en modo solo lectura.
- La auditoría se guarda en `./data/audit.log` (JSONL, rotación a los 5 MB).

### Rendimiento y resumen diario

- **📈 Rendimiento** (o `/rendimiento`) muestra CPU y RAM actuales con sparklines de las últimas muestras guardadas en `./data/state.json` (máximo 288).
- El bot envía un **resumen diario** a los chats suscritos a la hora configurada (`DIGEST_ENABLED`, `DIGEST_HOUR`, `DIGEST_MINUTE`). `/resumen` lo envía al momento.
- El resumen respeta el silencio de alertas y no se repite el mismo día.

### Operaciones largas

Actualizar contenedores, iniciar/detener el array y reiniciar/resetear VMs se ejecutan en segundo plano: el mensaje muestra el progreso y termina con el resultado y la duración. Las acciones rápidas siguen respondiendo al instante.

### Servicios extra (v1.5)

Todos vienen **desactivados**. Se activan por separado en el compose con
`active` / `noactive` y añaden un botón **🧰 Herramientas** al menú:

| Servicio | Variables | Qué permite |
|---|---|---|
| **qBittorrent** | `SERVICE_QBITTORRENT=active`, `QBITTORRENT_URL`, `QBITTORRENT_USERNAME`, `QBITTORRENT_PASSWORD` | Lista paginada con filtros, ficha del torrent, pausar/reanudar, añadir magnet/URL, borrar con confirmación, límites de velocidad, modo alternativo y categorías. |
| **MikroTik** | `SERVICE_MIKROTIK=active`, `MIKROTIK_URL`, `MIKROTIK_USERNAME`, `MIKROTIK_PASSWORD` | RouterOS 7: resumen, interfaces, leases DHCP, rutas, firewall, registros y reinicio con confirmación. |
| **Wake-on-LAN** | `SERVICE_WOL=active`, `WOL_DEVICES` (o `WOL_MAC`), `WOL_BROADCAST` | Varios equipos (`Nombre=MAC[@broadcast]`), encendido individual o «Encender todos». |
| **Proxy Telegram** | `SERVICE_TELEGRAM_PROXY=active`, `TELEGRAM_PROXY_URL` | Enruta las conexiones salientes del bot por SOCKS5/HTTP. |

Ejemplo para activar qBittorrent y dos equipos WOL:

```yaml
      SERVICE_QBITTORRENT: "active"
      QBITTORRENT_URL: "http://192.168.1.20:8080"
      QBITTORRENT_USERNAME: "admin"
      QBITTORRENT_PASSWORD: "tu-password"
      SERVICE_WOL: "active"
      WOL_DEVICES: "NAS=AA:BB:CC:DD:EE:FF,PC=11:22:33:44:55:66@192.168.1.255"
```

- `WOL_DEVICES` admite comas o saltos de línea; cada equipo puede usar su propio broadcast.
- Si solo defines `WOL_MAC`, se crea el equipo «Equipo» (compatibilidad con v1.4).
- Los servicios no activados no se cargan ni consumen recursos.
- El limitador global de Telegram (`TELEGRAM_RATE_LIMIT=active`) reintenta ante `429`;
  `USER_RATE_LIMIT_ACTIONS` / `USER_RATE_LIMIT_WINDOW` ajustan el límite por usuario.

### Idioma

La primera vez que envíes `/start`, el bot te pedirá elegir entre **English, Español, Français e Italiano**. Después puedes cambiarlo en **🌐 Idioma** desde el menú. La elección se guarda por chat en `./data/state.json`.

---

## 🔔 Alertas

Actívalas en **🔔 Alertas → Activar aquí**. El bot avisa de:

- API de Unraid inaccesible (tras dos ciclos consecutivos sin respuesta).
- Array detenido, casi lleno o con problemas.
- Paridad con errores, última comprobación fallida o demasiado antigua.
- Discos en rojo/amarillo, con errores, SMART distinto de `OK` o temperatura alta.
- Shares por encima del umbral de uso.
- Contenedores caídos, `unhealthy` o en estado `DEAD`.
- VMs bloqueadas.
- UPS en batería, batería baja o fallo.
- Interfaz de red principal caída.
- Notificaciones nuevas de Unraid.

Cada incidencia se avisa una vez, se recuerda cada `ALERT_REPEAT_MINUTES` y se marca como resuelta cuando desaparece. Si una incidencia empeora (`warning` → `critical`), se reenvía al momento. El estado se guarda en `./data/state.json`.

### Silencio temporal

Desde **🔔 Alertas** puedes silenciar un chat **1 h, 8 h o 24 h** sin desactivar la suscripción. Mientras está silenciado no se envían avisos a ese chat, pero el bot sigue vigilando el servidor. El botón **🔔 Quitar silencio** lo reactiva antes de tiempo. Las alertas incluyen un atajo para silenciar 8 h.

---

## 🛡️ Seguridad

- **Sin puertos abiertos**: solo conexiones salientes a Telegram y a la API local.
- **Proxy opcional**: con `SERVICE_TELEGRAM_PROXY=active` todo el tráfico de Telegram
  sale por `TELEGRAM_PROXY_URL` (SOCKS5/HTTP); sigue sin abrir puertos.
- **Allowlist**: sin usuarios autorizados el bot solo responde `/id` y `/help`.
- **Roles**: `ALLOWED_USER_IDS` administra; `VIEWER_USER_IDS` solo consulta.
- **Modo solo lectura**: `READ_ONLY=true` bloquea todas las acciones.
- **Límite por usuario**: `USER_RATE_LIMIT_ACTIONS` acciones por `USER_RATE_LIMIT_WINDOW`.
- **Confirmaciones** en array, paridad, VMs, actualizaciones, borrado de torrents y reinicio de MikroTik.
- **Auditoría** de cada acción en `./data/audit.log`.
- **Contenedor endurecido**: usuario 99:100, sin capacidades salvo las del entrypoint, rootfs de solo lectura y `/tmp` en tmpfs.

No compartas el token del bot ni la API key. Usa 2FA en Telegram.

---

## 🔄 Actualizar

Con la imagen publicada:

```bash
docker compose pull
docker compose up -d
```

Si instalaste desde el repositorio:

```bash
git pull
docker compose pull
docker compose up -d
```

Tus datos (`./data`) y `.env` se conservan.

---

## 🧰 Solución de problemas

| Problema | Solución |
|---|---|
| «No se pudo contactar con la API» | Usa `UNRAID_API_URL=http://IP-DE-UNRAID/graphql`; revisa que `unraid-api` funcione. |
| HTTP 401/403 | API key incorrecta o sin permisos. Crea otra con rol ADMIN. |
| El bot no responde | Revisa `docker compose logs -f unraidbot` y que tu ID esté autorizado. |
| «No autorizado» | Añade tu ID a `ALLOWED_USER_IDS` o `VIEWER_USER_IDS` y recrea el contenedor. |
| Error TLS | `UNRAID_VERIFY_SSL=false` o usa `http://`. |
| Healthcheck unhealthy | Ajusta `PUID`/`PGID` o ejecuta `chown -R 99:100 ./data`. |

Diagnóstico completo dentro del contenedor:

```bash
docker compose exec unraidbot python -m bot.doctor
```

Comprueba configuración, ping a la API y permisos de cada sección.

---

## ⚠️ Limitaciones

- La API de Unraid no permite apagar ni reiniciar el host.
- El bot no gestiona usuarios, shares ni plugins de Unraid.
- Las VMs no tienen consola ni snapshots desde el bot.
- El array cifrado debe iniciarse desde el WebGUI.

---

## 🤝 Contribuir

¿Quieres mejorar el proyecto? Lee [CONTRIBUTING.md](CONTRIBUTING.md). Para fallos de seguridad, usa **Security → Report a vulnerability**; no abras un issue público.

---

## 📄 Licencia

MIT. Unraid® es una marca registrada de Lime Technology, Inc.; este proyecto no está afiliado a Lime Technology.
