import json
import re
import time
from typing import Optional, List, Tuple
from openai import OpenAI, RateLimitError
from app.core.config import settings
from app.core.logging import logger
from app.models.llm import AnalysisResponse, ChartSuggestion, ChartParameters


def _get_client(model: Optional[str] = None) -> Tuple[OpenAI, str]:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    return client, model or settings.openrouter_model


def _clean_json(text: str) -> str:
    text = text.strip()
    # Remove markdown code blocks
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


SYSTEM_PROMPT = """Eres un analista de datos experto. Tu trabajo es examinar el schema de un dataset y sugerir las 3 a 5 visualizaciones más interesantes y reveladoras.

Reglas estrictas:
- SIEMPRE devuelves JSON válido siguiendo exactamente el schema indicado
- Sin texto adicional, sin markdown, sin explicaciones fuera del JSON
- Prioriza insights de negocio sobre gráficos genéricos
- EVITA sugerencias triviales tipo histogramas básicos
- Busca relaciones entre columnas, agrupaciones reveladoras, o patrones temporales no obvios
- Solo sugiere chart_type: "bar", "line", "pie", o "scatter"
- Solo menciona columnas que existen en el dataset
- aggregation debe ser: "sum", "count", "avg", o "none"

Devuelve SOLO este JSON (sin nada más):
{
  "suggestions": [
    {
      "title": "Título descriptivo del gráfico",
      "chart_type": "bar|line|pie|scatter",
      "parameters": {
        "x_axis": "nombre_columna_exacto",
        "y_axis": "nombre_columna_exacto_o_null",
        "aggregation": "sum|count|avg|none"
      },
      "insight": "Explicación de 1-2 oraciones de qué revela este gráfico y por qué importa"
    }
  ],
  "overall_summary": "Resumen del dataset en 2-3 oraciones"
}"""

FEW_SHOT_EXAMPLE = """
Ejemplo con dataset de ventas (NO uses estas columnas, son solo de referencia):
Dataset: fecha, region, producto, ventas, descuento
Respuesta correcta:
{
  "suggestions": [
    {
      "title": "Rendimiento de ventas por región",
      "chart_type": "bar",
      "parameters": {"x_axis": "region", "y_axis": "ventas", "aggregation": "sum"},
      "insight": "Muestra qué regiones generan más ingresos. Identificar regiones con bajo rendimiento permite priorizar recursos comerciales."
    },
    {
      "title": "Tendencia de ventas mensual",
      "chart_type": "line",
      "parameters": {"x_axis": "fecha", "y_axis": "ventas", "aggregation": "sum"},
      "insight": "Revela estacionalidad y tendencias. Picos inesperados pueden correlacionarse con campañas o eventos externos."
    },
    {
      "title": "Distribución de ventas por producto",
      "chart_type": "pie",
      "parameters": {"x_axis": "producto", "y_axis": "ventas", "aggregation": "sum"},
      "insight": "Identifica los productos que concentran el 80% del ingreso, útil para decisiones de portafolio."
    }
  ],
  "overall_summary": "Dataset de ventas con 3 dimensiones clave: temporal, geográfica y de producto. Permite análisis de tendencias y concentración de ingresos."
}
"""


def _call_llm_raw(schema_text: str, model: str, client: OpenAI, correction_note: str = "") -> str:
    user_content = f"{FEW_SHOT_EXAMPLE}\n\nAhora analiza ESTE dataset:\n\n{schema_text}"
    if correction_note:
        user_content += f"\n\nNOTA: {correction_note}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        timeout=45,
        extra_headers={
            "HTTP-Referer": "https://analisis-instantaneo.com",
            "X-Title": settings.app_name.encode("ascii", "ignore").decode("ascii"),
        },
    )
    return response.choices[0].message.content or ""


def analyze_with_llm(schema_text: str, column_names: List[str]) -> AnalysisResponse:
    client, model = _get_client()
    fallback_model = "openrouter/auto"
    max_retries = 3

    raw_response = ""
    for attempt in range(max_retries):
        try:
            correction = ""
            if attempt == 1:
                correction = "Tu respuesta anterior no era JSON válido. Devuelve SOLO un JSON sin texto adicional, sin bloques de código, sin explicaciones."
            elif attempt == 2:
                correction = "SOLO JSON. Nada más. Empieza con { y termina con }."

            current_model = fallback_model if attempt == 2 else model
            raw_response = _call_llm_raw(schema_text, current_model, client, correction)
            cleaned = _clean_json(raw_response)
            data = json.loads(cleaned)

            suggestions_raw = data.get("suggestions", [])
            valid_suggestions: List[ChartSuggestion] = []

            for s in suggestions_raw:
                try:
                    chart_type = s.get("chart_type", "").lower()
                    if chart_type not in ("bar", "line", "pie", "scatter"):
                        continue
                    params = s.get("parameters", {})
                    x_axis = params.get("x_axis", "")
                    y_axis = params.get("y_axis")

                    if x_axis not in column_names:
                        logger.warning(f"LLM suggested non-existent column: {x_axis}")
                        continue
                    if y_axis and y_axis not in column_names:
                        logger.warning(f"LLM suggested non-existent y column: {y_axis}")
                        y_axis = None

                    aggregation = params.get("aggregation", "none")
                    if aggregation not in ("sum", "count", "avg", "none"):
                        aggregation = "none"

                    valid_suggestions.append(ChartSuggestion(
                        title=s.get("title", "Sin título"),
                        chart_type=chart_type,
                        parameters=ChartParameters(
                            x_axis=x_axis,
                            y_axis=y_axis,
                            aggregation=aggregation,
                        ),
                        insight=s.get("insight", ""),
                    ))
                except Exception as e:
                    logger.warning(f"Skipping invalid suggestion: {e}")

            if len(valid_suggestions) < 2 and attempt < max_retries - 1:
                logger.warning(f"Only {len(valid_suggestions)} valid suggestions, retrying...")
                continue

            return AnalysisResponse(
                suggestions=valid_suggestions[:5],
                overall_summary=data.get("overall_summary", ""),
                file_id="",
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"El modelo no devolvió JSON válido después de {max_retries} intentos")
        except RateLimitError:
            logger.warning("Rate limit hit, waiting 60s...")
            time.sleep(60)
        except Exception as e:
            logger.error(f"LLM error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise

    raise ValueError("No se pudo obtener análisis del LLM")
