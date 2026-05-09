from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chaliye:chaliye_secret@localhost:5432/chaliye"
    redis_url: str = "redis://localhost:6379/0"

    psp_base_url: str = "https://httpbin.org/post"  # mock PSP endpoint
    psp_api_key: str = "mock_key"

    new_relic_license_key: str = ""
    new_relic_app_name: str = "chaliye"

    # Matching config
    offer_ttl_seconds: int = 30
    matching_max_attempts: int = 3  # tries at 2km, 5km, 10km

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
