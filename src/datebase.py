from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.testing.schema import mapped_column

engine = create_async_engine(
    "sqlite+aiosqlite:///cars.db",
)

new_session = async_sessionmaker(engine, expire_on_commit=False)

class Modal(DeclarativeBase):
    pass




class CarsOrm(Modal):
    __tablename__ = "cars"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    mark: Mapped[int]
    year_built: Mapped[int]
    description: Mapped[str | None]
    china_price: Mapped[int | None]
    photos: Mapped[list[Mapped[str]]| None]
    engine_type: Mapped[str]
    engine_volume: Mapped[int| None]
    horsepower: Mapped[int| None]
    engine_power: Mapped[int| None]


async def create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Modal.metadata.create_all)


async def delete_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Modal.metadata.drop_all)