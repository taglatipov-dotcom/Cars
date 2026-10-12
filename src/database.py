from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import BASE_DIR

engine = create_async_engine(
    f"sqlite+aiosqlite:///{BASE_DIR / 'cars.db'}",
)

new_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CarsOrm(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)

    # базовые
    popularity_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brend: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    car_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    drive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    china_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # двигатель
    engine_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    horsepower: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    engine: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    torque: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # динамика / расход
    acceleration: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    range: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battery: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consumption: Mapped[float | None] = mapped_column(Float, nullable=True)

    # габариты
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wheelbase: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clearance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trunk: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # салон
    interior_color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    interior_material: Mapped[str | None] = mapped_column(String(64), nullable=True)
    interior_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interior_display: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interior_audio: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # безопасность
    safety_abs: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_esp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_ebp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_bas: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_airbags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_blind: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_adaptive_cruise: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_ext_stop: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    safety_line: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # фичи / изображения
    features: Mapped[list | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # legacy (оставил для совместимости)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)


async def create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def delete_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)