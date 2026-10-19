# Contribuir a UnraidBot

Gracias por querer mejorar el proyecto. Este bot puede parar contenedores y VMs, así que priorizamos cambios pequeños, revisables y con tests.

## Antes de empezar

- Busca issues y PRs existentes para no duplicar trabajo.
- Para cambios grandes, abre una propuesta explicando el caso de uso.
- Para fallos de seguridad, **no abras un issue público**: usa *Security → Report a vulnerability* en GitHub.

## Entorno de desarrollo

```bash
git clone https://github.com/Alexmysterio/UnraidBot.git
cd UnraidBot
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Comprobaciones antes de subir cambios:

```bash
ruff check .
pytest -q
docker compose config --quiet   # si tocas el compose
```

Los tests no necesitan Telegram ni Unraid real. Usan `httpx.MockTransport` y snapshots sintéticos; si añades lógica, añade su test.

## Estilo

- Código e identificadores en inglés; mensajes de usuario en español.
- Funciones pequeñas, `async` para I/O y sin bloquear el event loop.
- Nada de secretos en el código, tests, logs o capturas.
- Errores de API siempre a través de `UnraidError`; el handler global se encarga de mostrarlos al usuario.
- Respeta el enfoque del proyecto: **sin puertos de entrada**, long polling y API local.

## Pull requests

- Una rama por cambio: `feat/...`, `fix/...`, `docs/...`.
- Commits claros; no hace falta firmar.
- Rellena la plantilla del PR y marca la checklist.
- Si cambias variables de entorno, actualiza `.env.example`, `README.md` y `scripts/setup.sh`.
- Si añades una pantalla o acción, añade su callback a `bot/handlers/__init__.py`, su teclado y su vista.

## Publicar el repositorio por primera vez

```bash
git init
git add .
git commit -m "feat: UnraidBot 1.0.0"
git branch -M main
git remote add origin git@github.com:Alexmysterio/UnraidBot.git
git push -u origin main
```

`.env` y `data/` están excluidos por `.gitignore`; comprueba con `git status` que no aparece ningún secreto antes del primer push.

## Publicar una release

El repositorio está preparado para construir la imagen en GitHub Container Registry:

```bash
git tag v1.0.0
git push origin v1.0.0
```

El workflow `Publicar imagen` genera `ghcr.io/alexmysterio/unraidbot:v1.0.0` y `latest`. Después, en GitHub:

1. *Settings → General → Description*: `Bot de Telegram para administrar Unraid sin abrir puertos`.
2. *Topics*: `unraid`, `telegram-bot`, `docker`, `selfhosted`, `homelab`, `graphql`.
3. *Settings → Security → Private vulnerability reporting*: activado.
4. *Settings → Actions → General*: permisos de solo lectura por defecto.
5. *Packages*: haz público el paquete GHCR si quieres que cualquiera pueda descargar la imagen.
6. Protege `main`: PR obligatorio y CI en verde.

## Código de conducta

Al participar aceptas el [código de conducta](CODE_OF_CONDUCT.md).
