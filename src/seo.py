"""
SEO: понятные адреса, готовый HTML для поисковиков, sitemap.

Как это работает
----------------
Сайт — SPA: обычно браузер получает пустой index.html, и всё рисует JavaScript.
Яндекс такие страницы индексирует плохо. Поэтому nginx отправляет запросы
страниц (/, /catalog, /car/..., /blog, /blog/..., /reviews) сюда, а мы
берём собранный index.html фронтенда и вставляем в него:
  • <title>, description, Open Graph, canonical, JSON-LD (Schema.org);
  • готовый HTML-контент страницы внутрь <div id="root">.
Дальше загружается React и рисует страницу как обычно (createRoot заменяет
содержимое #root). Пользователь видит тот же сайт, поисковик — полный текст.

Если бэкенд недоступен, nginx отдаёт обычный index.html (error_page → @spa),
так что сайт продолжает работать.

ВАЖНО: slugify / car_slug повторяют src/utils/slug.js фронтенда.
"""
import html
import json
import re
from pathlib import Path

from src.config import settings

FRONTEND_INDEX = Path(settings.FRONTEND_INDEX) if settings.FRONTEND_INDEX else None

TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(value: str | None) -> str:
    s = "".join(TRANSLIT_MAP.get(ch, ch) for ch in (value or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80].rstrip("-")


def car_name(car) -> str:
    return car.car_name or f"{car.brend} {car.model}".strip()


def car_slug(car) -> str:
    return f"{slugify(car_name(car)) or 'car'}-{car.id}"


def parse_car_id(slug: str) -> int | None:
    m = re.search(r"(\d+)$", slug or "")
    return int(m.group(1)) if m else None


def site_url(path: str = "/") -> str:
    return settings.SITE_URL.rstrip("/") + path


def abs_image(url: str | None) -> str | None:
    """Адрес картинки для og:image / sitemap — всегда абсолютный https."""
    if not url or url.startswith("data:"):
        return None
    i = url.find("/uploads/")
    if i >= 0:
        return site_url(url[i:])
    return url if url.startswith("http") else site_url(url)


def thumb_image(url: str | None) -> str | None:
    """Миниатюра для списков (см. src/images.py)."""
    a = abs_image(url)
    if not a or "/uploads/" not in a or "/uploads/thumbs/" in a:
        return a
    head, name = a.rsplit("/", 1)
    stem = name.rsplit(".", 1)[0]
    return f"{head}/thumbs/{stem}.webp"


# ---------- index.html фронтенда (кешируем по времени изменения) ----------

_index_cache: tuple[float, str] | None = None


def load_index_html() -> str | None:
    global _index_cache
    if not FRONTEND_INDEX or not FRONTEND_INDEX.exists():
        return None
    mtime = FRONTEND_INDEX.stat().st_mtime
    if _index_cache and _index_cache[0] == mtime:
        return _index_cache[1]
    text = FRONTEND_INDEX.read_text(encoding="utf-8")
    _index_cache = (mtime, text)
    return text


# ---------- сборка страницы ----------

def esc(v) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def clean_article_html(content: str) -> str:
    """Неразрывные пробелы → обычные, base64-картинки убираем (раздувают страницу)."""
    content = re.sub(r"(?:&nbsp;| )+", " ", content or "")
    content = re.sub(r"<img\b[^>]*\ssrc=\"data:[^\"]*\"[^>]*>", "", content, flags=re.I)
    return content


PRERENDER_STYLE = """<style>
.seo-prerender{max-width:1100px;margin:0 auto;padding:32px 16px;color:#e2e8f0;
font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;line-height:1.6}
.seo-prerender a{color:#a5b4fc}.seo-prerender h1{font-size:2rem;margin:0 0 16px;color:#fff}
.seo-prerender img{max-width:100%;height:auto;border-radius:12px}
.seo-prerender ul{padding-left:20px}.seo-prerender table{border-collapse:collapse}
.seo-prerender td{padding:2px 12px 2px 0}
</style>"""


def render_page(
    *,
    title: str,
    description: str,
    canonical_path: str,
    body_html: str,
    image: str | None = None,
    og_type: str = "website",
    json_ld: dict | list | None = None,
    noindex: bool = False,
) -> str | None:
    tpl = load_index_html()
    if tpl is None:
        return None

    full_title = f"{title} | ILSATAO" if "ILSATAO" not in title else title
    description = re.sub(r"\s+", " ", description or "").strip()[:300]
    canonical = site_url(canonical_path)

    # Убираем из шаблона мета-теги, которые заменяем
    tpl = re.sub(r"<title>.*?</title>", "", tpl, flags=re.S)
    tpl = re.sub(r'\s*<meta\s+(?:name="description"|property="og:[^"]+")[^>]*>', "", tpl)
    tpl = re.sub(r'\s*<link\s+rel="canonical"[^>]*>', "", tpl)

    head = [
        f"<title>{esc(full_title)}</title>",
        f'<meta name="description" content="{esc(description)}" />',
        f'<link rel="canonical" href="{esc(canonical)}" />',
        '<meta property="og:site_name" content="ILSATAO" />',
        f'<meta property="og:type" content="{og_type}" />',
        f'<meta property="og:title" content="{esc(title)}" />',
        f'<meta property="og:description" content="{esc(description)}" />',
        f'<meta property="og:url" content="{esc(canonical)}" />',
        '<meta property="og:locale" content="ru_RU" />',
    ]
    if image:
        head.append(f'<meta property="og:image" content="{esc(image)}" />')
    if noindex:
        head.append('<meta name="robots" content="noindex" />')
    if json_ld:
        data = json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/")
        head.append(f'<script type="application/ld+json">{data}</script>')
    head.append(PRERENDER_STYLE)

    tpl = tpl.replace("</head>", "  " + "\n  ".join(head) + "\n</head>", 1)
    root = f'<div id="root"><div class="seo-prerender">{body_html}</div></div>'
    tpl = re.sub(r'<div id="root">\s*</div>', lambda _: root, tpl, count=1)
    return tpl


ORGANIZATION_LD = {
    "@context": "https://schema.org",
    "@type": "AutoDealer",
    "name": "ILSATAO",
    "url": "https://ilsatao.ru",
    "telephone": "+7 987 498 17 37",
    "description": "Подбор, покупка и доставка автомобилей из Китая в Россию под ключ",
    "areaServed": "RU",
}


def nav_html() -> str:
    return (
        '<nav><a href="/">Главная</a> · <a href="/catalog">Каталог</a> · '
        '<a href="/blog">Блог</a> · <a href="/reviews">Отзывы</a> · <a href="/about">О нас</a></nav>'
    )


def price_text(price) -> str:
    try:
        return f"{int(price):,}".replace(",", " ") + " ¥" if price else "по запросу"
    except (TypeError, ValueError):
        return "по запросу"


def car_list_html(cars) -> str:
    items = []
    for c in cars:
        img = thumb_image((c.images or c.photos or [None])[0])
        img_html = f'<img src="{esc(img)}" alt="{esc(car_name(c))}" width="320" loading="lazy" /><br/>' if img else ""
        items.append(
            f'<li>{img_html}<a href="/car/{esc(car_slug(c))}">{esc(car_name(c))}</a>'
            f'{", " + esc(c.year) + " г." if c.year else ""} — {esc(price_text(c.china_price))}</li>'
        )
    return "<ul>" + "".join(items) + "</ul>"
