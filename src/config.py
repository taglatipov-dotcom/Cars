import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Папка с кодом (src/)
BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# ГДЕ ЖИВУТ ДАННЫЕ
# ------------------------------------------------------------
# Всё, что меняется во время работы сайта (база машин, JSON с
# отзывами/заявками/блогом, загруженные картинки), лежит в DATA_DIR.
#
#  • Локально DATA_DIR не задан → используется src/ (как раньше).
#  • В Docker DATA_DIR=/app/storage — это примонтированный volume,
#    который НЕ пересоздаётся при пересборке образа. Именно поэтому
#    база больше не обнуляется при `docker build` + `docker run`.
# ============================================================
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR))).resolve()
DB_PATH = DATA_DIR / "cars.db"
JSON_DIR = DATA_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# Стартовые JSON-файлы, которые лежат в репозитории (src/data).
# Копируются в JSON_DIR только если там такого файла ещё нет.
SEED_JSON_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    CALCUS_API_KEY: str = ""
    API_CLIENT_ID: str = ""
    # Адрес сайта — для ссылок в письмах (раньше был зашит localhost:5173)
    SITE_URL: str = "https://ilsatao.ru"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
