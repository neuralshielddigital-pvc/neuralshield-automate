from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuralShieldDigital API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False
    ENABLE_DOCS: bool = True
    API_PREFIX: str = "/api"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://neuralshield:neuralshield@localhost:5432/neuralshield"
    )

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    PASSWORD_BCRYPT_ROUNDS: int = 12

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STARTER_PRICE_ID: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_ENTERPRISE_PRICE_ID: str = ""

    FRONTEND_SUCCESS_URL: str = "http://localhost:3000/billing/success"
    FRONTEND_CANCEL_URL: str = "http://localhost:3000/billing/cancel"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "NeuralShieldDigital"
    SMTP_USE_TLS: bool = True

    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    TRUSTED_HOSTS: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "*.localhost", "testserver"])
    REQUEST_TIMEOUT_SECONDS: float = 30.0

    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    PUBLIC_LEAD_RATE_LIMIT: int = 10
    PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS: float = 60.0

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"
    REQUEST_ID_HEADER: str = "X-Request-ID"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        return cls._parse_list(value, "BACKEND_CORS_ORIGINS")

    @field_validator("TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, value: Any) -> list[str]:
        return cls._parse_list(value, "TRUSTED_HOSTS")

    @classmethod
    def _parse_list(cls, value: Any, field_name: str) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    raise ValueError(f"{field_name} JSON value must be a list")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        raise ValueError(f"{field_name} must be a list or comma-separated string")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            missing = []
            if self.SECRET_KEY == "change-this-secret-key-in-production" or len(self.SECRET_KEY) < 32:
                missing.append("SECRET_KEY")
            if not self.DATABASE_URL:
                missing.append("DATABASE_URL")
            if missing:
                raise ValueError(f"Production settings missing secure values: {', '.join(missing)}")
        return self

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
