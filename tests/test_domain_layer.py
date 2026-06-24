import pandas as pd

from domain.lifecycle import build_batch_label_map, build_next_season_maps, get_estimated_rate, get_kg_per_tree
from domain.forecast import build_weekly_cat_forecast


def test_lifecycle_domain_helpers_match_current_business_rules():
    assert get_estimated_rate("chich_bap") == 0.95
    assert get_estimated_rate("cat_bap") == 0.95
    assert get_estimated_rate("thu_hoach") == 0.90
    assert get_estimated_rate("trong_moi") == 1.0
    assert get_kg_per_tree("F0") == 15
    assert get_kg_per_tree("F1") == 18


def test_batch_label_map_adds_batch_numbers_only_when_lot_has_multiple_plantings():
    df_lots = pd.DataFrame([
        {"id": 25, "lo": "3B", "ngay_trong": "2025-04-23"},
        {"id": 7, "lo": "3B", "ngay_trong": "2025-10-13"},
        {"id": 14, "lo": "8A", "ngay_trong": "2025-11-28"},
    ])

    labels = build_batch_label_map(df_lots)

    assert labels[25] == "3B (đợt 1)"
    assert labels[7] == "3B (đợt 2)"
    assert labels[14] == "8A"


def test_next_season_map_only_closes_old_season_when_next_season_has_chich_bap():
    df_seasons = pd.DataFrame([
        {"base_lot_id": 1, "vu": "F0", "ngay_bat_dau": "2025-01-01"},
        {"base_lot_id": 1, "vu": "F1", "ngay_bat_dau": "2025-10-01"},
        {"base_lot_id": 2, "vu": "F0", "ngay_bat_dau": "2025-02-01"},
        {"base_lot_id": 2, "vu": "F1", "ngay_bat_dau": "2025-11-01"},
    ])
    df_stg = pd.DataFrame([
        {"base_lot_id": 1, "giai_doan": "Chích bắp", "ngay_thuc_hien": "2025-10-10"},
    ])

    next_season, next_producing = build_next_season_maps(df_seasons, df_stg)

    assert next_season[(1, "F0")] == pd.Timestamp("2025-10-01")
    assert next_season[(1, "F1")] is None
    assert next_season[(2, "F0")] is None
    assert (1, "F1") in next_producing


def test_weekly_cat_forecast_keeps_total_quantity_after_micro_spread():
    df_stg = pd.DataFrame([
        {
            "farm": "Farm 126",
            "giai_doan": "Cắt bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 88,
        },
        {
            "farm": "Farm 157",
            "giai_doan": "Chích bắp",
            "ngay_thuc_hien": "2026-06-10",
            "so_luong": 999,
        },
    ])

    result = build_weekly_cat_forecast(df_stg, forecast_weeks_inclusive=8)

    assert int(result["forecast_bunches"].sum()) == 88
    assert set(result["farm"]) == {"Farm 126"}
    assert {"farm", "year", "week", "forecast_bunches"}.issubset(result.columns)
