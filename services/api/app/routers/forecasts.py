from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query

from domain.forecast import CAT_FORECAST_WEEK_OPTIONS, build_weekly_cat_forecast
from ..deps import get_supabase_client


router = APIRouter(prefix="/forecasts", tags=["forecasts"])

STAGE_LOG_SELECT = (
    "id, ngay_thuc_hien, so_luong, giai_doan, is_deleted, "
    "dim_lo(lo_name, dim_farm(farm_name))"
)


def normalize_cut_bud_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten Supabase embedded rows into the domain forecast dataframe shape."""
    normalized = []
    for row in rows or []:
        lot = row.get("dim_lo") or {}
        farm = lot.get("dim_farm") or {}
        normalized.append(
            {
                "farm": farm.get("farm_name"),
                "lo": lot.get("lo_name"),
                "giai_doan": row.get("giai_doan"),
                "ngay_thuc_hien": row.get("ngay_thuc_hien"),
                "so_luong": row.get("so_luong"),
            }
        )
    return pd.DataFrame(normalized)


def _normalize_weeks(weeks: int) -> int:
    try:
        weeks = int(weeks)
    except (TypeError, ValueError):
        return 8
    return weeks if weeks in CAT_FORECAST_WEEK_OPTIONS else 8


def _fetch_cut_bud_rows(supabase, farm: str | None) -> list[dict[str, Any]]:
    query = (
        supabase.table("stage_logs")
        .select(STAGE_LOG_SELECT)
        .eq("is_deleted", False)
        .eq("giai_doan", "Cắt bắp")
    )
    if farm:
        query = query.eq("dim_lo.dim_farm.farm_name", farm)
    response = query.execute()
    return list(response.data or [])


@router.get("/cut-bud-weekly")
def get_cut_bud_weekly_forecast(
    farm: str | None = Query(default=None),
    weeks: int = Query(default=8, description="Forecast offset: 8 or 9 inclusive weeks"),
    supabase=Depends(get_supabase_client),
) -> dict[str, Any]:
    weeks_inclusive = _normalize_weeks(weeks)
    rows = _fetch_cut_bud_rows(supabase, farm)
    df = normalize_cut_bud_rows(rows)
    forecast = build_weekly_cat_forecast(df, forecast_weeks_inclusive=weeks_inclusive)

    payload_rows = [
        {
            "farm": str(row["farm"]),
            "year": int(row["year"]),
            "week": int(row["week"]),
            "forecast_bunches": int(row["forecast_bunches"]),
        }
        for row in forecast.to_dict(orient="records")
    ]
    return {
        "farm": farm,
        "weeks_inclusive": weeks_inclusive,
        "rows": payload_rows,
    }
