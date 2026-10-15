# Деплой бэкенда ILSATAO

## Почему раньше обнулялась база

Старый процесс был такой: `docker stop` → `docker rm` → `docker build` → `docker run`.

* `cars.db`, `src/data/*.json` и `src/uploads/` лежали **внутри контейнера**.
  `docker rm` удаляет контейнер вместе со всем, что в нём было записано —
  все машины, заявки, отзывы и картинки, добавленные через админку.
* Новый контейнер стартовал с теми файлами, которые попали в образ при
  `docker build`: `COPY . .` копировал `src/cars.db` с диска сервера
  (старый или пустой снимок) и JSON-файлы из git.
* В `.dockerignore` было написано `cars.db` и `.env` — это исключает только
  файлы в корне, а `src/cars.db` и `src/.env` (с паролями!) попадали в образ.

## Что изменилось

* Все изменяемые данные теперь лежат в одной папке `DATA_DIR`
  (в Docker это `/app/storage`), а она примонтирована к диску сервера:
  `./storage` рядом с проектом. Пересборка образа её не трогает.
* `docker-compose.yml`: один файл вместо ручных команд, автоперезапуск после
  ребута сервера, порт 8000 открыт только для nginx (`127.0.0.1:8000`).
* `.env` больше не попадает в образ: он подключается через `env_file`.

```
storage/
├── cars.db          ← база машин
├── data/            ← blogs.json, reviews.json, pending_reviews.json, leads.json
└── uploads/         ← картинки
```

## Файл .env

* В git лежит только шаблон `src/.env.example` — без секретов.
* Настоящий `src/.env` у каждой машины свой: локальный остаётся на компьютере,
  серверный создаётся на сервере руками. В git и в Docker-образ он не попадает.
* Значения с `$` (хеш пароля) и секреты — в одинарных кавычках.

## ⚠️ Переезд (один раз, ДО первой пересборки)

Сейчас на сервере работает старый контейнер, и в нём лежат текущие данные.
Сначала их нужно вытащить, иначе они пропадут.

```bash
cd /root/Cars
docker ps                       # запомнить CONTAINER ID старого контейнера
OLD=<id_контейнера>

mkdir -p storage/data storage/uploads
docker cp $OLD:/src/cars.db       storage/cars.db
docker cp $OLD:/src/data/.        storage/data/
docker cp $OLD:/src/uploads/.     storage/uploads/

ls -la storage storage/data storage/uploads   # убедиться, что всё на месте
cp -r storage /root/ilsatao-backup-$(date +%F)  # резервная копия на всякий случай

git pull
docker stop $OLD && docker rm $OLD
docker compose up -d --build
docker compose logs -f api      # должно быть «База данных готова, хранилище: /app/storage»
```

Если Docker Compose не установлен: `apt-get install docker-compose-plugin`.

## Обычное обновление (дальше всегда так)

```bash
cd /root/Cars
git pull
docker compose up -d --build
```

Данные в `storage/` сохраняются. Ничего удалять руками не нужно.

## Резервная копия (рекомендуется раз в день через cron)

```bash
# crontab -e
0 4 * * * tar czf /root/backups/ilsatao-$(date +\%F).tar.gz -C /root/Cars storage && find /root/backups -name 'ilsatao-*.tar.gz' -mtime +14 -delete
```

(Предварительно `mkdir -p /root/backups`.)

## Локальная разработка

Ничего не меняется: без переменной `DATA_DIR` база и данные лежат в `src/`,
как раньше. Запуск: `uvicorn src.main:app --reload`.


## Обновление: SEO-страницы, sitemap, сжатие фото (октябрь 2026)

Делается один раз. Порядок важен: сначала фронтенд, потом бэкенд, потом nginx.

1. **Фронтенд** (как обычно):
   ```bash
   cd /root/Front/CarsFrondend
   git pull && npm install && npm run build
   sudo rsync -a --delete dist/ /var/www/ilsatao-frontend/
   ```
2. **Бэкенд**: в `docker-compose.yml` теперь монтируется папка фронтенда
   (`/var/www/ilsatao-frontend` → `/app/frontend`, только чтение) — из неё берётся
   `index.html` для SEO-страниц. Добавилась библиотека Pillow (сжатие фото).
   ```bash
   cd /root/Cars && git pull && docker compose up -d --build
   curl -s http://127.0.0.1:8000/seo/render/catalog | grep -o "<title>.*</title>"
   ```
   Должен прийти заголовок «Каталог автомобилей из Китая с ценами | ILSATAO».
3. **nginx**: в `/etc/nginx/sites-available/ilsatao` в блок `server { ... listen 443 ... }`
   добавить блоки из `nginx.txt` (раздел «SEO»: регулярная `location` для страниц,
   `location @spa`, `location = /sitemap.xml`) и заменить `location /api/` на `location ^~ /api/`.
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   curl -s https://ilsatao.ru/catalog | grep -o "<title>.*</title>"
   curl -s https://ilsatao.ru/sitemap.xml | head -5
   ```
4. **Старые фото** — посмотреть экономию и пережать (имена файлов не меняются):
   ```bash
   cp -r storage /root/backup-$(date +%F)
   docker compose exec api python -m src.scripts.optimize_uploads          # пробный запуск
   docker compose exec api python -m src.scripts.optimize_uploads --apply  # применить
   ```
   Миниатюры для карточек создаются сами при первом открытии каталога.
5. **Почта** — проверка по шагам:
   ```bash
   docker compose exec api python -m src.scripts.test_email
   ```
6. В Яндекс.Вебмастере: «Индексирование → Файлы Sitemap» → добавить `https://ilsatao.ru/sitemap.xml`,
   и «Переобход страниц» для главной и каталога.

Если после обновления что-то не так со страницами — достаточно убрать SEO-блок из nginx
и сделать `reload`: сайт вернётся к обычной SPA-схеме.
