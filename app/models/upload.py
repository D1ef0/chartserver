from pydantic import BaseModel
from typing import Any, List, Dict


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]
    column_types: Dict[str, str]
