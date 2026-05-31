import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    ENV: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: str = "*"
    AGENT_ADMIN_TOKEN: Optional[str] = None

    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    DATABASE_URL: Optional[str] = None

    # xAI Settings
    XAI_API_KEY: str = ""
    LLM_MODEL: str = "grok-3"
    LLM_BASE_URL: str = "https://api.x.ai/v1"

    # Pipeline Thresholds & Limits
    MIN_VOLUME: float = 10000.0
    MIN_LIQUIDITY: float = 5000.0
    MIN_HOURS_TO_CLOSE: int = 48
    MAX_CANDIDATES_PER_RUN: int = 10
    DEFAULT_CANDIDATES_PER_RUN: int = 7
    MIN_EDGE_TO_PUBLISH: float = 0.08
    MIN_CONFIDENCE_TO_PUBLISH: float = 0.60
    PIPELINE_CADENCE_MINUTES: int = 45
    OUTCOME_CHECK_CADENCE_MINUTES: int = 120

    # Load from .env file if it exists
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def get_cors_origins() -> list[str]:
    if settings.CORS_ORIGINS.strip() == "*":
        return ["*"]
    return [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]
