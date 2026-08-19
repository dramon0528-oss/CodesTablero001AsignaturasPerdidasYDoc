"""
Módulo de datos del tablero — el equivalente en pandas de todo lo que antes
vivía como columnas calculadas / medidas DAX en Power BI: Resultado_Materia,
Orden_Periodo, NOMBRE_PROGRAMA/MODALIDAD, TERRITORIAL/CETAP, Rango_Nota,
Numero_Intento, Es_Repitencia, Tasa de Repitencia, etc.

NO vuelve a normalizar los datos crudos -- eso lo siguen haciendo, igual que
siempre, normalizar_historia_academica.py y normalizar_docencia.py. Este
módulo asume que ya corriste esos dos scripts y que sus carpetas de salida
(salida_normalizada/ y salida_docencia/), más tabla_programas_normalizada.xlsx
y tabla_territoriales.xlsx, están copiadas dentro de data/ (ver README.md).

Todo lo pesado está detrás de @st.cache_data: la primera persona que abre el
tablero espera unos segundos, todas las siguientes (y todas las páginas)
reutilizan el mismo resultado ya calculado, hasta que los archivos cambien.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 0. RUTAS -- ajusta esto si organizas las carpetas distinto
# ---------------------------------------------------------------------------
CARPETA_DATOS = Path(__file__).parent / "data"
CARPETA_HISTORIA = CARPETA_DATOS / "salida_normalizada"
CARPETA_DOCENCIA = CARPETA_DATOS / "salida_docencia"
RUTA_PROGRAMAS = CARPETA_DATOS / "tabla_programas_normalizada.xlsx"
RUTA_TERRITORIALES = CARPETA_DATOS / "tabla_territoriales.xlsx"

# El servidor donde corre Streamlit Community Cloud no está en Colombia (usa
# su propia hora, normalmente UTC) -- sin esto, "Datos actualizados" se ve
# adelantada varias horas. Colombia no cambia de horario en el año (no tiene
# horario de verano), así que esta zona horaria es siempre UTC-5.
ZONA_HORARIA_COLOMBIA = ZoneInfo("America/Bogota")

# ---------------------------------------------------------------------------
# 1. REGLAS DE NEGOCIO -- mismos valores que ya validamos en los dos scripts
#    de normalización y en las medidas DAX. Si el umbral de aprobación cambia
#    algún día, este es el único lugar que hay que tocar para que el tablero
#    completo (historia académica) quede consistente.
# ---------------------------------------------------------------------------
UMBRAL_APROBACION = {"Pregrado": 3.0, "Especialización": 3.5, "Maestría": 3.5}
UMBRAL_APROBACION_DEFAULT = 3.5

# Numero_Intento: mapeo de NOM_EST_MATERIA (los valores reales que confirmamos
# en tus datos) al número de intento. Cancelada no es un intento -- queda en blanco.
MAPA_NUMERO_INTENTO = {
    "Matriculado": 1,
    "Repite": 2,
    "Repite por tercera vez": 3,
    "Repite por cuarta vez": 4,
    "Repite por quinta vez": 5,
}


def _firma_carpeta(ruta: Path) -> tuple:
    """Huella (nombre, tamaño, fecha de modificación) de todos los archivos
    bajo `ruta`. Se usa como argumento "invisible" de las funciones con
    @st.cache_data: si reemplazas un parquet/xlsx por una versión nueva, la
    huella cambia sola y Streamlit recalcula todo automáticamente -- no hace
    falta reiniciar el servidor ni limpiar caché a mano."""
    if not ruta.exists():
        return ()
    archivos = sorted(ruta.rglob("*")) if ruta.is_dir() else [ruta]
    return tuple(
        (str(f), f.stat().st_size, f.stat().st_mtime) for f in archivos if f.is_file()
    )


# ---------------------------------------------------------------------------
# 2. CARGA CRUDA de las tablas ya normalizadas
# ---------------------------------------------------------------------------
def _leer_parquet(carpeta: Path, nombre: str) -> pd.DataFrame:
    ruta = carpeta / f"{nombre}.parquet"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No encuentro {ruta}. ¿Copiaste ahí la salida de "
            f"Normalizar_historia_academica.py / Normalizar_profesores.py? Revisa el README."
        )
    return pd.read_parquet(ruta)


def _clasificar_modalidad(cod_unidad):
    """Idéntica a la de normalizar_docencia.py -- PT es siempre Distancia,
    AP/EP siempre Presencial, cualquier otro caso mira el 3er carácter
    (D/V/P). Los códigos con 'S' u otro 3er carácter no cubierto quedan en
    blanco a propósito (pendiente de confirmar qué significa 'S')."""
    if pd.isna(cod_unidad):
        return None
    codigo = str(cod_unidad).strip().upper()
    prefijo2 = codigo[:2]
    caracter3 = codigo[2:3]
    if prefijo2 == "PT":
        return "Distancia"
    if prefijo2 in ("AP", "EP"):
        return "Presencial"
    return {"D": "Distancia", "V": "Virtual", "P": "Presencial"}.get(caracter3)


def _cargar_tabla_programas(ruta: Path):
    programas = pd.read_excel(ruta, sheet_name="Programas")
    pregrado_2car = pd.read_excel(ruta, sheet_name="Programas_Pregrado_2car")
    tabla_exacta = dict(zip(programas["COD"].str.upper(), programas["NOMBRE"]))
    tabla_pregrado = dict(zip(pregrado_2car["PREFIJO2"].str.upper(), pregrado_2car["NOMBRE"]))
    return tabla_exacta, tabla_pregrado


def _buscar_nombre_programa(cod_unidad, tabla_exacta, tabla_pregrado):
    if pd.isna(cod_unidad):
        return None
    codigo = str(cod_unidad).strip().upper()
    if codigo[:3] in tabla_exacta:
        return tabla_exacta[codigo[:3]]
    return tabla_pregrado.get(codigo[:2])


@st.cache_data(show_spinner="Cargando datos de historia académica…")
def _cargar_historia_cruda(_firma):
    dim_periodo = _leer_parquet(CARPETA_HISTORIA, "dim_periodo")
    dim_materia = _leer_parquet(CARPETA_HISTORIA, "dim_materia")
    dim_estudiante = _leer_parquet(CARPETA_HISTORIA, "dim_estudiante")
    fact_historia_materia = _leer_parquet(CARPETA_HISTORIA, "fact_historia_materia")
    return dim_periodo, dim_materia, dim_estudiante, fact_historia_materia


@st.cache_data(show_spinner="Cargando datos de docencia…")
def _cargar_docencia_cruda(_firma):
    dim_docente = _leer_parquet(CARPETA_DOCENCIA, "dim_docente")
    fact_docencia = _leer_parquet(CARPETA_DOCENCIA, "fact_docencia")
    return dim_docente, fact_docencia


def datos_disponibles() -> dict:
    """Chequeo rápido para mostrar un mensaje claro en pantalla en vez de un
    traceback si a Camilo se le olvidó copiar alguna carpeta."""
    return {
        "historia": CARPETA_HISTORIA.exists() and any(CARPETA_HISTORIA.glob("*.parquet")),
        "docencia": CARPETA_DOCENCIA.exists() and any(CARPETA_DOCENCIA.glob("*.parquet")),
        "programas": RUTA_PROGRAMAS.exists(),
        "territoriales": RUTA_TERRITORIALES.exists(),
    }


# ---------------------------------------------------------------------------
# 3. TRANSFORMACIONES -- el equivalente en pandas de las columnas/medidas DAX
# ---------------------------------------------------------------------------
def _calcular_orden_periodo(dim_periodo: pd.DataFrame) -> pd.DataFrame:
    """Igual que la medida DAX Orden_Periodo: año * 10 + posición dentro del
    año (1=primer período, 3=segundo período, 2=intersemestral -- así un
    intersemestral siempre ordena ENTRE el período 1 y el 2 del mismo año)."""
    dim_periodo = dim_periodo.copy()
    anio = pd.to_numeric(dim_periodo["ANIO"], errors="coerce")
    orden_dentro = np.select(
        [dim_periodo["NUM_PERIODO"] == "1", dim_periodo["NUM_PERIODO"] == "2"],
        [1, 3],
        default=2,
    )
    dim_periodo["ORDEN_PERIODO"] = anio * 10 + orden_dentro
    return dim_periodo.sort_values("ORDEN_PERIODO").reset_index(drop=True)


def _enriquecer_estudiante(dim_estudiante: pd.DataFrame, tabla_exacta, tabla_pregrado,
                            territoriales: pd.DataFrame) -> pd.DataFrame:
    """NOMBRE_PROGRAMA y MODALIDAD (antes LOOKUPVALUE en DAX) + TERRITORIAL/CETAP."""
    dim_estudiante = dim_estudiante.copy()
    dim_estudiante["MODALIDAD"] = dim_estudiante["COD_UNIDAD"].apply(_clasificar_modalidad)
    dim_estudiante["NOMBRE_PROGRAMA"] = dim_estudiante["COD_UNIDAD"].apply(
        lambda c: _buscar_nombre_programa(c, tabla_exacta, tabla_pregrado)
    )
    dim_estudiante = dim_estudiante.merge(
        territoriales, how="left", left_on="COD_UNIDAD", right_on="COD_PRO"
    ).drop(columns=["COD_PRO"])
    return dim_estudiante


def _calcular_resultado_materia(fact: pd.DataFrame, nivel_por_estudiante: pd.Series) -> pd.DataFrame:
    """Igual que la columna calculada DAX Resultado_Materia:
      1) NOM_EST_MATERIA = 'Cancelada'      -> 'Cancelada'
      2) NOM_DEF_HISTORIA en blanco          -> 'Sin nota'
      3) NOM_DEF_HISTORIA >= umbral del nivel -> 'Aprueba'
      4) cualquier otro caso                  -> 'Pierde'
    El umbral (RELATED(dim_estudiante[NIVEL_EDUCATIVO]) en DAX) se resuelve
    aquí con un merge/map contra dim_estudiante."""
    fact = fact.copy()
    nivel = fact["NUM_IDENTIFICACION"].map(nivel_por_estudiante)
    umbral = nivel.map(UMBRAL_APROBACION).fillna(UMBRAL_APROBACION_DEFAULT)

    condiciones = [
        fact["NOM_EST_MATERIA"] == "Cancelada",
        fact["NOM_DEF_HISTORIA"].isna(),
        fact["NOM_DEF_HISTORIA"] >= umbral,
    ]
    fact["RESULTADO_MATERIA"] = np.select(condiciones, ["Cancelada", "Sin nota", "Aprueba"], default="Pierde")

    # Rango_Nota: igual que el histograma en Power BI, bins de 0.5 en 0.5
    bins = [x / 2 for x in range(0, 11)]  # 0, 0.5, 1.0 ... 5.0
    etiquetas = [f"{bins[i]:.1f}–{bins[i+1]:.1f}" for i in range(len(bins) - 1)]
    fact["RANGO_NOTA"] = pd.cut(fact["NOM_DEF_HISTORIA"], bins=bins, labels=etiquetas, include_lowest=True)

    # Numero_Intento + Es_Repitencia
    fact["NUMERO_INTENTO"] = fact["NOM_EST_MATERIA"].map(MAPA_NUMERO_INTENTO)
    fact["ES_REPITENCIA"] = fact["NOM_EST_MATERIA"].fillna("").str.startswith("Repite")

    return fact


@st.cache_data(show_spinner="Preparando historia académica…")
def cargar_historia(_firma_historia, _firma_lookups):
    dim_periodo, dim_materia, dim_estudiante, fact = _cargar_historia_cruda(_firma_historia)

    dim_periodo = _calcular_orden_periodo(dim_periodo)

    tabla_exacta, tabla_pregrado = _cargar_tabla_programas(RUTA_PROGRAMAS)
    territoriales = pd.read_excel(RUTA_TERRITORIALES, sheet_name="Territoriales")
    dim_estudiante = _enriquecer_estudiante(dim_estudiante, tabla_exacta, tabla_pregrado, territoriales)

    nivel_por_estudiante = dim_estudiante.set_index("NUM_IDENTIFICACION")["NIVEL_EDUCATIVO"]
    fact = _calcular_resultado_materia(fact, nivel_por_estudiante)

    # Tabla ancha: 1 fila = 1 materia cursada, con todo lo necesario para
    # filtrar/graficar sin tener que hacer más merges en cada página.
    ancha = (
        fact.merge(
            dim_estudiante[["NUM_IDENTIFICACION", "NIVEL_EDUCATIVO", "NOMBRE_PROGRAMA", "MODALIDAD",
                             "TERRITORIAL", "CETAP"]],
            on="NUM_IDENTIFICACION", how="left",
        )
        .merge(
            dim_materia[["COD_MATERIA_PK", "NOM_MATERIA", "NOM_MATERIA_E"]],
            on="COD_MATERIA_PK", how="left",
        )
        .merge(
            dim_periodo[["COD_PERIODO_PK", "ANIO", "NUM_PERIODO", "ORDEN_PERIODO"]],
            left_on="COD_PERIODO_PK", right_on="COD_PERIODO_PK", how="left",
        )
    )

    columnas_categoricas = [
        "NIVEL_EDUCATIVO", "NOMBRE_PROGRAMA", "MODALIDAD", "TERRITORIAL", "CETAP",
        "RESULTADO_MATERIA", "RANGO_NOTA", "NOM_EST_MATERIA",
    ]
    for c in columnas_categoricas:
        if c in ancha.columns:
            ancha[c] = ancha[c].astype("category")

    return {
        "dim_periodo": dim_periodo,
        "dim_materia": dim_materia,
        "dim_estudiante": dim_estudiante,
        "fact_historia_materia": fact,
        "ancha": ancha,
    }


@st.cache_data(show_spinner="Preparando docencia…")
def cargar_docencia(_firma_docencia, _firma_lookups):
    dim_docente, fact = _cargar_docencia_cruda(_firma_docencia)

    territoriales = pd.read_excel(RUTA_TERRITORIALES, sheet_name="Territoriales")
    fact = fact.merge(territoriales, how="left", left_on="COD_UNIDAD", right_on="COD_PRO").drop(columns=["COD_PRO"])

    # Nombre del docente en la tabla ancha; filas sin IDENTIFICACION_DOCENTE
    # quedan explícitamente marcadas (igual que en Power BI: se ven en los
    # totales, pero no se les puede atribuir a NINGÚN docente puntual).
    dim_docente = dim_docente.copy()
    dim_docente["DOCENTE"] = dim_docente["DOCENTE"].fillna("(Sin identificar)")

    ancha = fact.merge(dim_docente, on="IDENTIFICACION_DOCENTE", how="left")
    ancha["DOCENTE"] = ancha["DOCENTE"].fillna("(Sin identificar)")

    for c in ["NIVEL_EDUCATIVO", "NOMBRE_PROGRAMA", "MODALIDAD", "TERRITORIAL", "CETAP", "DOCENTE"]:
        if c in ancha.columns:
            ancha[c] = ancha[c].astype("category")

    return {"dim_docente": dim_docente, "fact_docencia": fact, "ancha": ancha}


def cargar_todo():
    """Punto de entrada único que llaman las páginas. Calcula la huella de
    cada carpeta primero (barato) para que el caché de Streamlit se invalide
    solo cuando cambien los archivos de datos."""
    firma_historia = _firma_carpeta(CARPETA_HISTORIA)
    firma_docencia = _firma_carpeta(CARPETA_DOCENCIA)
    firma_lookups = _firma_carpeta(RUTA_PROGRAMAS) + _firma_carpeta(RUTA_TERRITORIALES)

    historia = cargar_historia(firma_historia, firma_lookups) if firma_historia else None
    docencia = cargar_docencia(firma_docencia, firma_lookups) if firma_docencia else None
    return historia, docencia


def fecha_ultima_actualizacion():
    """Fecha/hora del archivo de datos más reciente entre historia académica,
    docencia y las dos tablas de referencia -- para mostrar en la barra
    lateral "Datos actualizados: ..." y que cualquiera que abra el tablero
    sepa qué tan fresca es la información, sin tener que ir a revisar GitHub.
    Devuelve None si todavía no hay ningún dato cargado (carpeta data/ vacía)."""
    firmas = (
        _firma_carpeta(CARPETA_HISTORIA)
        + _firma_carpeta(CARPETA_DOCENCIA)
        + _firma_carpeta(RUTA_PROGRAMAS)
        + _firma_carpeta(RUTA_TERRITORIALES)
    )
    if not firmas:
        return None
    ultima_mtime = max(mtime for _nombre, _tamano, mtime in firmas)
    return datetime.fromtimestamp(ultima_mtime, tz=ZONA_HORARIA_COLOMBIA)


# ---------------------------------------------------------------------------
# 4. MEDIDAS -- funciones puras que reciben un dataframe YA FILTRADO y
#    devuelven un número. Así cada página filtra como quiera (programa,
#    modalidad, período...) y las fórmulas de negocio no se repiten ni se
#    desalinean entre páginas.
# ---------------------------------------------------------------------------
def materias_cursadas(df):
    return len(df)


def materias_con_resultado(df):
    return int(df["RESULTADO_MATERIA"].isin(["Aprueba", "Pierde"]).sum())


def tasa_aprobacion(df):
    con_resultado = materias_con_resultado(df)
    if con_resultado == 0:
        return None
    return int((df["RESULTADO_MATERIA"] == "Aprueba").sum()) / con_resultado


def tasa_perdida(df):
    con_resultado = materias_con_resultado(df)
    if con_resultado == 0:
        return None
    return int((df["RESULTADO_MATERIA"] == "Pierde").sum()) / con_resultado


def tasa_repitencia(df):
    cursadas = materias_cursadas(df)
    if cursadas == 0:
        return None
    return int(df["ES_REPITENCIA"].sum()) / cursadas


def intento_promedio_aprobacion(df):
    aprobadas = df.loc[df["RESULTADO_MATERIA"] == "Aprueba", "NUMERO_INTENTO"]
    if aprobadas.empty:
        return None
    return float(aprobadas.mean())


def resumen_por_materia(df):
    """Agregado 1 fila por materia -- lo reutilizan la página de Asignaturas
    (tabla + barras) y la de Dispersión (scatter), para que nunca calculen
    las tasas por su cuenta y terminen desalineadas entre sí."""
    resumen = (
        df.groupby(["COD_MATERIA_PK", "NOM_MATERIA"], observed=True, dropna=False)
        .agg(
            matriculados=("RESULTADO_MATERIA", "size"),
            aprueban=("RESULTADO_MATERIA", lambda s: (s == "Aprueba").sum()),
            pierden=("RESULTADO_MATERIA", lambda s: (s == "Pierde").sum()),
            repiten=("ES_REPITENCIA", "sum"),
        )
        .reset_index()
    )
    resumen["con_resultado"] = resumen["aprueban"] + resumen["pierden"]
    resumen = resumen[resumen["con_resultado"] > 0].copy()
    resumen["tasa_aprobacion"] = resumen["aprueban"] / resumen["con_resultado"]
    resumen["tasa_perdida"] = resumen["pierden"] / resumen["con_resultado"]
    resumen["tasa_repitencia"] = resumen["repiten"] / resumen["matriculados"]
    return resumen


def tasa_perdida_docencia(df):
    """Para Fact_Docencia (ya agregada): DIVIDE(SUM(Pierden), SUM(Matriculados))."""
    matriculados = int(df["MATRICULADOS"].sum())
    if matriculados == 0:
        return None
    return int(df["PIERDEN"].sum()) / matriculados


def tasa_aprobacion_docencia(df):
    matriculados = int(df["MATRICULADOS"].sum())
    if matriculados == 0:
        return None
    return int(df["APRUEBAN"].sum()) / matriculados


def _resumen_agregado_docencia(df, columnas_llave):
    # dropna=False es obligatorio aquí: IDENTIFICACION_DOCENTE viene vacío en
    # algunas filas (ya lo sabíamos, el AVISO de Normalizar_profesores.py lo
    # avisa) y pandas descarta esas filas del groupby por completo si no se
    # lo pides explícitamente -- eso rompía el modo "incluir sin identificar".
    resumen = (
        df.groupby(columnas_llave, observed=True, dropna=False)
        .agg(matriculados=("MATRICULADOS", "sum"), aprueban=("APRUEBAN", "sum"), pierden=("PIERDEN", "sum"))
        .reset_index()
    )
    resumen = resumen[resumen["matriculados"] > 0].copy()
    resumen["tasa_aprobacion"] = resumen["aprueban"] / resumen["matriculados"]
    resumen["tasa_perdida"] = resumen["pierden"] / resumen["matriculados"]
    return resumen


def resumen_por_docente(df, incluir_sin_identificar=False):
    """1 fila por docente. Por defecto excluye '(Sin identificar)' (filas de
    Fact_Docencia sin IDENTIFICACION_DOCENTE) -- no se le puede atribuir una
    alerta de peor docente a nadie en concreto."""
    if not incluir_sin_identificar:
        df = df[df["DOCENTE"] != "(Sin identificar)"]
    return _resumen_agregado_docencia(df, ["IDENTIFICACION_DOCENTE", "DOCENTE"])


def resumen_por_materia_docencia(df):
    """1 fila por materia (usa NOM_MATERIA/COD_MATERIA de Fact_Docencia, que
    es independiente de Dim_Materia de historia académica)."""
    return _resumen_agregado_docencia(df, ["COD_MATERIA", "NOM_MATERIA"])