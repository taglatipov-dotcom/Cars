"""
Разделы ILSATAO кроме авто: новогодние боксы (/box) и сумки (/bags).

Три коллекции в JSON-хранилище (как блог):
  box_items    → data/shop_box_items.json    товары для конструктора бокса
  box_presets  → data/shop_box_presets.json  готовые боксы (состав из box_items)
  bags         → data/shop_bags.json         сумки

Публично: GET /shop/{collection} — только активные (active=true), отсортированы по sort.
Админка (JWT): GET /shop/{collection}/all, POST, PUT /{id}, DELETE /{id}.
Стартовые данные — в src/data/shop_*.json (копируются в хранилище, если файла нет).
Заказы с этих страниц приходят в общие заявки (/leads) с source = "box" / "bags".
"""
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.auth import get_current_admin
from src.storage import json_path, load_json_list, next_id, save_json_list

router = APIRouter(prefix="/shop", tags=["Боксы и сумки"])


# ---------------- схемы ----------------

class SBoxItemIn(BaseModel):
    """Товар для бокса. Габариты — в см, вес — в граммах, цена — в ₽."""
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Сладости", max_length=60)
    price: int = Field(ge=0, le=1_000_000)
    weight_g: int = Field(ge=1, le=5000)
    w: float = Field(gt=0, le=30)
    h: float = Field(gt=0, le=30)
    d: float = Field(gt=0, le=30)
    emoji: str | None = Field(default=None, max_length=8)
    image: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    active: bool = True
    sort: int = 0


class SPresetLine(BaseModel):
    item_id: int
    qty: int = Field(default=1, ge=1, le=50)


class SBoxPresetIn(BaseModel):
    """Готовый бокс. Цена считается по составу; discount — скидка в % на готовый набор."""
    name: str = Field(min_length=1, max_length=120)
    tagline: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    items: list[SPresetLine] = Field(default_factory=list, max_length=60)
    discount: int = Field(default=0, ge=0, le=90)
    color: str | None = Field(default=None, max_length=16)   # акцент карточки, #RRGGBB
    image: str | None = Field(default=None, max_length=500)
    active: bool = True
    sort: int = 0


class SBagIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Шопер", max_length=60)
    price: int = Field(ge=0, le=10_000_000)
    old_price: int | None = Field(default=None, ge=0, le=10_000_000)
    material: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=60)          # «38 × 30 × 12 см»
    colors: list[str] = Field(default_factory=list, max_length=12)  # «Чёрный:#111111»
    images: list[str] = Field(default_factory=list, max_length=12)
    description: str | None = Field(default=None, max_length=2000)
    in_stock: bool = True
    active: bool = True
    sort: int = 0


class Collection(str, Enum):
    box_items = "box_items"
    box_presets = "box_presets"
    bags = "bags"


SCHEMAS: dict[Collection, type[BaseModel]] = {
    Collection.box_items: SBoxItemIn,
    Collection.box_presets: SBoxPresetIn,
    Collection.bags: SBagIn,
}


def _path(c: Collection):
    return json_path(f"shop_{c.value}.json")


def _load(c: Collection) -> list[dict]:
    return load_json_list(_path(c))


def _sorted(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda i: (i.get("sort", 0), i.get("id", 0)))


def _validate(c: Collection, data: dict) -> dict:
    try:
        return SCHEMAS[c].model_validate(data).model_dump()
    except Exception as e:  # pydantic.ValidationError → 422 с понятным текстом
        raise HTTPException(status_code=422, detail=str(e))


# ---------------- публичные ----------------

@router.get("/{collection}")
async def list_public(collection: Collection) -> list[dict]:
    return _sorted([i for i in _load(collection) if i.get("active", True)])


# ---------------- админка (статичный /all — раньше /{id}) ----------------

@router.get("/{collection}/all")
async def list_all(collection: Collection, _admin: str = Depends(get_current_admin)) -> list[dict]:
    return _sorted(_load(collection))


@router.post("/{collection}", status_code=status.HTTP_201_CREATED)
async def create(collection: Collection, data: dict, _admin: str = Depends(get_current_admin)) -> dict:
    clean = _validate(collection, data)
    items = _load(collection)
    item = {"id": next_id(items), **clean}
    items.append(item)
    save_json_list(_path(collection), items)
    return item


@router.put("/{collection}/{item_id}")
async def update(collection: Collection, item_id: int, data: dict,
                 _admin: str = Depends(get_current_admin)) -> dict:
    clean = _validate(collection, data)
    items = _load(collection)
    for idx, it in enumerate(items):
        if it.get("id") == item_id:
            items[idx] = {"id": item_id, **clean}
            save_json_list(_path(collection), items)
            return items[idx]
    raise HTTPException(status_code=404, detail="Not found")


@router.delete("/{collection}/{item_id}")
async def delete(collection: Collection, item_id: int, _admin: str = Depends(get_current_admin)) -> dict:
    items = _load(collection)
    rest = [i for i in items if i.get("id") != item_id]
    if len(rest) == len(items):
        raise HTTPException(status_code=404, detail="Not found")
    if collection == Collection.box_items:
        # убираем удалённый товар из готовых боксов, чтобы состав не ссылался в пустоту
        presets = _load(Collection.box_presets)
        for p in presets:
            p["items"] = [l for l in p.get("items", []) if l.get("item_id") != item_id]
        save_json_list(_path(Collection.box_presets), presets)
    save_json_list(_path(collection), rest)
    return {"ok": True, "id": item_id}
