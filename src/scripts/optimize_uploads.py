"""
Пережимает УЖЕ загруженные фото и создаёт миниатюры. Имена и форматы файлов
не меняются, поэтому ссылки в базе остаются рабочими.

    # посмотреть, сколько сэкономим (ничего не меняет):
    docker compose exec api python -m src.scripts.optimize_uploads
    # применить (сначала сделайте копию: cp -r storage /root/backup-$(date +%F)):
    docker compose exec api python -m src.scripts.optimize_uploads --apply
"""
import io
import sys

from PIL import Image

from src.config import UPLOAD_DIR
from src.images import MAX_SIDE, _atomic_write, _prepare, make_thumb

MIN_SAVING = 0.15  # пережимаем, только если файл станет меньше хотя бы на 15%


def recompress(path) -> bytes | None:
    ext = path.suffix.lower()
    with Image.open(path) as src:
        if getattr(src, "is_animated", False):
            return None
        img = _prepare(src)
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    out = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(out, "JPEG", quality=85, optimize=True, progressive=True)
    elif ext == ".webp":
        img.save(out, "WEBP", quality=82, method=4)
    elif ext == ".png":
        img.save(out, "PNG", optimize=True)
    else:
        return None
    return out.getvalue()


def main() -> int:
    apply = "--apply" in sys.argv
    before = after = changed = thumbs = 0
    files = sorted(p for p in UPLOAD_DIR.iterdir() if p.is_file() and not p.name.startswith("."))
    for path in files:
        if make_thumb(path):
            thumbs += 1
        size = path.stat().st_size
        before += size
        try:
            data = recompress(path)
        except Exception as e:  # noqa: BLE001
            print(f"  пропуск {path.name}: {e}")
            after += size
            continue
        if data and len(data) < size * (1 - MIN_SAVING):
            changed += 1
            after += len(data)
            print(f"  {path.name}: {size // 1024} КБ → {len(data) // 1024} КБ")
            if apply:
                _atomic_write(path, data)
        else:
            after += size

    print(f"\nФайлов: {len(files)}, миниатюр: {thumbs}, можно пережать: {changed}")
    print(f"Объём: {before / 1048576:.1f} МБ → {after / 1048576:.1f} МБ")
    if not apply:
        print("Это пробный запуск. Чтобы применить: добавьте --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
