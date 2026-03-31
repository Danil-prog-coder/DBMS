from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Обязательные
    TELEGRAM_BOT_TOKEN: str
    ANTHROPIC_API_KEY: str

    # Опциональный ALOR OpenAPI
    ALOR_REFRESH_TOKEN: Optional[str] = None

    # URL-адреса API
    MOEX_BASE_URL: str = "https://iss.moex.com/iss"
    ALOR_OAUTH_URL: str = "https://oauth.alor.ru"
    ALOR_API_URL: str = "https://api.alor.ru"

    # Настройки приложения
    DEFAULT_TOP_N: int = 5
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    CACHE_TTL: int = 300  # секунды

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()