"""
Страницы для поисковиков и sitemap. Описание схемы — в src/seo.py.

nginx (deploy/nginx-ilsatao.conf), сайт авто живёт в /cars/:
    /cars/, /cars/catalog, /cars/calculator, /cars/blog, /cars/reviews, /cars/about,
    /cars/privacy, /cars/car/*, /cars/blog/*       →  /seo/render/<путь без /cars>
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
            {"@type": "ListItem", "position": i + 1, "name": name, "item": seo.page_url(path)}
            for i, (name, path) in enumerate(items)
        ],
    }


# ---------------- страницы ----------------

async def page_home() -> Response:
    cars = (await _sorted_cars())[:9]
    blogs = _blogs()[-3:][::-1]
    body = (
        seo.nav_html()
        + "<h1>ILSATAO — автомобили из Китая для бизнеса</h1>"
        "<p>Поставки автомобилей из Китая для компаний, дилеров и автосалонов: подбор, проверка, выкуп, "
        "доставка, растаможка на юрлицо и документы для бухгалтерии.</p>"
        '<p><a href="/calculator">Калькулятор растаможки для юрлиц и физлиц</a></p>'
        "<h2>Популярные автомобили</h2>" + seo.car_list_html(cars)
        + '<p><a href="/catalog">Весь каталог автомобилей</a></p>'
        + ("<h2>Статьи</h2><ul>" + "".join(
            f'<li><a href="/blog/{seo.esc(b.get("slug") or b.get("id"))}">{seo.esc(b.get("title"))}</a></li>'
            for b in blogs) + "</ul>" if blogs else "")
    )
    return _html(seo.render_page(
        title="ILSATAO — автомобили из Китая для бизнеса",
        description="Поставки автомобилей из Китая для компаний, дилеров и автосалонов: подбор, выкуп, доставка, "
                    "растаможка на юрлицо. Каталог с ценами и калькулятор растаможки онлайн.",
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
        return RedirectResponse(seo.cars_path(f"/car/{canonical}"), status_code=301)

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
                "url": seo.page_url(f"/car/{canonical}"),
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
            return RedirectResponse(seo.cars_path(f"/blog/{b['slug']}"), status_code=301)
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
            "mainEntityOfPage": seo.page_url(path),
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


async def page_calculator() -> Response:
    body = (
        seo.nav_html()
        + "<h1>Калькулятор растаможки автомобиля из Китая</h1>"
        "<p>Введите данные автомобиля — посчитаем пошлину, НДС, утильсбор и итог под ключ с доставкой. "
        "Для юрлиц ставки отличаются от расчёта для частных лиц.</p>"
        "<h2>Что учитывает расчёт</h2><ul>"
        "<li>Стоимость автомобиля в юанях, долларах, евро или рублях</li>"
        "<li>Год выпуска, тип и объём двигателя, мощность в л.с. или кВт</li>"
        "<li>Таможенный сбор, пошлину, акциз, НДС и утилизационный сбор</li>"
        "<li>Доставку из Китая и итоговую стоимость под ключ, в том числе за партию автомобилей</li>"
        "</ul>"
        "<h2>Кто ввозит</h2><ul>"
        "<li>Юрлицо (ООО или ИП) — для компаний, дилеров и автосалонов</li>"
        "<li>Физлицо для перепродажи</li>"
        "<li>Физлицо для себя</li>"
        "</ul>"
        '<p><a href="/catalog">Каталог автомобилей из Китая с ценами</a></p>'
    )
    return _html(seo.render_page(
        title="Калькулятор растаможки авто из Китая онлайн",
        description="Онлайн-калькулятор растаможки автомобиля из Китая для юрлиц и физлиц: пошлина, НДС, "
                    "утильсбор, доставка и итоговая цена под ключ в рублях.",
        canonical_path="/calculator",
        body_html=body,
        json_ld=_breadcrumbs(("Главная", "/"), ("Калькулятор растаможки", "/calculator")),
    ))


async def page_about() -> Response:
    body = (
        seo.nav_html()
        + "<h1>О компании ILSATAO</h1>"
        "<p>Поставки автомобилей из Китая для бизнеса — без поиска посредников и самостоятельной логистики.</p>"
        "<h2>Не просто найти автомобиль. Найти тот, который стоит покупать.</h2>"
        "<p>Между ценой в объявлении и конечной стоимостью автомобиля в России может быть существенная разница. "
        "Мы сравниваем варианты, уточняем информацию у продавцов, рассчитываем стоимость ввоза и помогаем "
        "выбрать автомобиль, который подходит не только по характеристикам, но и по общему бюджету.</p>"
        "<h2>Китай ближе, чем кажется</h2>"
        "<p>Часть нашей команды находится в Китае: общаемся с продавцами, уточняем детали, организуем осмотры. "
        "В России ведём работу с клиентами, готовим расчёты, согласовываем условия покупки и координируем "
        "дальнейшие этапы.</p>"
        "<h2>Нам важны детали</h2>"
        "<p>До выкупа обсуждаем не только сам автомобиль, но и его проверку, стоимость доставки, "
        "таможенные расходы, порядок платежей и оформления документов.</p>"
        '<p>Телефон: <a href="tel:+79874981737">+7 987 498 17 37</a></p>'
    )
    return _html(seo.render_page(
        title="О компании — поставки автомобилей из Китая",
        description="ILSATAO — поставки автомобилей из Китая для компаний, дилеров и автосалонов. "
                    "Команда в Китае и России: подбор, проверка, выкуп, доставка и растаможка.",
        canonical_path="/about",
        body_html=body,
        json_ld=[seo.ORGANIZATION_LD,
                 _breadcrumbs(("Главная", "/"), ("О компании", "/about"))],
    ))


async def page_privacy() -> Response:
    body = (
        seo.nav_html()
        + "<h1>Политика конфиденциальности</h1>"
        "<p>Настоящая Политика определяет порядок обработки и защиты персональных данных пользователей "
        "сайта ILSATAO. Мы собираем только те данные, которые необходимы для оказания услуг по подбору "
        "и доставке автомобилей из Китая, и обрабатываем их в соответствии с законодательством "
        "Российской Федерации.</p>"
    )
    return _html(seo.render_page(
        title="Политика конфиденциальности",
        description="Порядок обработки и защиты персональных данных пользователей сайта ILSATAO.",
        canonical_path="/privacy",
        body_html=body,
    ))


@router.get("/render/{path:path}")
async def render(path: str = "") -> Response:
    path = path.strip("/")
    if path == "":
        return await page_home()
    if path == "catalog":
        return await page_catalog()
    if path == "calculator":
        return await page_calculator()
    if path == "about":
        return await page_about()
    if path == "privacy":
        return await page_privacy()
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


# ---------------- корень домена: витрина, /box, /bags ----------------
# nginx: /, /box, /bags → /seo/site/_, /seo/site/_box, /seo/site/_bags

def _shop(name: str) -> list[dict]:
    return [i for i in load_json_list(json_path(f"shop_{name}.json")) if i.get("active", True)]


@router.get("/site/{name}")
async def render_site(name: str) -> Response:
    name = name.lstrip("_")
    nav = ('<nav><a href="/">ILSATAO</a> · <a href="/cars/">Авто из Китая</a> · '
           '<a href="/box">Новогодние боксы</a> · <a href="/bags">Сумки</a></nav>')
    if name == "box":
        presets = _shop("box_presets")
        items = _shop("box_items")
        body = (nav + "<h1>Новогодние боксы — собери свой подарок</h1>"
                "<p>Конструктор подарочного бокса: выберите из " + str(len(items)) + " товаров — мандарины, "
                "шоколад, пряники, чай, свечи, пледы. Лимит бокса — 5 кг и 30×30×30 см. "
                "Или возьмите один из готовых боксов.</p><h2>Готовые боксы</h2><ul>"
                + "".join(f"<li><b>{seo.esc(p['name'])}</b> — {seo.esc(p.get('tagline') or '')}</li>" for p in presets)
                + "</ul>")
        return _html(seo.render_page(
            title="Новогодние боксы — конструктор подарков | ILSATAO",
            description="Соберите новогодний подарочный бокс из 40 товаров или выберите готовый: "
                        "мандарины, шоколад, пряники, чай, свечи. Доставка по России.",
            canonical_path="/box", body_html=body, root=True))
    if name == "bags":
        bags = _shop("bags")
        body = (nav + "<h1>Сумки ILSATAO</h1><p>Шоперы, рюкзаки, сумки через плечо, клатчи и дорожные сумки.</p><ul>"
                + "".join(f"<li>{seo.esc(b['name'])} — {seo.esc(b.get('category'))}, "
                          f"{seo.esc(b.get('material') or '')}, {int(b.get('price') or 0):,} ₽</li>".replace(",", " ")
                          for b in bags)
                + "</ul>")
        return _html(seo.render_page(
            title="Сумки — шоперы, рюкзаки, кросс-боди | ILSATAO",
            description="Каталог сумок ILSATAO: шоперы, рюкзаки, сумки через плечо, клатчи и дорожные сумки. "
                        "Заказ онлайн, доставка по России.",
            canonical_path="/bags", body_html=body, root=True))
    body = (nav + "<h1>ILSATAO</h1><ul>"
            "<li><a href=\"/cars/\">Автомобили из Китая для бизнеса</a> — подбор, выкуп, доставка, растаможка</li>"
            "<li><a href=\"/box\">Новогодние боксы</a> — конструктор подарков и готовые наборы</li>"
            "<li><a href=\"/bags\">Сумки</a> — шоперы, рюкзаки, кросс-боди</li></ul>")
    return _html(seo.render_page(
        title="ILSATAO — авто из Китая, новогодние боксы и сумки",
        description="ILSATAO: поставки автомобилей из Китая для бизнеса, конструктор новогодних подарочных боксов "
                    "и каталог сумок.",
        canonical_path="/", body_html=body, root=True))


# ---------------- sitemap ----------------

@router.get("/sitemap.xml")
async def sitemap() -> Response:
    today = date.today().isoformat()
    urls: list[str] = []

    def add(path, priority, changefreq="weekly", lastmod=None, images=(), root=False):
        """path — путь страницы авто без /cars; root=True — путь от корня домена (витрина, /box, /bags)."""
        loc = seo.site_url(path) if root else seo.page_url(path)
        img = "".join(f"<image:image><image:loc>{seo.esc(i)}</image:loc></image:image>" for i in images if i)
        urls.append(
            f"<url><loc>{seo.esc(loc)}</loc>"
            f"<lastmod>{lastmod or today}</lastmod><changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>{img}</url>"
        )

    # Корень домена: витрина и другие разделы (статические страницы проекта ilsatao-site)
    add("/", "1.0", "weekly", root=True)
    add("/box", "0.8", "weekly", root=True)
    add("/bags", "0.8", "weekly", root=True)

    # Сайт авто (/cars/...)
    add("/", "1.0", "daily")
    add("/catalog", "0.9", "daily")
    add("/blog", "0.7")
    add("/reviews", "0.6")
    add("/calculator", "0.7", "monthly")
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
