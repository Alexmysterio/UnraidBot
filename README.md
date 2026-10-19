# 🤖 UnraidBot

[![CI](https://github.com/Alexmysterio/UnraidBot/actions/workflows/ci.yml/badge.svg)](https://github.com/Alexmysterio/UnraidBot/actions/workflows/ci.yml)

Administra tu servidor **Unraid** desde **Telegram** sin abrir puertos, sin VPN y sin exponer el WebGUI a Internet.

El bot usa **long polling** contra Telegram (conexiones salientes) y habla con la **API GraphQL local de Unraid**. No hay ningún puerto de entrada, ni webhook público, ni reverse proxy.

```
   Tu móvil                    Internet                     Tu LAN
┌─────────────┐            ┌─────────────┐            ┌──────────────────────────┐
│  Telegram   │◀──────────▶│  Bot API    │◀───────────│  UnraidBot (contenedor)  │
└─────────────┘  long      └─────────────┘  saliente  │  · long polling          │
                 polling                              │  · allowlist de usuarios │
                                                      │  · alertas y auditoría   │
                                                      └────────────┬─────────────┘
                                                                   │ HTTP local
                                                                   ▼
                                                      ┌──────────────────────────┐
                                                      │ Unraid API GraphQL       │
                                                      │ (IP-del-servidor/graphql)│
                                                      └──────────────────────────┘
```

---

## ⚡ Instalación rápida

```bash
git clone https://github.com/Alexmysterio/UnraidBot.git
cd UnraidBot
bash scripts/setup.sh
```

El asistente te pide el token de @BotFather, la API key de Unraid, la URL de la API y, opcionalmente, tu ID de Telegram. Genera `.env` con permisos `600` y puede construir y arrancar el contenedor por ti.

Si prefieres hacerlo a mano, sigue los pasos detallados de abajo.

### Imagen publicada

Cada release se publica en GitHub Container Registry:

```bash
docker pull ghcr.io/alexmysterio/unraidbot:latest
```

Para usarla con Compose, define en `.env`:

```dotenv
UNRAIDBOT_IMAGE=ghcr.io/alexmysterio/unraidbot:latest
```

Y arranca con `docker compose pull && docker compose up -d`.

---

## ✨ Qué hace

| Función | Detalle |
|---|---|
| 📊 **Estado general** | Array, capacidad, paridad, CPU, RAM, temperaturas, red, Docker, VMs, UPS y notificaciones en una sola pantalla. |
| 💾 **HDDs y SSDs** | Estado, temperatura, uso, errores de E/S, disco en reposo y detalle por disco. Lista aparte de discos físicos con SMART. |
| 🐳 **Docker** | Listar, arrancar, parar, reiniciar, pausar, ver logs y actualizar imágenes. Detecta actualizaciones disponibles. |
| 🖥️ **VMs** | Listar, arrancar, apagar, reiniciar, pausar, reanudar, resetear y forzar apagado. |
| 🧱 **Array y paridad** | Iniciar/detener el array, lanzar/pausar/reanudar/cancelar comprobaciones de paridad. |
| 🔋 **UPS** | Estado, batería, autonomía, carga y voltajes. |
| 🔔 **Alertas** | Avisos automáticos por temperatura, discos, contenedores caídos, VMs bloqueadas, UPS y notificaciones de Unraid. |
| 📚 **Shares** | Ocupación de cada share de usuario. |
| 🛡️ **Seguridad** | Allowlist de usuarios/chats, modo solo lectura, confirmación de acciones destructivas, límite de acciones y auditoría. |

Extras incluidos: **modo configuración guiado** (`/id`), **healthcheck** de Docker, **persistencia** de suscripciones, **protección contra autodestrucción** del propio contenedor y **diagnóstico** con `python -m bot.doctor`.

---

## ✅ Requisitos

- **Unraid 7.x** (la API GraphQL viene integrada). En 6.12 puede funcionar con el plugin `unraid-api`, pero no está probado.
- Un **bot de Telegram** creado con [@BotFather](https://t.me/BotFather).
- Una **API key de Unraid**: *Settings → Management Access → API Keys*.
- **Docker Compose** (plugin *Compose Manager* de Community Applications, o por SSH).
- Tu **ID de usuario de Telegram**. El bot te lo dice con `/id`.

---

## 🚀 Puesta en marcha

### 1. Crea el bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) → `/newbot`.
2. Elige nombre y usuario. Guarda el token `123456789:AA...`.
3. Opcional: `/setdescription`, `/setuserpic`, `/setcommands`.

### 2. Crea la API key de Unraid

1. *Settings → Management Access → API Keys → Create*.
2. Nombre: `unraidbot`.
3. Rol: **ADMIN** para empezar (o permisos de lectura/escritura sobre `ARRAY`, `DOCKER`, `VMS`, `INFO`, `DISK`, `NOTIFICATIONS` y `SHARE`).
4. Copia la clave. No se vuelve a mostrar.

### 3. Copia el proyecto al servidor

Por SSH, en Unraid:

```bash
mkdir -p /mnt/user/appdata/unraidbot
cd /mnt/user/appdata/unraidbot
# copia aquí el contenido del proyecto (git clone, scp, Compose Manager…)
```

Si usas **Compose Manager**: crea un stack llamado `unraidbot`, pega el contenido de `docker-compose.yml` y coloca el resto de archivos en la carpeta del stack.

### 4. Configura `.env`

La forma recomendada:

```bash
bash scripts/setup.sh
```

O manualmente:

```bash
cp .env.example .env
nano .env
```

Mínimo imprescindible:

```dotenv
TELEGRAM_BOT_TOKEN=123456789:AA...
UNRAID_API_KEY=tu-api-key
ALLOWED_USER_IDS=
UNRAID_API_URL=http://host.docker.internal/graphql
```

Deja `ALLOWED_USER_IDS` vacío en el primer arranque: el bot entra en **modo configuración** y solo responde con tu ID.

### 5. Arranca y autorízate

```bash
docker compose up -d --build
docker compose logs -f unraidbot
```

Habla con tu bot y envía `/id`. Te responderá con tu ID de usuario. Ponlo en `.env`:

```dotenv
ALLOWED_USER_IDS=123456789
```

Y recrea el contenedor:

```bash
docker compose up -d --force-recreate
```

Envíale `/start` o `/menu`. Ya está.

> Si el bot no arranca por `.env`, revisa `docker compose logs unraidbot`: la validación de configuración indica exactamente qué falta.

---

## ⚙️ Configuración

Todas las variables viven en `.env`.

| Variable | Por defecto | Descripción |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Token de @BotFather. **Obligatorio**. |
| `ALLOWED_USER_IDS` | vacío | IDs de Telegram autorizados, separados por comas. Vacío = modo configuración. |
| `ALLOWED_CHAT_IDS` | vacío | Grupos/canales permitidos. Los privados de usuarios autorizados siempre se permiten. |
| `UNRAID_API_KEY` | — | API key de Unraid. **Obligatoria**. |
| `UNRAID_API_URL` | `http://host.docker.internal/graphql` | URL de la API. Acepta `http://IP/graphql` o `https://IP/graphql`. |
| `UNRAID_API_SOCKET` | vacío | Alternativa avanzada: socket Unix (`/var/run/nginx.sock`). Requiere montarlo y permisos. |
| `UNRAID_VERIFY_SSL` | `false` | Verificar certificado TLS. Unraid suele usar autofirmado. |
| `READ_ONLY` | `false` | `true` bloquea todas las escrituras (array, Docker, VMs, paridad). |
| `BOT_CONTAINER_NAME` | `unraidbot` | Evita que el bot se pare o actualice a sí mismo. |
| `ALERTS_ENABLED` | `true` | Activa el monitor de alertas. |
| `ALERT_INTERVAL_SECONDS` | `300` | Frecuencia de revisión (mínimo 60). |
| `ALERT_REPEAT_MINUTES` | `360` | Cada cuánto repetir una incidencia que sigue activa. |
| `DISK_TEMP_WARNING` | `50` | Umbral de aviso de temperatura de disco (°C). |
| `DISK_TEMP_CRITICAL` | `55` | Umbral crítico de disco (°C). |
| `CPU_TEMP_WARNING` | `85` | Umbral de aviso de CPU (°C). |
| `MEMORY_WARNING` | `90` | Umbral de aviso de RAM (%). |
| `TIMEZONE` | `Europe/Madrid` | Zona horaria para fechas. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PUID` / `PGID` | `99` / `100` | UID/GID de Unraid para `./data` (`nobody:users`). |
| `DATA_DIR` | `/data` | Carpeta de estado y auditoría dentro del contenedor. |

`UNRAIDBOT_IMAGE` es opcional y solo afecta a Compose: permite usar una imagen ya publicada (por ejemplo `ghcr.io/alexmysterio/unraidbot:latest`) en lugar de construirla en local.

### Con SSL

```dotenv
UNRAID_API_URL=https://192.168.1.10/graphql
UNRAID_VERIFY_SSL=false
```

### Con IP fija (si `host.docker.internal` no funciona)

```dotenv
UNRAID_API_URL=http://192.168.1.10/graphql
```

### Con socket Unix

```yaml
volumes:
  - ./data:/data
  - /var/run/nginx.sock:/var/run/nginx.sock:ro
```

```dotenv
UNRAID_API_SOCKET=/var/run/nginx.sock
```

El usuario del contenedor debe poder leer el socket; si no, usa la URL HTTP. El socket es más rápido y no depende de la red del bridge, pero los permisos de `nginx.sock` suelen ser de `root`.

---

## 🎮 Uso

Menú principal:

```
📊 Estado     💾 Discos
🐳 Docker     🖥️ VMs
⚙️ Sistema    🔔 Alertas
❓ Ayuda
```

Comandos:

| Comando | Acción |
|---|---|
| `/start` | Bienvenida y menú. |
| `/menu` | Menú principal. |
| `/estado` | Estado general. |
| `/discos` | Discos del array, pools y físicos. |
| `/docker` | Contenedores con acciones. |
| `/vms` | Máquinas virtuales con acciones. |
| `/sistema` | Array, paridad, UPS, notificaciones, shares e información. |
| `/alertas` | Activar/desactivar alertas en el chat. |
| `/id` | Tu ID de usuario y de chat. |
| `/help` | Ayuda. |

### Docker

- La lista está paginada (8 por página).
- Toca un contenedor para ver imagen, estado, puertos, autostart y actualizaciones.
- **Logs**: últimas 40 líneas.
- **Actualizar imagen**: pide confirmación y puede tardar varios minutos (pull + recreate).
- El bot **no puede pararse a sí mismo**: detecta su propio contenedor por `BOT_CONTAINER_NAME` o por el ID corto del hostname.

### VMs

- **Apagar** envía un apagado ordenado (ACPI).
- **Forzar apagado** y **Reset** piden confirmación porque pueden perder datos.
- Si una VM no responde al apagado ordenado, usa «Forzar apagado» y luego «Iniciar».

### Array y paridad

- Detener el array pide confirmación y avisa de que los shares dejarán de estar disponibles.
- La comprobación de paridad que lanza el bot es **no correctiva** (solo lectura).
- Si el array está **cifrado**, la API necesita la contraseña/keyfile y el bot no la pide: inícialo desde el WebGUI. El bot mostrará el error correspondiente.

### Discos

- La lista del array muestra paridad, datos y caché/pools con estado, tamaño, uso, temperatura y 💤 si el disco está en reposo.
- «Discos físicos» muestra modelo, SMART, interfaz y número de serie.
- Para atributos SMART completos (sectores reasignados, horas, etc.) usa el WebGUI o `smartctl`: la API solo expone estado y temperatura.

---

## 🔔 Alertas

Actívalas por chat en **🔔 Alertas → Activar aquí**. El monitor revisa el servidor cada `ALERT_INTERVAL_SECONDS` y envía:

- Array detenido o en estado anómalo.
- Paridad con errores o última comprobación fallida.
- Discos en rojo/amarillo, con errores de E/S o temperatura alta.
- Contenedores con `autostart` que están detenidos.
- VMs en estado `CRASHED`.
- UPS en batería, batería baja, reemplazo o desconectada.
- Notificaciones nuevas de Unraid (alertas y avisos).

**Deduplicación:** una incidencia se avisa una vez. Si sigue activa, se recuerda cada `ALERT_REPEAT_MINUTES`. Cuando se resuelve, se envía un mensaje de «Resuelto». El estado se guarda en `./data/state.json`, así que un reinicio no genera spam.

**Prueba:** «📣 Enviar prueba» manda el estado actual de incidencias a ese chat.

**Umbrales:** se ajustan en `.env`. Ejemplo conservador para una caja con HDDs:

```dotenv
DISK_TEMP_WARNING=45
DISK_TEMP_CRITICAL=50
CPU_TEMP_WARNING=80
MEMORY_WARNING=85
```

---

## 🛡️ Seguridad

Diseño deliberadamente paranoico para un bot que puede parar contenedores:

1. **Sin puertos de entrada.** El contenedor no publica ningún puerto. Telegram se consulta por long polling saliente.
2. **Allowlist obligatoria.** Sin `ALLOWED_USER_IDS`, el bot solo responde `/id` y `/help`; no ejecuta nada.
3. **API key con permisos mínimos.** Empieza con ADMIN y, si quieres, crea una key granular. La API key no se registra en logs.
4. **Modo solo lectura.** `READ_ONLY=true` convierte el bot en un panel de consulta.
5. **Confirmación explícita** para array, paridad, actualizaciones de imagen, reinicio/reset/forzado de VMs.
6. **Límite de acciones:** 30 acciones por minuto y usuario.
7. **Auditoría:** cada acción se escribe en `./data/audit.log` (JSONL, rotación a 5 MB).
8. **Contenedor sin privilegios:** usuario `99:100`, `cap_drop: ALL` + solo `CHOWN/SETUID/SETGID/FOWNER` para el entrypoint, raíz de solo lectura, `/tmp` en tmpfs y `no-new-privileges`.
9. **El bot no se autodestruye:** bloquea stop/restart/update de su propio contenedor.

Recomendaciones:

- Usa **2FA en Telegram** y revisa *Dispositivos activos*.
- No compartas el token del bot: quien lo tenga controla el bot.
- Rota la API key si sospechas. Puedes tener una key distinta por bot.
- El WebGUI sigue siendo la vía principal para operaciones delicadas; este bot es un mando rápido.
- Si quieres acceso remoto al WebGUI, usa **Tailscale/WireGuard**, no abras puertos.

> El archivo `.env` contiene secretos. Está en `.gitignore` y excluido de la imagen Docker.

---

## 🧰 Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| «No se pudo contactar con la API de Unraid» | `host.docker.internal` no resuelve o Unraid no escucha en el bridge | Usa `UNRAID_API_URL=http://IP_DEL_SERVIDOR/graphql`. |
| HTTP 401/403 | API key incorrecta, revocada o sin permisos | Crea otra key con rol ADMIN y actualiza `.env`. |
| HTTP 404 | URL sin `/graphql` | El cliente añade `/graphql`; comprueba que la URL base es correcta. |
| Error TLS / certificado | Unraid con certificado autofirmado | `UNRAID_VERIFY_SSL=false` o usa `http://`. |
| El bot no responde | Token inválido, allowlist vacía o contenedor caído | `docker compose logs -f unraidbot`; envía `/id`. |
| «No autorizado» | Tu ID no está en `ALLOWED_USER_IDS` | Añádelo y recrea el contenedor. |
| El array cifrado no arranca | La API necesita contraseña | Inícialo desde el WebGUI. |
| La actualización Docker da timeout | Pull lento | El timeout es 300 s; revisa logs y vuelve a intentar. |
| Healthcheck `unhealthy` | `./data` sin permisos | Ajusta `PUID`/`PGID` o `chown -R 99:100 ./data`. |
| Faltan datos (UPS, shares…) | API antigua o sin permisos | Actualiza Unraid/API key. La pantalla indica qué sección falló. |
| Bot bloqueado por el usuario | El usuario bloqueó el bot | Desuscribe el chat y vuelve a activar alertas. |

Comandos útiles:

```bash
docker compose logs -f --tail=200 unraidbot
docker compose exec unraidbot python -m bot.doctor
docker compose exec unraidbot python -m bot.healthcheck
docker compose exec unraidbot cat /data/state.json
docker compose exec unraidbot tail -n 20 /data/audit.log
```

`python -m bot.doctor` comprueba la configuración, el ping a la API y el acceso a cada sección (array, discos, Docker, VMs, UPS, notificaciones y shares). Es la primera parada cuando algo no carga.

---

## 🗂️ Estructura

```
.
├── docker-compose.yml
├── Dockerfile
├── docker-entrypoint.sh
├── requirements.txt
├── .env.example
├── scripts/
│   └── setup.sh            # asistente interactivo de configuración
├── .github/
│   ├── workflows/          # CI + publicación en GHCR
│   └── ISSUE_TEMPLATE/
├── bot/
│   ├── app.py              # arranque, post_init/post_shutdown
│   ├── config.py           # validación de entorno
│   ├── unraid.py           # cliente GraphQL + snapshot
│   ├── health.py           # reglas de incidencias
│   ├── monitor.py          # alertas periódicas y deduplicación
│   ├── state.py            # suscripciones y estado persistente
│   ├── security.py         # auth, rate limit, confirmaciones, auditoría
│   ├── views.py            # mensajes HTML
│   ├── keyboards.py        # botones inline
│   ├── formatting.py       # tamaños, fechas, emojis
│   ├── heartbeat.py        # latido para healthcheck
│   ├── doctor.py           # diagnóstico de API y permisos
│   └── handlers/           # comandos y callbacks por dominio
├── tests/                  # pytest (sin red)
└── data/                   # state.json, audit.log, heartbeat (runtime)
```

---

## 🧪 Desarrollo

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
ruff check .
python -m pytest -q
```

También puedes usar `make test`, `make lint` o `make doctor` si tienes `make`.

Los tests no necesitan Telegram ni Unraid: usan `httpx.MockTransport` y snapshots sintéticos. Cubren formato, reglas de alertas, cliente GraphQL, persistencia, confirmaciones y deduplicación del monitor.

Para probar el bot en local:

```bash
cp .env.example .env
# rellena token y API key
python -m bot
python -m bot.doctor
```

---

## 💡 Propuestas (roadmap)

Ya incluido en esta versión: alertas, UPS, paridad, shares, auditoría, solo lectura, confirmaciones, modo configuración y healthcheck.

Ideas ordenadas por utilidad/esfuerzo:

| Propuesta | Por qué | Esfuerzo |
|---|---|---|
| **Notificaciones de Unraid en tiempo real** | La API tiene `Subscription.notificationAdded`; ahora se consultan cada 5 min. Un flujo SSE/WebSocket daría avisos instantáneos. | Medio |
| **Apagar/reiniciar el servidor** | La API GraphQL no expone shutdown/reboot. Se puede añadir con un script en `/boot/config/plugins/user.scripts` y un comando del bot que lo invoque (con doble confirmación). | Medio |
| **Backup del flash a Telegram** | Descargar el ZIP del flash y enviarlo como documento; útil antes de actualizar Unraid. | Bajo |
| **Wake-on-LAN** | Encender el servidor desde el móvil si está apagado (el bot necesitaría correr en otro host o usar un dispositivo siempre encendido). | Bajo |
| **Actualizar plugins de Unraid** | La API ya lista plugins; falta mutación de actualización y gestión de reinicios. | Medio |
| **Métricas históricas y gráficas** | Guardar CPU/RAM/temperaturas en SQLite y enviar un PNG diario/semanal. | Medio |
| **Multi-servidor** | Una instancia, varios Unraid y un selector de servidor. | Medio |
| **Roles** | Lectura para familia, administración para ti, usando chats distintos. | Bajo |
| **Lenguaje natural** | «reinicia plex», «¿cuánto espacio queda?» con un LLM y confirmación explícita antes de escribir. | Alto |
| **Home Assistant / MQTT** | Publicar estado y exponer acciones para automatizaciones. | Medio |

Mi recomendación de siguiente paso: **notificaciones en tiempo real + backup del flash**, porque añaden valor sin tocar la superficie de riesgo, y después **shutdown/reboot controlado** con doble confirmación.

---

## ⚠️ Limitaciones

- La API de Unraid no permite apagar ni reiniciar el host; tampoco expone todos los atributos SMART.
- El bot no sustituye al WebGUI: no gestiona shares, usuarios, plugins ni actualizaciones de Unraid.
- Las VMs solo se gestionan por estado (start/stop/pause/resume/reboot/reset); no hay consola ni snapshots.
- El botón de un mensaje antiguo puede caducar si la entidad desaparece o el bot se reinicia; vuelve a abrir el menú.
- El arranque de un array cifrado requiere el WebGUI.
- Telegram no es un canal de tiempo real duro: en una caída de red, las alertas llegan cuando el bot recupera conexión.

---

## ❓ FAQ

**¿Necesito abrir algún puerto?**
No. El bot inicia conexiones salientes a Telegram y a la API local de Unraid.

**¿Funciona en Unraid 6.12?**
Está pensado para Unraid 7.x. En 6.12 puede funcionar con el plugin `unraid-api`, pero no está probado; revisa que existan las consultas GraphQL que usa el bot.

**¿Puedo dar solo lectura a alguien?**
Sí: `READ_ONLY=true` desactiva todas las escrituras. Si quieres roles distintos, lo más sencillo es ejecutar dos contenedores con allowlists y modos separados.

**¿Cómo actualizo?**
```bash
git pull
docker compose up -d --build
```
Tus datos (`./data`) y `.env` se conservan.

**¿Dónde se guardan las suscripciones y la auditoría?**
En `./data/state.json` y `./data/audit.log`. Puedes borrar `state.json` para resetear las alertas; se recrea solo.

**¿Puedo usarlo en un grupo?**
Sí, añade el ID del grupo a `ALLOWED_CHAT_IDS` y activa las alertas allí. Los usuarios deben estar además en `ALLOWED_USER_IDS`.

**¿Por qué no aparece el botón de actualizar Docker?**
Solo se muestra si la API detecta una imagen más reciente (`isUpdateAvailable`).

---

## 🤝 Contribuir

Las propuestas y PRs son bienvenidos. Antes de abrir uno:

- Lee [CONTRIBUTING.md](CONTRIBUTING.md) para el entorno de desarrollo y el estilo.
- Para fallos de seguridad, usa **Security → Report a vulnerability**; no abras un issue público. Detalles en [SECURITY.md](SECURITY.md).
- Revisa el [CHANGELOG.md](CHANGELOG.md) y las plantillas de issue/PR.

El CI ejecuta `ruff`, los tests y un build de la imagen en cada push y PR. Las releases se publican en GHCR al empujar un tag `v*`.

---

## 📄 Licencia

MIT. Úsalo, modifícalo y compártelo. Unraid® es una marca registrada de Lime Technology, Inc.; este proyecto no está afiliado a Lime Technology.

## 🔗 Referencias

- [Documentación de la API de Unraid](https://docs.unraid.net/API/how-to-use-the-api/)
- [Esquema GraphQL generado](https://github.com/unraid/api/blob/main/api/generated-schema.graphql)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [Bot API de Telegram](https://core.telegram.org/bots/api)
