from typing import Annotated

from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from src.datebase import create_tables, delete_tables


@asynccontextmanager
async def lifespan():
    await delete_tables()
    print("База данных очищена")
    await create_tables()
    print("База данных готова")
    yield
    print("Выключение")


app = FastAPI()


cars = []

class SCarAdd(BaseModel):
    name: str
    mark: str
    year_built: int | None = None
    description: str | None = None
    china_price: float | None = None
    photos: list[str] | None = None
    engine_type: str = Field(examples=["Бензиновый", "Электрический", "Гибрид"])
    engine_volume: float | None = None   ### l
    horsepower: int | None = None
    engine_power: float | None = None ###KWT



class SCar(SCarAdd):
    id: int


# @app.get("/cars")
# def get_cars():
#     car = SCarAdd(name="Audi", mark="A2", engine_type="Бензиновый")
#     return {"cars": [car]}


@app.post("/cars")
async def add_car(car: Annotated[SCarAdd, Depends()]):
    cars.append(car)
    return {"result": True}