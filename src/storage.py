"""
Общие функции работы с файловым хранилищем.

Раньше в каждом роутере (blog, reviews, leads) были свои копии
_load/_save. Теперь — одна реализация, и запись атомарная:
сначала пишем во временный файл, потом os.replace(). Если процесс
упадёт посреди записи, старый файл останется целым, а не обрезанным
(обрезанный JSON = сломанный раздел сайта).
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

from src.config import DATA_DIR, JSON_DIR, SEED_JSON_DIR, UPLOAD_DIR


def ensure_storage() -> None:
    """Создаёт папки хранилища и кладёт стартовые JSON, если их нет."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if SEED_JSON_DIR.resolve() == JSON_DIR.resolve():
        return  # локальный режим: хранилище и есть src/data

    if SEED_JSON_DIR.exists():
        for seed in SEED_JSON_DIR.glob("*.json"):
            target = JSON_DIR / seed.name
            if not target.exists():
                shutil.copy2(seed, target)
                print(f"[storage] Создан {target} из стартового файла")


def json_path(name: str) -> Path:
    return JSON_DIR / name


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_json_list(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def next_id(items: list[dict]) -> int:
    return max((i.get("id", 0) for i in items), default=0) + 1
