import json

import app


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTableQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        if key == "is_active":
            self._rows = [row for row in self._rows if row.get("is_active") == value]
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _FakeResponse(self._rows)


class _FakeSupabase:
    def __init__(self, rows):
        self._rows = rows

    def table(self, table_name):
        assert table_name == "dim_lo"
        return _FakeTableQuery(self._rows)


def test_get_lots_by_farm_only_returns_lots_present_on_map(monkeypatch, tmp_path):
    polygon_file = tmp_path / "farm_test_polygons.json"
    polygon_file.write_text(
        json.dumps(
            {
                "lots": [
                    {"name": "A1", "points": []},
                    {"name": "A2", "points": []},
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(app, "FARM_POLYGON_FILES", {"Farm Test": polygon_file.name}, raising=False)
    monkeypatch.setattr(app, "FARM_POLYGON_BASE_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(
        app,
        "supabase",
        _FakeSupabase(
            [
                {"lo_name": "A2", "is_active": True},
                {"lo_name": "OLD_3B", "is_active": True},
                {"lo_name": "A1", "is_active": True},
            ]
        ),
    )

    assert app.get_lots_by_farm("Farm Test") == ["A1", "A2"]


def test_get_lots_by_farm_falls_back_to_active_db_lots_without_map(monkeypatch):
    monkeypatch.setattr(app, "FARM_POLYGON_FILES", {}, raising=False)
    monkeypatch.setattr(
        app,
        "supabase",
        _FakeSupabase(
            [
                {"lo_name": "B2", "is_active": True},
                {"lo_name": "B1", "is_active": True},
            ]
        ),
    )

    assert app.get_lots_by_farm("Farm Without Map") == ["B2", "B1"]
