from collections import defaultdict
import re
import unicodedata

import pandas as pd


HARVEST_COST_KEYWORD = "THUHOACH"
CUT_STAGE_NAME = "Cắt bắp"
BUNCH_CARE_REQUIRES_CUT_TOKENS = (
    "BAOBUONG",
    "BAOBUP",
    "BEHOA",
    "LATRAU",
    "CHAMSOCBUONG",
    "GOBAO",
    "SUABAO",
    "VESINHBUONG",
    "VENLA",
    "DOSIZECHUOI",
)
STAGE_QUANTITY_CAPPED_TOKENS = BUNCH_CARE_REQUIRES_CUT_TOKENS + ("CATBAP",)


def money(value) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def normalize_label(value) -> str:
    text = str(value or "").strip().replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9+]+", "", text.upper())


def to_timestamp(value):
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.tz_localize(None) if getattr(ts, "tzinfo", None) else ts


def is_harvest_related_cost(cost: dict) -> bool:
    fields = (
        "cong_doan",
        "category",
        "detail",
        "ma_cv",
        "ma_cv_chuan",
        "ma_khoan_muc_cp",
        "hang_muc",
        "scope_label",
    )
    return any(HARVEST_COST_KEYWORD in normalize_label(cost.get(field)) for field in fields)


def _normalized_cost_text(cost: dict) -> str:
    fields = (
        "cong_doan",
        "category",
        "detail",
        "ma_cv",
        "ma_cv_chuan",
        "ma_khoan_muc_cp",
        "hang_muc",
    )
    return "|".join(normalize_label(cost.get(field)) for field in fields)


def is_bunch_care_requiring_cut(cost: dict) -> bool:
    text = _normalized_cost_text(cost)
    return any(token in text for token in BUNCH_CARE_REQUIRES_CUT_TOKENS)


def is_stage_quantity_capped_cost(cost: dict) -> bool:
    text = _normalized_cost_text(cost)
    return any(token in text for token in STAGE_QUANTITY_CAPPED_TOKENS)


def _group_rows_by_base_lot(rows):
    grouped = defaultdict(list)
    for row in rows or []:
        base_lot_id = row.get("base_lot_id")
        if base_lot_id is not None and not pd.isna(base_lot_id):
            grouped[int(base_lot_id)].append(dict(row))
    return grouped


def harvest_quantity_for_batch_until(harvest_rows_by_batch: dict, base_lot_id, cost_dt) -> float:
    cost_ts = to_timestamp(cost_dt)
    if base_lot_id is None or cost_ts is None:
        return 0.0
    total = 0.0
    for row in harvest_rows_by_batch.get(int(base_lot_id), []):
        harvest_ts = to_timestamp(row.get("ngay_thu_hoach"))
        if harvest_ts is not None and harvest_ts <= cost_ts:
            total += money(row.get("so_luong"))
    return total


def build_harvest_rows_by_batch(harvest_rows):
    return _group_rows_by_base_lot(harvest_rows)


def build_stage_rows_by_batch(stage_rows):
    return _group_rows_by_base_lot(stage_rows)


def stage_quantity_for_batch_until(stage_rows_by_batch: dict, base_lot_id, stage_name: str, cost_dt) -> float:
    cost_ts = to_timestamp(cost_dt)
    if base_lot_id is None or cost_ts is None:
        return 0.0
    total = 0.0
    for row in stage_rows_by_batch.get(int(base_lot_id), []):
        if str(row.get("giai_doan") or "") != stage_name:
            continue
        stage_ts = to_timestamp(row.get("ngay_thuc_hien"))
        if stage_ts is not None and stage_ts <= cost_ts:
            total += money(row.get("so_luong"))
    return total


def build_batch_lifecycle(planting_rows, season_rows=None, harvest_rows=None, destruction_rows=None):
    seasons_by_batch = _group_rows_by_base_lot(season_rows)
    harvest_by_batch = _group_rows_by_base_lot(harvest_rows)
    destruction_by_batch = _group_rows_by_base_lot(destruction_rows)
    processed = []

    for row in planting_rows or []:
        batch = dict(row)
        base_lot_id = batch.get("id") or batch.get("base_lot_id")
        if base_lot_id is None or pd.isna(base_lot_id):
            processed.append(batch)
            continue

        base_lot_id = int(base_lot_id)
        start_ts = to_timestamp(batch.get("ngay_trong"))
        batch["ngay_trong_ts"] = start_ts

        season_rows_for_batch = seasons_by_batch.get(base_lot_id, [])
        has_open_season = any(to_timestamp(s.get("ngay_ket_thuc_thuc_te")) is None for s in season_rows_for_batch)
        end_candidates = [
            to_timestamp(s.get("ngay_ket_thuc_thuc_te"))
            for s in season_rows_for_batch
            if to_timestamp(s.get("ngay_ket_thuc_thuc_te")) is not None
        ]

        active_until = None
        end_reason = ""
        if season_rows_for_batch and not has_open_season and end_candidates:
            active_until = max(end_candidates)
            end_reason = "season_end"

        if active_until is None and not has_open_season:
            events = []
            for h in harvest_by_batch.get(base_lot_id, []):
                events.append((to_timestamp(h.get("ngay_thu_hoach")), money(h.get("so_luong")), "harvest_full"))
            for d in destruction_by_batch.get(base_lot_id, []):
                events.append((to_timestamp(d.get("ngay_xuat_huy")), money(d.get("so_luong")), "destruction_full"))
            events = [(dt, qty, reason) for dt, qty, reason in events if dt is not None and (start_ts is None or dt >= start_ts)]
            events.sort(key=lambda item: item[0])
            total_removed = 0.0
            target_trees = money(batch.get("so_luong"))
            for event_dt, qty, reason in events:
                total_removed += qty
                if target_trees > 0 and total_removed >= target_trees:
                    active_until = event_dt
                    end_reason = reason
                    break

        batch["active_until_ts"] = active_until
        batch["active_until"] = active_until.date() if active_until is not None else None
        batch["lifecycle_end_reason"] = end_reason
        processed.append(batch)

    return processed


def is_batch_active_on_date(batch: dict, cost_dt) -> bool:
    cost_ts = to_timestamp(cost_dt)
    start_ts = batch.get("ngay_trong_ts") or to_timestamp(batch.get("ngay_trong"))
    if cost_ts is None or start_ts is None:
        return False
    if start_ts > cost_ts:
        return False
    active_until = batch.get("active_until_ts") or to_timestamp(batch.get("active_until"))
    return active_until is None or cost_ts <= active_until


def lot_weight_on_date(lot_id, cost_dt, plantings_by_lot: dict, lot_meta_by_id: dict) -> float:
    active_rows = [
        row for row in plantings_by_lot.get(lot_id, [])
        if is_batch_active_on_date(row, cost_dt)
    ]
    if not active_rows:
        return 0.0

    planted_area = sum(money(row.get("dien_tich_trong")) for row in active_rows)
    if planted_area > 0:
        return planted_area

    lot_area = money((lot_meta_by_id.get(lot_id) or {}).get("area_ha"))
    active_trees = sum(money(row.get("so_luong")) for row in active_rows)
    all_trees = sum(money(row.get("so_luong")) for row in plantings_by_lot.get(lot_id, []))
    if lot_area > 0 and active_trees > 0 and all_trees > 0:
        return lot_area * min(1.0, active_trees / all_trees)
    if lot_area > 0:
        return lot_area
    return active_trees
