from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TrainerOS API"
    database_url: str = "postgresql+psycopg://traineros:traineros@localhost:5432/traineros"
    # Dev fallback only; >= 32 bytes for HS256. Always set JWT_SECRET in real envs.
    jwt_secret: str = "insecure-dev-only-secret-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    invite_ttl_days: int = 14
    # Object storage (local backend); swap for S3 via app.storage later.
    storage_dir: str = "./storage-data"
    max_upload_mb: int = 10
    # Comma-separated browser origins allowed to call the API.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
