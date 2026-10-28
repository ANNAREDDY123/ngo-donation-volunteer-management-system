from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NGO Management System"
    database_url: str = "sqlite:///./ngo_management.db"
    secret_key: str = "development-only-change-this-secret-key"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()