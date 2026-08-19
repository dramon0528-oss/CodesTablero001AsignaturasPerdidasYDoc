"""
Página "Docencia": peor docente, peor materia y detalle de qué dicta el
docente que selecciones -- igual que ya tenías armado en Power BI.
"""

import plotly.graph_objects as go
import streamlit as st

import datos
from filtros import filtro_docencia
from tema import aplicar_tema, COLOR_PIERDE

st.title("🧑‍🏫 Alertas de docencia")

if not datos.datos_disponibles()["docencia"]:
    st.error(
        "No encuentro los datos de docencia en `data/salida_docencia/`. "
        "Corre `Normalizar_profesores.py` y copia esa carpeta ahí (ver README.md)."
    )
    st.stop()

_, docencia = datos.cargar_todo()
ancha = docencia["ancha"]
filtrado = filtro_docencia(ancha)
st.divider()

# --- KPIs ---------------------------------------------------------------
total_docentes = filtrado.loc[filtrado["DOCENTE"] != "(Sin identificar)", "IDENTIFICACION_DOCENTE"].nunique()
matriculados_total = int(filtrado["MATRICULADOS"].sum())
tasa_aprob = datos.tasa_aprobacion_docencia(filtrado)
tasa_perd = datos.tasa_perdida_docencia(filtrado)
sin_identificar = int(filtrado.loc[filtrado["DOCENTE"] == "(Sin identificar)", "MATRICULADOS"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Docentes", f"{total_docentes:,}")
c2.metric("Matriculados", f"{matriculados_total:,}")
c3.metric("Tasa de aprobación", f"{tasa_aprob:.1%}" if tasa_aprob is not None else "—")
c4.metric("Tasa de pérdida", f"{tasa_perd:.1%}" if tasa_perd is not None else "—")
if sin_identificar:
    st.caption(
        f"⚠️ {sin_identificar:,} matrícula(s) no tienen docente identificado en el archivo de "
        f"origen — se cuentan en los totales de arriba, pero no pueden aparecer en el ranking "
        f"de \"peor docente\" porque no hay a quién atribuírselas."
    )

st.divider()

# --- Peor docente ---------------------------------------------------------
st.markdown("#### Docentes con mayor tasa de pérdida")
col_a, col_b = st.columns(2)
minimo_docente = col_a.number_input("Mínimo de matriculados por docente", min_value=1, value=15, step=1, key="min_docente")
top_n_docente = col_b.slider("Cuántos docentes mostrar", 5, 30, 10, key="top_docente")

resumen_docente = datos.resumen_por_docente(filtrado)
candidatos = resumen_docente[resumen_docente["matriculados"] >= minimo_docente]
peores_docentes = candidatos.sort_values("tasa_perdida", ascending=False).head(top_n_docente).sort_values("tasa_perdida")

if peores_docentes.empty:
    st.info("Ningún docente cumple el mínimo de matriculados con los filtros actuales.")
else:
    fig = go.Figure(go.Bar(
        y=peores_docentes["DOCENTE"], x=peores_docentes["tasa_perdida"], orientation="h",
        marker_color=COLOR_PIERDE,
        customdata=peores_docentes["matriculados"],
        hovertemplate="<b>%{y}</b><br>Pérdida: %{x:.1%}<br>Matriculados: %{customdata:,}<extra></extra>",
    ))
    fig.update_layout(xaxis_tickformat=".0%", xaxis_title="Tasa de pérdida",
                       height=max(320, 32 * len(peores_docentes)))
    aplicar_tema(fig)
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- Peor materia ---------------------------------------------------------
st.markdown("#### Materias con mayor tasa de pérdida (vista docencia)")
col_c, col_d = st.columns(2)
minimo_materia = col_c.number_input("Mínimo de matriculados por materia", min_value=1, value=15, step=1, key="min_materia_doc")
top_n_materia = col_d.slider("Cuántas materias mostrar", 5, 30, 10, key="top_materia_doc")

resumen_materia = datos.resumen_por_materia_docencia(filtrado)
candidatas = resumen_materia[resumen_materia["matriculados"] >= minimo_materia]
peores_materias = candidatas.sort_values("tasa_perdida", ascending=False).head(top_n_materia).sort_values("tasa_perdida")

if peores_materias.empty:
    st.info("Ninguna materia cumple el mínimo de matriculados con los filtros actuales.")
else:
    fig2 = go.Figure(go.Bar(
        y=peores_materias["NOM_MATERIA"], x=peores_materias["tasa_perdida"], orientation="h",
        marker_color=COLOR_PIERDE,
        customdata=peores_materias["matriculados"],
        hovertemplate="<b>%{y}</b><br>Pérdida: %{x:.1%}<br>Matriculados: %{customdata:,}<extra></extra>",
    ))
    fig2.update_layout(xaxis_tickformat=".0%", xaxis_title="Tasa de pérdida",
                        height=max(320, 32 * len(peores_materias)))
    aplicar_tema(fig2)
    st.plotly_chart(fig2, width="stretch")

st.divider()

# --- Drill-down: qué dicta un docente puntual ------------------------------
st.markdown("#### ¿Qué dicta un docente en particular?")
lista_docentes = sorted(resumen_docente["DOCENTE"].unique().tolist())
if not lista_docentes:
    st.info("No hay docentes identificados con los filtros actuales.")
else:
    elegido = st.selectbox("Elige un docente", lista_docentes)
    detalle = (
        filtrado[filtrado["DOCENTE"] == elegido]
        .groupby(["NOM_MATERIA", "NOMBRE_PROGRAMA", "COD_PERIODO"], observed=True, dropna=False)
        .agg(matriculados=("MATRICULADOS", "sum"), aprueban=("APRUEBAN", "sum"), pierden=("PIERDEN", "sum"))
        .reset_index()
    )
    detalle["tasa_perdida"] = (detalle["pierden"] / detalle["matriculados"] * 100).round(1)
    detalle = detalle.rename(columns={
        "NOM_MATERIA": "Materia", "NOMBRE_PROGRAMA": "Programa", "COD_PERIODO": "Período",
        "matriculados": "Matriculados", "aprueban": "Aprueban", "pierden": "Pierden",
        "tasa_perdida": "Tasa pérdida",
    }).sort_values(["Período", "Materia"], ascending=[False, True])

    st.dataframe(
        detalle, width="stretch", hide_index=True,
        column_config={"Tasa pérdida": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)},
    )