"""
Страницы для поисковиков и sitemap. Описание схемы — в src/seo.py.

nginx (см. nginx.txt):
    /, /catalog, /blog, /reviews, /car/*, /blog/*  →  /seo/render/<путь>
    /sitemap.xml                                   →  /seo/sitemap.xml
"""
import re
from datetime import date

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from src import seo
from src.repository import CarRepository
from src.storage import json_path, load_json_list

router = APIRouter(prefix="/seo", include_in_schema=False)

HTML_HEADERS = {"Cache-Control": "no-cache"}

BODY_TYPES = {"SUV": "Внедорожник", "Sedan": "Седан", "MPV": "Минивэн", "Coupe": "Купе",
              "Hatchback": "Хэтчбек", "Wagon": "Универсал"}

RU_MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7,
             "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}


def parse_ru_date(value: str | None) -> str | None:
    """«12 Мая 2024» / «15 октября 2026» → «2024-05-12»."""
    m = re.match(r"\s*(\d{1,2})\s+([А-Яа-яЁё]+)\s+(\d{4})", value or "")
    if not m:
        return None
    word = m.group(2).lower()
    # «ма» (май/мая) проверяем последним, чтобы не спутать с «март»
    for prefix in sorted(RU_MONTHS, key=len, reverse=True):
        if word.startswith(prefix):
            try:
                return date(int(m.group(3)), RU_MONTHS[prefix], int(m.group(1))).isoformat()
            except ValueError:
                return None
    return None


def _html(page: str | None, status: int = 200) -> Response:
    if page is None:
        # Нет index.html фронтенда — nginx по 503 отдаст обычную SPA-страницу
        return Response("frontend index.html not found", status_code=503)
    return HTMLResponse(page, status_code=status, headers=HTML_HEADERS)


async def _sorted_cars():
    cars = await CarRepository.find_all()
    return sorted(cars, key=lambda c: (c.popularity_rank is None, c.popularity_rank or 0, c.id))


def _blogs() -> list[dict]:
    return load_json_list(json_path("blogs.json"))


def _breadcrumbs(*items: tuple[str, str]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": seo.site_url(path)}
            for i, (name, path) in enumerate(items)
        ],
    }


# ---------------- страницы ----------------

async def page_home() -> Response:
    cars = (await _sorted_cars())[:9]
    blogs = _blogs()[-3:][::-1]
    body = (
        seo.nav_html()
        + "<h1>ILSATAO — автомобили из Китая под ключ</h1>"
        "<p>Подбор, покупка, доставка и растаможка автомобилей из Китая в Россию. "
        "Проверка перед покупкой, прозрачный расчёт стоимости, сопровождение до получения ПТС.</p>"
        "<h2>Популярные автомобили</h2>" + seo.car_list_html(cars)
        + '<p><a href="/catalog">Весь каталог автомобилей</a></p>'
        + ("<h2>Статьи</h2><ul>" + "".join(
            f'<li><a href="/blog/{seo.esc(b.get("slug") or b.get("id"))}">{seo.esc(b.get("title"))}</a></li>'
            for b in blogs) + "</ul>" if blogs else "")
    )
    return _html(seo.render_page(
        title="ILSATAO — автомобили из Китая под ключ",
        description="Подбор, покупка и доставка автомобилей из Китая в Россию под ключ. "
                    "Каталог новых и б/у авто с ценами, расчёт растаможки онлайн.",
        canonical_path="/",
        body_html=body,
        json_ld=seo.ORGANIZATION_LD,
    ))


async def page_catalog() -> Response:
    cars = await _sorted_cars()
    body = (seo.nav_html() + "<h1>Каталог автомобилей из Китая</h1>"
            f"<p>Автомобилей в каталоге: {len(cars)}. Цены указаны в Китае, в юанях; "
            "стоимость под ключ с растаможкой рассчитывается на странице автомобиля.</p>"
            + seo.car_list_html(cars))
    return _html(seo.render_page(
        title="Каталог автомобилей из Китая с ценами",
        description=f"Каталог автомобилей из Китая: {len(cars)} моделей с ценами и характеристиками — "
                    "Zeekr, Li Auto, BYD, Geely, Changan, Jetour и другие. Доставка и растаможка под ключ.",
        canonical_path="/catalog",
        body_html=body,
        image=seo.abs_image(next((c.images[0] for c in cars if c.images), None)),
        json_ld=_breadcrumbs(("Главная", "/"), ("Каталог", "/catalog")),
    ))


async def page_car(slug: str) -> Response:
    car_id = seo.parse_car_id(slug)
    car = await CarRepository.find_by_id(car_id) if car_id else None
    if car is None:
        return _html(seo.render_page(
            title="Автомобиль не найден", description="Автомобиль не найден или уже продан.",
            canonical_path="/catalog", noindex=True,
            body_html=seo.nav_html() + '<h1>Автомобиль не найден</h1><p><a href="/catalog">Перейти в каталог</a></p>',
        ), status=404)

    canonical = seo.car_slug(car)
    if slug != canonical:
        # /car/7 или старое название → постоянный редирект на понятный адрес
        return RedirectResponse(f"/car/{canonical}", status_code=301)

    name = seo.car_name(car)
    # год дописываем, только если его нет в названии («Zeekr 001 2026»)
    year_sfx = f", {car.year}" if car.year and str(car.year) not in name else ""
    images = [u for u in (car.images or car.photos or []) if u]
    engine = car.engine_type if isinstance(car.engine_type, str) else getattr(car.engine_type, "value", car.engine_type)
    drive = car.drive if isinstance(car.drive, str) else getattr(car.drive, "value", car.drive)
    condition = car.condition if isinstance(car.condition, str) else getattr(car.condition, "value", car.condition)

    specs = [
        ("Год выпуска", car.year),
        ("Состояние", {"новая": "Новый", "бу": "С пробегом"}.get(condition, condition)),
        ("Пробег", f"{car.mileage:,} км".replace(",", " ") if car.mileage else None),
        ("Двигатель", engine),
        ("Объём двигателя", f"{car.engine_volume} л" if car.engine_volume else None),
        ("Мощность", f"{car.horsepower} л.с." if car.horsepower else None),
        ("Привод", drive),
        ("Коробка передач", car.transmission),
        ("Кузов", BODY_TYPES.get(car.body_type, car.body_type)),
        ("Цвет", car.color),
        ("Где находится", car.location),
    ]
    rows = "".join(f"<tr><td>{seo.esc(k)}</td><td>{seo.esc(v)}</td></tr>" for k, v in specs if v)
    imgs = "".join(
        f'<img src="{seo.esc(seo.abs_image(u))}" alt="{seo.esc(name)} — фото {i + 1}" loading="lazy" />'
        for i, u in enumerate(images[:6])
    )
    price = seo.price_text(car.china_price)
    description = (car.description or "").strip()

    body = (
        seo.nav_html()
        + f"<h1>{seo.esc(name + year_sfx)}</h1>"
        f"<p><strong>Цена в Китае: {seo.esc(price)}</strong>. Доставка в Россию и растаможка под ключ.</p>"
        f"<table>{rows}</table>"
        + (f"<p>{seo.esc(description)}</p>" if description else "")
        + imgs
        + '<p><a href="/catalog">← Все автомобили в каталоге</a></p>'
    )
    summary = ", ".join(str(v) for v in [engine, f"{car.horsepower} л.с." if car.horsepower else None,
                                         drive and f"{drive} привод"] if v)
    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": ["Product", "Car"],
            "name": name,
            "brand": {"@type": "Brand", "name": car.brend},
            "model": car.model,
            "image": [seo.abs_image(u) for u in images[:6]],
            "description": description or f"{name} из Китая под ключ",
            **({"vehicleModelDate": str(car.year)} if car.year else {}),
            **({"fuelType": engine} if engine else {}),
            **({"mileageFromOdometer": {"@type": "QuantitativeValue", "value": car.mileage, "unitCode": "KMT"}}
               if car.mileage else {}),
            **({"offers": {
                "@type": "Offer",
                "price": car.china_price,
                "priceCurrency": "CNY",
                "availability": "https://schema.org/InStock",
                "url": seo.site_url(f"/car/{canonical}"),
            }} if car.china_price else {}),
        },
        _breadcrumbs(("Главная", "/"), ("Каталог", "/catalog"), (name, f"/car/{canonical}")),
    ]
    return _html(seo.render_page(
        title=f"{name}{year_sfx} — купить из Китая",
        description=f"{name}{year_sfx}"
                    f"{': ' + summary if summary else ''}. Цена в Китае {price}. "
                    "Доставка в Россию и растаможка под ключ — ILSATAO.",
        canonical_path=f"/car/{canonical}",
        body_html=body,
        image=seo.abs_image(images[0]) if images else None,
        og_type="product",
        json_ld=json_ld,
    ))


async def page_blog_list() -> Response:
    blogs = _blogs()[::-1]
    items = "".join(
        f'<li><a href="/blog/{seo.esc(b.get("slug") or b.get("id"))}">{seo.esc(b.get("title"))}</a>'
        f'<br/>{seo.esc(b.get("excerpt"))}</li>' for b in blogs)
    return _html(seo.render_page(
        title="Блог: всё о покупке авто из Китая",
        description="Статьи о покупке, доставке и растаможке автомобилей из Китая: расчёты, сравнения моделей, советы.",
        canonical_path="/blog",
        body_html=seo.nav_html() + "<h1>Блог и новости</h1><ul>" + items + "</ul>",
        json_ld=_breadcrumbs(("Главная", "/"), ("Блог", "/blog")),
    ))


async def page_blog_post(slug: str) -> Response:
    blogs = _blogs()
    if slug.isdigit():
        b = next((x for x in blogs if x.get("id") == int(slug)), None)
        if b and b.get("slug"):
            return RedirectResponse(f"/blog/{b['slug']}", status_code=301)
    else:
        b = next((x for x in blogs if x.get("slug") == slug), None)
    if b is None:
        return _html(seo.render_page(
            title="Статья не найдена", description="Статья не найдена.", canonical_path="/blog", noindex=True,
            body_html=seo.nav_html() + '<h1>Статья не найдена</h1><p><a href="/blog">Все статьи</a></p>',
        ), status=404)

    path = f"/blog/{b.get('slug') or b.get('id')}"
    published = parse_ru_date(b.get("date"))
    image = seo.abs_image(b.get("image"))
    body = (
        seo.nav_html()
        + f"<article><h1>{seo.esc(b.get('title'))}</h1>"
        f"<p>{seo.esc(b.get('author'))} · {seo.esc(b.get('date'))}</p>"
        + (f'<img src="{seo.esc(image)}" alt="{seo.esc(b.get("title"))}" />' if image else "")
        + seo.clean_article_html(b.get("content", ""))
        + "</article>"
    )
    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": b.get("title"),
            "description": b.get("excerpt"),
            **({"image": [image]} if image else {}),
            **({"datePublished": published} if published else {}),
            "author": {"@type": "Organization", "name": b.get("author") or "ILSATAO"},
            "publisher": {"@type": "Organization", "name": "ILSATAO"},
            "mainEntityOfPage": seo.site_url(path),
        },
        _breadcrumbs(("Главная", "/"), ("Блог", "/blog"), (b.get("title") or "Статья", path)),
    ]
    return _html(seo.render_page(
        title=b.get("title") or "Статья",
        description=b.get("excerpt") or "",
        canonical_path=path,
        body_html=body,
        image=image,
        og_type="article",
        json_ld=json_ld,
    ))


async def page_reviews() -> Response:
    reviews = load_json_list(json_path("reviews.json"))[::-1]
    items = "".join(
        f"<li><strong>{seo.esc(r.get('name'))}</strong> — {seo.esc(r.get('car'))}, "
        f"оценка {seo.esc(r.get('rating'))}/5<br/>{seo.esc(r.get('text'))}</li>" for r in reviews)
    return _html(seo.render_page(
        title="Отзывы клиентов",
        description="Отзывы клиентов ILSATAO о покупке и доставке автомобилей из Китая.",
        canonical_path="/reviews",
        body_html=seo.nav_html() + "<h1>Отзывы клиентов</h1><ul>" + items + "</ul>",
    ))


@router.get("/render/{path:path}")
async def render(path: str = "") -> Response:
    path = path.strip("/")
    if path == "":
        return await page_home()
    if path == "catalog":
        return await page_catalog()
    if path == "blog":
        return await page_blog_list()
    if path == "reviews":
        return await page_reviews()
    if path.startswith("car/"):
        return await page_car(path[4:])
    if path.startswith("blog/"):
        return await page_blog_post(path[5:])
    # Остальные страницы — обычный index.html
    return _html(seo.load_index_html())


@router.get("/render")
async def render_root() -> Response:
    return await page_home()


# ---------------- sitemap ----------------

@router.get("/sitemap.xml")
async def sitemap() -> Response:
    today = date.today().isoformat()
    urls: list[str] = []

    def add(path, priority, changefreq="weekly", lastmod=None, images=()):
        img = "".join(f"<image:image><image:loc>{seo.esc(i)}</image:loc></image:image>" for i in images if i)
        urls.append(
            f"<url><loc>{seo.esc(seo.site_url(path))}</loc>"
            f"<lastmod>{lastmod or today}</lastmod><changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>{img}</url>"
        )

    add("/", "1.0", "daily")
    add("/catalog", "0.9", "daily")
    add("/blog", "0.7")
    add("/reviews", "0.6")
    add("/about", "0.5", "monthly")
    add("/privacy", "0.2", "yearly")

    for car in await _sorted_cars():
        imgs = [seo.abs_image(u) for u in (car.images or car.photos or [])[:5]]
        add(f"/car/{seo.car_slug(car)}", "0.8", "weekly", images=imgs)

    for b in _blogs():
        add(f"/blog/{b.get('slug') or b.get('id')}", "0.6", "monthly",
            lastmod=parse_ru_date(b.get("date")), images=[seo.abs_image(b.get("image"))])

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(urls) + "\n</urlset>\n"
    )
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "max-age=3600"})
