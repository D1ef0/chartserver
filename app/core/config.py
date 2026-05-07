import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    # Stored as str so pydantic-settings doesn't try JSON-decode comma-separated values
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_file_size_mb: int = 10
    dataframe_ttl_minutes: int = 60
    app_name: str = "Análisis al Instante"

    def get_cors_origins(self) -> list[str]:
        v = self.cors_origins.strip()
        if v.startswith("["):
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]


settings = Settings()
