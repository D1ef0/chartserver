import io
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.dataframe_store import dataframe_store
from app.core.logging import logger

router = APIRouter()


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
):
    df = dataframe_store.get(file_id)
    if df is None:
        raise HTTPException(404, "Archivo no encontrado o expirado. Por favor, vuelve a subirlo.")

    short_id = file_id[:8]

    if format == "xlsx":
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        logger.info(f"Downloading file_id={file_id} as xlsx")
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="datos_{short_id}.xlsx"'},
        )

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    logger.info(f"Downloading file_id={file_id} as csv")
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="datos_{short_id}.csv"'},
    )
