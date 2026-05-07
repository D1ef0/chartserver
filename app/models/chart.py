from pydantic import BaseModel
from typing import Any, List, Dict


class ChartDataRequest(BaseModel):
    file_id: str
    chart_type: str
    parameters: Dict[str, Any]


class ChartDataResponse(BaseModel):
    data: List[Dict[str, Any]]
    x_key: str
    y_keys: List[str]
    chart_type: str
