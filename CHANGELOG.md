# Changelog

Todas las novedades relevantes de este proyecto se documentan aquí. El formato
sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

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
