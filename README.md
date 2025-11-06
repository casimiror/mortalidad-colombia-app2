# Mortalidad en Colombia — 2019 (Dash)

## 1) Introducción del proyecto
Esta aplicación web, desarrollada con **Dash/Plotly** en **Python**, permite explorar de forma interactiva los microdatos de mortalidad **no fetal** en Colombia (EEVV 2019, DANE). Está pensada como una herramienta accesible para identificar **patrones demográficos y regionales** que faciliten el análisis, la docencia y la toma de decisiones.

## 2) Objetivo
Proveer una interfaz visual que:
- Muestre la **distribución de muertes por departamento** (mapa o barras si no hay GeoJSON).
- Permita estudiar la **estacionalidad** a través de un **gráfico de líneas** con muertes por mes.
- Identifique las **5 ciudades con mayor violencia** (homicidios, configurable por códigos CIE-10).
- Destaque las **10 ciudades con menor mortalidad** (gráfico circular).
- Presente una **tabla con las 10 principales causas de muerte** (código, nombre, total).
- Compare las **muertes por sexo** en cada departamento (barras apiladas).
- Visualice la **distribución por grupo de edad (GRUPO_EDAD1)** remapeada a categorías (neonatal, infantil, vejez, etc.).

## 3) Estructura del proyecto
```
mortalidad-colombia-app/
├─ app.py                    # Código principal de la app (Dash)
├─ requirements.txt          # Dependencias con versiones
├─ render.yaml               # Blueprint para desplegar en Render (PaaS)
├─ Procfile                  # Arranque con gunicorn (opcional para algunos PaaS)
├─ README.md                 # Este archivo
└─ data/                     # Archivos de datos (no versionar si son sensibles)
   ├─ NoFetal2019.xlsx
   ├─ CodigosDeMuerte.xlsx
   ├─ Divipola.xlsx
   ├─ CodigosDeMuerte.cleaned.csv    # Generado opcionalmente para lectura rápida
   └─ colombia_departamentos.geojson # Opcional; activa el mapa coroplético
```

## 4) Requisitos
- **Python 3.10+**
- Librerías (ver `requirements.txt` con versiones):
  - `dash==2.17.1`
  - `plotly==5.24.1`
  - `pandas==2.2.2`
  - `openpyxl==3.1.5`
  - `requests==2.32.3`
  - `gunicorn==22.0.0`

Instalación rápida de dependencias:
```bash
pip install -r requirements.txt
```

## 5) Despliegue (ejemplo en Render)
**Opción A — Blueprint con `render.yaml` (recomendada)**
1. **Sube el proyecto a GitHub** (incluye la carpeta `data/` con los 3 Excel y, si quieres mapa, el GeoJSON).
2. En **Render**: ve a **Blueprints → New Blueprint**, conecta tu repo y confirma la configuración detectada en `render.yaml`.
3. Render construirá e iniciará el servicio. Copia la **URL pública** para tu entrega.

**Opción B — Servicio Web manual**
1. En **Render → New + → Web Service**, conecta el repo.  
2. Configura:
   - _Runtime_: Python
   - _Build Command_: `pip install -r requirements.txt`
   - _Start Command_: `gunicorn app:server`
3. Asegúrate de que `data/` contenga los **3 Excel** y, si usarás mapa, `colombia_departamentos.geojson`.

> **Nota sobre el mapa**: Si el GeoJSON no está presente, la pestaña “Mapa por departamento” mostrará **barras por departamento** (fallback). Con el GeoJSON (que debe incluir `properties.COD_DEPTO` = código DIVIPOLA del departamento), se activará el **coroplético**.

## 6) Software utilizado
- **Python**
- **Dash** (framework web y componentes UI)
- **Plotly** (gráficos interactivos)
- **Pandas** (manejo de datos)
- **OpenPyXL** (lectura de Excel)
- **Requests** (descarga de GeoJSON de referencia)
- **Gunicorn** (servidor WSGI para despliegue)

## 7) Instalación (ejecución local)
1. Clonar el repositorio y entrar al directorio:
   ```bash
   git clone <URL_DE_TU_REPO>.git
   cd mortalidad-colombia-app
   ```
2. (Opcional) Crear y activar entorno virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. **Colocar los datos** en `data/`:
   - `NoFetal2019.xlsx` (EEVV 2019, no fetal)
   - `CodigosDeMuerte.xlsx` (catálogo CIE-10)
   - `Divipola.xlsx` (DIVIPOLA)
   - `colombia_departamentos.geojson` (opcional, para mapa coroplético)
5. Ejecutar la aplicación:
   ```bash
   python app.py
   ```
6. Abrir en el navegador: <http://localhost:8050>

## 8) Visualizaciones con explicaciones de los resultados
Incluye capturas de pantalla en `docs/` y referencia aquí con rutas relativas.

### 8.1 Mapa por departamento (o barras si falta GeoJSON)
- **Qué muestra**: total de muertes por dpto para el año seleccionado.  
- **Cómo leerlo**: coroplético (intensidad = mayor mortalidad). Fallback: barras ordenadas.

### 8.2 Muertes por mes (línea)
- Evolución mensual y estacionalidad del total de muertes.

### 8.3 Top 5 ciudades más violentas (barras)
- Filtra por CIE-10: acepta `X93,X94,X95,Y09` y rangos `X93-X95` (coincidencia por prefijo de 3 caracteres).

### 8.4 10 ciudades con menor mortalidad (circular)
- Menores totales absolutos de mortalidad por municipio.

### 8.5 Top 10 causas de muerte (tabla)
- Código CIE-10, nombre y total de casos.

### 8.6 Muertes por sexo por dpto (barras apiladas)
- Comparación por sexo a nivel departamental.

### 8.7 Distribución por grupo de edad (histograma)
- `GRUPO_EDAD1` remapeado a categorías del ciclo de vida.
