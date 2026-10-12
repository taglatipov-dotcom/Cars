from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from src.auth import get_current_admin
from src.config import settings
from src.http_client import CALCUSHttpClient
from src.repository import CarRepository
from src.schemas import SCar, SCarAdd, SCarId, SCarUpdate, SDeleteResult

router = APIRouter(prefix="/cars", tags=["Машины"])

calcus_client = CALCUSHttpClient(
    base_url="https://calcus.ru/api/",
    api_client=settings.API_CLIENT_ID,
    api_key=settings.CALCUS_API_KEY,
)


# ---------- Чтение с пагинацией ----------

@router.get("", response_model=list[SCar])
async def get_cars() -> list[SCar]:
    return await CarRepository.find_all()


@router.get("/page/{page}", response_model=list[SCar])
async def get_cars_page(
    page: Annotated[int, Path(ge=1, description="Номер страницы, начиная с 1")],
) -> list[SCar]:
    """Универсальный эндпоинт: page=1 — первые 40, page=2 — вторые 40 и т.д."""
    return await CarRepository.find_page(page)


@router.get("/popularity/1", response_model=list[SCar])
async def get_cars_popularity_1() -> list[SCar]:
    """Первые 40 машин по популярности."""
    return await CarRepository.find_page(1)


@router.get("/popularity/2", response_model=list[SCar])
async def get_cars_popularity_2() -> list[SCar]:
    """Вторые 40 машин по популярности."""
    return await CarRepository.find_page(2)


@router.get("/popularity/3", response_model=list[SCar])
async def get_cars_popularity_3() -> list[SCar]:
    """Третьи 40 машин по популярности."""
    return await CarRepository.find_page(3)


@router.get("/popularity/4", response_model=list[SCar])
async def get_cars_popularity_4() -> list[SCar]:
    """Четвёртые 40 машин по популярности."""
    return await CarRepository.find_page(4)


@router.get("/popularity/5", response_model=list[SCar])
async def get_cars_popularity_5() -> list[SCar]:
    """Пятые 40 машин по популярности."""
    return await CarRepository.find_page(5)


# ---------- Чтение одной ----------

@router.get("/{car_id}", response_model=SCar)
async def get_car(car_id: int) -> SCar:
    car = await CarRepository.find_by_id(car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


# ---------- Создание (только админ) ----------

@router.post("", response_model=SCarId, status_code=status.HTTP_201_CREATED)
async def add_car(
    car: SCarAdd,
    _admin: str = Depends(get_current_admin),
) -> SCarId:
    car_id = await CarRepository.add_one(car)
    return SCarId(ok=True, car_id=car_id)


# ---------- Обновление (только админ) ----------

@router.patch("/{car_id}", response_model=SCar)
async def update_car(
    car_id: int,
    data: SCarUpdate,
    _admin: str = Depends(get_current_admin),
) -> SCar:
    car = await CarRepository.update_by_id(car_id, data)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


# ---------- Удаление (только админ) ----------

@router.delete("/{car_id}", response_model=SDeleteResult)
async def delete_car(
    car_id: int,
    _admin: str = Depends(get_current_admin),
) -> SDeleteResult:
    deleted = await CarRepository.delete_by_id(car_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Car not found")
    return SDeleteResult(ok=True, car_id=car_id)


# ---------- Расчёт таможни (публичный) ----------

@router.post("/cal")
async def get_calcus(car: Annotated[SCarAdd, Depends()]):
    return await calcus_client.get_price(car)