from pydantic import BaseModel, Field, ConfigDict



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

    model_config = ConfigDict(from_attributes=True)


class ScarId(BaseModel):
    ok: bool = True
    car_id: int