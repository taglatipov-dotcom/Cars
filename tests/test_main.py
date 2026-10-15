from src.storage import load_json_list, next_id, save_json_list


def test_json_roundtrip(tmp_path):
    path = tmp_path / "items.json"
    assert load_json_list(path) == []
    items = [{"id": 1, "name": "Тест"}]
    save_json_list(path, items)
    assert load_json_list(path) == items
    # временных файлов не осталось
    assert [p.name for p in tmp_path.iterdir()] == ["items.json"]


def test_next_id():
    assert next_id([]) == 1
    assert next_id([{"id": 3}, {"id": 7}]) == 8


# ---------- SEO: адреса и даты ----------
from types import SimpleNamespace

from src.seo import car_slug, parse_car_id, slugify, thumb_image
from src.seo_router import parse_ru_date


def test_slugify_matches_frontend():
    # те же ожидания, что и для src/utils/slug.js во фронтенде
    assert slugify("Zeekr 001 2026") == "zeekr-001-2026"
    assert slugify("Ёжик в тумане — Тест") == "ezhik-v-tumane-test"
    assert car_slug(SimpleNamespace(id=13, car_name="Jetour Freedom (自由者)", brend="", model="")) == "jetour-freedom-13"
    assert car_slug(SimpleNamespace(id=5, car_name="自由者", brend="", model="")) == "car-5"


def test_parse_car_id():
    assert parse_car_id("zeekr-001-2026-7") == 7
    assert parse_car_id("7") == 7
    assert parse_car_id("abc") is None


def test_parse_ru_date():
    assert parse_ru_date("12 Мая 2024") == "2024-05-12"
    assert parse_ru_date("05 марта 2025") == "2025-03-05"
    assert parse_ru_date("что-то") is None


def test_thumb_image():
    assert thumb_image("/uploads/abc.jpeg").endswith("/uploads/thumbs/abc.webp")
    assert thumb_image("https://images.unsplash.com/x.jpg") == "https://images.unsplash.com/x.jpg"
