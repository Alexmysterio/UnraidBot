#!/bin/sh
# Prepara /data con el UID/GID de Unraid y ejecuta el bot sin privilegios.
set -eu

PUID="${PUID:-99}"
PGID="${PGID:-100}"
DATA_DIR="${DATA_DIR:-/data}"

mkdir -p "$DATA_DIR"
chown "$PUID:$PGID" "$DATA_DIR" 2>/dev/null || true
chmod u+rwx "$DATA_DIR" 2>/dev/null || true

exec gosu "$PUID:$PGID" "$@"
