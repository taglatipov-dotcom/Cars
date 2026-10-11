from fastapi import FastAPI

from src.router import router as cars_router

from  fastapi.middleware.cors import CORSMiddleware

# from contextlib import asynccontextmanager
#
# from src.datebase import create_tables, delete_tables
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await delete_tables()
#     print("База данных очищена")
#     await create_tables()
#     print("База данных готова")
#     yield
#     print("Выключение")




# app = FastAPI(lifespan=lifespan)
app = FastAPI()
app.include_router(cars_router)


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
)