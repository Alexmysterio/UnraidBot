# Seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| 1.x | ✅ Activa |

## Reportar una vulnerabilidad

**No abras un issue público.** Usa la pestaña **Security → Report a
vulnerability** del repositorio (GitHub Security Advisories). Si no está
disponible, contacta con el mantenedor por GitHub.

Incluye:

- Versión del bot y de Unraid.
- Descripción del impacto y cómo reproducirlo.
- Pasos mínimos; no incluyas tu token, API key ni datos de tu servidor.

Intentaremos responder en 72 horas y publicar un parche coordinado.

## Modelo de amenaza

UnraidBot puede ejecutar acciones sobre el servidor (parar contenedores, apagar
VMs, detener el array). Las credenciales y la allowlist son la frontera de
seguridad.

| Activo | Riesgo | Mitigación |
|---|---|---|
| Token del bot | Quien lo tenga controla el bot | Secreto en `.env` (0600), no en logs ni issues, rotación en BotFather |
| API key de Unraid | Acceso completo a la API | Rol mínimo, rotación, no se registra en logs |
| Usuarios de Telegram | Suplantación o cuenta comprometida | Allowlist de IDs + 2FA en Telegram |
| Contenedor | Escalada de privilegios | Usuario 99:100, `cap_drop: ALL`, rootfs de solo lectura, sin puertos |
| Acciones destructivas | Error humano | Confirmación explícita, modo `READ_ONLY`, auditoría |

## Buenas prácticas para usuarios

- No expongas el contenedor ni el WebGUI a Internet. Si necesitas acceso remoto,
  usa Tailscale o WireGuard.
- Usa una API key propia y, si es posible, con permisos mínimos.
- Activa 2FA en Telegram y revisa los dispositivos conectados.
- Revisa `data/audit.log` si algo no cuadra.
- Mantén el bot y la imagen actualizados.

## Alcance

Quedan fuera de alcance los fallos de Unraid, Telegram o Docker, y los derivados
de exponer el WebGUI o el socket de Docker a Internet.
