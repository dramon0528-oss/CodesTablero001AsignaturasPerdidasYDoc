"""
Página "Activos": panorama general de historia académica -- las mismas
medidas clave (Materias Cursadas, Tasa de Aprobación/Pérdida, Repitencia,
Intento Promedio de Aprobación) que ya validamos en Power BI, más su
evolución período a período.

Nota para Camilo: esta es mi mejor aproximación al contenido de tu pestaña
"Activos" original -- no tenía el detalle pixel a pixel de esa pestaña
específica a la mano. Dime qué le falta o qué le sobra y lo ajusto.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import datos
from filtros import filtro_historia
from tema import aplicar_tema, COLOR_APRUEBA, COLOR_PIERDE

st.title("📋 Activos — Historia académica")

disponibles = datos.datos_disponibles()
if not disponibles["historia"]:
    st.error(
        "No encuentro los datos de historia académica en `data/salida_normalizada/`. "
        "Corre `Normalizar_historia_academica.py` y copia esa carpeta ahí (ver README.md)."
    )
    st.stop()

historia, _ = datos.cargar_todo()
ancha = historia["ancha"]

if historia.get("ofertas_excluidas_perdida_total"):
    st.caption(
        f"⚠️ Se omitieron {historia['ofertas_excluidas_perdida_total']} oferta(s) de materia+período "
        f"con 100% de pérdida (probable curso que se ofertó pero no se dictó) -- no se cuentan en "
        f"ninguna cifra de este tablero."
    )

filtrado = filtro_historia(ancha)
st.divider()

# --- KPIs ---------------------------------------------------------------
estudiantes_activos = filtrado["NUM_IDENTIFICACION"].nunique()
cursadas = datos.materias_cursadas(filtrado)
tasa_aprob = datos.tasa_aprobacion(filtrado)
tasa_perd = datos.tasa_perdida(filtrado)
tasa_repi = datos.tasa_repitencia(filtrado)
intento_prom = datos.intento_promedio_aprobacion(filtrado)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Estudiantes en el filtro", f"{estudiantes_activos:,}")
c2.metric("Materias cursadas", f"{cursadas:,}")
c3.metric("Tasa de aprobación", f"{tasa_aprob:.1%}" if tasa_aprob is not None else "—")
c4.metric("Tasa de pérdida", f"{tasa_perd:.1%}" if tasa_perd is not None else "—")
c5.metric("Tasa de repitencia", f"{tasa_repi:.1%}" if tasa_repi is not None else "—")
c6.metric("Intento promedio de aprobación", f"{intento_prom:.2f}" if intento_prom is not None else "—")

st.divider()

# --- Evolución por período ------------------------------------------------
st.markdown("#### Evolución de aprobación y pérdida por período")

evolucion = (
    filtrado.groupby(["COD_PERIODO_PK", "ORDEN_PERIODO"], observed=True, dropna=False)
    .apply(lambda g: pd.Series({
        "Tasa de aprobación": datos.tasa_aprobacion(g),
        "Tasa de pérdida": datos.tasa_perdida(g),
    }), include_groups=False)
    .reset_index()
    .sort_values("ORDEN_PERIODO")
)

if evolucion.empty:
    st.info("No hay datos suficientes para graficar la evolución con los filtros actuales.")
else:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=evolucion["COD_PERIODO_PK"], y=evolucion["Tasa de aprobación"],
        name="Aprobación", marker_color=COLOR_APRUEBA,
        hovertemplate="<b>%{y:.1%}</b> aprobación · %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=evolucion["COD_PERIODO_PK"], y=evolucion["Tasa de pérdida"],
        name="Pérdida", marker_color=COLOR_PIERDE,
        hovertemplate="<b>%{y:.1%}</b> pérdida · %{x}<extra></extra>",
    ))
    fig.update_layout(
        barmode="group",
        xaxis_type="category",  # sin esto, Plotly ve "20181", "20182"... como
                                 # números grandes y los muestra abreviados (20.18k)
        yaxis_tickformat=".0%",
        hovermode="x unified",
    )
    aplicar_tema(fig, altura=380)
    st.plotly_chart(fig, width="stretch")