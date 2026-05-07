import io
import numpy as np
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.dataframe_store import dataframe_store
from app.models.upload import UploadResponse
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Extensión no soportada. Usa .csv o .xlsx")

    content = await file.read()

    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(413, f"Archivo demasiado grande. Límite: {settings.max_file_size_mb} MB")

    if len(content) == 0:
        raise HTTPException(400, "El archivo está vacío")

    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(io.BytesIO(content))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        raise HTTPException(422, f"No se pudo leer el archivo: {str(e)}")

    df = df.dropna(how="all")

    if df.empty:
        raise HTTPException(422, "El archivo no contiene datos válidos")

    file_id = dataframe_store.store(df)

    # Build column types
    col_types = {col: str(df[col].dtype) for col in df.columns}

    # Preview: first 5 rows, make serializable
    preview_df = df.head(5).fillna("")
    preview = preview_df.to_dict(orient="records")
    for row in preview:
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                row[k] = int(v)
            elif isinstance(v, (np.floating,)):
                fv = float(v)
                row[k] = None if (np.isnan(fv) or np.isinf(fv)) else fv

    logger.info(f"Uploaded file {filename}: {len(df)} rows, {len(df.columns)} columns")

    return UploadResponse(
        file_id=file_id,
        filename=filename,
        rows=len(df),
        columns=list(df.columns),
        preview=preview,
        column_types=col_types,
    )
