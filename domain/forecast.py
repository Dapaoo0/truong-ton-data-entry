from __future__ import annotations

from datetime import timedelta

import pandas as pd

CAT_FORECAST_WEEK_OPTIONS = [8, 9]
MICRO_WINDOW_HALF = 7
MICRO_SIGMA = 3.0


def build_weekly_cat_forecast(
    df_stg: pd.DataFrame,
    forecast_weeks_inclusive: int = 8,
) -> pd.DataFrame:
    """Group harvest forecast from cut-bud logs by ISO year/week."""
    empty_cols = ["farm", "year", "week", "forecast_bunches"]
    if df_stg is None or df_stg.empty or "giai_doan" not in df_stg.columns:
        return pd.DataFrame(columns=empty_cols)

    df_cat = df_stg[df_stg["giai_doan"] == "Cắt bắp"].copy()
    if df_cat.empty:
        return pd.DataFrame(columns=empty_cols)

    try:
        forecast_weeks_inclusive = int(forecast_weeks_inclusive)
    except (TypeError, ValueError):
        forecast_weeks_inclusive = 8
    if forecast_weeks_inclusive not in CAT_FORECAST_WEEK_OPTIONS:
        forecast_weeks_inclusive = 8
    forecast_days_from_cut = (forecast_weeks_inclusive - 1) * 7

    micro_offsets = list(range(-MICRO_WINDOW_HALF, MICRO_WINDOW_HALF + 1))
    raw_weights = [
        pow(2.718281828459045, -0.5 * pow(offset / MICRO_SIGMA, 2))
        for offset in micro_offsets
    ]
    total_weight = sum(raw_weights) or 1
    micro_weights = [weight / total_weight for weight in raw_weights]

    rows = []
    for _, row in df_cat.iterrows():
        ngay_cat = pd.to_datetime(row.get("ngay_thuc_hien"), errors="coerce")
        if pd.isna(ngay_cat):
            continue
        try:
            qty = int(row.get("so_luong", 0) or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue

        farm_name = row.get("farm") or "Không rõ farm"
        midpoint = ngay_cat + timedelta(days=forecast_days_from_cut)
        for offset, weight in zip(micro_offsets, micro_weights):
            harvest_day = midpoint + timedelta(days=offset)
            iso = harvest_day.isocalendar()
            rows.append(
                {
                    "farm": farm_name,
                    "year": int(iso.year),
                    "week": int(iso.week),
                    "_qty_float": qty * weight,
                }
            )

    if not rows:
        return pd.DataFrame(columns=empty_cols)

    weekly = pd.DataFrame(rows).groupby(["farm", "year", "week"], as_index=False)["_qty_float"].sum()
    total_target = int(round(weekly["_qty_float"].sum()))
    weekly["_floor"] = weekly["_qty_float"].apply(lambda x: int(x))
    weekly["_remainder"] = weekly["_qty_float"] - weekly["_floor"]
    deficit = total_target - int(weekly["_floor"].sum())
    weekly["forecast_bunches"] = weekly["_floor"]
    if deficit > 0:
        idx = weekly.sort_values("_remainder", ascending=False).head(deficit).index
        weekly.loc[idx, "forecast_bunches"] += 1

    return weekly[empty_cols].sort_values(["year", "week", "farm"])
