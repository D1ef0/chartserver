from pydantic import BaseModel
from typing import Optional, List


class ChartParameters(BaseModel):
    x_axis: str
    y_axis: Optional[str] = None
    aggregation: str = "none"


class ChartSuggestion(BaseModel):
    title: str
    chart_type: str  # bar | line | pie | scatter
    parameters: ChartParameters
    insight: str


class AnalysisResponse(BaseModel):
    suggestions: List[ChartSuggestion]
    overall_summary: str
    file_id: str
