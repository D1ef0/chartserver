# API — Análisis de datos con IA

Backend para análisis de datos asistido por IA. Recibe archivos CSV o XLSX, extrae el esquema de columnas, consulta un modelo de lenguaje para generar sugerencias de visualización, y agrega los datos según el tipo de gráfico solicitado.

No hay base de datos. Los DataFrames se guardan en memoria por proceso con un TTL configurable (por defecto 60 minutos).

---

## Stack

| Paquete | Versión | Rol |
|---|---|---|
| Python | 3.13 | Runtime |
| FastAPI | 0.115.0 | Framework HTTP |
| Uvicorn | 0.30.6 | Servidor ASGI |
| Pydantic | 2.13.3 | Validación y settings |
| Pandas | 3.0.2 | Procesamiento de datos |
| NumPy | 2.4.4 | Cómputo numérico |
| openai | 1.51.0 | Cliente HTTP para el LLM |
| openpyxl | 3.1.5 | Lectura de XLSX |
| python-dotenv | 1.0.1 | Variables de entorno |

---

## Estructura

```
api/
├── app/
│   ├── main.py                  # App FastAPI, CORS, registro de routers
│   ├── api/
│   │   ├── upload.py            # POST /api/upload
│   │   ├── analyze.py           # POST /api/analyze
│   │   ├── chart_data.py        # POST /api/chart-data
│   │   └── download.py          # GET  /api/download/{file_id}
│   ├── core/
│   │   ├── config.py            # Settings via pydantic-settings
│   │   └── logging.py           # Configuración de logs
│   ├── models/
│   │   ├── upload.py            # Schemas de request/response de upload
│   │   ├── llm.py               # Schemas de sugerencias del modelo
│   │   └── chart.py             # Schemas de datos de gráficos
│   └── services/
│       ├── dataframe_store.py   # Store en RAM con TTL
│       ├── schema_extractor.py  # Extrae tipo y estadísticas de columnas
│       ├── llm_client.py        # Llama al modelo con retry y corrección
│       └── chart_aggregator.py  # Agrega datos para bar/line/pie/scatter
├── .env.example
├── .dockerignore
├── Dockerfile
└── requirements.txt
```

---

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

| Variable | Requerida | Descripción |
|---|---|---|
| `OPENROUTER_API_KEY` | Sí | Clave de API del proveedor de LLM |
| `OPENROUTER_MODEL` | No | Modelo a usar (ver `.env.example` para el valor por defecto) |
| `CORS_ORIGINS` | No | Orígenes permitidos (default: `http://localhost:5173,http://localhost:3000`) |
| `MAX_FILE_SIZE_MB` | No | Tamaño máximo de archivo en MB (default: `10`) |
| `DATAFRAME_TTL_MINUTES` | No | Tiempo de vida de los DataFrames en RAM (default: `60`) |
| `APP_NAME` | No | Nombre de la app en logs |

---

## Desarrollo local

### Requisitos previos

- Python 3.13
- Una clave de API configurada en `.env`

### Pasos

```bash
# 1. Crear y activar el entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y completar OPENROUTER_API_KEY

# 4. Levantar el servidor con hot-reload
uvicorn app.main:app --reload --port 8000
```

La API queda disponible en `http://localhost:8000`.  
Documentación interactiva en `http://localhost:8000/docs`.

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/upload` | Sube un CSV o XLSX. Devuelve `file_id` y preview de columnas. |
| `POST` | `/api/analyze` | Recibe `file_id`, extrae schema y consulta el modelo. Devuelve lista de sugerencias de gráficos. |
| `POST` | `/api/chart-data` | Recibe `file_id` + sugerencia. Devuelve datos agregados listos para el frontend. |
| `GET` | `/api/download/{file_id}` | Descarga el archivo original subido. |

### Flujo típico

```
POST /api/upload        →  { file_id, columns, row_count, preview }
POST /api/analyze       →  { suggestions: [{ chart_type, x_column, y_column, title, ... }] }
POST /api/chart-data    →  { data: [...], x_key, y_keys, ... }
GET  /api/download/{id} →  archivo CSV o XLSX
```

---

## Producción con Docker

```bash
# Construir la imagen
docker build -t app-api .

# Correr el contenedor
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=tu-clave \
  -e CORS_ORIGINS=https://tu-dominio.com \
  app-api
```

La variable `PORT` del CMD del Dockerfile permite cambiar el puerto sin reconstruir la imagen:

```bash
docker run -p 9000:9000 -e PORT=9000 -e OPENROUTER_API_KEY=... app-api
```

### Nota importante sobre workers

`DataFrameStore` guarda los DataFrames en memoria del proceso. Si se levantan múltiples workers de Uvicorn (o se usa Gunicorn con múltiples workers), cada worker tiene su propio store y los `file_id` no son compartidos. En producción, usa **un solo worker** o migra el store a Redis/disco si necesitas escalar horizontalmente.

```bash
# Un solo worker (recomendado por ahora)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```
