# ILSATAO — бэкенд (FastAPI)

API сайта ilsatao.ru: пригон автомобилей из Китая в Россию.
Фронтенд — отдельный репозиторий `CarsFrondend` (React + Vite).
Общаемся и пишем комментарии/сообщения коммитов **на русском**.

## Стек
- Python 3.14, FastAPI, SQLAlchemy 2 (async) + aiosqlite, Pydantic v2 / pydantic-settings
- Авторизация админки: bcrypt-хеш пароля + JWT (HS256), зависимость `get_current_admin`
- Внешний API: calcus.ru (расчёт таможни), aiohttp
- Почта: Яндекс SMTP (smtp.yandex.ru:465, SSL), отправка в BackgroundTasks

## Структура
```
src/
  main.py            приложение, lifespan (ensure_storage + create_tables), CORS, /uploads
  config.py          ВСЕ пути к данным (DATA_DIR, DB_PATH, JSON_DIR, UPLOAD_DIR) и Settings
  storage.py         работа с JSON: load_json_list / save_json_list (атомарно) / next_id
  database.py        модель CarsOrm (таблица cars)
  repository.py      CarRepository — запросы к машинам
  schemas.py         Pydantic-схемы (SCar*, SReview*, SBlog*, SLead*)
  router.py          /cars + /cars/cal (калькулятор таможни)
  blog_router.py     /blog          → data/blogs.json
  reviews_router.py  /reviews       → data/reviews.json, data/pending_reviews.json (модерация)
  leads_router.py    /leads         → data/leads.json + письмо о новой заявке
  upload_router.py   /upload (админ), /upload/public (фото к отзывам, ≤3 МБ, без SVG); сжатие → images.py
  images.py          WebP до 2000 px при загрузке, миниатюры uploads/thumbs/<имя>.webp (800 px)
  images_router.py   GET /uploads/thumbs/<имя>.webp — создаёт миниатюру по запросу (подключать ДО mount /uploads)
  seo.py, seo_router.py  готовый HTML для поисковиков (/seo/render/...), /seo/sitemap.xml, слаги
  auth.py, auth_router.py   /auth/login
  http_client.py     клиент calcus.ru
  data/              СТАРТОВЫЕ JSON (seed): копируются в хранилище, только если там файла нет
  scripts/generate_admin_credentials.py   генерация хеша пароля и JWT-секрета для .env
  scripts/test_email.py       диагностика почты: docker compose exec api python -m src.scripts.test_email
  scripts/optimize_uploads.py пережать старые фото (+ --apply)
tests/
```

## Хранилище данных — главное правило
Все изменяемые данные лежат в `DATA_DIR` (см. `src/config.py`):
`cars.db`, `data/*.json`, `uploads/`.
- Локально `DATA_DIR` не задан → используется `src/`.
- В Docker `DATA_DIR=/app/storage` — volume `./storage` на сервере. Он переживает пересборку.

Никогда не хардкодить пути вида `Path(__file__).parent / "data"` в роутерах — только
через `config.py` / `storage.py`. Иначе вернётся баг «база обнуляется при пересборке».
Никогда не вызывать `delete_tables()` автоматически.
Не класть `cars.db`, `storage/`, `leads.json`, `pending_reviews.json` в git.

## .env
- В git только шаблон `src/.env.example`. Настоящий `src/.env` у каждой машины свой:
  локальный не попадает ни на сервер, ни в Docker-образ (`.dockerignore`: `**/.env`).
- На сервере `.env` подключается через `env_file` в `docker-compose.yml`.
- Значения с `$` (bcrypt-хеш) и секреты — в **одинарных** кавычках, иначе compose их испортит.
- В `.env` только настройки. Никаких паролей от сервера, заметок и команд.
- Новая переменная → добавить в `src/.env.example` и (если читается через Settings) в `config.py`.

## Запуск
```bash
# локально (Windows, PyCharm)
uvicorn src.main:app --reload          # http://localhost:8000/docs
python -m pytest tests
python src/scripts/generate_admin_credentials.py
```
Фронтенд в dev ходит на `/api/*`, Vite проксирует на `localhost:8000` и срезает `/api`.

## Деплой (сервер hera, Ubuntu, root)
Подробно — `DEPLOY.md`. Коротко:
```bash
cd /root/Cars && git pull && docker compose up -d --build
docker compose logs -f api
```
- nginx: `/api/` → `127.0.0.1:8000/` (префикс срезается), `location ^~ /uploads/` → бэкенд.
  `^~` обязателен: без него regex-локация для `.jpg/.png` перехватывает картинки → 404.
- Порт 8000 опубликован только на `127.0.0.1` — наружу ходим только через nginx.
- Git-remote этого репо называется `github` (не `origin`).

## Соглашения
- Роуты со статичными сегментами (`/submit`, `/pending`, `/slug/{slug}`) объявлять РАНЬШЕ `/{id}`,
  иначе FastAPI пытается распарсить строку как int → 422.
- Записывающие эндпоинты — только с `Depends(get_current_admin)`. Публичные: чтение, `/leads` POST,
  `/reviews/submit`, `/upload/public`, `/cars/cal`.
- Хранимые коды — английские (`body_type`: SUV, Sedan, MPV, Coupe, Hatchback, Wagon), подписи в UI — русские.
  Тип двигателя/привод/состояние хранятся русскими enum-значениями (см. `schemas.py`) — не менять, на них
  завязаны калькулятор и фронт.
- Поле марки называется `brend` (историческая опечатка, на ней завязан фронт) — не переименовывать.
- `china_price` — цена в юанях (¥). Калькулятор отдаёт итоги в рублях.
- URL загруженных картинок — относительные `/uploads/<uuid>.<ext>`; браузер берёт их по `/uploads/...`
  (nginx `location ^~ /uploads/` → бэкенд). Путь `/api/uploads/...` в проде даёт 404 — не использовать.
- Ошибки внешних сервисов → 400/502 с понятным `detail` на русском, не 500.
- Windows-репозиторий с `core.autocrlf=true`: при работе с git из Linux использовать
  `git -c core.autocrlf=true ...`, иначе все файлы покажутся изменёнными.

## SEO-страницы и адреса
- nginx отправляет `/`, `/catalog`, `/blog`, `/reviews`, `/car/*`, `/blog/*` на `/seo/render/...`:
  бэкенд берёт собранный `index.html` фронтенда (`FRONTEND_INDEX`, в compose — `/app/frontend`)
  и вставляет title/description/OG/canonical/JSON-LD и HTML-контент в `#root`. React затем
  рисует страницу поверх. Нет index.html → 503 → nginx отдаёт обычную SPA.
- Адрес машины: `/car/<slugify(car_name)>-<id>`, ищем по id в конце. `slugify` ОБЯЗАН совпадать
  с `src/utils/slug.js` фронтенда (тест `test_slugify_matches_frontend`). `/car/7` → 301 на полный адрес.
- Статьи: `/blog/<slug>`, `/blog/<id>` → 301 на slug.
- `/sitemap.xml` генерируется из базы — статичного sitemap во фронтенде нет.

## Почта
- `send_email` никогда не бросает исключений; повторяет при сетевых ошибках, пробует второй порт
  (465 SSL ↔ 587 STARTTLS), подключается по IPv4 (`SMTP_FORCE_IPV4`).
- Яндекс: отправитель всегда = `SMTP_USER`, пароль — пароль приложения. Другие сервисы
  (SendGrid: `SMTP_USER=apikey`): отправитель = `SMTP_FROM`.
