"""
Trae los datos reales desde el repositorio PRIVADO de GitHub que los
contiene, y los deja listos en la carpeta local `data/` -- para que el resto
de la app (datos.py) los use exactamente igual que si hubieran estado ahí
desde siempre.

Por qué existe este archivo: el repositorio de CÓDIGO de este tablero es
público (así Streamlit Cloud no exige invitar por correo a cada persona que
quiera entrar -- ver README.md). Pero los datos reales de estudiantes NO
pueden estar en un repositorio público bajo ninguna circunstancia. Por eso
viven en un segundo repositorio, separado y privado, y esta pieza los trae
en tiempo de ejecución usando un token que solo puede LEER ese repositorio
puntual -- nada más.

Configuración necesaria en Secrets (ver README.md):
    github_token_datos = "..."   # fine-grained PAT, solo lectura, solo ese repo
    github_repo_datos  = "usuario/nombre-del-repo-de-datos"
"""

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from datos import CARPETA_DATOS, ZONA_HORARIA_COLOMBIA

RAMA_DATOS = "main"

# Metadato aparte de data/ a propósito: _sincronizar_carpeta() borra de data/
# cualquier archivo que no venga en el zip del repositorio de datos, así que
# si este archivo quedara adentro se autodestruiría en cada sincronización.
RUTA_META = CARPETA_DATOS.parent / ".ultima_actualizacion_datos.json"


def _descargar_zip(repo: str, token: str) -> bytes:
    """Descarga el .zip del repositorio de datos desde la API de GitHub.

    GitHub responde a este endpoint con una redirección hacia
    codeload.github.com para la descarga real. Por seguridad, `requests` NO
    reenvía el header Authorization a un dominio distinto del de la petición
    original -- así que hay que repetirlo a mano en esa segunda petición. Si
    no se hace esto, la descarga del repo privado falla (o llega vacía) en
    vez de fallar con un error claro de permisos.
    """
    url = f"https://api.github.com/repos/{repo}/zipball/{RAMA_DATOS}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(url, headers=headers, allow_redirects=False, timeout=30)
    if resp.status_code in (301, 302, 303, 307, 308):
        resp = requests.get(resp.headers["Location"], headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.content


def _fecha_ultimo_commit(repo: str, token: str) -> str:
    """Fecha (ISO 8601, UTC) del commit más reciente en el repositorio de
    datos -- esto es lo que de verdad responde "¿cuándo se cargaron las
    bases nuevas?". A propósito NO usamos la fecha del archivo local: esa
    cambia cada vez que el servidor sincroniza (aunque las bases llevan un
    mes sin cambiar), y terminaría pareciendo que los datos están más
    frescos de lo que en realidad están."""
    url = f"https://api.github.com/repos/{repo}/commits/{RAMA_DATOS}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["commit"]["committer"]["date"]


def _escribir_si_cambio(ruta: Path, contenido: bytes) -> bool:
    """Solo reescribe el archivo si el contenido realmente cambió -- así no
    tocamos su fecha de modificación sin necesidad, y el caché de pandas
    (que depende de esa fecha, ver datos._firma_carpeta) no se invalida
    gratis en cada sincronización cuando en realidad no cambió nada."""
    if ruta.exists() and ruta.read_bytes() == contenido:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    return True


def _sincronizar_carpeta(contenido_zip: bytes, destino: Path) -> int:
    """Refleja el contenido del zip en `destino`: escribe lo nuevo/cambiado
    y borra ahí cualquier archivo que ya no exista en el repo de datos --
    así un archivo que Camilo borre allá también desaparece acá, en vez de
    quedar como basura desactualizada que nadie nota."""
    archivos_nuevos = {}
    with zipfile.ZipFile(io.BytesIO(contenido_zip)) as zf:
        nombres = [n for n in zf.namelist() if not n.endswith("/")]
        if not nombres:
            raise ValueError("El repositorio de datos está vacío.")
        raiz = nombres[0].split("/")[0]  # GitHub empaqueta todo dentro de usuario-repo-sha/
        for nombre in nombres:
            relativa = Path(nombre).relative_to(raiz)
            archivos_nuevos[relativa] = zf.read(nombre)

    cambios = 0
    for relativa, contenido in archivos_nuevos.items():
        if _escribir_si_cambio(destino / relativa, contenido):
            cambios += 1

    if destino.exists():
        for archivo_local in destino.rglob("*"):
            if archivo_local.is_file():
                relativa = archivo_local.relative_to(destino)
                if relativa not in archivos_nuevos:
                    archivo_local.unlink()
                    cambios += 1

    return cambios


@st.cache_resource(ttl=600, show_spinner="Sincronizando los datos más recientes…")
def sincronizar_datos_remotos():
    """Punto de entrada único, pensado para llamarse desde app.py antes de
    cargar cualquier página. Streamlit reejecuta esta función como máximo
    cada 10 minutos -- o de inmediato si alguien aprieta el botón "Actualizar
    datos ahora" (que limpia este caché puntual) -- para no golpear la API
    de GitHub en cada clic de cada persona."""
    try:
        repo = st.secrets.get("github_repo_datos")
        token = st.secrets.get("github_token_datos")
    except Exception:
        # st.secrets lanza un error (en vez de devolver None) cuando no
        # existe NINGÚN secrets.toml todavía -- por ejemplo, en una copia
        # local recién clonada antes de configurar nada.
        repo = token = None

    if not repo or not token:
        # Sin estas dos claves configuradas en Secrets asumimos que estás
        # trabajando en local con los datos ya copiados a mano en data/ --
        # no es un error, simplemente no hay nada que sincronizar.
        return {"ok": False, "motivo": "sin_configurar"}

    try:
        contenido_zip = _descargar_zip(repo, token)
        cambios = _sincronizar_carpeta(contenido_zip, CARPETA_DATOS)
        try:
            fecha_commit = _fecha_ultimo_commit(repo, token)
            RUTA_META.write_text(json.dumps({"fecha_commit": fecha_commit}))
        except Exception:
            # Si esto puntual falla (por ejemplo, un error de red pasajero),
            # no arriesgamos la sincronización de los datos en sí -- la app
            # sigue funcionando, solo se queda con la fecha guardada antes.
            pass
        return {"ok": True, "cambios": cambios}
    except Exception as e:
        return {"ok": False, "motivo": "error", "detalle": str(e)}


def fecha_ultima_actualizacion_remota():
    """Fecha del último commit en el repositorio de datos (cuándo se
    cargaron ahí las bases más recientes), en hora de Colombia -- tal como
    quedó guardada en la sincronización más reciente. Devuelve None si
    todavía no se ha sincronizado ni una vez con éxito (por ejemplo, en una
    copia local sin Secrets configurados), en cuyo caso app.py usa como
    respaldo la fecha del archivo local (ver datos.fecha_ultima_actualizacion)."""
    if not RUTA_META.exists():
        return None
    try:
        fecha_iso = json.loads(RUTA_META.read_text())["fecha_commit"]
        fecha_utc = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
        return fecha_utc.astimezone(ZONA_HORARIA_COLOMBIA)
    except Exception:
        return None