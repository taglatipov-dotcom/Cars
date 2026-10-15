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
