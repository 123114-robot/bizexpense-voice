from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    app_environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://bizexpense:bizexpense@localhost:5432/bizexpense"
    )
    cors_origins: str = "http://localhost:5173"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    jwt_secret: str = "development-only-change-me"
    access_token_minutes: int = Field(default=60, ge=5, le=1440)
    refresh_token_days: int = Field(default=30, ge=1, le=365)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    auth_rate_limit_requests: int = Field(default=10, ge=1, le=1000)
    upload_rate_limit_requests: int = Field(default=20, ge=1, le=1000)
    ocr_rate_limit_requests: int = Field(default=30, ge=1, le=1000)

    @model_validator(mode="after")
    def require_production_secret(self):
        if (
            self.app_environment == "production"
            and (
                self.jwt_secret == "development-only-change-me"
                or len(self.jwt_secret) < 32
            )
        ):
            raise ValueError("JWT_SECRET must be configured in production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
