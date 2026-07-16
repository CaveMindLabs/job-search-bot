# core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Environment setting
    ENVIRONMENT: str = "development"

    # Meta WhatsApp settings
    VERIFY_TOKEN: str
    WHATSAPP_TOKEN: str
    PHONE_NUMBER_ID: str
    WHATSAPP_API_VERSION: str = "v18.0" # Add a default value

    # Memory settings
    MEMORY_HISTORY_LIMIT: int = 20 # Add a default value

    # Google AI Studio settings
    GEMINI_API_KEY: str = ""

    SERPER_API_KEY: str = ""

    # Security
    INTERNAL_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings():
    """
    Returns a cached instance of the Settings class.
    Caching ensures the .env file is read only once.
    """
    return Settings()
