"""
Обработка картинок: сжатие при загрузке и миниатюры.

• При загрузке JPG/PNG/WEBP: поворот по EXIF, уменьшение до MAX_SIDE по длинной
  стороне, сохранение в WebP. Фото 1440×1920 на 2–3 МБ становится ~250–400 КБ
  почти без видимой разницы. GIF и SVG сохраняются как есть.
• Миниатюры для карточек и списков: /uploads/thumbs/<имя>.webp (до THUMB_SIDE px).
  Создаются при загрузке, а для старых фото — автоматически при первом запросе
  (маршрут в images_router), так что ничего пересчитывать руками не нужно.
"""
import io
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from src.config import UPLOAD_DIR

MAX_SIDE = 2000
QUALITY = 82
THUMB_SIDE = 800
THUMB_QUALITY = 78
THUMB_DIR = UPLOAD_DIR / "thumbs"

PROCESSABLE = {".jpg", ".jpeg", ".png", ".webp"}
ORIGINAL_EXTS = (".webp", ".jpg", ".jpeg", ".png", ".gif")

# Защита от «картинок-бомб» (огромные размеры при маленьком файле)
Image.MAX_IMAGE_PIXELS = 60_000_000


def _prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        return img.convert("RGBA")
    return img.convert("RGB")


def optimize_upload(contents: bytes, ext: str) -> tuple[bytes, str]:
    """
    Сжимает загруженную картинку. Возвращает (байты, расширение).
    Если обработать нельзя (GIF, SVG, битый файл) — возвращает исходник.
    """
    if ext not in PROCESSABLE:
        return contents, ext
    try:
        with Image.open(io.BytesIO(contents)) as src:
            if getattr(src, "is_animated", False):
                return contents, ext
            img = _prepare(src)
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, "WEBP", quality=QUALITY, method=4)
        data = out.getvalue()
        # Уже маленький и хорошо сжатый webp — оставляем как был
        if ext == ".webp" and len(data) >= len(contents):
            return contents, ext
        return data, ".webp"
    except Exception:  # noqa: BLE001 — любой сбой: сохраняем оригинал
        return contents, ext


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def make_thumb(original: Path) -> Path | None:
    """Создаёт миниатюру для файла из uploads. Возвращает путь или None."""
    dst = THUMB_DIR / f"{original.stem}.webp"
    if dst.exists():
        return dst
    if original.suffix.lower() not in ORIGINAL_EXTS:
        return None
    try:
        with Image.open(original) as src:
            img = _prepare(src)
        img.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, "WEBP", quality=THUMB_QUALITY, method=4)
        _atomic_write(dst, out.getvalue())
        return dst
    except Exception:  # noqa: BLE001
        return None


def find_original(stem: str) -> Path | None:
    for ext in ORIGINAL_EXTS:
        p = UPLOAD_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None
