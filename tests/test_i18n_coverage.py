from __future__ import annotations

import pytest

from bot.i18n import CATALOG, EXTRA_TRANSLATIONS, localize, set_language

LANGUAGES = ("en", "fr", "it")

# Cadenas introducidas en 1.3.0: deben existir en los tres idiomas.
REQUIRED_STRINGS = (
    "Array casi lleno",
    "• Disco: aviso ",
    "Comprobación de paridad antigua",
    "errores con la comprobación al ",
    "Interfaz de red caída",
    "Contenedor unhealthy: ",
    "🔕 Silenciado hasta el ",
    "🔕 Alertas silenciadas hasta el ",
    "🔔 Silencio desactivado.",
    "Duración de silencio no válida.",
    "El bot no puede contactar con la API local. Revisa que Unraid esté encendido, la URL y la conectividad de la red Docker.",
)

# Cadenas introducidas en 1.4.0: UX, búsqueda, historial, rendimiento y digest.
REQUIRED_STRINGS_V14 = (
    "🔎 Buscar",
    "📈 Rendimiento",
    "🔎 <b>Búsqueda</b> · «",
    "No se encontraron resultados.",
    "Toca un resultado para abrirlo.",
    "🔎 Nueva búsqueda",
    "🗂️ <b>Historial de auditoría</b>",
    "🔒 El historial de auditoría es solo para administradores.",
    "🧹 Quitar filtro",
    "📈 <b>Rendimiento</b>",
    "Sin historial de CPU todavía.",
    "📬 <b>Resumen diario · ",
    "Operación en curso… ",
    "⏱️ Duración: ",
    "✅ <b>Array iniciado</b>",
    "✅ <b>Array detenido</b>",
    "🔄 VM reiniciada",
)


# Cadenas introducidas en 1.5.0: integraciones, WOL multi-equipo y servicios extra.
REQUIRED_STRINGS_V15 = (
    "⚙️ <b>Límites de velocidad</b>",
    "📚 <b>Categorías</b>",
    "📚 Categorías",
    "⚙️ Límites",
    "📋 <b>Leases DHCP</b>",
    "🧭 <b>Rutas</b>",
    "🧭 Rutas",
    "📜 <b>Registros</b>",
    "📜 Registros",
    "⚡ Encender todos",
    "🧰 Herramientas",
    "🔁 Reiniciar",
    "🗑 Borrar",
    "➕ Añadir",
    "⏸ Pausar todo",
    "▶️ Reanudar todo",
    "⚡ Activar alternativa",
    "⚡ Desactivar alternativa",
    "No hay torrents con este filtro.",
    "No hay interfaces.",
    "No hay leases DHCP.",
    "No hay rutas.",
    "No hay reglas de firewall.",
    "No hay registros.",
    "No hay equipos configurados.",
    "No hay equipos configurados en WOL_DEVICES.",
    "Pulsa un equipo para enviar su magic packet.",
    "Equipos configurados: <b>",
    "Ese equipo ya no está configurado.",
    "No encontré ningún equipo llamado «",
    "No encontré ningún torrent llamado «",
    "✅ Torrent añadido",
    "⚙️ Límites actualizados",
    "❌ Envía un enlace magnet o una URL http(s).",
    "➕ <b>Añadir torrent</b>",
    "🔁 <b>Reiniciar MikroTik</b>",
    "El router se reiniciará y la red quedará cortada unos segundos. ¿Continuar?",
    "🔁 <b>Reinicio de MikroTik enviado.</b>",
    "Se eliminará el torrent, pero no los archivos descargados.",
    "🗑 <b>Torrent eliminado</b>",
    "Uso de /qbittorrent",
    "Uso de /mikrotik",
    "Uso de /wol",
    "⚡ Magic packet enviado a <b>",
    "Magic packets enviados: <b>",
    "Velocidad alternativa: <b>",
    "Límites alternativa: ",
    "Descarga: <b>",
    "Subida: <b>",
    # Fragmentos de pantalla de las integraciones.
    "Todos",
    "Pausados",
    "Descargando",
    "Sembrando",
    "Información",
    "ilimitado",
    "⚡ alternativa activa",
    "⚡ alternativa inactiva",
    "Velocidad alternativa: <b>activada</b>",
    "Velocidad alternativa: <b>desactivada</b>",
    "Progreso: ",
    "Semillas: ",
    "Pares: ",
    "Categoría: <code>",
    "Ruta: <code>",
    "Añadido: ",
    "Sin categoría",
    "No hay categorías definidas.",
    "Para cambiarlos: ",
    "(KB/s; 0 = ilimitado).",
    " más en total",
    " libres de ",
    "% usada)",
    "Rutas: ",
    "activas",
    " reglas activas",
    "dinámica",
    "estática",
    "deshabilitada",
    " paquetes · ",
    "⏸ Torrent pausado",
    "▶️ Torrent reanudado",
    "❌ No se pudo añadir el torrent: ",
    "Se eliminará el torrent y también los archivos descargados.",
    "🗑 <b>Borrar ",
    "⚡ Magic packet enviado a ",
)


def test_catalogs_share_the_same_keys() -> None:
    reference = set(CATALOG["en"])
    for language in ("fr", "it"):
        assert set(CATALOG[language]) == reference
    for language in LANGUAGES:
        assert all(value.strip() for value in CATALOG[language].values())


def test_extra_translations_are_complete() -> None:
    reference = set(EXTRA_TRANSLATIONS["en"])
    for language in ("fr", "it"):
        assert set(EXTRA_TRANSLATIONS[language]) == reference
        assert all(value.strip() for value in EXTRA_TRANSLATIONS[language].values())


@pytest.mark.parametrize("language", LANGUAGES)
def test_release_strings_are_translated(language: str) -> None:
    catalog = CATALOG[language]
    for source in REQUIRED_STRINGS + REQUIRED_STRINGS_V14 + REQUIRED_STRINGS_V15:
        assert source in catalog, f"Falta {source!r} en {language}"
        assert catalog[source].strip(), f"Traducción vacía de {source!r} en {language}"


@pytest.mark.parametrize("language", LANGUAGES)
def test_localize_uses_release_strings(language: str) -> None:
    set_language(language)
    for source in REQUIRED_STRINGS + REQUIRED_STRINGS_V14 + REQUIRED_STRINGS_V15:
        translated = localize(source)
        assert translated == CATALOG[language][source]
        if language != "es":
            assert translated != source


def test_spanish_remains_untranslated() -> None:
    set_language("es")
    for source in REQUIRED_STRINGS + REQUIRED_STRINGS_V14 + REQUIRED_STRINGS_V15:
        assert localize(source) == source


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_keys_localize_without_cascading(language: str) -> None:
    """Cada clave debe traducirse a su valor sin que otra sustitución la corrompa.

    Protege frente a casos como la clave francesa «Red» → «Réseau», que
    convertía «Redémarrer» en «Réseauémarrer».
    """
    set_language(language)
    broken = {
        key: (localize(key), value)
        for key, value in CATALOG[language].items()
        if key != "lang_choose" and localize(key) != value
    }
    assert not broken, f"Traducciones corruptas en {language}: {broken}"
