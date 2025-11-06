
import os, json, pandas as pd
from functools import lru_cache
from dash import Dash, html, dcc, dash_table, Input, Output, no_update
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
DATA_DIR = os.environ.get("DATA_DIR", "data")
MORTALITY_FILE = os.environ.get("MORTALITY_FILE", "NoFetal2019.xlsx")
CAUSES_FILE = os.environ.get("CAUSES_FILE", "CodigosDeMuerte.xlsx")
DIVIPOLA_FILE = os.environ.get("DIVIPOLA_FILE", "Divipola.xlsx")
GEOJSON_FILE = os.environ.get("GEOJSON_FILE", "colombia_departamentos.geojson")

# Posibles nombres de columnas según EEVV DANE
COLS = {
    "fecha_defuncion": ["FECHA_DEF", "FECHA_OCURR", "FECHA", "FECHA_DEFUNCION"],
    "anio": ["ANO", "AÑO", "ANIO", "YEAR"],
    "mes": ["MES", "MONTH"],
    "depto": ["DPTO", "DPTO_RES", "COD_DPTO", "DEPARTAMENTO", "COD_DEPTO_RES", "COD_DEPARTAMENTO"],
    "depto_nombre": ["DPTO_NOM", "DEPARTAMENTO_NOMBRE", "NOM_DPTO"],
    "muni": ["MUNI", "MUNI_RES", "COD_MPIO", "COD_MUNI_RES", "COD_MUNICIPIO"],
    "muni_nombre": ["MPIO_NOM", "MUNICIPIO", "MUNICIPIO_NOMBRE", "NOM_MPIO"],
    "sexo": ["SEXO", "SEXO_DEF", "SEX"],
    "causa": ["CIE10_DEF", "CAUSA", "COD_CAUSA", "CIE10", "COD_MUERTE"],
    "grupo_edad": ["GRUPO_EDAD1", "GRUPO_EDAD", "GRUPOEDAD1"],
}

# --------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------
def map_age(x: object) -> str:
    """Mapea GRUPO_EDAD1 (códigos DANE) a las categorías pedidas."""
    try:
        v = int(x)
    except:
        return "Desconocido"
    if 0 <= v <= 4:   return "Mortalidad neonatal"
    if 5 <= v <= 6:   return "Mortalidad infantil"
    if 7 <= v <= 8:   return "Primera infancia"
    if 9 <= v <= 10:  return "Niñez"
    if v == 11:       return "Adolescencia"
    if 12 <= v <= 13: return "Juventud"
    if 14 <= v <= 16: return "Adultez temprana"
    if 17 <= v <= 19: return "Adultez intermedia"
    if 20 <= v <= 24: return "Vejez"
    if 25 <= v <= 28: return "Longevidad / Centenarios"
    if v == 29:       return "Edad desconocida"
    return "Desconocido"

def _first_existing_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

# --------------------------------------------------------------------------------------
# Carga de datos (con cache)
# --------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_data():
    mort_path    = os.path.join(DATA_DIR, MORTALITY_FILE)
    causes_path  = os.path.join(DATA_DIR, CAUSES_FILE)
    divipola_path= os.path.join(DATA_DIR, DIVIPOLA_FILE)
    geojson_path = os.path.join(DATA_DIR, GEOJSON_FILE)

    if not os.path.exists(mort_path):
        raise FileNotFoundError(f"No se encontró {mort_path}.")
    if not os.path.exists(causes_path):
        raise FileNotFoundError(f"No se encontró {causes_path}.")
    if not os.path.exists(divipola_path):
        raise FileNotFoundError(f"No se encontró {divipola_path}.")

    # 1) Mortalidad
    df = pd.read_excel(mort_path, engine="openpyxl")

    # 2) Catálogo de causas (intenta CSV limpio primero; si no, parsea Excel del DANE)
    cleaned_csv = os.path.join(DATA_DIR, "CodigosDeMuerte.cleaned.csv")
    if os.path.exists(cleaned_csv):
        causas = pd.read_csv(cleaned_csv, dtype=str)
    else:
        tmp = pd.read_excel(causes_path, sheet_name="Final", header=8, engine="openpyxl")
        tmp.columns = [str(c).strip() for c in tmp.columns]
        causas = tmp.rename(columns={
            "Código de la CIE-10 cuatro caracteres": "COD_CAUSA",
            "Descripcion  de códigos mortalidad a cuatro caracteres": "NOMBRE_CAUSA",
        })

    # 3) DIVIPOLA (departamentos y municipios)
    divipola = pd.read_excel(divipola_path, engine="openpyxl")

    # Normaliza encabezados
    df.columns       = [c.strip().upper() for c in df.columns]
    causas.columns   = [c.strip().upper() for c in causas.columns]
    divipola.columns = [c.strip().upper() for c in divipola.columns]

    # Detecta columnas
    fecha_col = _first_existing_column(df, COLS["fecha_defuncion"])
    anio_col  = _first_existing_column(df, COLS["anio"])
    mes_col   = _first_existing_column(df, COLS["mes"])
    dpto_col  = _first_existing_column(df, COLS["depto"])
    muni_col  = _first_existing_column(df, COLS["muni"])
    sexo_col  = _first_existing_column(df, COLS["sexo"])
    causa_col = _first_existing_column(df, COLS["causa"])
    grupo_col = _first_existing_column(df, COLS["grupo_edad"])

    # Si no hay AÑO/MES explícito, derivar desde FECHA
    if anio_col is None and fecha_col is not None:
        dt = pd.to_datetime(df[fecha_col], errors="coerce")
        df["__YEAR"]  = dt.dt.year
        df["__MONTH"] = dt.dt.month
        anio_col = "__YEAR"
        mes_col  = "__MONTH"

    # Tipos numéricos para columnas clave
    for c in [anio_col, mes_col, dpto_col, muni_col, grupo_col]:
        if c and c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Catálogo de causas (limpio)
    causas = causas[["COD_CAUSA", "NOMBRE_CAUSA"]].dropna()
    causas["COD_CAUSA"] = causas["COD_CAUSA"].astype(str).str.upper().str.strip()

    # DIVIPOLA: columnas más probables
    dpto_code_col = _first_existing_column(divipola, ["COD_DEPTO", "COD_DPTO", "DPTO", "CODIGO_DEPTO", "COD_DEPARTAMENTO"])
    dpto_name_col = _first_existing_column(divipola, ["NOM_DEPTO", "DEPARTAMENTO", "DPTO_NOM"])
    muni_code_col = _first_existing_column(divipola, ["COD_MPIO", "COD_MUNICIPIO", "MUNI", "CODIGO_MPIO"])
    muni_name_col = _first_existing_column(divipola, ["NOM_MPIO", "MUNICIPIO", "MPIO_NOM"])

    div_dpto = divipola[[dpto_code_col, dpto_name_col]].drop_duplicates().rename(
        columns={dpto_code_col: "COD_DEPTO", dpto_name_col: "NOM_DEPTO"}
    )
    div_muni = divipola[[dpto_code_col, muni_code_col, muni_name_col]].drop_duplicates().rename(
        columns={dpto_code_col: "COD_DEPTO", muni_code_col: "COD_MPIO", muni_name_col: "NOM_MPIO"}
    )

    # Dataset estándar para graficar
    std = pd.DataFrame()
    std["ANIO"]        = df[anio_col] if anio_col in df.columns else pd.NA
    std["MES"]         = df[mes_col] if mes_col in df.columns else pd.NA
    std["COD_DEPTO"]   = df[dpto_col] if dpto_col in df.columns else pd.NA
    std["COD_MPIO"]    = df[muni_col] if muni_col in df.columns else pd.NA
    std["SEXO"]        = df[sexo_col] if sexo_col in df.columns else pd.NA
    std["COD_CAUSA"]   = df[causa_col].astype(str).str.upper().str.strip() if causa_col in df.columns else ""
    std["GRUPO_EDAD1"] = df[grupo_col] if grupo_col in df.columns else pd.NA

    # Enriquecimiento con nombres
    std = std.merge(div_dpto, on="COD_DEPTO", how="left")
    std = std.merge(div_muni, on=["COD_DEPTO", "COD_MPIO"], how="left")
    std = std.merge(causas, on="COD_CAUSA", how="left")

    # GeoJSON opcional (fallback a barras si falta)
    if not os.path.exists(geojson_path):
        geojson = None
    else:
        with open(geojson_path, "r", encoding="utf-8") as gjf:
            geojson = json.load(gjf)

    return std, geojson

# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
app = Dash(__name__, title="Mortalidad en Colombia 2019", suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1("Mortalidad en Colombia — 2019"),
    html.Div("Explora patrones demográficos y regionales."),
    html.Div([
        html.Label("Filtrar por año"),
        dcc.Dropdown(id="year-dd", options=[], value=2019, clearable=False),
        html.Label("Código(s) homicidio (coma-separados o rangos X93-X95)"),
        dcc.Input(id="homicide-codes", type="text", value="X93,X94,X95,Y09"),
    ], style={"display": "grid", "gridTemplateColumns": "260px 1fr", "gap": "8px", "maxWidth": "620px"}),

    dcc.Tabs([
        dcc.Tab(label="Mapa por departamento", children=[dcc.Graph(id="mapa-deptos")]),
        dcc.Tab(label="Muertes por mes (línea)", children=[dcc.Graph(id="linea-mensual")]),
        dcc.Tab(label="Top 5 ciudades violentas (barras)", children=[dcc.Graph(id="barras-violencia")]),
        dcc.Tab(label="10 ciudades con menor mortalidad (circular)", children=[dcc.Graph(id="pie-ciudades-menor")]),
        dcc.Tab(label="Top 10 causas (tabla)", children=[dash_table.DataTable(
            id="tabla-causas",
            columns=[
                {"name": "Código", "id": "COD_CAUSA"},
                {"name": "Causa",  "id": "NOMBRE_CAUSA"},
                {"name": "Total",  "id": "TOTAL"},
            ],
            page_size=10,
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"fontWeight": "bold"},
        )]),
        dcc.Tab(label="Muertes por sexo por dpto (apiladas)", children=[dcc.Graph(id="barras-apiladas-sexo")]),
        dcc.Tab(label="Distribución por grupo de edad (histograma)", children=[dcc.Graph(id="histograma-edad")]),
    ]),
    html.Div(id="status-msg", style={"marginTop": "8px", "color": "#555"}),
])

# --------------------------------------------------------------------------------------
# Callbacks
# --------------------------------------------------------------------------------------
@app.callback(
    Output("year-dd", "options"),
    Output("year-dd", "value"),
    Output("status-msg", "children"),
    Input("year-dd", "value"),
)
def init_years(_):
    try:
        df, _ = load_data()
        years = sorted(df["ANIO"].dropna().unique().astype(int).tolist())
        default = 2019 if 2019 in years else (years[-1] if years else None)
        return [{"label": str(y), "value": int(y)} for y in years], default, f"Registros: {len(df):,}"
    except Exception as e:
        return [], None, f"⚠️ {e}"

@app.callback(
    Output("mapa-deptos", "figure"),
    Output("linea-mensual", "figure"),
    Output("barras-violencia", "figure"),
    Output("pie-ciudades-menor", "figure"),
    Output("tabla-causas", "data"),
    Output("barras-apiladas-sexo", "figure"),
    Output("histograma-edad", "figure"),
    Input("year-dd", "value"),
    Input("homicide-codes", "value"),
)
def update_figures(year, homicide_codes):
    try:
        df, geojson = load_data()
    except Exception as e:
        blank = go.Figure().update_layout(title_text=f"Error: {e}")
        return blank, blank, blank, blank, [], blank, blank

    if year is None:
        return no_update
    dff = df[df["ANIO"] == int(year)].copy()

    # ----------------- 1) Mapa por departamento (o barras si falta GeoJSON) -----------------
    tot_depto = dff.groupby(["COD_DEPTO", "NOM_DEPTO"], as_index=False).size().rename(columns={"size": "TOTAL"})
    if geojson is None:
        fig_map = px.bar(
            tot_depto.sort_values("TOTAL", ascending=False),
            x="NOM_DEPTO", y="TOTAL",
            title=f"Total de muertes por departamento — {year} (sin GeoJSON)",
        )
        fig_map.update_xaxes(tickangle=45)
    else:
        fig_map = px.choropleth(
            tot_depto, geojson=geojson, locations="COD_DEPTO",
            featureidkey="properties.COD_DEPTO", color="TOTAL",
            hover_name="NOM_DEPTO", color_continuous_scale="Reds",
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(title=f"Total de muertes por departamento — {year}")

    # ----------------- 2) Línea mensual -----------------
    mens = dff.groupby("MES", as_index=False).size().rename(columns={"size": "TOTAL"}).sort_values("MES")
    fig_line = px.line(mens, x="MES", y="TOTAL", markers=True, title=f"Muertes por mes — {year}")
    fig_line.update_xaxes(dtick=1)

    # ----------------- 3) Barras — Top 5 ciudades más violentas (homicidios) -----------------
    # Acepta lista separada por comas y rangos tipo X93-X95; matchea por prefijo de 3 caracteres
    raw_codes = (homicide_codes or "X93,X94,X95,Y09").upper()
    tokens = [t.strip() for t in raw_codes.split(",") if t.strip()]

    def expand_token(tok: str):
        """Expande rangos tipo 'X93-X95' a ['X93','X94','X95']; caso contrario devuelve [tok]."""
        if "-" in tok and len(tok) == 7:  # p.ej. "X93-X95"
            a, b = tok.split("-")
            if len(a) == 3 and len(b) == 3 and a[0] == b[0]:
                a3, b3 = int(a[1:]), int(b[1:])
                step = 1 if a3 <= b3 else -1
                return [f"{a[0]}{i:02d}" for i in range(a3, b3 + step, step)]
        return [tok]

    codes3 = []
    for t in tokens:
        codes3.extend(expand_token(t))
    codes3 = [c[:3] for c in codes3]  # trabajamos con prefijo de 3 chars (p.ej. X95)

    # Prefijo de 3 chars de COD_CAUSA para capturar X950, X951, etc.
    dff["__COD3"] = dff["COD_CAUSA"].astype(str).str.upper().str.strip().str[:3]
    violentas = dff[dff["__COD3"].isin(codes3)]

    # Agrupar por municipio si hay nombre; si no, por código de municipio; y si tampoco, por dpto
    if "NOM_MPIO" in violentas.columns and violentas["NOM_MPIO"].notna().any():
        top5 = (violentas.groupby(["NOM_MPIO"], as_index=False).size()
                .rename(columns={"size": "TOTAL"})
                .sort_values("TOTAL", ascending=False)
                .head(5))
        x_col = "NOM_MPIO"
        title_scope = "ciudad (municipio)"
    elif "COD_MPIO" in violentas.columns and violentas["COD_MPIO"].notna().any():
        top5 = (violentas.groupby(["COD_MPIO"], as_index=False).size()
                .rename(columns={"size": "TOTAL"})
                .sort_values("TOTAL", ascending=False)
                .head(5))
        x_col = "COD_MPIO"
        title_scope = "municipio (código)"
    else:
        top5 = (violentas.groupby(["NOM_DEPTO"], as_index=False).size()
                .rename(columns={"size": "TOTAL"})
                .sort_values("TOTAL", ascending=False)
                .head(5))
        x_col = "NOM_DEPTO"
        title_scope = "departamento"

    fig_barras_viol = px.bar(
        top5, x=x_col, y="TOTAL",
        title=f"Top 5 {title_scope} por homicidio ({', '.join(codes3)}) — {year}",
    )
    fig_barras_viol.update_layout(xaxis_title=title_scope.capitalize(), yaxis_title="Total")

    # ----------------- 4) Pie — 10 ciudades con menor mortalidad -----------------
    ciudad_tot = dff.groupby(["NOM_MPIO"], as_index=False).size().rename(columns={"size": "TOTAL"})
    bottom10 = ciudad_tot.sort_values("TOTAL", ascending=True).head(10)
    fig_pie = px.pie(bottom10, names="NOM_MPIO", values="TOTAL",
                     title=f"10 ciudades con menor mortalidad — {year}", hole=0.3)

    # ----------------- 5) Tabla — Top 10 causas -----------------
    top_causas = (dff.groupby(["COD_CAUSA", "NOMBRE_CAUSA"], as_index=False).size()
                  .rename(columns={"size": "TOTAL"})
                  .sort_values("TOTAL", ascending=False)
                  .head(10))
    tabla_data = top_causas.to_dict("records")

    # ----------------- 6) Barras apiladas — por sexo y dpto -----------------
    sexo_depto = dff.groupby(["NOM_DEPTO", "SEXO"], as_index=False).size().rename(columns={"size": "TOTAL"})
    fig_apiladas = px.bar(sexo_depto, x="NOM_DEPTO", y="TOTAL", color="SEXO",
                          title=f"Muertes por sexo por dpto — {year}")
    fig_apiladas.update_layout(barmode="stack")
    fig_apiladas.update_xaxes(tickangle=45)

    # ----------------- 7) Histograma — grupo de edad -----------------
    dff["GRUPO_EDAD_LABEL"] = dff["GRUPO_EDAD1"].apply(map_age)
    order = [
        "Mortalidad neonatal", "Mortalidad infantil", "Primera infancia", "Niñez",
        "Adolescencia", "Juventud", "Adultez temprana", "Adultez intermedia",
        "Vejez", "Longevidad / Centenarios", "Edad desconocida",
    ]
    fig_hist = px.histogram(
        dff, x="GRUPO_EDAD_LABEL",
        category_orders={"GRUPO_EDAD_LABEL": order},
        title="Distribución por grupo de edad",
    )
    fig_hist.update_xaxes(tickangle=30)

    return fig_map, fig_line, fig_barras_viol, fig_pie, tabla_data, fig_apiladas, fig_hist

# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)
