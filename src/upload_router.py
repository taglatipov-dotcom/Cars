import uuid
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from src.auth import get_current_admin
from src.config import UPLOAD_DIR
from src.images import make_thumb, optimize_upload

router = APIRouter(prefix="/upload", tags=["Загрузка файлов"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Сигнатуры файлов: проверяем, что внутри действительно картинка,
# а не, например, HTML/скрипт с расширением .jpg
_MAGIC = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}


def _looks_like_image(ext: str, contents: bytes) -> bool:
    if ext == ".svg":
        return b"<svg" in contents[:2048].lower()
    sigs = _MAGIC.get(ext)
    if not sigs:
        return False
    ok = any(contents.startswith(s) for s in sigs)
    if ext == ".webp":
        ok = ok and contents[8:12] == b"WEBP"
    return ok

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


def _save_image_sync(contents: bytes, ext: str) -> str:
    """Сжимает (WebP, до 2000 px), сохраняет под uuid-именем и делает миниатюру."""
    data, new_ext = optimize_upload(contents, ext)
    filename = f"{uuid.uuid4().hex}{new_ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(data)
    make_thumb(dest)
    return filename


async def _save_image(contents: bytes, ext: str) -> str:
    # Pillow работает синхронно — уносим в пул потоков, чтобы не блокировать сервер
    return await run_in_threadpool(_save_image_sync, contents, ext)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    _admin: str = Depends(get_current_admin),
) -> dict:
    """Загружает изображение в src/uploads и возвращает абсолютный URL."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Не указано имя файла")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый формат. Разрешены: {allowed}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Файл больше {MAX_FILE_SIZE // (1024 * 1024)} МБ",
        )

    if not _looks_like_image(ext, contents):
        raise HTTPException(status_code=400, detail="Файл не похож на изображение")

    filename = await _save_image(contents, ext)

    # Относительный URL: фронт сам превращает его в /api/uploads/...
    # (раньше тут был http://127.0.0.1:8000/... — внутренний адрес за nginx)
    return {
        "url": f"/uploads/{filename}",
        "filename": filename,
        "size": (UPLOAD_DIR / filename).stat().st_size,
    }

PUBLIC_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PUBLIC_MAX_FILE_SIZE = 3 * 1024 * 1024  # 3 МБ


@router.post("/public", status_code=status.HTTP_201_CREATED)
async def upload_public_image(
    request: Request,
    file: UploadFile = File(...),
) -> dict:
    """
    Публичная загрузка фото к отзыву.
    Без JWT, но с более жёсткими ограничениями:
      • только JPG/PNG/WEBP (без SVG — XSS),
      • максимум 3 МБ.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Не указано имя файла")

    ext = Path(file.filename).suffix.lower()
    if ext not in PUBLIC_ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(PUBLIC_ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый формат. Разрешены: {allowed}",
        )

    contents = await file.read()
    if len(contents) > PUBLIC_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Файл больше {PUBLIC_MAX_FILE_SIZE // (1024 * 1024)} МБ",
        )

    if not _looks_like_image(ext, contents):
        raise HTTPException(status_code=400, detail="Файл не похож на изображение")

    filename = await _save_image(contents, ext)

    return {
        "url": f"/uploads/{filename}",
        "filename": filename,
        "size": (UPLOAD_DIR / filename).stat().st_size,
    }