"""
Puerta de acceso simple: una sola contraseña compartida para todos los
gestores. No hay cuentas individuales que crear ni mantener -- justo lo que
pediste para no repetir el dolor de cabeza de administrar permisos uno por
uno como en Power BI.

CÓMO CONFIGURAR LA CONTRASEÑA (nunca se escribe directo en el código):
  - En tu computador, mientras pruebas: crea el archivo
    .streamlit/secrets.toml (NO se sube a git, ver .gitignore) con:
        app_password = "la-clave-que-quieras"
  - En Streamlit Community Cloud: se configura desde la web, en
    "Settings" -> "Secrets" de tu app ya desplegada (ver README.md).

Patrón recomendado por la propia documentación de Streamlit (usa hmac.compare_digest
en vez de "==" para comparar la contraseña, así ninguna variación mínima de tiempo
de respuesta puede filtrar información sobre la contraseña real).
"""

import hmac

import streamlit as st


def check_password() -> bool:
    """Devuelve True si ya se ingresó la contraseña correcta en esta sesión
    del navegador. Si no, dibuja el campo de contraseña y devuelve False."""

    def _password_entered():
        try:
            clave_esperada = st.secrets.get("app_password")
        except Exception:
            # st.secrets lanza un error (en vez de devolver None) cuando no
            # existe NINGÚN secrets.toml todavía -- por ejemplo, en una copia
            # local recién clonada antes de configurar nada.
            clave_esperada = None
        if clave_esperada is None:
            st.session_state["password_correct"] = False
            st.session_state["password_missing_secret"] = True
            return
        if hmac.compare_digest(st.session_state.get("password", ""), clave_esperada):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.markdown("## 🔒 Tablero de Seguimiento Académico — ESAP")
    st.text_input(
        "Contraseña",
        type="password",
        on_change=_password_entered,
        key="password",
        placeholder="Ingresa la contraseña que te compartieron por correo",
    )

    if st.session_state.get("password_missing_secret"):
        st.error(
            "No hay ninguna contraseña configurada todavía (falta app_password en "
            "Secrets). Revisa el README antes de compartir el enlace."
        )
    elif "password_correct" in st.session_state:
        st.error("Contraseña incorrecta, intenta de nuevo.")

    return False
