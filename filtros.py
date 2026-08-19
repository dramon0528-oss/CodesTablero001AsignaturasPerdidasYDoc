"""
Fila de filtros compartida (programa, modalidad, nivel, período). Vive en un
solo lugar para que las 3 páginas de historia académica filtren exactamente
igual -- así los números de una página nunca contradicen a otra.

Las selecciones quedan guardadas en st.session_state con llaves fijas, así
que si eliges un programa en "Asignaturas" y pasas a "Dispersión", el filtro
te espera ya aplicado (igual que en Power BI al sincronizar filtros entre
páginas).
"""

import streamlit as st


def _opciones(df, col):
    if col not in df.columns:
        return []
    return sorted(x for x in df[col].dropna().unique().tolist())


def filtro_historia(ancha):
    st.markdown("##### Filtros")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        programas = st.multiselect(
            "Programa", _opciones(ancha, "NOMBRE_PROGRAMA"), key="f_historia_programa"
        )
    with col2:
        modalidades = st.multiselect(
            "Modalidad", _opciones(ancha, "MODALIDAD"), key="f_historia_modalidad"
        )
    with col3:
        niveles = st.multiselect(
            "Nivel educativo", _opciones(ancha, "NIVEL_EDUCATIVO"), key="f_historia_nivel"
        )
    with col4:
        periodos = (
            ancha[["COD_PERIODO_PK", "ORDEN_PERIODO"]]
            .dropna()
            .drop_duplicates()
            .sort_values("ORDEN_PERIODO")["COD_PERIODO_PK"]
            .tolist()
        )
        rango = None
        if periodos:
            rango = st.select_slider(
                "Período",
                options=periodos,
                value=(periodos[0], periodos[-1]),
                key="f_historia_periodo",
            )

    filtrado = ancha
    if programas:
        filtrado = filtrado[filtrado["NOMBRE_PROGRAMA"].isin(programas)]
    if modalidades:
        filtrado = filtrado[filtrado["MODALIDAD"].isin(modalidades)]
    if niveles:
        filtrado = filtrado[filtrado["NIVEL_EDUCATIVO"].isin(niveles)]
    if rango:
        ini, fin = rango
        orden_ini = ancha.loc[ancha["COD_PERIODO_PK"] == ini, "ORDEN_PERIODO"].iloc[0]
        orden_fin = ancha.loc[ancha["COD_PERIODO_PK"] == fin, "ORDEN_PERIODO"].iloc[0]
        filtrado = filtrado[filtrado["ORDEN_PERIODO"].between(orden_ini, orden_fin)]
    return filtrado


def filtro_docencia(ancha):
    st.markdown("##### Filtros")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        programas = st.multiselect(
            "Programa", _opciones(ancha, "NOMBRE_PROGRAMA"), key="f_docencia_programa"
        )
    with col2:
        modalidades = st.multiselect(
            "Modalidad", _opciones(ancha, "MODALIDAD"), key="f_docencia_modalidad"
        )
    with col3:
        niveles = st.multiselect(
            "Nivel educativo", _opciones(ancha, "NIVEL_EDUCATIVO"), key="f_docencia_nivel"
        )
    with col4:
        periodos = sorted(ancha["COD_PERIODO"].dropna().unique().tolist())
        rango = None
        if periodos:
            rango = st.select_slider(
                "Período", options=periodos, value=(periodos[0], periodos[-1]), key="f_docencia_periodo"
            )

    filtrado = ancha
    if programas:
        filtrado = filtrado[filtrado["NOMBRE_PROGRAMA"].isin(programas)]
    if modalidades:
        filtrado = filtrado[filtrado["MODALIDAD"].isin(modalidades)]
    if niveles:
        filtrado = filtrado[filtrado["NIVEL_EDUCATIVO"].isin(niveles)]
    if rango:
        ini, fin = rango
        filtrado = filtrado[filtrado["COD_PERIODO"].between(ini, fin)]
    return filtrado
