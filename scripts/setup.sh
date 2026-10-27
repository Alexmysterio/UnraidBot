#!/usr/bin/env bash
# Configurador interactivo de UnraidBot.
# Crea .env a partir de unas pocas preguntas y, opcionalmente, arranca el stack.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "🤖 UnraidBot · configuración"
echo

if [[ -f .env ]]; then
    read -r -p ".env ya existe. ¿Sobrescribirlo? [s/N] " overwrite
    case "${overwrite:-n}" in
        s|S|si|Si|SI|sí|Sí|SÍ) ;;
        *) echo "Cancelado. No se ha tocado .env."; exit 0 ;;
    esac
fi

read -r -p "Token de @BotFather: " token
if [[ ! "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
    echo "❌ El token no tiene el formato esperado (123456:ABC...)." >&2
    exit 1
fi

read -r -p "API key de Unraid: " api_key
if [[ -z "$api_key" ]]; then
    echo "❌ La API key es obligatoria." >&2
    exit 1
fi
if [[ ! "$api_key" =~ ^[A-Za-z0-9._~+/=-]+$ ]]; then
    echo "❌ La API key contiene caracteres no esperados." >&2
    exit 1
fi

read -r -p "URL de la API [http://host.docker.internal/graphql]: " api_url
api_url="${api_url:-http://host.docker.internal/graphql}"
if [[ ! "$api_url" =~ ^https?:// ]]; then
    echo "❌ La URL debe empezar por http:// o https://." >&2
    exit 1
fi

read -r -p "Tu ID de Telegram (opcional; déjalo vacío y usa /id): " user_ids
if [[ -n "$user_ids" && ! "$user_ids" =~ ^[0-9,[:space:]]+$ ]]; then
    echo "❌ Los IDs deben ser números separados por comas." >&2
    exit 1
fi

read -r -p "Zona horaria [Europe/Madrid]: " timezone
timezone="${timezone:-Europe/Madrid}"

read -r -p "PUID de Unraid [99]: " puid
puid="${puid:-99}"
read -r -p "PGID de Unraid [100]: " pgid
pgid="${pgid:-100}"
if [[ ! "$puid" =~ ^[0-9]+$ || ! "$pgid" =~ ^[0-9]+$ ]]; then
    echo "❌ PUID y PGID deben ser numéricos." >&2
    exit 1
fi

umask 077
cat > .env <<EOF
# Generado por scripts/setup.sh el $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Consulta .env.example para todas las opciones disponibles.

TELEGRAM_BOT_TOKEN=${token}
ALLOWED_USER_IDS=${user_ids}
ALLOWED_CHAT_IDS=

UNRAID_API_KEY=${api_key}
UNRAID_API_URL=${api_url}
UNRAID_API_SOCKET=
UNRAID_VERIFY_SSL=false

READ_ONLY=false
BOT_CONTAINER_NAME=unraidbot

ALERTS_ENABLED=true
ALERT_INTERVAL_SECONDS=300
ALERT_REPEAT_MINUTES=360
DISK_TEMP_WARNING=50
DISK_TEMP_CRITICAL=55
CPU_TEMP_WARNING=85
MEMORY_WARNING=90

DIGEST_ENABLED=true
DIGEST_HOUR=9
DIGEST_MINUTE=0

# Servicios extra: cámbialos a "active" y rellena sus datos cuando los uses.
SERVICE_QBITTORRENT=noactive
SERVICE_MIKROTIK=noactive
SERVICE_WOL=noactive
SERVICE_TELEGRAM_PROXY=noactive
TELEGRAM_RATE_LIMIT=active
TELEGRAM_RATE_LIMIT_MAX_RETRIES=2
USER_RATE_LIMIT_ACTIONS=30
USER_RATE_LIMIT_WINDOW=60

TIMEZONE=${timezone}
LOG_LEVEL=INFO
DATA_DIR=/data
PUID=${puid}
PGID=${pgid}
TZ=${timezone}
EOF
chmod 600 .env

echo
echo "✅ .env creado con permisos 600."
if [[ -z "$user_ids" ]]; then
    echo "⚠️  ALLOWED_USER_IDS está vacío: el bot arrancará en modo configuración."
    echo "   Envía /id al bot, copia tu ID y edítalo en .env."
fi
echo

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    COMPOSE=""
fi

if [[ -n "$COMPOSE" ]]; then
    read -r -p "¿Construir y arrancar el contenedor ahora? [S/n] " start_now
    case "${start_now:-s}" in
        n|N|no|No|NO)
            echo "Cuando quieras: docker compose up -d"
            ;;
        *)
            $COMPOSE up -d
            echo
            echo "📋 Logs: docker compose logs -f unraidbot"
            echo "🩺 Diagnóstico: docker compose exec unraidbot python -m bot.doctor"
            ;;
    esac
else
    echo "Docker Compose no está disponible en este shell."
    echo "Cuando lo tengas: docker compose up -d"
fi
