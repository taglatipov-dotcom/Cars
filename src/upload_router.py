import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from src.auth import get_current_admin

router = APIRouter(prefix="/upload", tags=["Загрузка файлов"])

# Папка хранения — src/uploads/
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


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

    # Уникальное имя — uuid + исходное расширение
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(contents)

    # Собираем абсолютный URL — фронт сохраняет его как есть
    base = str(request.base_url).rstrip("/")
    return {
        "url": f"{base}/uploads/{filename}",
        "filename": filename,
        "size": len(contents),
    }