from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Blog API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://blog:blog@localhost:5432/blog"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    discord_webhook_url: str | None = None
    discord_uid: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "120/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_secret(self):
        if self.environment == "production" and len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        if not self.jwt_secret_key:
            raise ValueError("Set JWT_SECRET_KEY in your environment or .env file")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
