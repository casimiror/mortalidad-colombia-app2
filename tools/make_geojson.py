
# tools/make_geojson.py
import json, os, re, unicodedata, requests, pandas as pd

DATA_DIR = os.environ.get("DATA_DIR", "data")
DIVIPOLA_XLSX = os.path.join(DATA_DIR, "Divipola.xlsx")
OUT_GEOJSON   = os.path.join(DATA_DIR, "colombia_departamentos.geojson")

# Fuente GeoJSON base (departamentos). Puedes cambiar a otra fuente si prefieres.
SRC_URL = "https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_DPTO_POLITICO.geojson"

def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s

def pick(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def main():
    # 1) DIVIPOLA
    divi = pd.read_excel(DIVIPOLA_XLSX, engine="openpyxl")
    divi.columns = [c.strip().upper() for c in divi.columns]

    col_dep_code = pick(divi, ["COD_DEPTO","COD_DPTO","DPTO","CODIGO_DEPTO","COD_DEPARTAMENTO"])
    col_dep_name = pick(divi, ["NOM_DEPTO","DEPARTAMENTO","DPTO_NOM","NOMBRE_DEPTO"])
    if not col_dep_code or not col_dep_name:
        raise SystemExit("No encuentro columnas de código/nombre de departamento en Divipola.xlsx")

    divi_use = divi[[col_dep_code, col_dep_name]].drop_duplicates()
    divi_use = divi_use.rename(columns={col_dep_code:"COD_DEPTO", col_dep_name:"NOM_DEPTO"})
    divi_use["COD_DEPTO"] = pd.to_numeric(divi_use["COD_DEPTO"], errors="coerce").astype("Int64")
    divi_use["NORM_NOM"]  = divi_use["NOM_DEPTO"].map(norm)

    # 2) Descargar GeoJSON base
    print(f"Descargando: {SRC_URL}")
    r = requests.get(SRC_URL, timeout=60)
    r.raise_for_status()
    gjson = r.json()

    # 3) Mapear COD_DEPTO a properties
    CAND_CODE_KEYS = ["COD_DEPTO","DPTO_CCDGO","DPTO","CODIGO_DEPTO","DPTO_CCDGO","MPIO_CDPTO"]
    CAND_NAME_KEYS = ["NOM_DEPTO","DEPARTAMEN","DPTO_CNMBR","DEPARTAMENTO","NOMBRE_DEPTO","NOMBRE_DPT"]

    name_to_code = {row["NORM_NOM"]: int(row["COD_DEPTO"]) for _, row in divi_use.dropna().iterrows()}
    not_matched = 0

    for feat in gjson.get("features", []):
        props = feat.setdefault("properties", {})
        dep_code = None
        dep_name = None

        for k in CAND_CODE_KEYS:
            if k in props and props[k] not in (None, ""):
                try:
                    dep_code = int(str(props[k]).strip())
                    break
                except:
                    pass

        for k in CAND_NAME_KEYS:
            if k in props and props[k]:
                dep_name = str(props[k]).strip()
                break

        if dep_code is not None:
            props["COD_DEPTO"] = dep_code
            continue

        if dep_name:
            key = norm(dep_name)
            if key in name_to_code:
                props["COD_DEPTO"] = name_to_code[key]
                continue

        not_matched += 1

    print(f"Departamentos sin COD_DEPTO asignado: {not_matched}")
    missing = [f for f in gjson.get("features", []) if "COD_DEPTO" not in f.get("properties", {})]
    if missing:
        sample = missing[0].get("properties", {})
        print("Ejemplo de feature sin COD_DEPTO -> properties:", sample)
        raise SystemExit(f"Faltan {len(missing)} features con COD_DEPTO. Revisa normalización de nombres.")

    # 4) Guardar
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(gjson, f, ensure_ascii=False)
    print(f"Listo: {OUT_GEOJSON}")

if __name__ == "__main__":
    main()
