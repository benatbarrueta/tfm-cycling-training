from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./veloform.db"
    google_client_id: str = ""
    session_secret: str = Field(default="", repr=False)
    frontend_origin: str = "http://localhost:5173"
    session_cookie_name: str = "veloform_session"
    session_ttl_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_runtime(self) -> None:
        if self.app_env != "test" and not self.session_secret:
            raise ValueError("SESSION_SECRET is required outside tests")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
