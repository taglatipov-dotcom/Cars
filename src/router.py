from fastapi import APIRouter


from typing import Annotated

from fastapi import Depends, FastAPI

from src.repository import CarRepository
from src.schemas import SCarAdd, SCar, ScarId

router = APIRouter(
    prefix="/cars",
    tags=["Машины"]
)

@router.get("")
async def get_cars() -> list[SCar]:
    cars = await CarRepository.find_all()
    return cars


@router.post("")
async def add_car(car: Annotated[SCarAdd, Depends()]) -> ScarId:
    car_id = await CarRepository.add_one(car)
    return {"result": True, "car_id": car_id}