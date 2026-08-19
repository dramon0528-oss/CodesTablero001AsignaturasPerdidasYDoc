"""
Punto de entrada del tablero. Controla en un solo lugar:
  1) la puerta de contraseña (nadie ve nada sin pasar por auth.check_password)
  2) la navegación entre páginas, agrupada igual que tus pestañas de Power BI

Correr localmente:
    streamlit run app.py
"""

from pathlib import Path

import streamlit as st

import datos
import sincronizar_datos
import tema
from auth import check_password

# Path absoluto (no un string relativo como "assets/logo.png") por la misma
# razón que datos.py usa Path(__file__).parent para la carpeta de datos: así
# el logo se encuentra sin importar desde qué directorio arranque el proceso.
LOGO = Path(__file__).parent / "assets" / "logo_esap.png"

st.set_page_config(
    page_title="ESAP · Seguimiento Académico",
    page_icon="🎓",
    layout="wide",
)

if not check_password():
    st.stop()

# Logo institucional: arriba a la izquierda de la barra lateral en todas las
# páginas (y en el encabezado si alguien colapsa la barra). Streamlit lo
# redimensiona solo -- "large" es la opción más grande disponible (32px de
# alto); el archivo es horizontal (escudo + texto), tal como recomienda la
# documentación para este parámetro.
st.logo(LOGO, size="large")

# Dos toques de marca que st.logo()/st.title() no dejan configurar directo:
# 1) el título grande (st.title) de cada página, en el azul institucional
#    (mismo AZUL_ESAP que ya usa auth.py, para que se vea consistente).
# 2) el logo de la barra lateral un poco más grande que el máximo que ofrece
#    size="large" (32px). El selector [data-testid="stSidebarLogo"] es el que
#    usa el propio Streamlit instalado (1.61.1) específicamente para el logo
#    DENTRO de la barra lateral -- no toca el que aparece arriba a la
#    izquierda si alguien la colapsa (ese usa data-testid="stLogo").
# Si más adelante quieres otro azul o otro tamaño, este es el único lugar
# que hay que tocar.
st.markdown(
    f"""
    <style>
    h1 {{ color: {tema.AZUL_ESAP} !important; }}
    [data-testid="stSidebar"] [data-testid="stSidebarLogo"] {{
        height: 46px !important;
        width: auto !important;
        max-width: none !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

paginas = {
    "Historia académica": [
        st.Page("paginas/1_activos.py", title="Activos", icon="📋"),
        st.Page("paginas/2_asignaturas.py", title="Asignaturas", icon="📚"),
        st.Page("paginas/3_dispersion.py", title="Dispersión", icon="📈"),
    ],
    "Docencia": [
        st.Page("paginas/4_docencia.py", title="Alertas de docencia", icon="🧑‍🏫"),
    ],
}

# Trae la versión más reciente de los datos reales desde el repositorio
# privado que los contiene (ver sincronizar_datos.py) ANTES de mostrar nada.
# Si falla, no bloqueamos la app -- seguimos con lo que ya haya localmente
# (aunque esté un poco viejo) y solo avisamos; cada página ya sabe mostrar
# su propio error si de plano no hay ningún dato disponible.
_sync = sincronizar_datos.sincronizar_datos_remotos()
if _sync and not _sync["ok"] and _sync["motivo"] == "error":
    st.sidebar.warning("No pude traer los datos más recientes -- puede que estés viendo una versión anterior.")
    st.sidebar.caption(f"Detalle técnico: {_sync['detalle']}")

if st.sidebar.button("🔄 Actualizar datos ahora"):
    sincronizar_datos.sincronizar_datos_remotos.clear()
    st.rerun()

# Para que cualquiera que abra el tablero sepa qué tan frescos son los datos,
# sin tener que ir a revisar GitHub. Preferimos la fecha del último commit en
# el repositorio de datos (cuándo Camilo cargó ahí las bases más recientes) --
# NO la fecha del archivo local, que cambia cada vez que el servidor
# sincroniza aunque las bases lleven semanas sin cambiar de verdad. Si todavía
# no hay ninguna sincronización remota exitosa (ej: copia local sin Secrets),
# caemos de respaldo a la fecha del archivo local.
# IMPORTANTE: esto va ANTES de pg.run(), no después -- varias páginas llaman
# st.stop() cuando un filtro no deja resultados (para no seguir dibujando algo
# vacío más abajo), y st.stop() corta el resto del script completo. Si esto
# quedara después de pg.run(), desaparecería justo en esos casos.
_fecha_datos = sincronizar_datos.fecha_ultima_actualizacion_remota() or datos.fecha_ultima_actualizacion()
if _fecha_datos:
    st.sidebar.caption(f"📅 Datos actualizados: {_fecha_datos.strftime('%d/%m/%Y %H:%M')}")

pg = st.navigation(paginas)
pg.run()