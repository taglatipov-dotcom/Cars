from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EngineType(str, Enum):
    petrol = "Бензиновый"
    diesel = "Дизельный"
    electric = "Электрический"
    series_hybrid = "Последовательный гибрид"
    parallel_hybrid = "Параллельный гибрид"


class Condition(str, Enum):
    new = "новая"
    used = "бу"


class Drive(str, Enum):
    fwd = "передний"
    rwd = "задний"
    awd = "полный"


class EngineInfo(BaseModel):
    type: EngineType | str
    power: float | None = None


class SCarAdd(BaseModel):
    # базовые
    popularity_rank: int | None = Field(default=None, ge=1, le=10)
    brend: str
    model: str
    car_name: str | None = None          # если не передан — соберётся из brend+model
    country: str | None = None
    year: int | None = None
    condition: Condition | str | None = None
    mileage: int | None = None
    body_type: str | None = None
    color: str | None = None
    drive: Drive | str | None = None
    location: str | None = None
    china_price: float | None = None
    description: str | None = None

    # двигатель
    engine_type: EngineType | str | None = None
    engine_volume: float | None = None
    horsepower: int | None = None
    engine_power: float | None = None
    engine: dict[str, EngineInfo] | None = None   # {"1": {"type": "...", "power": 150}}
    torque: int | None = None

    # динамика / расход
    acceleration: float | None = None
    top_speed: int | None = Field(default=None, alias="topSpeed")
    range: int | None = None
    battery: float | None = None
    charging: str | None = None
    transmission: str | None = None
    consumption: float | None = None

    # габариты
    length: int | None = None
    width: int | None = None
    height: int | None = None
    wheelbase: int | None = None
    clearance: int | None = None
    weight: int | None = None
    trunk: int | None = None

    # салон
    interior_color: str | None = None
    interior_material: str | None = None
    interior_seats: int | None = None
    interior_display: str | None = None
    interior_audio: str | None = None

    # безопасность
    safety_abs: bool | None = None
    safety_esp: bool | None = None
    safety_ebp: bool | None = None
    safety_bas: bool | None = None
    safety_airbags: int | None = None
    safety_blind: bool | None = None
    safety_adaptive_cruise: bool | None = None
    safety_ext_stop: bool | None = None
    safety_line: bool | None = None

    # фичи / изображения
    features: list[str] | None = None
    images: list[str] | None = None
    photos: list[str] | None = None  # legacy

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def fill_car_name(self):
        if not self.car_name:
            self.car_name = f"{self.brend} {self.model}".strip()
        return self


class SCar(SCarAdd):
    id: int
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SCarId(BaseModel):
    ok: bool = True
    car_id: int

class SCarUpdate(BaseModel):
    """Все поля опциональны — частичное обновление."""
    popularity_rank: int | None = Field(default=None, ge=1, le=10)
    brend: str | None = None
    model: str | None = None
    car_name: str | None = None
    country: str | None = None
    year: int | None = None
    condition: Condition | str | None = None
    mileage: int | None = None
    body_type: str | None = None
    color: str | None = None
    drive: Drive | str | None = None
    location: str | None = None
    china_price: float | None = None
    description: str | None = None

    engine_type: EngineType | str | None = None
    engine_volume: float | None = None
    horsepower: int | None = None
    engine_power: float | None = None
    engine: dict[str, EngineInfo] | None = None
    torque: int | None = None

    acceleration: float | None = None
    top_speed: int | None = Field(default=None, alias="topSpeed")
    range: int | None = None
    battery: float | None = None
    charging: str | None = None
    transmission: str | None = None
    consumption: float | None = None

    length: int | None = None
    width: int | None = None
    height: int | None = None
    wheelbase: int | None = None
    clearance: int | None = None
    weight: int | None = None
    trunk: int | None = None

    interior_color: str | None = None
    interior_material: str | None = None
    interior_seats: int | None = None
    interior_display: str | None = None
    interior_audio: str | None = None

    safety_abs: bool | None = None
    safety_esp: bool | None = None
    safety_ebp: bool | None = None
    safety_bas: bool | None = None
    safety_airbags: int | None = None
    safety_blind: bool | None = None
    safety_adaptive_cruise: bool | None = None
    safety_ext_stop: bool | None = None
    safety_line: bool | None = None

    features: list[str] | None = None
    images: list[str] | None = None
    photos: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)


class SDeleteResult(BaseModel):
    ok: bool = True
    car_id: int


class SReview(BaseModel):
    id: int
    name: str
    avatar: str | None = None
    rating: int = Field(ge=1, le=5)
    text: str
    car: str

class SReviewAdd(BaseModel):
    """Создание отзыва. id назначается сервером."""
    name: str
    avatar: str | None = None
    rating: int = Field(ge=1, le=5)
    text: str
    car: str


class SReviewUpdate(BaseModel):
    """Частичное обновление отзыва. Все поля опциональны."""
    name: str | None = None
    avatar: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = None
    car: str | None = None


class SReviewId(BaseModel):
    ok: bool = True
    review_id: int


class SDeleteReviewResult(BaseModel):
    ok: bool = True
    review_id: int


class SBlogPreview(BaseModel):
    """Краткая информация о статье — для карточек и превью."""
    id: int
    slug: str
    title: str
    excerpt: str
    image: str
    date: str
    tag: str
    author: str
    readTime: str


class SBlog(SBlogPreview):
    """Полная статья — с HTML-контентом."""
    content: str

class SBlogAdd(BaseModel):
    """Создание статьи. id назначается сервером."""
    slug: str
    title: str
    excerpt: str
    image: str
    date: str
    tag: str
    author: str
    readTime: str
    content: str


class SBlogUpdate(BaseModel):
    """Частичное обновление статьи. Все поля опциональны."""
    slug: str | None = None
    title: str | None = None
    excerpt: str | None = None
    image: str | None = None
    date: str | None = None
    tag: str | None = None
    author: str | None = None
    readTime: str | None = None
    content: str | None = None


class SBlogId(BaseModel):
    ok: bool = True
    blog_id: int


class SDeleteBlogResult(BaseModel):
    ok: bool = True
    blog_id: int


class SReviewSubmit(BaseModel):
    """Что присылает посетитель сайта через форму «Оставить отзыв»."""
    name: str = Field(min_length=2, max_length=100)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=1000)
    car: str = Field(min_length=2, max_length=200)


class SPendingReview(SReviewSubmit):
    """Отзыв на модерации — то же + id, avatar, дата."""
    id: int
    avatar: str | None = None
    submitted_at: str

class LeadStatus(str, Enum):
    new = "new"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class SLeadSubmit(BaseModel):
    """Что присылает публичная форма."""
    phone: str = Field(min_length=5, max_length=32)
    contact_method: str | None = Field(default=None, max_length=64)
    preferences: str | None = Field(default=None, max_length=1000)
    budget: str | None = Field(default=None, max_length=64)
    consent: bool = False
    newsletter: bool = False
    source: str | None = Field(default=None, max_length=64)


class SLead(SLeadSubmit):
    id: int
    status: LeadStatus = LeadStatus.new
    comment: str | None = None
    created_at: str


class SLeadUpdate(BaseModel):
    status: LeadStatus | None = None
    comment: str | None = Field(default=None, max_length=2000)


class SLeadId(BaseModel):
    ok: bool = True
    lead_id: int


class SDeleteLeadResult(BaseModel):
    ok: bool = True
    lead_id: int