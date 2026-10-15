import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import DATA_DIR, UPLOAD_DIR
from src.database import create_tables
from src.storage import ensure_storage
from src.router import calcus_client
from src.router import router as cars_router
from src.reviews_router import router as reviews_router
from src.blog_router import router as blog_router
from src.leads_router import router as leads_router
from src.auth_router import router as auth_router
from src.upload_router import router as upload_router
from src.seo_router import router as seo_router
from src.images_router import router as images_router

# Логи наших модулей (почта, хранилище) видны в `docker compose logs api`
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_storage()
    await create_tables()
    print(f"База данных готова, хранилище: {DATA_DIR}")
    yield
    await calcus_client.close()
    print("Выключение")


app = FastAPI(lifespan=lifespan, title="Car API", version="1.0")

# Папка для загруженных картинок (внутри DATA_DIR, см. config.py)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Миниатюры /uploads/thumbs/... — РАНЬШЕ, чем mount("/uploads"), иначе mount перехватит
app.include_router(images_router)

# Раздача статики: GET /uploads/<filename>
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.include_router(auth_router)
app.include_router(cars_router)
app.include_router(reviews_router)
app.include_router(blog_router)
app.include_router(leads_router)
app.include_router(upload_router)
app.include_router(seo_router)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#todo отправка уведомлений
#todo калькулятор для электричек и гибридов
#todo доавить реальные отзывы
#todo добавить реальные статьи
#todo добавить реальные машины
#todo добавить реальную политику конфиденциальности
#todo проверить все плашки текстовые на сайте
#todo сделать профиль на дзен
#todo продвижение сайта
#todo добавить икноку в шапку
#todo отправить файлы map

