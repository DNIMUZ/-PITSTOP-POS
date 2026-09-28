"""Application configuration loaded from environment variables / .env."""
from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "PITSTOP POS"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"  # development | testing | production
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = (
        "postgresql+asyncpg://pitstop:pitstop_dev_password@localhost:5432/pitstop_dev"
    )

    JWT_SECRET: str = "dev-only-change-me-91f8c7e2a4b6d0e3"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8h POS shift

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    TAX_RATE_PERCENT: str = "8.00"  # applied server-side to every sale (retail SST)
    LOGIN_RATE_LIMIT: str = "10/minute"
    # Whether to return {detail: ...} validation body. Always JSON, never raw traces.
    EXPOSE_DOCS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    @property
    def tax_rate_decimal(self) -> Decimal:
        return Decimal(self.TAX_RATE_PERCENT)

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
