from fastapi import APIRouter


from typing import Annotated

from fastapi import Depends

from src.http_client import CALCUSHttpClient
from src.repository import CarRepository
from src.schemas import SCarAdd, SCar, ScarId
from src.config import settings

calcus_client = CALCUSHttpClient(
    base_url="https://calcus.ru/api/",
    api_client=settings.API_CLIENT_ID,
    api_key=settings.CALCUS_API_KEY,

)

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


@router.post("/cal")
async def get_calcus(car: Annotated[SCarAdd, Depends()]):
    car_calcus = await calcus_client.get_price(car)
    return car_calcus



