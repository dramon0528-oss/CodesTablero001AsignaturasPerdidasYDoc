# Tablero de Seguimiento Académico — ESAP

Reemplazo de Power BI: la misma información (historia académica y alertas de
docencia) como una app web que cualquiera abre con un enlace y una
contraseña compartida, sin instalar nada ni necesitar una licencia.

## 1. Arquitectura: DOS repositorios de GitHub, no uno

Esto es lo más importante de entender antes de tocar nada.

Streamlit Community Cloud (el servicio gratuito donde vive la app) amarra
quién puede VER la app a si el repositorio de GitHub es público o privado.
Si el repositorio es privado, Streamlit exige que invites a cada persona por
correo una por una — exactamente el dolor de cabeza de permisos que
queríamos dejar atrás de Power BI. Si el repositorio es público, cualquiera
con el enlace entra directo (y de ahí para adentro, la contraseña de
`auth.py` es la que de verdad protege el contenido).

La solución: separar el CÓDIGO de los DATOS en dos repositorios distintos.

- **Repositorio de código — PÚBLICO.** Todo lo que hay en esta carpeta
  (`app.py`, `datos.py`, `paginas/`, etc.) menos `data/`. No tiene nada
  sensible — es solo instrucciones de cómo dibujar gráficas — así que no
  pasa nada si es público.
- **Repositorio de datos — PRIVADO, para siempre.** Contiene únicamente los
  archivos reales (`salida_normalizada/`, `salida_docencia/`, las dos
  tablas de referencia). Nunca se conecta a Streamlit directamente; la app
  lo lee en tiempo de ejecución a través de un token que solo puede leer
  ESE repositorio (`sincronizar_datos.py` hace ese trabajo).

**Advertencia importante:** si ya tenías un repositorio con el código Y los
datos juntos (como el que usaste hasta ahora), **no lo vuelvas público**.
Aunque borres `data/` del último commit, el historial de git todavía
guarda esos archivos con datos reales de estudiantes en versiones
anteriores — hacerlo público expondría igual toda esa historia. Crea un
repositorio de código nuevo, desde cero, y deja el viejo privado para
siempre (o bórralo una vez que confirmes que todo funciona en el nuevo).

## 2. Cómo se organizan los datos

Esta app **no reemplaza** tus dos scripts de normalización — los sigue
necesitando exactamente igual que Power BI:

```
Normalizar_historia_academica.py  -->  salida_normalizada/   (5 parquet)
Normalizar_profesores.py          -->  salida_docencia/      (2 parquet)
```

En el **repositorio de DATOS** (el privado), esos archivos van en la RAÍZ
del repositorio — no dentro de una carpeta `data/`:

```
tu-repo-de-datos/              <- este repositorio es privado
├── salida_normalizada/        <- carpeta completa que genera Normalizar_historia_academica.py
├── salida_docencia/           <- carpeta completa que genera Normalizar_profesores.py
├── tabla_programas_normalizada.xlsx
└── tabla_territoriales.xlsx
```

La app arma esto mismo dentro de una carpeta local `data/` automáticamente
(ver `sincronizar_datos.py`) — no tienes que crear esa carpeta a mano en la
nube. Para probar en tu computador sí la creas a mano una vez (siguiente
sección).

## 3. Probarlo en tu computador primero

```bash
pip install -r requirements.txt
```

Crea a mano la carpeta `data/` junto a este `README.md` con la misma
estructura de arriba, y el archivo `.streamlit/secrets.toml` (este NO se
sube nunca a git — ya está en `.gitignore`) con la contraseña que quieras
usar:

```toml
app_password = "escribe-aqui-la-clave-que-quieras"
```

Y arranca la app:

```bash
streamlit run app.py
```

Se abre solo en tu navegador en `http://localhost:8501`. Revisa que las 4
páginas carguen bien contra tus datos reales ANTES de compartir el enlace
con nadie.

*(Tip opcional: si además agregas `github_repo_datos` y `github_token_datos`
a tu `secrets.toml` local — ver siguiente sección — la app también
sincroniza sola desde el repositorio de datos en tu computador, igual que en
la nube. No es obligatorio; copiar `data/` a mano sigue funcionando.)*

## 4. Publicarlo gratis (Streamlit Community Cloud)

### 4.1 Crea el repositorio de DATOS (privado)

1. En GitHub, crea un repositorio nuevo, **privado**, por ejemplo
   `esap-tablero-datos`.
2. Sube ahí `salida_normalizada/`, `salida_docencia/` y las dos tablas de
   referencia, directo en la raíz (estructura de la sección 2).

### 4.2 Crea un token que solo pueda leer ese repositorio

1. Entra a tu perfil de GitHub (esquina superior derecha) → **Settings**.
2. En el menú de la izquierda, **Developer settings**.
3. **Personal access tokens** → **Fine-grained tokens**.
4. **Generate new token**.
5. Ponle un nombre descriptivo, por ejemplo `tablero-esap-lectura-datos`.
6. En **Expiration**, elige la fecha más lejana que te permitan (o
   "Custom" y pones una fecha lejana). Anota en tu calendario renovarlo
   antes de que venza — cuando venza, la app sigue funcionando con los
   últimos datos que alcanzó a traer, pero deja de recibir actualizaciones
   hasta que generes uno nuevo.
7. En **Resource owner**, tu cuenta personal.
8. En **Repository access**, elige **Only select repositories** y
   selecciona `esap-tablero-datos` (el que acabas de crear). Ningún otro
   repositorio tuyo debe quedar seleccionado.
9. En **Permissions**, busca **Contents** y ponlo en **Read-only**. No
   actives ningún otro permiso.
10. **Generate token**.
11. GitHub te muestra el token una sola vez — cópialo antes de salir de esa
    pantalla. Si lo pierdes, no pasa nada grave, simplemente generas otro
    repitiendo estos pasos.

### 4.3 Crea el repositorio de CÓDIGO (público) y despliega

1. Crea un repositorio nuevo en GitHub, **público** esta vez, por ejemplo
   `esap-tablero-app` — **distinto** del que hayas usado antes si ese tenía
   datos reales en su historial (ver advertencia de la sección 1).
2. Sube ahí todo el contenido de esta carpeta **excepto** `data/` (si
   existe localmente, `.gitignore` ya la excluye sola).
3. Entra a **[share.streamlit.io](https://share.streamlit.io)** con tu
   cuenta, autoriza el acceso a este repositorio, y elige "New app".
4. Selecciona el repositorio, la rama, y `app.py` como archivo principal.
5. Antes de darle "Deploy", entra a **"Advanced settings" → "Secrets"** y
   pega:
   ```toml
   app_password = "escribe-aqui-la-clave-que-quieras"
   github_repo_datos = "tu-usuario/esap-tablero-datos"
   github_token_datos = "el-token-que-copiaste-en-4.2"
   ```
6. Dale "Deploy". En un par de minutos te da un enlace parecido a
   `https://tu-app.streamlit.app` — ese es el que envías por correo a los
   gestores, junto con la contraseña (en un correo aparte, nunca en el mismo
   mensaje, es buena práctica).

Como el repositorio de código es público, Streamlit ya no te va a pedir que
invites a nadie por correo — cualquiera con el enlace llega directo a la
pantalla de contraseña.

*(Si ya tenías una app desplegada apuntando al repositorio viejo:
Streamlit Cloud no permite "cambiarle" el repositorio a una app ya creada —
hay que borrar esa app desde su menú de tres puntos → "Delete", y crear una
nueva con estos pasos. Si quieres conservar el mismo enlace, intenta usar el
mismo nombre de subdominio al desplegar la nueva — normalmente queda libre
apenas borras la anterior.)*

La app queda funcionando 24/7 sin costo y sin que tu computador tenga que
estar prendido.

## 5. Actualizar los datos más adelante

Ahora los datos y el código se actualizan por separado:

- **Datos nuevos:** sube (push) los archivos nuevos al repositorio de
  DATOS (`esap-tablero-datos`), no al de código. La app los recoge sola en
  un máximo de 10 minutos, o de inmediato si en la barra lateral le das al
  botón **"🔄 Actualizar datos ahora"**. Si un archivo desaparece del
  repositorio de datos, también desaparece de la app — se mantienen
  siempre en espejo.
- **Cambios de código** (ajustar una gráfica, agregar una página): sube
  esos cambios al repositorio de CÓDIGO (`esap-tablero-app`), igual que
  antes; Streamlit lo redespliega solo.
- **Cambiar la contraseña o el token:** "Settings → Secrets" de tu app en
  share.streamlit.io, edita el valor que corresponda y guarda — se
  reinicia sola.

La barra lateral siempre muestra "📅 Datos actualizados: ..." con la fecha
del archivo más reciente que la app alcanzó a leer, en hora de Colombia —
así cualquiera puede confirmar qué tan fresca es la información sin tener
que preguntarte.

## 6. Qué hace cada archivo

| Archivo | Qué hace |
|---|---|
| `app.py` | Punto de entrada: puerta de contraseña + sincronización de datos + menú de navegación |
| `auth.py` | La contraseña compartida |
| `sincronizar_datos.py` | Trae los datos reales desde el repositorio privado de datos antes de mostrar cualquier página |
| `datos.py` | Carga los parquet/xlsx y aplica toda la lógica que antes vivía en DAX (Resultado_Materia, Orden_Periodo, umbral por nivel, programa/modalidad/territorial, repitencia...) |
| `filtros.py` | La fila de filtros (programa, modalidad, nivel, período) que comparten las páginas |
| `tema.py` | Colores y estilo de todas las gráficas, en un solo lugar |
| `paginas/1_activos.py` | KPIs generales + evolución por período |
| `paginas/2_asignaturas.py` | Aprobación/pérdida por materia, histograma de notas, tabla |
| `paginas/3_dispersion.py` | Pérdida vs. repitencia por materia, en cuadrantes |
| `paginas/4_docencia.py` | Peor docente, peor materia, detalle por docente |

## 7. Nota sobre la página "Activos"

Reconstruí esta página con las medidas que ya habíamos validado (materias
cursadas, aprobación, pérdida, repitencia, intento promedio) más un gráfico
de evolución por período, porque no tenía el detalle exacto de cómo se veía
tu pestaña "Activos" original en Power BI. Si le falta o le sobra algo,
dime qué específicamente y lo ajusto.
