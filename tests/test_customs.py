"""Калькулятор растаможки: тело запроса к calcus.ru (src/customs.py) и схемы ввода."""
import pytest
from pydantic import ValidationError

from src.customs import build_customs_payload, resolve_age
from src.schemas import SCustomsCalcInput, SLeadSubmit


def test_resolve_age():
    assert resolve_age(None, 2026) == "0-3"
    assert resolve_age(2026, 2026) == "0-3"   # раньше новая машина попадала в «3-5»
    assert resolve_age(2024, 2026) == "0-3"
    assert resolve_age(2023, 2026) == "3-5"
    assert resolve_age(2021, 2026) == "5-7"
    assert resolve_age(2019, 2026) == "7-0"


def test_payload_company_petrol():
    p = build_customs_payload(price=150000, engine_type="Бензиновый", power=150, engine_volume=1.5,
                              year=2025, owner=2, curr="cny", now_year=2026)
    assert p["owner"] == 2 and p["engine"] == 1 and p["value"] == 1500
    assert p["age"] == "0-3" and p["curr"] == "CNY" and p["power_unit"] == 1
    assert p["year"] == 2026


def test_payload_electric_without_volume():
    p = build_customs_payload(price=200000, engine_type="Электрический", power=150, power_unit=2,
                              owner=3, now_year=2026)
    assert p["engine"] == 4 and p["value"] == 0 and p["power_unit"] == 2 and p["owner"] == 3


def test_payload_year_clamped():
    assert build_customs_payload(price=1, engine_type="Электрический", power=1, now_year=2024)["year"] == 2025
    assert build_customs_payload(price=1, engine_type="Электрический", power=1, now_year=2040)["year"] == 2030


@pytest.mark.parametrize("kwargs, text", [
    (dict(price=0, engine_type="Бензиновый", power=100, engine_volume=1.5), "стоимость"),
    (dict(price=100, engine_type="Паровой", power=100), "тип двигателя"),
    (dict(price=100, engine_type="Бензиновый", power=100), "объём"),
    (dict(price=100, engine_type="Бензиновый", power=0, engine_volume=1.5), "мощность"),
    (dict(price=100, engine_type="Бензиновый", power=100, engine_volume=1.5, owner=5), "Тип ввоза"),
    (dict(price=100, engine_type="Бензиновый", power=100, engine_volume=1.5, curr="BTC"), "Валюта"),
])
def test_payload_errors(kwargs, text):
    with pytest.raises(ValueError, match=text):
        build_customs_payload(**kwargs)


def test_catalog_mode_is_lenient():
    # у машины из каталога нет мощности — расчёт как раньше, без ошибки
    p = build_customs_payload(price=100, engine_type="Бензиновый", power=0, strict=False)
    assert p["power"] == 0 and p["value"] == 0


def test_calc_input_defaults_to_company():
    data = SCustomsCalcInput(price=100000, engine_type="Бензиновый", power=150, engine_volume=2.0)
    assert data.owner == 2 and data.curr == "CNY"
    build_customs_payload(**data.model_dump())  # поля схемы совпадают с аргументами


def test_lead_b2b_fields():
    lead = SLeadSubmit(phone="+7 (987) 498-17-37", client_type="company", company="ООО Ромашка",
                       inn="1234567890", quantity=5)
    assert lead.quantity == 5
    with pytest.raises(ValidationError):
        SLeadSubmit(phone="+7 (987) 498-17-37", inn="12345")
    assert SLeadSubmit(phone="+7 (987) 498-17-37").company is None
