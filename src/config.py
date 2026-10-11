from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# BASE_DIR — папка, где лежит этот файл config.py
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    CALCUS_API_KEY: str = ""
    API_CLIENT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env"
    )

settings = Settings()