from fastapi import APIRouter, HTTPException
from app.services.dataframe_store import dataframe_store
from app.services.chart_aggregator import get_chart_data
from app.models.chart import ChartDataRequest, ChartDataResponse
from app.core.logging import logger

router = APIRouter()


@router.post("/chart-data", response_model=ChartDataResponse)
async def get_chart(request: ChartDataRequest):
    df = dataframe_store.get(request.file_id)
    if df is None:
        raise HTTPException(404, "Archivo no encontrado o expirado.")

    try:
        result = get_chart_data(df, request.chart_type, request.parameters)
        return ChartDataResponse(**result)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Chart data error: {e}")
        raise HTTPException(500, f"Error al procesar datos del gráfico: {str(e)}")
