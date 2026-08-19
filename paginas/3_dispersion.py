"""
Página "Dispersión": pérdida vs. repitencia por materia, en cuadrantes --
cada punto es UNA materia (no un estudiante), del mismo resumen que usa la
página de Asignaturas, así que ambas páginas siempre coinciden en las cifras.
"""

import plotly.graph_objects as go
import streamlit as st

import datos
from filtros import filtro_historia
from tema import aplicar_tema, CATEGORICO, EJE, TINTA_MUTED

st.title("📈 Dispersión — Pérdida vs. repitencia por materia")

if not datos.datos_disponibles()["historia"]:
    st.error("No encuentro los datos de historia académica en `data/salida_normalizada/`.")
    st.stop()

historia, _ = datos.cargar_todo()
ancha = historia["ancha"]
filtrado = filtro_historia(ancha)
st.divider()

minimo = st.number_input("Mínimo de matriculados para incluir la materia", min_value=1, value=10, step=1)
resumen = datos.resumen_por_materia(filtrado)
resumen = resumen[resumen["matriculados"] >= minimo]

if resumen.empty:
    st.info("Ninguna materia cumple el mínimo de matriculados con los filtros actuales.")
    st.stop()

media_perdida = resumen["tasa_perdida"].mean()
media_repitencia = resumen["tasa_repitencia"].mean()

tam_max_px = 42
sizeref = 2.0 * resumen["matriculados"].max() / (tam_max_px ** 2)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=resumen["tasa_perdida"], y=resumen["tasa_repitencia"],
    mode="markers",
    marker=dict(
        size=resumen["matriculados"], sizemode="area", sizeref=sizeref, sizemin=4,
        color=CATEGORICO[0], line=dict(width=1, color="white"),
    ),
    customdata=resumen[["NOM_MATERIA", "matriculados"]],
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Pérdida: %{x:.1%}<br>Repitencia: %{y:.1%}<br>"
        "Matriculados: %{customdata[1]:,}<extra></extra>"
    ),
))

fig.add_hline(y=media_repitencia, line_dash="dash", line_color=EJE)
fig.add_vline(x=media_perdida, line_dash="dash", line_color=EJE)

anotaciones = [
    dict(x=1, y=1, xref="paper", yref="paper", xanchor="right", yanchor="top",
         text="Alta pérdida · alta repitencia", showarrow=False, font=dict(color=TINTA_MUTED, size=11)),
    dict(x=0, y=1, xref="paper", yref="paper", xanchor="left", yanchor="top",
         text="Baja pérdida · alta repitencia", showarrow=False, font=dict(color=TINTA_MUTED, size=11)),
    dict(x=1, y=0, xref="paper", yref="paper", xanchor="right", yanchor="bottom",
         text="Alta pérdida · baja repitencia", showarrow=False, font=dict(color=TINTA_MUTED, size=11)),
    dict(x=0, y=0, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
         text="Baja pérdida · baja repitencia", showarrow=False, font=dict(color=TINTA_MUTED, size=11)),
]
fig.update_layout(
    xaxis_title="Tasa de pérdida", yaxis_title="Tasa de repitencia",
    xaxis_tickformat=".0%", yaxis_tickformat=".0%",
    annotations=anotaciones, showlegend=False,
)
aplicar_tema(fig, altura=560)
st.plotly_chart(fig, width="stretch")

st.caption(
    "El tamaño de cada burbuja es proporcional a los matriculados de esa materia. Las líneas "
    "punteadas marcan el promedio de pérdida y de repitencia entre las materias mostradas — "
    "no un valor fijo — así que cambian si ajustas los filtros o el mínimo de matriculados."
)