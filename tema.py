"""
Tema visual del tablero — paleta validada (accesible para daltonismo, contraste
verificado) tomada del skill de visualización de datos. Un solo lugar para que
todas las páginas usen exactamente los mismos colores; si algún día quieres
cambiar la paleta, este es el único archivo que hay que tocar.

No inventes colores nuevos en las páginas: importa de aquí.
"""

import plotly.graph_objects as go
import plotly.io as pio

# ---------------------------------------------------------------------------
# Identidad de marca -- distinto de la paleta de datos de abajo: esto es el
# azul institucional de la ESAP (tomado por muestreo directo de
# assets/logo_esap.png, no es una aproximación) para "chrome" de interfaz
# -- títulos, pantalla de login -- no para graficar datos.
# ---------------------------------------------------------------------------
AZUL_ESAP = "#003287"

# ---------------------------------------------------------------------------
# Paleta categórica (orden fijo — nunca la reordenes ni la cicles; el orden es
# justo lo que la hace distinguible para daltonismo). Úsala solo cuando las
# categorías NO tengan una lectura de "bueno/malo" propia (para eso existe la
# paleta de estado, más abajo).
# ---------------------------------------------------------------------------
CATEGORICO = [
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 naranja
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 amarillo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 rojo
]

# ---------------------------------------------------------------------------
# Paleta de estado (fija, nunca se reutiliza para "serie 4"): úsala para
# Aprueba/Pierde, alertas, semáforos -- cualquier cosa que sea literalmente
# bueno/malo, no solo "una categoría más".
# ---------------------------------------------------------------------------
ESTADO = {
    "bueno": "#0ca30c",
    "advertencia": "#fab219",
    "grave": "#ec835a",
    "critico": "#d03b3b",
}

# Colores de negocio, construidos sobre la paleta de estado -- así Aprueba
# siempre se ve "bien" y Pierde siempre se ve "mal" en todo el tablero.
COLOR_APRUEBA = ESTADO["bueno"]
COLOR_PIERDE = ESTADO["critico"]
COLOR_CANCELADA = "#898781"   # gris muted -- ni bueno ni malo, es info "neutra"
COLOR_SIN_NOTA = "#c3c2b7"    # gris más claro -- pendiente, no es un resultado

# Rampa secuencial (un solo hue, claro -> oscuro) para magnitudes continuas
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Cromática y tinta del "chrome" del gráfico
SUPERFICIE = "#fcfcfb"
PLANO_PAGINA = "#f9f9f7"
TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
EJE = "#c3c2b7"

FUENTE = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# ---------------------------------------------------------------------------
# Plantilla de Plotly: registrar una vez, usar en todas las figuras con
# fig.update_layout(template="esap")
# ---------------------------------------------------------------------------
_plantilla = go.layout.Template()
_plantilla.layout = go.Layout(
    colorway=CATEGORICO,
    font=dict(family=FUENTE, color=TINTA_PRIMARIA, size=13),
    paper_bgcolor=SUPERFICIE,
    plot_bgcolor=SUPERFICIE,
    title=dict(font=dict(size=16, color=TINTA_PRIMARIA)),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA_SECUNDARIA, size=12),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    xaxis=dict(
        gridcolor=GRIDLINE,
        linecolor=EJE,
        tickfont=dict(color=TINTA_MUTED, size=11),
        title=dict(font=dict(color=TINTA_SECUNDARIA, size=12)),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=GRIDLINE,
        linecolor=EJE,
        tickfont=dict(color=TINTA_MUTED, size=11),
        title=dict(font=dict(color=TINTA_SECUNDARIA, size=12)),
        zeroline=False,
    ),
    margin=dict(l=10, r=10, t=40, b=10),
    hoverlabel=dict(
        bgcolor=SUPERFICIE,
        bordercolor=EJE,
        font=dict(family=FUENTE, color=TINTA_PRIMARIA, size=12),
    ),
)
pio.templates["esap"] = _plantilla
pio.templates.default = "esap"


def aplicar_tema(fig, altura=None):
    """Aplica la plantilla + retoques comunes a cualquier figura de Plotly.
    Llamar SIEMPRE antes de mostrar una figura con st.plotly_chart()."""
    fig.update_layout(template="esap")
    if altura:
        fig.update_layout(height=altura)
    return fig