"""Pure helpers for allocating harvested banana bunches by hand position."""

from __future__ import annotations

import math
from typing import Any

try:
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - optional production dependency
    cp_model = None


DEFAULT_SKU_ROWS = [
    {
        "market_priority": 1,
        "market": "Nhật",
        "sku_priority": 1,
        "sku": "27CP",
        "hand_from": 1,
        "hand_to": 4,
        "demand": 520,
        "unit": "Thùng",
    },
    {
        "market_priority": 1,
        "market": "Nhật",
        "sku_priority": 2,
        "sku": "6H",
        "hand_from": 5,
        "hand_to": 7,
        "demand": 240,
        "unit": "Thùng",
    },
]


OPTIMIZER_SKU_RULES = {
    "27CP": {
        "markets": ["Nhật"],
        "group": "Phần Ngọn",
        "description": "Quả to, mập nhất. Vùng nải mẹ 1-5; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(1, 5)],
    },
    "8H": {
        "markets": ["Hàn"],
        "group": "Phần Ngọn",
        "description": "Vùng nải mẹ 1-4 cho container Hàn; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(1, 4)],
    },
    "6H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Vùng nải mẹ 5-7; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(5, 7)],
    },
    "30CP": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Vùng nải mẹ 1-9; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(1, 9)],
    },
    "5H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Vùng nải mẹ 8-10; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(8, 10)],
    },
    "5/6H": {
        "markets": ["Hàn"],
        "group": "Khúc Giữa",
        "description": "Vùng nải mẹ 5-9; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(5, 9)],
    },
    "15CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Vùng nải mẹ 10-12; thuật toán có thể chọn mọi khoảng con liền kề bên trong vùng này.",
        "ranges": [(10, 12)],
    },
}

MARKET_MAX_CONTAINER_RECIPES = {
    "Nhật": [
        {"sku": "27CP", "hand_from": 1, "hand_to": 4},
        {"sku": "6H", "hand_from": 5, "hand_to": 7},
        {"sku": "5H", "hand_from": 8, "hand_to": 10},
    ],
    "Hàn": [
        {"sku": "8H", "hand_from": 1, "hand_to": 4},
        {"sku": "5/6H", "hand_from": 5, "hand_to": 9},
        {"sku": "15CP", "hand_from": 10, "hand_to": 12},
    ],
}

BEAM_WIDTH = 250
CP_SAT_TIME_LIMIT_SECONDS = 60
WEIGHT_SCALE = 12000


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_sku_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize UI rows into stable keys used by the allocator."""
    normalized = []
    for row in rows:
        normalized.append(
            {
                "market_priority": _to_int(
                    row.get("market_priority", row.get("Ưu tiên thị trường")), 999
                ),
                "market": str(row.get("market", row.get("Thị trường", "")) or "").strip(),
                "sku_priority": _to_int(
                    row.get("sku_priority", row.get("Ưu tiên loại hàng")), 999
                ),
                "sku": str(row.get("sku", row.get("Mã hàng", "")) or "").strip(),
                "hand_from": _to_int(row.get("hand_from", row.get("Nải từ")), 0),
                "hand_to": _to_int(row.get("hand_to", row.get("Nải đến")), 0),
                "demand": _to_float(row.get("demand", row.get("Nhu cầu")), 0.0),
                "unit": str(row.get("unit", row.get("Đơn vị", "Thùng")) or "Thùng").strip(),
            }
        )
    return normalized


def _requested_boxes(row: dict[str, Any], boxes_per_container: int) -> int:
    demand = max(0.0, row["demand"])
    unit = row["unit"]
    return (
        int(math.ceil(demand * boxes_per_container))
        if unit.lower().startswith("cont")
        else int(math.ceil(demand))
    )


def _contiguous_subranges(hand_from: int, hand_to: int) -> list[tuple[int, int]]:
    ranges = []
    for hand_count in range(1, hand_to - hand_from + 2):
        for start in range(hand_from, hand_to - hand_count + 2):
            ranges.append((start, start + hand_count - 1))
    return ranges


def _valid_optimizer_ranges(row: dict[str, Any], hands_per_bunch: int) -> list[tuple[int, int]]:
    sku = row["sku"].upper()
    sku_rule = OPTIMIZER_SKU_RULES.get(sku, {})
    allowed_markets = sku_rule.get("markets", [])
    if allowed_markets and row.get("market") not in allowed_markets:
        return []
    ranges = sku_rule.get("ranges")
    expand_subranges = bool(ranges)
    if not ranges and row.get("hand_from") and row.get("hand_to"):
        ranges = [(row["hand_from"], row["hand_to"])]

    valid_ranges = []
    for hand_from, hand_to in ranges or []:
        if 1 <= hand_from <= hand_to <= hands_per_bunch:
            candidate_ranges = (
                _contiguous_subranges(hand_from, hand_to)
                if expand_subranges
                else [(hand_from, hand_to)]
            )
            for candidate in candidate_ranges:
                if candidate not in valid_ranges:
                    valid_ranges.append(candidate)
    return valid_ranges


def _allocate_candidate_range(
    row: dict[str, Any],
    original_index: int,
    remaining_hands: dict[int, int],
    hand_from: int,
    hand_to: int,
    kg_per_hand: float,
    kg_per_box: float,
    boxes_per_container: int,
    processing_order: int,
    range_rank: int,
) -> tuple[dict[str, Any], dict[int, int], dict[str, float]]:
    hand_range = list(range(hand_from, hand_to + 1))
    hand_count = len(hand_range)
    kg_per_bunch_for_sku = hand_count * kg_per_hand
    requested_boxes = _requested_boxes(row, boxes_per_container)
    bunches_needed = (
        int(math.ceil((requested_boxes * kg_per_box) / kg_per_bunch_for_sku))
        if kg_per_bunch_for_sku > 0
        else 0
    )
    available_bunches = min(remaining_hands[hand] for hand in hand_range)
    bunches_allocated = min(bunches_needed, available_bunches)

    next_remaining = dict(remaining_hands)
    for hand in hand_range:
        next_remaining[hand] -= bunches_allocated

    kg_allocated = bunches_allocated * kg_per_bunch_for_sku
    boxes_capacity = int(math.floor(kg_allocated / kg_per_box)) if kg_per_box > 0 else 0
    boxes_fulfilled = min(requested_boxes, boxes_capacity)
    short_boxes = max(0, requested_boxes - boxes_fulfilled)
    extra_kg_from_rounding = max(0.0, kg_allocated - boxes_fulfilled * kg_per_box)
    hand_units_consumed = bunches_allocated * hand_count

    result_row = {
        "processing_order": processing_order,
        "original_index": original_index,
        "market_priority": row["market_priority"],
        "market": row["market"],
        "sku_priority": row["sku_priority"],
        "sku": row["sku"].upper(),
        "hand_from": hand_from,
        "hand_to": hand_to,
        "hand_count": hand_count,
        "range_rank": range_rank,
        "range_label": f"{hand_from}-{hand_to}",
        "requested_boxes": requested_boxes,
        "kg_per_bunch_for_sku": kg_per_bunch_for_sku,
        "bunches_needed": bunches_needed,
        "bunches_allocated": bunches_allocated,
        "kg_allocated": kg_allocated,
        "boxes_capacity": boxes_capacity,
        "boxes_fulfilled": boxes_fulfilled,
        "containers_fulfilled": boxes_fulfilled / boxes_per_container,
        "short_boxes": short_boxes,
        "short_containers": short_boxes / boxes_per_container,
        "extra_kg_from_rounding": extra_kg_from_rounding,
        "hand_units_consumed": hand_units_consumed,
        "is_fulfilled": short_boxes == 0,
    }
    penalties = {
        "short_boxes": float(short_boxes),
        "hand_units_consumed": float(hand_units_consumed),
        "range_preference": float(range_rank),
        "extra_kg_from_rounding": float(extra_kg_from_rounding),
    }
    return result_row, next_remaining, penalties


def _optimizer_state_key(state: dict[str, Any]) -> tuple:
    return (
        tuple(state["shortage_vector"]),
        state["active_bunches_estimated"],
        state["segment_count"],
        state["hand_units_consumed"],
        state["range_preference"],
        round(state["extra_kg_from_rounding"], 6),
    )


def _active_bunches_from_remaining(total_bunches: int, remaining_hands: dict[int, int]) -> int:
    if not remaining_hands:
        return 0
    return max(total_bunches - remaining_qty for remaining_qty in remaining_hands.values())


def _allocate_bunches_beam(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    beam_width: int = BEAM_WIDTH,
    solver_status: str = "APPROXIMATE",
    solver_backend: str = "beam_search",
) -> dict[str, Any]:
    """Optimize SKU allocation by trying candidate hand ranges per SKU.

    The search keeps a beam of low-loss plans. The loss is lexicographic:
    shortage for higher-priority rows dominates shortage for lower-priority
    rows, then the optimizer minimizes the number of whole bunches opened.
    Splitting one order row across multiple contiguous subranges is allowed,
    but segment count is penalized immediately after opened bunches so a split
    only survives when it improves fulfillment or lowers whole-bunch usage.
    """
    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))
    beam_width = max(1, _to_int(beam_width, BEAM_WIDTH))

    empty_summary = {
        "total_bunches": total_bunches,
        "source_kg": 0.0,
        "kg_per_hand": 0.0,
        "source_boxes_capacity": 0,
        "source_cont_capacity": 0.0,
        "fulfilled_boxes": 0,
        "fulfilled_containers": 0.0,
        "short_boxes": 0,
        "short_containers": 0.0,
        "optimizer_loss": 0.0,
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }
    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return {
            "rows": [],
            "detail_rows": [],
            "remaining_hands": {},
            "summary": empty_summary,
            "loss": {},
            "solver_status": "NO_SOLUTION",
            "solver_backend": solver_backend,
        }

    normalized_rows = normalize_sku_rows(sku_rows)
    sorted_rows = sorted(
        enumerate(normalized_rows),
        key=lambda item: (
            item[1]["market_priority"],
            item[1]["sku_priority"],
            item[0],
        ),
    )
    candidate_rows = []
    for original_index, row in sorted_rows:
        row["sku"] = row["sku"].upper()
        is_invalid = not row["sku"] or row["demand"] <= 0
        if is_invalid:
            continue
        ranges = _valid_optimizer_ranges(row, hands_per_bunch)
        if not ranges:
            continue
        candidate_rows.append((original_index, row, ranges))

    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    kg_per_hand = kg_per_bunch / hands_per_bunch
    states = [{
        "remaining_hands": remaining_hands,
        "rows": [],
        "shortage_vector": [],
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "hand_units_consumed": 0.0,
        "range_preference": 0.0,
        "extra_kg_from_rounding": 0.0,
    }]

    for processing_order, (original_index, row, ranges) in enumerate(candidate_rows, start=1):
        next_states = []
        for state in states:
            for range_rank, (hand_from, hand_to) in enumerate(ranges):
                result_row, next_remaining, penalties = _allocate_candidate_range(
                    row,
                    original_index,
                    state["remaining_hands"],
                    hand_from,
                    hand_to,
                    kg_per_hand,
                    kg_per_box,
                    boxes_per_container,
                    processing_order,
                    range_rank,
                )
                active_bunches_estimated = _active_bunches_from_remaining(total_bunches, next_remaining)
                next_states.append({
                    "remaining_hands": next_remaining,
                    "rows": state["rows"] + [result_row],
                    "shortage_vector": state["shortage_vector"] + [result_row["short_boxes"]],
                    "active_bunches_estimated": active_bunches_estimated,
                    "segment_count": state["segment_count"] + (1 if result_row["bunches_allocated"] > 0 else 0),
                    "hand_units_consumed": state["hand_units_consumed"] + penalties["hand_units_consumed"],
                    "range_preference": state["range_preference"] + penalties["range_preference"],
                    "extra_kg_from_rounding": state["extra_kg_from_rounding"] + penalties["extra_kg_from_rounding"],
                })

        states = sorted(next_states, key=_optimizer_state_key)[:beam_width]

    if not states:
        source_kg = total_bunches * kg_per_bunch
        empty_summary.update({
            "source_kg": source_kg,
            "kg_per_hand": kg_per_hand,
            "source_boxes_capacity": int(math.floor(source_kg / kg_per_box)),
            "source_cont_capacity": int(math.floor(source_kg / kg_per_box)) / boxes_per_container,
        })
        return {
            "rows": [],
            "detail_rows": [],
            "remaining_hands": remaining_hands,
            "summary": empty_summary,
            "loss": {},
            "solver_status": "NO_SOLUTION",
            "solver_backend": solver_backend,
        }

    best_state = sorted(states, key=_optimizer_state_key)[0]
    fulfilled_boxes = sum(row["boxes_fulfilled"] for row in best_state["rows"])
    short_boxes_total = sum(row["short_boxes"] for row in best_state["rows"])
    source_kg = total_bunches * kg_per_bunch
    shortage_loss = sum(
        short_boxes * (len(best_state["shortage_vector"]) - index)
        for index, short_boxes in enumerate(best_state["shortage_vector"])
    )
    optimizer_loss = (
        shortage_loss * 1_000_000
        + best_state["active_bunches_estimated"] * 100_000
        + best_state["segment_count"] * 10_000
        + best_state["hand_units_consumed"] * 10
        + best_state["range_preference"] * 100
        + best_state["extra_kg_from_rounding"]
    )
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "source_boxes_capacity": int(math.floor(source_kg / kg_per_box)),
        "source_cont_capacity": int(math.floor(source_kg / kg_per_box)) / boxes_per_container,
        "fulfilled_boxes": fulfilled_boxes,
        "fulfilled_containers": fulfilled_boxes / boxes_per_container,
        "short_boxes": short_boxes_total,
        "short_containers": short_boxes_total / boxes_per_container,
        "optimizer_loss": optimizer_loss,
        "active_bunches_estimated": best_state["active_bunches_estimated"],
        "segment_count": best_state["segment_count"],
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }
    loss = {
        "shortage_vector": best_state["shortage_vector"],
        "shortage_loss": shortage_loss,
        "active_bunches_estimated": best_state["active_bunches_estimated"],
        "segment_count": best_state["segment_count"],
        "hand_units_consumed": best_state["hand_units_consumed"],
        "range_preference": best_state["range_preference"],
        "extra_kg_from_rounding": best_state["extra_kg_from_rounding"],
        "optimizer_loss": optimizer_loss,
    }
    return {
        "rows": best_state["rows"],
        "detail_rows": best_state["rows"],
        "remaining_hands": best_state["remaining_hands"],
        "summary": summary,
        "loss": loss,
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }


def _cp_status_name(status: int) -> str:
    if cp_model is None:
        return "APPROXIMATE"
    if status == cp_model.OPTIMAL:
        return "OPTIMAL"
    if status == cp_model.FEASIBLE:
        return "FEASIBLE"
    return "NO_SOLUTION"


def _build_candidate_rows(
    sku_rows: list[dict[str, Any]],
    hands_per_bunch: int,
) -> list[tuple[int, dict[str, Any], list[tuple[int, int]]]]:
    normalized_rows = normalize_sku_rows(sku_rows)
    sorted_rows = sorted(
        enumerate(normalized_rows),
        key=lambda item: (
            item[1]["market_priority"],
            item[1]["sku_priority"],
            item[0],
        ),
    )
    candidate_rows = []
    for original_index, row in sorted_rows:
        row["sku"] = row["sku"].upper()
        if not row["sku"] or row["demand"] <= 0:
            continue
        ranges = _valid_optimizer_ranges(row, hands_per_bunch)
        if ranges:
            candidate_rows.append((original_index, row, ranges))
    return candidate_rows


def _empty_optimized_result(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    kg_per_box: float,
    boxes_per_container: int,
    solver_status: str,
    solver_backend: str,
) -> dict[str, Any]:
    source_kg = total_bunches * kg_per_bunch if total_bunches > 0 and kg_per_bunch > 0 else 0.0
    source_boxes = int(math.floor(source_kg / kg_per_box)) if kg_per_box > 0 else 0
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_bunch / hands_per_bunch if hands_per_bunch > 0 else 0.0,
        "source_boxes_capacity": source_boxes,
        "source_cont_capacity": source_boxes / boxes_per_container if boxes_per_container else 0.0,
        "fulfilled_boxes": 0,
        "fulfilled_containers": 0.0,
        "short_boxes": 0,
        "short_containers": 0.0,
        "optimizer_loss": 0.0,
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }
    return {
        "rows": [],
        "detail_rows": [],
        "remaining_hands": {hand: total_bunches for hand in range(1, hands_per_bunch + 1)},
        "summary": summary,
        "loss": {},
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }


def _allocate_bunches_cpsat(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    time_limit_seconds: int = CP_SAT_TIME_LIMIT_SECONDS,
) -> dict[str, Any] | None:
    if cp_model is None:
        return None

    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))
    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return _empty_optimized_result(
            total_bunches,
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "ortools_cp_sat",
        )

    candidate_rows = _build_candidate_rows(sku_rows, hands_per_bunch)
    if not candidate_rows:
        return _empty_optimized_result(
            total_bunches,
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "ortools_cp_sat",
        )

    model = cp_model.CpModel()
    kg_per_hand_units = int(round((kg_per_bunch * WEIGHT_SCALE) / hands_per_bunch))
    kg_per_box_units = max(1, int(round(kg_per_box * WEIGHT_SCALE)))
    row_records: list[dict[str, Any]] = []
    all_segments: list[dict[str, Any]] = []

    for processing_order, (original_index, row, ranges) in enumerate(candidate_rows, start=1):
        requested_boxes = _requested_boxes(row, boxes_per_container)
        row_record = {
            "processing_order": processing_order,
            "original_index": original_index,
            "row": row,
            "requested_boxes": requested_boxes,
            "segments": [],
        }
        for range_rank, (hand_from, hand_to) in enumerate(ranges):
            hand_count = hand_to - hand_from + 1
            kg_per_bunch_units = hand_count * kg_per_hand_units
            var_prefix = f"r{processing_order}_c{range_rank}"
            bunches_var = model.NewIntVar(0, total_bunches, f"{var_prefix}_bunches")
            boxes_var = model.NewIntVar(0, requested_boxes, f"{var_prefix}_boxes")
            used_var = model.NewBoolVar(f"{var_prefix}_used")
            model.Add(boxes_var * kg_per_box_units <= bunches_var * kg_per_bunch_units)
            model.Add(bunches_var <= total_bunches * used_var)
            model.Add(bunches_var >= used_var)
            segment = {
                "processing_order": processing_order,
                "original_index": original_index,
                "row": row,
                "range_rank": range_rank,
                "hand_from": hand_from,
                "hand_to": hand_to,
                "hand_count": hand_count,
                "hands": list(range(hand_from, hand_to + 1)),
                "kg_per_bunch_units": kg_per_bunch_units,
                "bunches_var": bunches_var,
                "boxes_var": boxes_var,
                "used_var": used_var,
            }
            row_record["segments"].append(segment)
            all_segments.append(segment)

        fulfilled_var = model.NewIntVar(0, requested_boxes, f"r{processing_order}_fulfilled")
        short_var = model.NewIntVar(0, requested_boxes, f"r{processing_order}_short")
        model.Add(fulfilled_var == sum(segment["boxes_var"] for segment in row_record["segments"]))
        model.Add(fulfilled_var <= requested_boxes)
        model.Add(short_var == requested_boxes - fulfilled_var)
        row_record["fulfilled_var"] = fulfilled_var
        row_record["short_var"] = short_var
        row_records.append(row_record)

    hand_usage_exprs = {}
    for hand in range(1, hands_per_bunch + 1):
        hand_usage_exprs[hand] = sum(
            segment["bunches_var"] for segment in all_segments if hand in segment["hands"]
        )
        model.Add(hand_usage_exprs[hand] <= total_bunches)

    active_bunches_var = model.NewIntVar(0, total_bunches, "active_bunches")
    for hand_usage_expr in hand_usage_exprs.values():
        model.Add(active_bunches_var >= hand_usage_expr)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1, _to_int(time_limit_seconds, CP_SAT_TIME_LIMIT_SECONDS))
    solver.parameters.num_search_workers = 8
    final_status_name = "OPTIMAL"

    for row_record in row_records:
        model.Minimize(row_record["short_var"])
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        if status != cp_model.OPTIMAL:
            final_status_name = "FEASIBLE"
        model.Add(row_record["short_var"] == solver.Value(row_record["short_var"]))

    hand_units_expr = sum(
        segment["bunches_var"] * segment["hand_count"]
        for segment in all_segments
    )
    capacity_units_expr = sum(
        segment["bunches_var"] * segment["kg_per_bunch_units"]
        for segment in all_segments
    )
    fulfilled_units_expr = sum(
        segment["boxes_var"] * kg_per_box_units
        for segment in all_segments
    )
    range_preference_expr = sum(
        segment["used_var"] * (segment["range_rank"] + 1)
        for segment in all_segments
    )
    segment_count_expr = sum(segment["used_var"] for segment in all_segments)
    extra_units_expr = capacity_units_expr - fulfilled_units_expr

    for objective_expr in (active_bunches_var, segment_count_expr, hand_units_expr, extra_units_expr):
        model.Minimize(objective_expr)
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        if status != cp_model.OPTIMAL:
            final_status_name = "FEASIBLE"
        model.Add(objective_expr == solver.Value(objective_expr))

    model.Minimize(range_preference_expr)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    if status != cp_model.OPTIMAL or final_status_name != "OPTIMAL":
        final_status_name = "FEASIBLE"

    detail_rows = []
    rows = []
    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}

    for row_record in row_records:
        row = row_record["row"]
        requested_boxes = row_record["requested_boxes"]
        segment_rows = []
        for segment in row_record["segments"]:
            bunches_allocated = solver.Value(segment["bunches_var"])
            boxes_fulfilled = solver.Value(segment["boxes_var"])
            if bunches_allocated <= 0 and boxes_fulfilled <= 0:
                continue
            for hand in segment["hands"]:
                remaining_hands[hand] -= bunches_allocated
            kg_allocated = (bunches_allocated * segment["kg_per_bunch_units"]) / WEIGHT_SCALE
            boxes_capacity = (
                bunches_allocated * segment["kg_per_bunch_units"]
            ) // kg_per_box_units
            extra_kg_from_rounding = max(0.0, kg_allocated - boxes_fulfilled * kg_per_box)
            bunches_needed = (
                int(math.ceil((boxes_fulfilled * kg_per_box_units) / segment["kg_per_bunch_units"]))
                if boxes_fulfilled > 0 and segment["kg_per_bunch_units"] > 0
                else 0
            )
            segment_row = {
                "processing_order": row_record["processing_order"],
                "original_index": row_record["original_index"],
                "market_priority": row["market_priority"],
                "market": row["market"],
                "sku_priority": row["sku_priority"],
                "sku": row["sku"].upper(),
                "hand_from": segment["hand_from"],
                "hand_to": segment["hand_to"],
                "hand_count": segment["hand_count"],
                "range_rank": segment["range_rank"],
                "range_label": f"{segment['hand_from']}-{segment['hand_to']}",
                "requested_boxes": boxes_fulfilled,
                "order_requested_boxes": requested_boxes,
                "kg_per_bunch_for_sku": segment["kg_per_bunch_units"] / WEIGHT_SCALE,
                "bunches_needed": bunches_needed,
                "bunches_allocated": bunches_allocated,
                "kg_allocated": kg_allocated,
                "boxes_capacity": int(boxes_capacity),
                "boxes_fulfilled": boxes_fulfilled,
                "containers_fulfilled": boxes_fulfilled / boxes_per_container,
                "short_boxes": 0,
                "short_containers": 0.0,
                "extra_kg_from_rounding": extra_kg_from_rounding,
                "hand_units_consumed": bunches_allocated * segment["hand_count"],
                "is_fulfilled": True,
            }
            segment_rows.append(segment_row)
            detail_rows.append(segment_row)

        fulfilled_boxes = sum(segment["boxes_fulfilled"] for segment in segment_rows)
        short_boxes = max(0, requested_boxes - fulfilled_boxes)
        kg_allocated = sum(segment["kg_allocated"] for segment in segment_rows)
        row_hand_usage = {
            hand: sum(
                segment["bunches_allocated"]
                for segment in segment_rows
                if segment["hand_from"] <= hand <= segment["hand_to"]
            )
            for hand in range(1, hands_per_bunch + 1)
        }
        bunches_allocated = max(row_hand_usage.values(), default=0)
        hand_units_consumed = sum(segment["hand_units_consumed"] for segment in segment_rows)
        boxes_capacity = sum(segment["boxes_capacity"] for segment in segment_rows)
        extra_kg_from_rounding = max(0.0, kg_allocated - fulfilled_boxes * kg_per_box)
        range_labels = ", ".join(segment["range_label"] for segment in segment_rows)
        rows.append({
            "processing_order": row_record["processing_order"],
            "original_index": row_record["original_index"],
            "market_priority": row["market_priority"],
            "market": row["market"],
            "sku_priority": row["sku_priority"],
            "sku": row["sku"].upper(),
            "hand_from": min((segment["hand_from"] for segment in segment_rows), default=0),
            "hand_to": max((segment["hand_to"] for segment in segment_rows), default=0),
            "hand_count": int(round(hand_units_consumed / bunches_allocated)) if bunches_allocated else 0,
            "range_rank": min((segment["range_rank"] for segment in segment_rows), default=0),
            "range_label": range_labels or "Chưa phân bổ",
            "requested_boxes": requested_boxes,
            "kg_per_bunch_for_sku": kg_allocated / bunches_allocated if bunches_allocated else 0.0,
            "bunches_needed": bunches_allocated if fulfilled_boxes else 0,
            "bunches_allocated": bunches_allocated,
            "kg_allocated": kg_allocated,
            "boxes_capacity": boxes_capacity,
            "boxes_fulfilled": fulfilled_boxes,
            "containers_fulfilled": fulfilled_boxes / boxes_per_container,
            "short_boxes": short_boxes,
            "short_containers": short_boxes / boxes_per_container,
            "extra_kg_from_rounding": extra_kg_from_rounding,
            "hand_units_consumed": hand_units_consumed,
            "is_fulfilled": short_boxes == 0,
        })

    fulfilled_boxes_total = sum(row["boxes_fulfilled"] for row in rows)
    short_boxes_total = sum(row["short_boxes"] for row in rows)
    source_kg = total_bunches * kg_per_bunch
    source_boxes_capacity = int(math.floor(source_kg / kg_per_box))
    loss = {
        "shortage_vector": [row["short_boxes"] for row in rows],
        "active_bunches_estimated": solver.Value(active_bunches_var),
        "segment_count": solver.Value(segment_count_expr),
        "hand_units_consumed": sum(row["hand_units_consumed"] for row in rows),
        "extra_kg_from_rounding": sum(row["extra_kg_from_rounding"] for row in rows),
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_bunch / hands_per_bunch,
        "source_boxes_capacity": source_boxes_capacity,
        "source_cont_capacity": source_boxes_capacity / boxes_per_container,
        "active_bunches_estimated": solver.Value(active_bunches_var),
        "segment_count": solver.Value(segment_count_expr),
        "fulfilled_boxes": fulfilled_boxes_total,
        "fulfilled_containers": fulfilled_boxes_total / boxes_per_container,
        "short_boxes": short_boxes_total,
        "short_containers": short_boxes_total / boxes_per_container,
        "optimizer_loss": sum(row["short_boxes"] for row in rows),
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }
    return {
        "rows": rows,
        "detail_rows": detail_rows,
        "remaining_hands": remaining_hands,
        "summary": summary,
        "loss": loss,
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }


def allocate_bunches_optimized(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    beam_width: int = BEAM_WIDTH,
) -> dict[str, Any]:
    cp_result = _allocate_bunches_cpsat(
        total_bunches,
        kg_per_bunch,
        hands_per_bunch,
        sku_rows,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
    )
    if cp_result is not None:
        return cp_result

    return _allocate_bunches_beam(
        total_bunches,
        kg_per_bunch,
        hands_per_bunch,
        sku_rows,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
        beam_width=beam_width,
        solver_status="APPROXIMATE",
        solver_backend="beam_search_fallback",
    )


def _recipe_hand_positions(recipe: list[dict[str, Any]], hands_per_bunch: int) -> list[int]:
    positions = []
    for component in recipe:
        hand_from = _to_int(component.get("hand_from"))
        hand_to = _to_int(component.get("hand_to"))
        for hand in range(hand_from, hand_to + 1):
            if 1 <= hand <= hands_per_bunch and hand not in positions:
                positions.append(hand)
    return positions


def _calculate_max_containers_cpsat(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    market_order: list[str],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    time_limit_seconds: int = CP_SAT_TIME_LIMIT_SECONDS,
) -> dict[str, Any] | None:
    if cp_model is None:
        return None

    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))
    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return None

    ordered_markets = []
    for market in market_order or []:
        if market not in ordered_markets:
            ordered_markets.append(market)
    if not ordered_markets:
        ordered_markets = sorted({
            market
            for sku_rule in OPTIMIZER_SKU_RULES.values()
            for market in sku_rule.get("markets", [])
        })

    model = cp_model.CpModel()
    kg_per_hand_units = int(round((kg_per_bunch * WEIGHT_SCALE) / hands_per_bunch))
    kg_per_box_units = max(1, int(round(kg_per_box * WEIGHT_SCALE)))
    source_kg = total_bunches * kg_per_bunch
    source_boxes_capacity = int(math.floor(source_kg / kg_per_box))
    max_possible_containers = max(0, source_boxes_capacity // boxes_per_container)
    all_segments = []
    market_records = []

    for market_priority, market in enumerate(ordered_markets, start=1):
        market_segments = []
        for sku, sku_rule in OPTIMIZER_SKU_RULES.items():
            if market not in sku_rule.get("markets", []):
                continue
            sku_segments = []
            row = {
                "sku": sku,
                "market": market,
                "demand": source_boxes_capacity,
                "unit": "Thùng",
            }
            for range_rank, (hand_from, hand_to) in enumerate(_valid_optimizer_ranges(row, hands_per_bunch)):
                hand_count = hand_to - hand_from + 1
                kg_per_bunch_units = hand_count * kg_per_hand_units
                var_prefix = f"m{market_priority}_{sku}_{range_rank}".replace("/", "_")
                bunches_var = model.NewIntVar(0, total_bunches, f"{var_prefix}_bunches")
                boxes_var = model.NewIntVar(0, source_boxes_capacity, f"{var_prefix}_boxes")
                used_var = model.NewBoolVar(f"{var_prefix}_used")
                model.Add(boxes_var * kg_per_box_units <= bunches_var * kg_per_bunch_units)
                model.Add(bunches_var <= total_bunches * used_var)
                model.Add(bunches_var >= used_var)
                segment = {
                    "market": market,
                    "market_priority": market_priority,
                    "sku": sku,
                    "range_rank": range_rank,
                    "hand_from": hand_from,
                    "hand_to": hand_to,
                    "hand_count": hand_count,
                    "hands": list(range(hand_from, hand_to + 1)),
                    "kg_per_bunch_units": kg_per_bunch_units,
                    "bunches_var": bunches_var,
                    "boxes_var": boxes_var,
                    "used_var": used_var,
                }
                market_segments.append(segment)
                sku_segments.append(segment)
                all_segments.append(segment)
        boxes_var = model.NewIntVar(0, source_boxes_capacity, f"market_{market_priority}_boxes")
        full_containers_var = model.NewIntVar(0, max_possible_containers, f"market_{market_priority}_containers")
        excess_boxes_var = model.NewIntVar(0, boxes_per_container - 1, f"market_{market_priority}_excess_boxes")
        model.Add(boxes_var == sum(segment["boxes_var"] for segment in market_segments))
        model.Add(full_containers_var * boxes_per_container + excess_boxes_var == boxes_var)
        market_records.append({
            "market": market,
            "market_priority": market_priority,
            "segments": market_segments,
            "boxes_var": boxes_var,
            "full_containers_var": full_containers_var,
            "excess_boxes_var": excess_boxes_var,
        })

    if not all_segments:
        return None

    hand_usage_exprs = {}
    for hand in range(1, hands_per_bunch + 1):
        hand_usage_exprs[hand] = sum(
            segment["bunches_var"] for segment in all_segments if hand in segment["hands"]
        )
        model.Add(hand_usage_exprs[hand] <= total_bunches)

    active_bunches_var = model.NewIntVar(0, total_bunches, "max_cont_active_bunches")
    for hand_usage_expr in hand_usage_exprs.values():
        model.Add(active_bunches_var >= hand_usage_expr)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1, _to_int(time_limit_seconds, CP_SAT_TIME_LIMIT_SECONDS))
    solver.parameters.num_search_workers = 8
    final_status_name = "OPTIMAL"
    for market_record in market_records:
        model.Maximize(market_record["full_containers_var"])
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        if status != cp_model.OPTIMAL:
            final_status_name = "FEASIBLE"
        model.Add(market_record["full_containers_var"] == solver.Value(market_record["full_containers_var"]))

    hand_units_expr = sum(segment["bunches_var"] * segment["hand_count"] for segment in all_segments)
    excess_boxes_expr = sum(market_record["excess_boxes_var"] for market_record in market_records)
    range_preference_expr = sum(
        segment["used_var"] * (segment["range_rank"] + 1)
        for segment in all_segments
    )
    segment_count_expr = sum(segment["used_var"] for segment in all_segments)
    for objective_expr in (active_bunches_var, segment_count_expr, hand_units_expr, excess_boxes_expr):
        model.Minimize(objective_expr)
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        if status != cp_model.OPTIMAL:
            final_status_name = "FEASIBLE"
        model.Add(objective_expr == solver.Value(objective_expr))

    model.Minimize(range_preference_expr)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    if status != cp_model.OPTIMAL or final_status_name != "OPTIMAL":
        final_status_name = "FEASIBLE"

    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    market_rows = []
    detail_rows = []
    for market_record in market_records:
        bundles_used = 0
        kg_allocated = 0.0
        for segment in market_record["segments"]:
            bunches_allocated = solver.Value(segment["bunches_var"])
            boxes_equivalent = solver.Value(segment["boxes_var"])
            if bunches_allocated <= 0 and boxes_equivalent <= 0:
                continue
            for hand in segment["hands"]:
                remaining_hands[hand] -= bunches_allocated
            segment_kg = bunches_allocated * segment["kg_per_bunch_units"] / WEIGHT_SCALE
            bundles_used += bunches_allocated
            kg_allocated += segment_kg
            detail_rows.append({
                "market": market_record["market"],
                "market_priority": market_record["market_priority"],
                "sku": segment["sku"],
                "range_label": f"{segment['hand_from']}-{segment['hand_to']}",
                "hand_count": segment["hand_count"],
                "bundles_used": bunches_allocated,
                "kg_allocated": segment_kg,
                "boxes_equivalent": boxes_equivalent,
            })

        boxes_allocated = solver.Value(market_record["full_containers_var"]) * boxes_per_container
        boxes_actual = solver.Value(market_record["boxes_var"])
        market_rows.append({
            "market": market_record["market"],
            "market_priority": market_record["market_priority"],
            "available_bundles": total_bunches,
            "hands_per_recipe": hands_per_bunch,
            "capacity_kg": kg_allocated,
            "capacity_boxes": boxes_actual,
            "capacity_containers": boxes_actual / boxes_per_container,
            "full_containers": solver.Value(market_record["full_containers_var"]),
            "boxes_allocated": boxes_allocated,
            "remaining_boxes_potential": solver.Value(market_record["excess_boxes_var"]),
            "bundles_used": bundles_used,
            "kg_allocated": kg_allocated,
        })

    fulfilled_boxes = sum(row["boxes_allocated"] for row in market_rows)
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_bunch / hands_per_bunch,
        "source_boxes_capacity": source_boxes_capacity,
        "source_cont_capacity": source_boxes_capacity / boxes_per_container,
        "active_bunches_estimated": solver.Value(active_bunches_var),
        "segment_count": solver.Value(segment_count_expr),
        "fulfilled_boxes": fulfilled_boxes,
        "fulfilled_containers": sum(row["full_containers"] for row in market_rows),
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }
    return {
        "rows": market_rows,
        "detail_rows": detail_rows,
        "remaining_hands": remaining_hands,
        "summary": summary,
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }


def calculate_max_containers_by_market(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    market_order: list[str],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
) -> dict[str, Any]:
    """Calculate full containers by market using fixed market packing recipes."""
    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))

    cp_result = _calculate_max_containers_cpsat(
        total_bunches,
        kg_per_bunch,
        hands_per_bunch,
        market_order,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
    )
    if cp_result is not None:
        return cp_result

    ordered_markets = []
    for market in market_order or []:
        if market in MARKET_MAX_CONTAINER_RECIPES and market not in ordered_markets:
            ordered_markets.append(market)
    if not ordered_markets:
        ordered_markets = list(MARKET_MAX_CONTAINER_RECIPES.keys())

    empty_summary = {
        "total_bunches": total_bunches,
        "source_kg": 0.0,
        "kg_per_hand": 0.0,
        "source_boxes_capacity": 0,
        "source_cont_capacity": 0.0,
        "fulfilled_boxes": 0,
        "fulfilled_containers": 0,
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "solver_status": "APPROXIMATE",
        "solver_backend": "recipe_fallback",
    }
    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return {
            "rows": [],
            "detail_rows": [],
            "remaining_hands": {},
            "summary": empty_summary,
            "solver_status": "NO_SOLUTION",
            "solver_backend": "recipe_fallback",
        }

    kg_per_hand = kg_per_bunch / hands_per_bunch
    source_kg = total_bunches * kg_per_bunch
    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    market_rows = []
    detail_rows = []

    for market_priority, market in enumerate(ordered_markets, start=1):
        recipe = MARKET_MAX_CONTAINER_RECIPES.get(market, [])
        recipe_hands = _recipe_hand_positions(recipe, hands_per_bunch)
        if not recipe_hands:
            continue

        available_bundles = min(remaining_hands.get(hand, 0) for hand in recipe_hands)
        hands_per_recipe = len(recipe_hands)
        kg_per_recipe_bundle = hands_per_recipe * kg_per_hand
        capacity_kg = available_bundles * kg_per_recipe_bundle
        capacity_boxes = int(math.floor(capacity_kg / kg_per_box)) if kg_per_box > 0 else 0
        full_containers = capacity_boxes // boxes_per_container
        boxes_allocated = full_containers * boxes_per_container
        bundles_used = (
            int(math.ceil((boxes_allocated * kg_per_box) / kg_per_recipe_bundle))
            if boxes_allocated > 0 and kg_per_recipe_bundle > 0
            else 0
        )
        bundles_used = min(bundles_used, available_bundles)
        kg_allocated = bundles_used * kg_per_recipe_bundle

        if bundles_used > 0:
            for hand in recipe_hands:
                remaining_hands[hand] -= bundles_used

        market_rows.append({
            "market": market,
            "market_priority": market_priority,
            "available_bundles": available_bundles,
            "hands_per_recipe": hands_per_recipe,
            "capacity_kg": capacity_kg,
            "capacity_boxes": capacity_boxes,
            "capacity_containers": capacity_boxes / boxes_per_container,
            "full_containers": full_containers,
            "boxes_allocated": boxes_allocated,
            "remaining_boxes_potential": max(0, capacity_boxes - boxes_allocated),
            "bundles_used": bundles_used,
            "kg_allocated": kg_allocated,
        })

        if bundles_used > 0:
            for component in recipe:
                hand_from = _to_int(component.get("hand_from"))
                hand_to = _to_int(component.get("hand_to"))
                if hand_from < 1 or hand_to < hand_from or hand_to > hands_per_bunch:
                    continue
                hand_count = hand_to - hand_from + 1
                component_kg = bundles_used * hand_count * kg_per_hand
                detail_rows.append({
                    "market": market,
                    "market_priority": market_priority,
                    "sku": str(component.get("sku", "")).upper(),
                    "range_label": f"{hand_from}-{hand_to}",
                    "hand_count": hand_count,
                    "bundles_used": bundles_used,
                    "kg_allocated": component_kg,
                    "boxes_equivalent": component_kg / kg_per_box if kg_per_box > 0 else 0.0,
                })

    fulfilled_boxes = sum(row["boxes_allocated"] for row in market_rows)
    active_bunches_estimated = _active_bunches_from_remaining(total_bunches, remaining_hands)
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "source_boxes_capacity": int(math.floor(source_kg / kg_per_box)),
        "source_cont_capacity": int(math.floor(source_kg / kg_per_box)) / boxes_per_container,
        "active_bunches_estimated": active_bunches_estimated,
        "segment_count": len(detail_rows),
        "fulfilled_boxes": fulfilled_boxes,
        "fulfilled_containers": sum(row["full_containers"] for row in market_rows),
        "solver_status": "APPROXIMATE",
        "solver_backend": "recipe_fallback",
    }
    return {
        "rows": market_rows,
        "detail_rows": detail_rows,
        "remaining_hands": remaining_hands,
        "summary": summary,
        "solver_status": "APPROXIMATE",
        "solver_backend": "recipe_fallback",
    }


def allocate_bunches_by_hands(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
) -> dict[str, Any]:
    """Allocate bunches to SKUs by remaining stock at each hand position.

    The allocator processes rows by market priority, then SKU priority, then
    original row order. Non-overlapping SKU ranges can use the same bunches;
    overlapping ranges compete for the same hand-position inventory.
    """
    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))

    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return {
            "rows": [],
            "remaining_hands": {},
            "summary": {
                "total_bunches": total_bunches,
                "source_kg": 0.0,
                "kg_per_hand": 0.0,
                "source_boxes_capacity": 0,
                "source_cont_capacity": 0.0,
                "fulfilled_boxes": 0,
                "fulfilled_containers": 0.0,
                "short_boxes": 0,
            },
        }

    normalized_rows = normalize_sku_rows(sku_rows)
    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    kg_per_hand = kg_per_bunch / hands_per_bunch
    results: list[dict[str, Any]] = []

    sorted_rows = sorted(
        enumerate(normalized_rows),
        key=lambda item: (
            item[1]["market_priority"],
            item[1]["sku_priority"],
            item[0],
        ),
    )

    for original_index, row in sorted_rows:
        hand_from = row["hand_from"]
        hand_to = row["hand_to"]
        demand = max(0.0, row["demand"])
        unit = row["unit"]

        is_invalid = (
            not row["sku"]
            or demand <= 0
            or hand_from < 1
            or hand_to < hand_from
            or hand_to > hands_per_bunch
        )
        if is_invalid:
            continue

        hand_range = list(range(hand_from, hand_to + 1))
        hand_count = len(hand_range)
        kg_per_bunch_for_sku = hand_count * kg_per_hand
        requested_boxes = (
            int(math.ceil(demand * boxes_per_container))
            if unit.lower().startswith("cont")
            else int(math.ceil(demand))
        )
        bunches_needed = int(math.ceil((requested_boxes * kg_per_box) / kg_per_bunch_for_sku))
        available_bunches = min(remaining_hands[hand] for hand in hand_range)
        bunches_allocated = min(bunches_needed, available_bunches)

        for hand in hand_range:
            remaining_hands[hand] -= bunches_allocated

        kg_allocated = bunches_allocated * kg_per_bunch_for_sku
        boxes_capacity = int(math.floor(kg_allocated / kg_per_box))
        boxes_fulfilled = min(requested_boxes, boxes_capacity)
        short_boxes = max(0, requested_boxes - boxes_fulfilled)
        extra_kg_from_rounding = max(0.0, kg_allocated - boxes_fulfilled * kg_per_box)

        results.append(
            {
                "processing_order": len(results) + 1,
                "original_index": original_index,
                "market_priority": row["market_priority"],
                "market": row["market"],
                "sku_priority": row["sku_priority"],
                "sku": row["sku"],
                "hand_from": hand_from,
                "hand_to": hand_to,
                "hand_count": hand_count,
                "requested_boxes": requested_boxes,
                "kg_per_bunch_for_sku": kg_per_bunch_for_sku,
                "bunches_needed": bunches_needed,
                "bunches_allocated": bunches_allocated,
                "kg_allocated": kg_allocated,
                "boxes_capacity": boxes_capacity,
                "boxes_fulfilled": boxes_fulfilled,
                "containers_fulfilled": boxes_fulfilled / boxes_per_container,
                "short_boxes": short_boxes,
                "short_containers": short_boxes / boxes_per_container,
                "extra_kg_from_rounding": extra_kg_from_rounding,
                "is_fulfilled": short_boxes == 0,
            }
        )

    fulfilled_boxes = sum(row["boxes_fulfilled"] for row in results)
    short_boxes_total = sum(row["short_boxes"] for row in results)
    source_kg = total_bunches * kg_per_bunch
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "source_boxes_capacity": int(math.floor(source_kg / kg_per_box)),
        "source_cont_capacity": int(math.floor(source_kg / kg_per_box)) / boxes_per_container,
        "fulfilled_boxes": fulfilled_boxes,
        "fulfilled_containers": fulfilled_boxes / boxes_per_container,
        "short_boxes": short_boxes_total,
        "short_containers": short_boxes_total / boxes_per_container,
    }
    return {
        "rows": results,
        "remaining_hands": remaining_hands,
        "summary": summary,
    }
