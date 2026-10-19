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
| `TIMEZONE` | `Europe/Madrid` | Zona horaria de las fechas. |
| `PUID` / `PGID` | `99` / `100` | Usuario/grupo de Unraid para `./data`. |
| `UNRAIDBOT_IMAGE` | `ghcr.io/alexmysterio/unraidbot:latest` | Imagen a usar (solo Compose). |

---

## 🎮 Uso

Menú principal:

```
📊 Estado     💾 Discos
🐳 Docker     🖥️ VMs
⚙️ Sistema    🔔 Alertas
❓ Ayuda
```

| Comando | Acción |
|---|---|
| `/estado` | Estado general: array, CPU, RAM, Docker, VMs, UPS y avisos. |
| `/discos` | Discos del array, pools y discos físicos con SMART. |
| `/docker` | Contenedores: arrancar, parar, reiniciar, logs, autostart y actualizar. |
| `/vms` | VMs: arrancar, apagar, reiniciar, pausar, resetear. |
| `/sistema` | Array, paridad, UPS, notificaciones y shares. |
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

---

## 🔔 Alertas

Actívalas en **🔔 Alertas → Activar aquí**. El bot avisa de:

- Array detenido o con problemas.
- Paridad con errores o última comprobación fallida.
- Discos en rojo/amarillo, con errores o temperatura alta.
- Contenedores con autostart que están caídos.
- VMs bloqueadas.
- UPS en batería, batería baja o fallo.
- Notificaciones nuevas de Unraid.

Cada incidencia se avisa una vez, se recuerda cada `ALERT_REPEAT_MINUTES` y se marca como resuelta cuando desaparece. El estado se guarda en `./data/state.json`.

---

## 🛡️ Seguridad

- **Sin puertos abiertos**: solo conexiones salientes a Telegram y a la API local.
- **Allowlist**: sin usuarios autorizados el bot solo responde `/id` y `/help`.
- **Roles**: `ALLOWED_USER_IDS` administra; `VIEWER_USER_IDS` solo consulta.
- **Modo solo lectura**: `READ_ONLY=true` bloquea todas las acciones.
- **Confirmaciones** en array, paridad, VMs y actualizaciones.
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
