import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import pandas as pd
from app.core.config import settings
from app.core.logging import logger


class DataFrameStore:
    def __init__(self):
        self._store: Dict[str, Tuple[pd.DataFrame, datetime]] = {}

    def store(self, df: pd.DataFrame) -> str:
        file_id = str(uuid.uuid4())
        self._store[file_id] = (df, datetime.utcnow())
        logger.info(f"Stored DataFrame with id={file_id}, shape={df.shape}")
        return file_id

    def get(self, file_id: str) -> Optional[pd.DataFrame]:
        self.cleanup_expired()
        if file_id not in self._store:
            return None
        df, _ = self._store[file_id]
        return df

    def cleanup_expired(self):
        cutoff = datetime.utcnow() - timedelta(minutes=settings.dataframe_ttl_minutes)
        expired = [fid for fid, (_, ts) in self._store.items() if ts < cutoff]
        for fid in expired:
            del self._store[fid]
            logger.info(f"Cleaned up expired DataFrame id={fid}")


dataframe_store = DataFrameStore()
