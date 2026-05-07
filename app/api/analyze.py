from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.dataframe_store import dataframe_store
from app.services.schema_extractor import extract_schema, schema_to_text
from app.services.llm_client import analyze_with_llm
from app.models.llm import AnalysisResponse
from app.core.logging import logger

router = APIRouter()


class AnalyzeRequest(BaseModel):
    file_id: str


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_file(request: AnalyzeRequest):
    df = dataframe_store.get(request.file_id)
    if df is None:
        raise HTTPException(404, "Archivo no encontrado o expirado. Por favor, vuelve a subirlo.")

    try:
        schema = extract_schema(df)
        schema_text = schema_to_text(schema)
        column_names = list(df.columns)

        logger.info(f"Analyzing file_id={request.file_id}, cols={column_names[:5]}...")
        result = analyze_with_llm(schema_text, column_names)
        result.file_id = request.file_id
        return result

    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(500, "Error al analizar el archivo. Intenta de nuevo.")
