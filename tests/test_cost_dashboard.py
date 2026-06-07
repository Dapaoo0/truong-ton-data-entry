from datetime import date

import pandas as pd

from cost_dashboard import (
    _apply_cost_filters,
    _classify_material_type,
    _resolve_allowed_farms,
)


def test_resolve_allowed_farms_scopes_non_global_account():
    farms = [
        {"farm_id": 1, "farm_name": "Farm 126", "farm_code": "Farm 126", "is_active": True},
        {"farm_id": 2, "farm_name": "Farm 157", "farm_code": "Farm 157", "is_active": True},
    ]

    assert [row["farm_id"] for row in _resolve_allowed_farms("Farm 126", farms)] == [1]
    assert [row["farm_id"] for row in _resolve_allowed_farms("Phòng Kinh doanh", farms)] == [1, 2]


def test_apply_cost_filters_date_lot_team_support():
    labor = pd.DataFrame(
        [
            {
                "lo_id": 10,
                "lo_code": "A1",
                "lo_type": "Lô thực",
                "doi_code": "NT1",
                "ngay_dt": pd.Timestamp("2026-05-01"),
                "is_ho_tro": False,
                "thanh_tien": 100,
            },
            {
                "lo_id": 11,
                "lo_code": "A2",
                "lo_type": "Lô thực",
                "doi_code": "NT2",
                "ngay_dt": pd.Timestamp("2026-05-02"),
                "is_ho_tro": True,
                "thanh_tien": 200,
            },
        ]
    )
    material = pd.DataFrame(
        [
            {
                "lo_id": 10,
                "lo_code": "A1",
                "lo_type": "Lô thực",
                "ngay_dt": pd.Timestamp("2026-05-01"),
                "thanh_tien": 50,
            },
            {
                "lo_id": 11,
                "lo_code": "A2",
                "lo_type": "Lô thực",
                "ngay_dt": pd.Timestamp("2026-06-01"),
                "thanh_tien": 500,
            },
        ]
    )

    filtered_labor, filtered_material = _apply_cost_filters(
        labor,
        material,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
        selected_lo_types=["Lô thực"],
        selected_los=["A1"],
        selected_dois=["NT1"],
        selected_seasons=pd.DataFrame(),
        include_support=False,
    )

    assert filtered_labor["thanh_tien"].sum() == 100
    assert filtered_material["thanh_tien"].sum() == 50


def test_material_type_fallback_classifier():
    assert _classify_material_type(pd.Series({"loai_vat_tu": "", "ten_vat_tu": "Phân hữu cơ"})) == "Phân bón"
    assert _classify_material_type(pd.Series({"loai_vat_tu": "", "ten_vat_tu": "Dây chống ngã"})) == "Vật tư tiêu hao"
