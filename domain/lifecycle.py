from __future__ import annotations

from typing import Any

import pandas as pd

F0_DAYS_TO_CHICH = 180
F0_DAYS_TO_CAT = 194
F0_DAYS_TO_THU = 264
FN_CYCLE_DAYS = 174
FN_DAYS_CHICH_OFFSET = 90
FN_DAYS_CAT_OFFSET = 104
FN_DAYS_THU_OFFSET = 174
MAX_GENERATION = 5

KG_PER_TREE_F0 = 15
KG_PER_TREE_FN = 18

LOSS_RATE_TO_CHICH = 0.05
LOSS_RATE_TO_THU = 0.10

STAGE_OFFSETS = {
    "Chích bắp": {"f0": F0_DAYS_TO_CHICH, "fn": FN_DAYS_CHICH_OFFSET},
    "Cắt bắp": {"f0": F0_DAYS_TO_CAT, "fn": FN_DAYS_CAT_OFFSET},
    "Thu hoạch": {"f0": F0_DAYS_TO_THU, "fn": FN_DAYS_THU_OFFSET},
}

DESTRUCTION_STAGE_MAP = {
    "Trước chích bắp": "Chích bắp",
    "Trước cắt bắp": "Cắt bắp",
    "Trước thu hoạch": "Thu hoạch",
}


def get_estimated_rate(stage: str) -> float:
    """Return remaining production ratio after standard stage loss."""
    if stage in ("chich_bap", "cat_bap"):
        return 1 - LOSS_RATE_TO_CHICH
    if stage == "thu_hoach":
        return 1 - LOSS_RATE_TO_THU
    return 1.0


def get_kg_per_tree(vu: str) -> int:
    """Return standard kg/bunch by crop generation."""
    return KG_PER_TREE_F0 if vu == "F0" else KG_PER_TREE_FN


def safe_int_id(value: Any) -> int | None:
    """Return an integer id when possible; otherwise None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            return int(float(value))
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def build_next_season_maps(
    df_seasons: pd.DataFrame,
    df_stg_all: pd.DataFrame,
) -> tuple[dict[tuple[int, str], pd.Timestamp | None], set[tuple[int, str]]]:
    """Return next producing season boundaries keyed by (base_lot_id, vu)."""
    next_season: dict[tuple[int, str], pd.Timestamp | None] = {}
    next_producing: set[tuple[int, str]] = set()
    if df_seasons.empty or "base_lot_id" not in df_seasons.columns:
        return next_season, next_producing

    season_rows = df_seasons[df_seasons["base_lot_id"].notna()].copy()
    season_rows["_base_lot_id_int"] = season_rows["base_lot_id"].apply(safe_int_id)
    season_rows = season_rows[season_rows["_base_lot_id_int"].notna()]
    if (
        not df_stg_all.empty
        and "base_lot_id" in df_stg_all.columns
        and "giai_doan" in df_stg_all.columns
    ):
        stg_chich_all = df_stg_all[df_stg_all["giai_doan"] == "Chích bắp"]
        stg_chich_ids = pd.to_numeric(stg_chich_all["base_lot_id"], errors="coerce")
        for _, s_row in season_rows.iterrows():
            s_blid = int(s_row["_base_lot_id_int"])
            s_vu = s_row["vu"]
            s_start = pd.to_datetime(s_row["ngay_bat_dau"])
            chich_batch = stg_chich_all[stg_chich_ids == s_blid]
            if not chich_batch.empty and "ngay_thuc_hien" in chich_batch.columns:
                chich_in = chich_batch[
                    pd.to_datetime(chich_batch["ngay_thuc_hien"], errors="coerce") >= s_start
                ]
                if not chich_in.empty:
                    next_producing.add((s_blid, s_vu))

    for blid, blid_grp in season_rows.groupby("_base_lot_id_int"):
        blid_int = int(blid)
        sorted_s = blid_grp.sort_values("ngay_bat_dau").drop_duplicates("vu")
        vu_list = sorted_s[["vu", "ngay_bat_dau"]].values.tolist()
        for i, (vu_val, _start_dt) in enumerate(vu_list):
            if i + 1 < len(vu_list):
                next_vu = vu_list[i + 1][0]
                if (blid_int, next_vu) in next_producing:
                    next_season[(blid_int, vu_val)] = pd.to_datetime(vu_list[i + 1][1])
                else:
                    next_season[(blid_int, vu_val)] = None
            else:
                next_season[(blid_int, vu_val)] = None
    return next_season, next_producing


def build_batch_label_map(df_lots_trong_moi: pd.DataFrame) -> dict[Any, str]:
    """Build display labels for lots with multiple planting batches."""
    labels: dict[Any, str] = {}
    required = {"id", "lo"}
    if df_lots_trong_moi.empty or not required.issubset(df_lots_trong_moi.columns):
        return labels

    for lo_name_grp, grp_df in df_lots_trong_moi.groupby("lo"):
        if len(grp_df) > 1:
            sorted_grp = grp_df.sort_values("ngay_trong") if "ngay_trong" in grp_df.columns else grp_df
            for i, (_, b_row) in enumerate(sorted_grp.iterrows(), 1):
                labels[b_row["id"]] = f"{lo_name_grp} (đợt {i})"
        else:
            for _, b_row in grp_df.iterrows():
                labels[b_row["id"]] = lo_name_grp
    return labels

