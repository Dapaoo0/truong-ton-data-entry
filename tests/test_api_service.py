from fastapi.testclient import TestClient

from services.api.app.deps import get_supabase_client
from services.api.app.main import api


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        if key == "is_deleted":
            self.rows = [row for row in self.rows if row.get("is_deleted") == value]
        elif key == "giai_doan":
            self.rows = [row for row in self.rows if row.get("giai_doan") == value]
        elif key == "dim_lo.dim_farm.farm_name":
            self.rows = [
                row
                for row in self.rows
                if (((row.get("dim_lo") or {}).get("dim_farm") or {}).get("farm_name")) == value
            ]
        return self

    def execute(self):
        return _FakeResponse(self.rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "stage_logs"
        return _FakeQuery(self.rows)


def test_health_endpoint_returns_ok():
    client = TestClient(api)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cut_bud_weekly_forecast_uses_domain_logic_and_filters_farm():
    rows = [
        {
            "is_deleted": False,
            "giai_doan": "Cắt bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 88,
            "dim_lo": {"lo_name": "A8", "dim_farm": {"farm_name": "Farm 126"}},
        },
        {
            "is_deleted": False,
            "giai_doan": "Chích bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 999,
            "dim_lo": {"lo_name": "A8", "dim_farm": {"farm_name": "Farm 126"}},
        },
        {
            "is_deleted": False,
            "giai_doan": "Cắt bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 100,
            "dim_lo": {"lo_name": "1A", "dim_farm": {"farm_name": "Farm 157"}},
        },
    ]
    api.dependency_overrides[get_supabase_client] = lambda: _FakeSupabase(rows)
    client = TestClient(api)

    response = client.get("/forecasts/cut-bud-weekly", params={"farm": "Farm 126", "weeks": 8})

    api.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["farm"] == "Farm 126"
    assert payload["weeks_inclusive"] == 8
    assert sum(row["forecast_bunches"] for row in payload["rows"]) == 88
    assert {row["farm"] for row in payload["rows"]} == {"Farm 126"}


def test_cut_bud_weekly_forecast_normalizes_invalid_week_option():
    rows = [
        {
            "is_deleted": False,
            "giai_doan": "Cắt bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 10,
            "dim_lo": {"lo_name": "A8", "dim_farm": {"farm_name": "Farm 126"}},
        }
    ]
    api.dependency_overrides[get_supabase_client] = lambda: _FakeSupabase(rows)
    client = TestClient(api)

    response = client.get("/forecasts/cut-bud-weekly", params={"weeks": 99})

    api.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["weeks_inclusive"] == 8
