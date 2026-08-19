"""
Página "Asignaturas": aprobación/pérdida por materia, histograma de notas y
tabla detallada. Todo reacciona a los mismos filtros de arriba.
"""

import plotly.graph_objects as go
import streamlit as st

import datos
from filtros import filtro_historia
from tema import aplicar_tema, COLOR_APRUEBA, COLOR_PIERDE

st.title("📚 Asignaturas")

if not datos.datos_disponibles()["historia"]:
    st.error("No encuentro los datos de historia académica en `data/salida_normalizada/`.")
    st.stop()

historia, _ = datos.cargar_todo()
ancha = historia["ancha"]
filtrado = filtro_historia(ancha)
st.divider()

# --- Resumen por materia --------------------------------------------------
resumen = datos.resumen_por_materia(filtrado)

st.markdown("#### Aprobación / pérdida por materia")
col_a, col_b = st.columns(2)
minimo = col_a.number_input("Mínimo de matriculados para incluir la materia", min_value=1, value=10, step=1)
top_n = col_b.slider("Cuántas materias mostrar (las de peor tasa de pérdida primero)", 5, 50, 15)

candidatas = resumen[resumen["matriculados"] >= minimo].sort_values("tasa_perdida", ascending=False)
top = candidatas.head(top_n).sort_values("tasa_perdida")

if top.empty:
    st.info("Ninguna materia cumple el mínimo de matriculados con los filtros actuales.")
else:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top["NOM_MATERIA"], x=top["tasa_aprobacion"], name="Aprobación",
        orientation="h", marker_color=COLOR_APRUEBA,
        hovertemplate="<b>%{x:.1%}</b> aprobación<br>%{y}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=top["NOM_MATERIA"], x=top["tasa_perdida"], name="Pérdida",
        orientation="h", marker_color=COLOR_PIERDE,
        hovertemplate="<b>%{x:.1%}</b> pérdida<br>%{y}<extra></extra>",
    ))
    fig.update_layout(barmode="group", xaxis_tickformat=".0%", height=max(320, 32 * len(top)))
    aplicar_tema(fig)
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- Histograma de notas ---------------------------------------------------
st.markdown("#### Distribución de notas definitivas")
notas = filtrado["NOM_DEF_HISTORIA"].dropna()
if notas.empty:
    st.info("No hay notas para graficar con los filtros actuales.")
else:
    conteo = filtrado["RANGO_NOTA"].value_counts().sort_index()
    fig_hist = go.Figure(go.Bar(
        x=conteo.index.astype(str), y=conteo.values,
        marker_color="#2a78d6",
        hovertemplate="<b>%{y:,}</b> materias · rango %{x}<extra></extra>",
    ))
    fig_hist.update_layout(xaxis_title="Rango de nota", yaxis_title="Materias")
    aplicar_tema(fig_hist, altura=360)
    st.plotly_chart(fig_hist, width="stretch")
    st.caption(
        "El resultado Aprueba/Pierde de cada materia ya aplica el umbral correcto según el "
        "nivel del estudiante (3.0 pregrado / 3.5 posgrado) — este histograma es solo la "
        "distribución de notas en bruto, no re-deriva el resultado a partir de los rangos."
    )

st.divider()

# --- Tabla detallada ---------------------------------------------------
st.markdown("#### Tabla detallada por materia")
tabla = resumen.sort_values("tasa_perdida", ascending=False).rename(columns={
    "NOM_MATERIA": "Materia", "matriculados": "Matriculados", "aprueban": "Aprueban",
    "pierden": "Pierden", "tasa_aprobacion": "Tasa aprobación", "tasa_perdida": "Tasa pérdida",
    "tasa_repitencia": "Tasa repitencia",
})[["Materia", "Matriculados", "Aprueban", "Pierden", "Tasa aprobación", "Tasa pérdida", "Tasa repitencia"]]

# ProgressColumn no multiplica el valor por 100 solo -- se escala aquí para
# que el formato "%.1f%%" muestre "65.0%" en vez de "0.7%".
for col in ["Tasa aprobación", "Tasa pérdida", "Tasa repitencia"]:
    tabla[col] = tabla[col] * 100

st.dataframe(
    tabla,
    width="stretch",
    hide_index=True,
    column_config={
        "Tasa aprobación": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "Tasa pérdida": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "Tasa repitencia": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
    },
)