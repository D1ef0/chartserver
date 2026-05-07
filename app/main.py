from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.api import upload, analyze, chart_data, download

app = FastAPI(
    title=settings.app_name,
    description="API para análisis de datos con IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


app.include_router(upload.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(chart_data.router, prefix="/api")
app.include_router(download.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
