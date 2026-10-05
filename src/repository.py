from sqlalchemy import select

from src.datebase import new_session, CarsOrm
from src.schemas import SCarAdd, SCar


class CarRepository:
    @classmethod
    async def add_one(cls, data: SCarAdd) -> int:
       async with new_session.begin() as session:

           car_dict = data.model_dump()
           car = CarsOrm(**car_dict)
           session.add(car)
           await session.flush()
           await session.commit()
           return car.id

    @classmethod
    async def find_all(cls) -> list[SCar]:
       async with new_session.begin() as session:
            query = select(CarsOrm)
            result = await session.execute(query)
            cars_models = result.scalars().all()
            cars_schemas = [SCar.model_validate(car_model) for car_model in cars_models]
            return cars_schemas


