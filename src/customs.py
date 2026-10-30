"""Подготовка запроса к calcus.ru (v1/Customs) — чистый Python, без сети.

Используется и для карточки машины (/cars/cal), и для отдельного калькулятора
(/cars/calculator), где пользователь вводит данные сам.

Коды calcus.ru (https://calcus.ru/apidocs.html):
  owner: 1 — физлицо для личного пользования, 2 — юрлицо, 3 — физлицо для перепродажи
  age:   "0-3", "3-5", "5-7", "7-0" (старше 7 лет)
  engine: 1 бензин, 2 дизель, 4 электро, 5 последовательный гибрид, 6 параллельный гибрид
  power_unit: 1 — л.с., 2 — кВт
"""
from datetime import datetime

ENGINE_TYPE_CODES = {
    "Бензиновый": 1,
    "Дизельный": 2,
    "Электрический": 4,
    "Последовательный гибрид": 5,
    "Параллельный гибрид": 6,
}

# Двигатели, для которых calcus требует объём (value, см³)
ENGINES_WITH_VOLUME = {1, 2, 6}

OWNER_PERSONAL = 1
OWNER_COMPANY = 2
OWNER_RESALE = 3
OWNERS = {OWNER_PERSONAL, OWNER_COMPANY, OWNER_RESALE}

CURRENCIES = {"CNY", "RUB", "USD", "EUR", "JPY", "KRW"}
AGES = {"0-3", "3-5", "5-7", "7-0"}


def resolve_age(year: int | None, now_year: int | None = None) -> str:
    """Год выпуска → возрастная группа calcus. Нет года — считаем новым."""
    if not year:
        return "0-3"
    age = (now_year or datetime.now().year) - year
    if age < 3:
        return "0-3"
    if age < 5:
        return "3-5"
    if age < 7:
        return "5-7"
    return "7-0"


def build_customs_payload(
    *,
    price: float,
    engine_type: str,
    power: float,
    power_unit: int = 1,
    engine_volume: float | None = None,
    year: int | None = None,
    age: str | None = None,
    owner: int = OWNER_PERSONAL,
    curr: str = "CNY",
    now_year: int | None = None,
    strict: bool = True,
) -> dict:
    """Тело запроса v1/Customs. Ошибки ввода — ValueError с понятным текстом.

    strict=False — для машин из каталога: не требуем мощность и объём
    (как было раньше; у части машин в базе они не заполнены)."""
    if not price or price <= 0:
        raise ValueError("Укажите стоимость автомобиля")
    engine = ENGINE_TYPE_CODES.get(str(engine_type))
    if engine is None:
        raise ValueError(f"Неизвестный тип двигателя: {engine_type}")
    if strict and (not power or power <= 0):
        raise ValueError("Укажите мощность двигателя")
    if power_unit not in (1, 2):
        raise ValueError("Единица мощности: 1 — л.с., 2 — кВт")
    if owner not in OWNERS:
        raise ValueError("Тип ввоза: 1 — физлицо, 2 — юрлицо, 3 — физлицо для перепродажи")
    curr = (curr or "CNY").upper()
    if curr not in CURRENCIES:
        raise ValueError(f"Валюта не поддерживается: {curr}")
    if age is not None and age not in AGES:
        raise ValueError(f"Возраст: одно из {sorted(AGES)}")

    value = int(round((engine_volume or 0) * 1000))
    if strict and engine in ENGINES_WITH_VOLUME and value <= 0:
        raise ValueError("Укажите объём двигателя")

    current_year = now_year or datetime.now().year
    return {
        "owner": owner,
        "age": age or resolve_age(year, current_year),
        "engine": engine,
        "power": round(float(power or 0), 1),
        "power_unit": power_unit,
        "value": value,
        "price": round(float(price), 2),
        "curr": curr,
        # calcus принимает расчётный год 2025–2030 (коэффициенты утильсбора)
        "year": min(max(current_year, 2025), 2030),
        "usd_rate": 0,
        "eur_rate": 0,
        "cny_rate": 0,
        "jpy_rate": 0,
        "krw_rate": 0,
    }
