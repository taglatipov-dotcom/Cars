"""
GET /uploads/thumbs/<имя>.webp — миниатюра. Если её ещё нет (старые фото),
создаётся при первом запросе и дальше отдаётся как обычный файл.
Маршрут должен быть подключён РАНЬШЕ, чем app.mount("/uploads", ...).
"""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.images import THUMB_DIR, find_original, make_thumb

router = APIRouter(include_in_schema=False)

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}\.webp$")
CACHE = {"Cache-Control": "public, max-age=31536000, immutable"}


@router.get("/uploads/thumbs/{name}")
async def thumb(name: str):
    if not NAME_RE.match(name):
        raise HTTPException(status_code=404)
    path = THUMB_DIR / name
    if not path.exists():
        original = find_original(name[:-5])
        if original is None:
            raise HTTPException(status_code=404)
        made = await run_in_threadpool(make_thumb, original)
        if made is None:
            # Не смогли уменьшить — отдаём оригинал, чтобы картинка всё равно показалась
            return FileResponse(original, headers=CACHE)
        path = made
    return FileResponse(path, media_type="image/webp", headers=CACHE)
