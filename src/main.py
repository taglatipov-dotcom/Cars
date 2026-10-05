from fastapi import FastAPI

from contextlib import asynccontextmanager

from src.datebase import create_tables, delete_tables
from src.router import router as cars_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    print("База данных очищена")
    await create_tables()
    print("База данных готова")
    yield
    print("Выключение")


app = FastAPI(lifespan=lifespan)
app.include_router(cars_router)