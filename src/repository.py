from sqlalchemy import delete as sa_delete
from sqlalchemy import select, update as sa_update

from src.database import CarsOrm, new_session
from src.schemas import SCar, SCarAdd, SCarUpdate


class CarRepository:
    PAGE_SIZE = 40

    @classmethod
    async def add_one(cls, data: SCarAdd) -> int:
        async with new_session.begin() as session:
            car = CarsOrm(**data.model_dump(mode="json", by_alias=False))
            session.add(car)
            await session.flush()
            return car.id

    @classmethod
    async def find_all(cls) -> list[SCar]:
        async with new_session() as session:
            query = select(CarsOrm)
            result = await session.execute(query)
            return [SCar.model_validate(c) for c in result.scalars().all()]

    @classmethod
    async def find_page(cls, page: int, size: int | None = None) -> list[SCar]:
        """
        page: 1..N (номер страницы)
        size: размер страницы (по умолчанию 40)
        Сортировка: popularity_rank ASC (1 — самый популярный),
        затем id ASC для стабильного порядка.
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        size = size or cls.PAGE_SIZE
        offset = (page - 1) * size

        async with new_session() as session:
            query = (
                select(CarsOrm)
                .order_by(
                    CarsOrm.popularity_rank.is_(None),  # None в конец
                    CarsOrm.popularity_rank.asc(),
                    CarsOrm.id.asc(),
                )
                .offset(offset)
                .limit(size)
            )
            result = await session.execute(query)
            return [SCar.model_validate(c) for c in result.scalars().all()]

    @classmethod
    async def delete_by_id(cls, car_id: int) -> bool:
        async with new_session.begin() as session:
            result = await session.execute(
                sa_delete(CarsOrm).where(CarsOrm.id == car_id)
            )
            return result.rowcount > 0

    @classmethod
    async def update_by_id(cls, car_id: int, data: SCarUpdate) -> SCar | None:
        # exclude_unset — обновляем только переданные поля
        payload = data.model_dump(
            mode="json", by_alias=False, exclude_unset=True, exclude_none=False
        )
        if not payload:
            # нечего обновлять — вернём текущую запись
            return await cls.find_by_id(car_id)

        # если обновили brend или model и не передали car_name — пересоберём
        if ("brend" in payload or "model" in payload) and "car_name" not in payload:
            current = await cls.find_by_id(car_id)
            if current:
                new_brend = payload.get("brend", current.brend)
                new_model = payload.get("model", current.model)
                payload["car_name"] = f"{new_brend} {new_model}".strip()

        async with new_session.begin() as session:
            result = await session.execute(
                sa_update(CarsOrm)
                .where(CarsOrm.id == car_id)
                .values(**payload)
            )
            if result.rowcount == 0:
                return None

        return await cls.find_by_id(car_id)

    @classmethod
    async def find_by_id(cls, car_id: int) -> SCar | None:
        async with new_session() as session:
            query = select(CarsOrm).where(CarsOrm.id == car_id)
            result = await session.execute(query)
            model = result.scalar_one_or_none()
            return SCar.model_validate(model) if model else None