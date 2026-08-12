# backend/config.py
import os
import json
from typing import List, Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Configuration settings for the ULTRON-AI FastAPI Backend."""

    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"
    log_level: str = "INFO"
    cors_origins: Union[List[str], str] = []

    # Secure metadata
    app_title: str = "ULTRON-AI API"
    app_description: str = "Connected AI assistant gateway and remote controller endpoint."
    app_version: str = "1.0.0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Convert comma-separated strings or JSON arrays securely to a List of strings."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [x.strip() for x in v_stripped.split(",") if x.strip()]
        return v

    # Load from .env file securely
    model_config = SettingsConfigDict(
        env_prefix="ultron_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate settings singleton
settings = BackendSettings()
