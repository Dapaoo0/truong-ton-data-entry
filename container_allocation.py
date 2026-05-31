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


BASE_HAND_WEIGHT_PROFILES = {
    12: {
        1: 1.3,
        2: 1.5,
        3: 1.7,
        4: 2.0,
        5: 2.0,
        6: 2.3,
        7: 2.5,
        8: 2.6,
        9: 2.7,
        10: 3.0,
        11: 3.3,
        12: 3.5,
    },
    9: {
        1: 1.4,
        2: 1.5,
        3: 1.7,
        4: 1.9,
        5: 2.1,
        6: 2.3,
        7: 2.5,
        8: 2.7,
        9: 2.9,
    },
}

HAND_WEIGHT_SCENARIOS = {
    "12_18": {
        "label": "12 nải - 18 kg",
        "hands_per_bunch": 12,
        "target_kg_per_bunch": 18.0,
    },
    "12_20": {
        "label": "12 nải - 20 kg",
        "hands_per_bunch": 12,
        "target_kg_per_bunch": 20.0,
    },
    "9_156": {
        "label": "9 nải - 15.6 kg",
        "hands_per_bunch": 9,
        "target_kg_per_bunch": 15.6,
    },
}


OPTIMIZER_SKU_RULES_12_HANDS = {
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
    "12CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Cùng nhóm quy cách Hàn với 15CP; vùng nải mẹ 10-12 cho buồng 12 nải.",
        "ranges": [(10, 12)],
    },
    "10CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Cùng nhóm quy cách Hàn với 15CP; vùng nải mẹ 10-12 cho buồng 12 nải.",
        "ranges": [(10, 12)],
    },
}

OPTIMIZER_SKU_RULES_9_HANDS = {
    "27CP": {
        "markets": ["Nhật"],
        "group": "Phần Ngọn",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 1-4.",
        "ranges": [(1, 4)],
    },
    "8H": {
        "markets": ["Hàn"],
        "group": "Phần Ngọn",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 1-3.",
        "ranges": [(1, 3)],
    },
    "6H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 4-5.",
        "ranges": [(4, 5)],
    },
    "30CP": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 1-7.",
        "ranges": [(1, 7)],
    },
    "5H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 6-8.",
        "ranges": [(6, 8)],
    },
    "5/6H": {
        "markets": ["Hàn"],
        "group": "Khúc Giữa",
        "description": "Mapping suy luận cho buồng 9 nải: vùng nải mẹ 4-7.",
        "ranges": [(4, 7)],
    },
    "15CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Mapping cho buồng 9 nải: vùng nải mẹ 6-9.",
        "ranges": [(6, 9)],
    },
    "12CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Mapping cho buồng 9 nải: vùng nải mẹ 6-9, tương tự 15CP.",
        "ranges": [(6, 9)],
    },
    "10CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Mapping cho buồng 9 nải: vùng nải mẹ 6-9, tương tự 15CP.",
        "ranges": [(6, 9)],
    },
}

OPTIMIZER_SKU_RULES_BY_HAND_COUNT = {
    12: OPTIMIZER_SKU_RULES_12_HANDS,
    9: OPTIMIZER_SKU_RULES_9_HANDS,
}

OPTIMIZER_SKU_RULES = OPTIMIZER_SKU_RULES_12_HANDS

MARKET_MAX_CONTAINER_RECIPES_12_HANDS = {
    "Nhật": [
        {"sku": "27CP", "hand_from": 1, "hand_to": 4},
        {"sku": "6H", "hand_from": 5, "hand_to": 7},
        {"sku": "5H", "hand_from": 8, "hand_to": 10},
    ],
    "Hàn": [
        {"sku": "8H", "hand_from": 1, "hand_to": 4},
        {"sku": "5/6H", "hand_from": 5, "hand_to": 9},
        {"sku": "15CP", "hand_from": 10, "hand_to": 12},
        {"sku": "12CP", "hand_from": 10, "hand_to": 12},
        {"sku": "10CP", "hand_from": 10, "hand_to": 12},
    ],
}

MARKET_MAX_CONTAINER_RECIPES_9_HANDS = {
    "Nhật": [
        {"sku": "27CP", "hand_from": 1, "hand_to": 3},
        {"sku": "6H", "hand_from": 4, "hand_to": 5},
        {"sku": "5H", "hand_from": 6, "hand_to": 8},
    ],
    "Hàn": [
        {"sku": "8H", "hand_from": 1, "hand_to": 3},
        {"sku": "5/6H", "hand_from": 4, "hand_to": 7},
        {"sku": "15CP", "hand_from": 6, "hand_to": 9},
        {"sku": "12CP", "hand_from": 6, "hand_to": 9},
        {"sku": "10CP", "hand_from": 6, "hand_to": 9},
    ],
}

MARKET_MAX_CONTAINER_RECIPES_BY_HAND_COUNT = {
    12: MARKET_MAX_CONTAINER_RECIPES_12_HANDS,
    9: MARKET_MAX_CONTAINER_RECIPES_9_HANDS,
}

MARKET_MAX_CONTAINER_RECIPES = MARKET_MAX_CONTAINER_RECIPES_12_HANDS

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


def get_optimizer_sku_rules(hands_per_bunch: int) -> dict[str, dict[str, Any]]:
    """Return SKU parent ranges for the selected bunch profile."""
    return OPTIMIZER_SKU_RULES_BY_HAND_COUNT.get(_to_int(hands_per_bunch), OPTIMIZER_SKU_RULES)


def get_market_max_container_recipes(hands_per_bunch: int) -> dict[str, list[dict[str, Any]]]:
    return MARKET_MAX_CONTAINER_RECIPES_BY_HAND_COUNT.get(_to_int(hands_per_bunch), MARKET_MAX_CONTAINER_RECIPES)


def scale_hand_weight_profile(hands_per_bunch: int, target_kg_per_bunch: float) -> dict[int, float]:
    """Scale the base hand-weight profile so its total matches target kg/bunch."""
    hands_per_bunch = _to_int(hands_per_bunch)
    target_kg_per_bunch = max(0.0, _to_float(target_kg_per_bunch))
    base_profile = BASE_HAND_WEIGHT_PROFILES.get(hands_per_bunch)
    if not base_profile or target_kg_per_bunch <= 0:
        return {}
    base_total = sum(base_profile.values())
    if base_total <= 0:
        return {}
    scale = target_kg_per_bunch / base_total
    return {hand: weight * scale for hand, weight in base_profile.items()}


def build_hand_weight_profile(hands_per_bunch: int, target_kg_per_bunch: float) -> dict[str, Any]:
    hand_weights = scale_hand_weight_profile(hands_per_bunch, target_kg_per_bunch)
    profile_total = sum(hand_weights.values())
    hands_per_bunch = len(hand_weights) or _to_int(hands_per_bunch)
    return {
        "hands_per_bunch": hands_per_bunch,
        "kg_per_bunch": profile_total,
        "kg_per_hand": profile_total / hands_per_bunch if hands_per_bunch else 0.0,
        "hand_weights": hand_weights,
    }


def _resolve_hand_weights(
    hands_per_bunch: int,
    kg_per_bunch: float,
    hand_weights: dict[int, float] | None = None,
) -> tuple[dict[int, float], float, float]:
    """Return normalized hand weights, total kg/bunch, and average kg/hand.

    If no profile is passed, keep the legacy uniform distribution so old callers
    and tests remain compatible.
    """
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    normalized: dict[int, float] = {}
    if hand_weights:
        for key, value in hand_weights.items():
            hand = _to_int(key)
            weight = max(0.0, _to_float(value))
            if 1 <= hand <= hands_per_bunch and weight > 0:
                normalized[hand] = weight
        if len(normalized) == hands_per_bunch:
            raw_total = sum(normalized.values())
            if raw_total > 0:
                if kg_per_bunch > 0 and abs(raw_total - kg_per_bunch) > 1e-6:
                    scale = kg_per_bunch / raw_total
                    normalized = {hand: weight * scale for hand, weight in normalized.items()}
                total = sum(normalized.values())
                return normalized, total, total / hands_per_bunch if hands_per_bunch else 0.0

    if hands_per_bunch <= 0 or kg_per_bunch <= 0:
        return {}, 0.0, 0.0

    uniform_weight = kg_per_bunch / hands_per_bunch
    normalized = {hand: uniform_weight for hand in range(1, hands_per_bunch + 1)}
    return normalized, kg_per_bunch, uniform_weight


def range_weight(hand_from: int, hand_to: int, hand_weights: dict[int, float]) -> float:
    return sum(hand_weights.get(hand, 0.0) for hand in range(hand_from, hand_to + 1))


def _range_weight_units(hand_from: int, hand_to: int, hand_weight_units: dict[int, int]) -> int:
    return sum(hand_weight_units.get(hand, 0) for hand in range(hand_from, hand_to + 1))


def normalize_sku_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize UI rows into stable keys used by the allocator."""
    normalized = []
    for row in rows:
        normalized.append(
            {
                "customer_priority": _to_int(
                    row.get(
                        "customer_priority",
                        row.get("Ưu tiên khách hàng", row.get("market_priority", row.get("Ưu tiên thị trường"))),
                    ),
                    999,
                ),
                "customer": str(row.get("customer", row.get("Khách hàng", "")) or "").strip(),
                "market_priority": _to_int(
                    row.get(
                        "market_priority",
                        row.get("Ưu tiên thị trường", row.get("customer_priority", row.get("Ưu tiên khách hàng"))),
                    ),
                    999,
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
    sku_rule = get_optimizer_sku_rules(hands_per_bunch).get(sku, {})
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
    hand_weights: dict[int, float],
    kg_per_box: float,
    boxes_per_container: int,
    processing_order: int,
    range_rank: int,
) -> tuple[dict[str, Any], dict[int, int], dict[str, float]]:
    hand_range = list(range(hand_from, hand_to + 1))
    hand_count = len(hand_range)
    kg_per_bunch_for_sku = range_weight(hand_from, hand_to, hand_weights)
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
        "customer_priority": row.get("customer_priority", row["market_priority"]),
        "customer": row.get("customer", ""),
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
        "kg_allocated": float(kg_allocated),
        "range_preference": float(range_rank),
        "extra_kg_from_rounding": float(extra_kg_from_rounding),
    }
    return result_row, next_remaining, penalties


def _optimizer_state_key(state: dict[str, Any]) -> tuple:
    return (
        tuple(state["shortage_vector"]),
        state["active_bunches_estimated"],
        state["segment_count"],
        round(state["kg_allocated"], 6),
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
    hand_weights: dict[int, float] | None = None,
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
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))
    beam_width = max(1, _to_int(beam_width, BEAM_WIDTH))

    empty_summary = {
        "total_bunches": total_bunches,
        "source_kg": 0.0,
        "kg_per_hand": 0.0,
        "hand_weights": hand_weights,
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
            item[1]["customer_priority"],
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
    states = [{
        "remaining_hands": remaining_hands,
        "rows": [],
        "shortage_vector": [],
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "kg_allocated": 0.0,
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
                    hand_weights,
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
                    "kg_allocated": state["kg_allocated"] + penalties["kg_allocated"],
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
        + best_state["kg_allocated"] * 100
        + best_state["hand_units_consumed"] * 10
        + best_state["range_preference"] * 100
        + best_state["extra_kg_from_rounding"]
    )
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
        "source_boxes_capacity": int(math.floor(source_kg / kg_per_box)),
        "source_cont_capacity": int(math.floor(source_kg / kg_per_box)) / boxes_per_container,
        "fulfilled_boxes": fulfilled_boxes,
        "fulfilled_containers": fulfilled_boxes / boxes_per_container,
        "short_boxes": short_boxes_total,
        "short_containers": short_boxes_total / boxes_per_container,
        "optimizer_loss": optimizer_loss,
        "active_bunches_estimated": best_state["active_bunches_estimated"],
        "segment_count": best_state["segment_count"],
        "kg_allocated": best_state["kg_allocated"],
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }
    loss = {
        "shortage_vector": best_state["shortage_vector"],
        "shortage_loss": shortage_loss,
        "active_bunches_estimated": best_state["active_bunches_estimated"],
        "segment_count": best_state["segment_count"],
        "kg_allocated": best_state["kg_allocated"],
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
            item[1]["customer_priority"],
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
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    source_kg = total_bunches * kg_per_bunch if total_bunches > 0 and kg_per_bunch > 0 else 0.0
    source_boxes = int(math.floor(source_kg / kg_per_box)) if kg_per_box > 0 else 0
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
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
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any] | None:
    if cp_model is None:
        return None

    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
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
            hand_weights,
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
            hand_weights,
        )

    model = cp_model.CpModel()
    hand_weight_units = {
        hand: max(1, int(round(weight * WEIGHT_SCALE)))
        for hand, weight in hand_weights.items()
    }
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
            kg_per_bunch_units = _range_weight_units(hand_from, hand_to, hand_weight_units)
            var_prefix = f"r{processing_order}_c{range_rank}"
            bunches_var = model.NewIntVar(0, total_bunches, f"{var_prefix}_bunches")
            used_var = model.NewBoolVar(f"{var_prefix}_used")
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
                "used_var": used_var,
            }
            row_record["segments"].append(segment)
            all_segments.append(segment)

        fulfilled_var = model.NewIntVar(0, requested_boxes, f"r{processing_order}_fulfilled")
        short_var = model.NewIntVar(0, requested_boxes, f"r{processing_order}_short")
        row_capacity_units = sum(
            segment["bunches_var"] * segment["kg_per_bunch_units"]
            for segment in row_record["segments"]
        )
        model.Add(fulfilled_var * kg_per_box_units <= row_capacity_units)
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
        row_record["fulfilled_var"] * kg_per_box_units
        for row_record in row_records
    )
    range_preference_expr = sum(
        segment["used_var"] * (segment["range_rank"] + 1)
        for segment in all_segments
    )
    segment_count_expr = sum(segment["used_var"] for segment in all_segments)
    extra_units_expr = capacity_units_expr - fulfilled_units_expr

    for objective_expr in (active_bunches_var, segment_count_expr, capacity_units_expr, extra_units_expr):
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
        row_fulfilled_boxes = solver.Value(row_record["fulfilled_var"])
        segment_rows = []
        for segment in row_record["segments"]:
            bunches_allocated = solver.Value(segment["bunches_var"])
            if bunches_allocated <= 0:
                continue
            for hand in segment["hands"]:
                remaining_hands[hand] -= bunches_allocated
            kg_allocated = (bunches_allocated * segment["kg_per_bunch_units"]) / WEIGHT_SCALE
            boxes_capacity = (
                bunches_allocated * segment["kg_per_bunch_units"]
            ) // kg_per_box_units
            boxes_equivalent = kg_allocated / kg_per_box if kg_per_box > 0 else 0.0
            segment_row = {
                "processing_order": row_record["processing_order"],
                "original_index": row_record["original_index"],
                "customer_priority": row.get("customer_priority", row["market_priority"]),
                "customer": row.get("customer", ""),
                "market_priority": row["market_priority"],
                "market": row["market"],
                "sku_priority": row["sku_priority"],
                "sku": row["sku"].upper(),
                "hand_from": segment["hand_from"],
                "hand_to": segment["hand_to"],
                "hand_count": segment["hand_count"],
                "range_rank": segment["range_rank"],
                "range_label": f"{segment['hand_from']}-{segment['hand_to']}",
                "requested_boxes": 0,
                "order_requested_boxes": requested_boxes,
                "kg_per_bunch_for_sku": segment["kg_per_bunch_units"] / WEIGHT_SCALE,
                "bunches_needed": 0,
                "bunches_allocated": bunches_allocated,
                "kg_allocated": kg_allocated,
                "boxes_capacity": int(boxes_capacity),
                "boxes_equivalent": boxes_equivalent,
                "boxes_fulfilled": 0,
                "containers_fulfilled": 0.0,
                "short_boxes": 0,
                "short_containers": 0.0,
                "extra_kg_from_rounding": 0.0,
                "hand_units_consumed": bunches_allocated * segment["hand_count"],
                "is_fulfilled": True,
            }
            segment_rows.append(segment_row)

        remaining_segment_boxes = row_fulfilled_boxes
        for segment_row in segment_rows:
            assigned_boxes = min(segment_row["boxes_capacity"], remaining_segment_boxes)
            segment_row["boxes_fulfilled"] = assigned_boxes
            remaining_segment_boxes -= assigned_boxes
        if remaining_segment_boxes > 0:
            fractional_rows = sorted(
                segment_rows,
                key=lambda item: item["boxes_equivalent"] - math.floor(item["boxes_equivalent"]),
                reverse=True,
            )
            for segment_row in fractional_rows:
                if remaining_segment_boxes <= 0:
                    break
                segment_row["boxes_fulfilled"] += 1
                remaining_segment_boxes -= 1

        for segment_row in segment_rows:
            segment_row["requested_boxes"] = segment_row["boxes_fulfilled"]
            segment_row["containers_fulfilled"] = segment_row["boxes_fulfilled"] / boxes_per_container
            segment_row["bunches_needed"] = (
                int(math.ceil((segment_row["boxes_fulfilled"] * kg_per_box) / segment_row["kg_per_bunch_for_sku"]))
                if segment_row["boxes_fulfilled"] > 0 and segment_row["kg_per_bunch_for_sku"] > 0
                else 0
            )
            segment_row["extra_kg_from_rounding"] = max(
                0.0,
                segment_row["kg_allocated"] - segment_row["boxes_fulfilled"] * kg_per_box,
            )
        detail_rows.extend(segment_rows)

        fulfilled_boxes = row_fulfilled_boxes
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
        boxes_capacity = int(math.floor(kg_allocated / kg_per_box)) if kg_per_box > 0 else 0
        extra_kg_from_rounding = max(0.0, kg_allocated - fulfilled_boxes * kg_per_box)
        range_labels = ", ".join(segment["range_label"] for segment in segment_rows)
        rows.append({
            "processing_order": row_record["processing_order"],
            "original_index": row_record["original_index"],
            "customer_priority": row.get("customer_priority", row["market_priority"]),
            "customer": row.get("customer", ""),
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
        "kg_allocated": sum(row["kg_allocated"] for row in rows),
        "hand_units_consumed": sum(row["hand_units_consumed"] for row in rows),
        "extra_kg_from_rounding": sum(row["extra_kg_from_rounding"] for row in rows),
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
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
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    cp_result = _allocate_bunches_cpsat(
        total_bunches,
        kg_per_bunch,
        hands_per_bunch,
        sku_rows,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
        hand_weights=hand_weights,
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
        hand_weights=hand_weights,
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
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any] | None:
    if cp_model is None:
        return None

    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
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
            for sku_rule in get_optimizer_sku_rules(hands_per_bunch).values()
            for market in sku_rule.get("markets", [])
        })

    model = cp_model.CpModel()
    hand_weight_units = {
        hand: max(1, int(round(weight * WEIGHT_SCALE)))
        for hand, weight in hand_weights.items()
    }
    kg_per_box_units = max(1, int(round(kg_per_box * WEIGHT_SCALE)))
    source_kg = total_bunches * kg_per_bunch
    source_boxes_capacity = int(math.floor(source_kg / kg_per_box))
    max_possible_containers = max(0, source_boxes_capacity // boxes_per_container)
    all_segments = []
    market_records = []

    for market_priority, market in enumerate(ordered_markets, start=1):
        market_segments = []
        for sku, sku_rule in get_optimizer_sku_rules(hands_per_bunch).items():
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
                kg_per_bunch_units = _range_weight_units(hand_from, hand_to, hand_weight_units)
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

    capacity_units_expr = sum(
        segment["bunches_var"] * segment["kg_per_bunch_units"]
        for segment in all_segments
    )
    excess_boxes_expr = sum(market_record["excess_boxes_var"] for market_record in market_records)
    range_preference_expr = sum(
        segment["used_var"] * (segment["range_rank"] + 1)
        for segment in all_segments
    )
    segment_count_expr = sum(segment["used_var"] for segment in all_segments)
    for objective_expr in (active_bunches_var, segment_count_expr, capacity_units_expr, excess_boxes_expr):
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
        market_hand_usage = {hand: 0 for hand in range(1, hands_per_bunch + 1)}
        for segment in market_record["segments"]:
            bunches_allocated = solver.Value(segment["bunches_var"])
            boxes_equivalent = solver.Value(segment["boxes_var"])
            if bunches_allocated <= 0 and boxes_equivalent <= 0:
                continue
            for hand in segment["hands"]:
                remaining_hands[hand] -= bunches_allocated
                market_hand_usage[hand] += bunches_allocated
            segment_kg = bunches_allocated * segment["kg_per_bunch_units"] / WEIGHT_SCALE
            bundles_used += bunches_allocated
            kg_allocated += segment_kg
            detail_rows.append({
                "market": market_record["market"],
                "market_priority": market_record["market_priority"],
                "sku": segment["sku"],
                "hand_from": segment["hand_from"],
                "hand_to": segment["hand_to"],
                "range_label": f"{segment['hand_from']}-{segment['hand_to']}",
                "hand_count": segment["hand_count"],
                "bundles_used": bunches_allocated,
                "kg_allocated": segment_kg,
                "kg_per_bunch_for_sku": segment["kg_per_bunch_units"] / WEIGHT_SCALE,
                "boxes_equivalent": boxes_equivalent,
            })

        boxes_allocated = solver.Value(market_record["full_containers_var"]) * boxes_per_container
        boxes_actual = solver.Value(market_record["boxes_var"])
        market_rows.append({
            "market": market_record["market"],
            "market_priority": market_record["market_priority"],
            "available_bundles": total_bunches,
            "hands_per_recipe": len({
                hand
                for segment in market_record["segments"]
                if solver.Value(segment["bunches_var"]) > 0
                for hand in segment["hands"]
            }),
            "capacity_kg": kg_allocated,
            "capacity_boxes": boxes_actual,
            "capacity_containers": boxes_actual / boxes_per_container,
            "full_containers": solver.Value(market_record["full_containers_var"]),
            "boxes_allocated": boxes_allocated,
            "remaining_boxes_potential": solver.Value(market_record["excess_boxes_var"]),
            "bundles_used": bundles_used,
            "active_bunches_used": max(market_hand_usage.values(), default=0),
            "kg_allocated": kg_allocated,
        })

    fulfilled_boxes = sum(row["boxes_allocated"] for row in market_rows)
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
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
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Calculate full containers by market using fixed market packing recipes."""
    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))

    cp_result = _calculate_max_containers_cpsat(
        total_bunches,
        kg_per_bunch,
        hands_per_bunch,
        market_order,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
        hand_weights=hand_weights,
    )
    if cp_result is not None:
        return cp_result

    ordered_markets = []
    for market in market_order or []:
        if market in get_market_max_container_recipes(hands_per_bunch) and market not in ordered_markets:
            ordered_markets.append(market)
    if not ordered_markets:
        ordered_markets = list(get_market_max_container_recipes(hands_per_bunch).keys())

    empty_summary = {
        "total_bunches": total_bunches,
        "source_kg": 0.0,
        "kg_per_hand": 0.0,
        "hand_weights": hand_weights,
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

    source_kg = total_bunches * kg_per_bunch
    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    market_rows = []
    detail_rows = []

    for market_priority, market in enumerate(ordered_markets, start=1):
        recipe = get_market_max_container_recipes(hands_per_bunch).get(market, [])
        recipe_hands = _recipe_hand_positions(recipe, hands_per_bunch)
        if not recipe_hands:
            continue

        available_bundles = min(remaining_hands.get(hand, 0) for hand in recipe_hands)
        hands_per_recipe = len(recipe_hands)
        kg_per_recipe_bundle = sum(hand_weights.get(hand, 0.0) for hand in recipe_hands)
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
            "active_bunches_used": bundles_used,
            "kg_allocated": kg_allocated,
        })

        if bundles_used > 0:
            for component in recipe:
                hand_from = _to_int(component.get("hand_from"))
                hand_to = _to_int(component.get("hand_to"))
                if hand_from < 1 or hand_to < hand_from or hand_to > hands_per_bunch:
                    continue
                hand_count = hand_to - hand_from + 1
                component_kg = bundles_used * range_weight(hand_from, hand_to, hand_weights)
                detail_rows.append({
                    "market": market,
                    "market_priority": market_priority,
                    "sku": str(component.get("sku", "")).upper(),
                    "hand_from": hand_from,
                    "hand_to": hand_to,
                    "range_label": f"{hand_from}-{hand_to}",
                    "hand_count": hand_count,
                    "bundles_used": bundles_used,
                    "kg_allocated": component_kg,
                    "kg_per_bunch_for_sku": range_weight(hand_from, hand_to, hand_weights),
                    "boxes_equivalent": component_kg / kg_per_box if kg_per_box > 0 else 0.0,
                })

    fulfilled_boxes = sum(row["boxes_allocated"] for row in market_rows)
    active_bunches_estimated = _active_bunches_from_remaining(total_bunches, remaining_hands)
    summary = {
        "total_bunches": total_bunches,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
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


def _minimum_bunch_upper_bound(
    sku_rows: list[dict[str, Any]],
    hands_per_bunch: int,
    hand_weights: dict[int, float],
    kg_per_box: float,
    boxes_per_container: int,
) -> int:
    upper_bound = 0
    for _, row, ranges in _build_candidate_rows(sku_rows, hands_per_bunch):
        requested_boxes = _requested_boxes(row, boxes_per_container)
        if requested_boxes <= 0:
            continue
        max_range_kg = max((range_weight(start, end, hand_weights) for start, end in ranges), default=0.0)
        if max_range_kg <= 0:
            continue
        upper_bound += int(math.ceil((requested_boxes * kg_per_box) / max_range_kg))
    return max(0, upper_bound)


def _empty_min_bunch_result(
    kg_per_bunch: float,
    hands_per_bunch: int,
    kg_per_box: float,
    boxes_per_container: int,
    solver_status: str,
    solver_backend: str,
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    summary = {
        "total_bunches": 0,
        "target_containers": 0,
        "requested_boxes": 0,
        "source_kg": 0.0,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
        "source_boxes_capacity": 0,
        "source_cont_capacity": 0.0,
        "active_bunches_estimated": 0,
        "segment_count": 0,
        "fulfilled_boxes": 0,
        "fulfilled_containers": 0.0,
        "short_boxes": 0,
        "short_containers": 0.0,
        "kg_allocated": 0.0,
        "extra_kg_from_rounding": 0.0,
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }
    return {
        "rows": [],
        "detail_rows": [],
        "remaining_hands": {hand: 0 for hand in range(1, hands_per_bunch + 1)},
        "summary": summary,
        "loss": {},
        "solver_status": solver_status,
        "solver_backend": solver_backend,
    }


def _calculate_min_bunches_cpsat(
    sku_rows: list[dict[str, Any]],
    kg_per_bunch: float,
    hands_per_bunch: int,
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    time_limit_seconds: int = CP_SAT_TIME_LIMIT_SECONDS,
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any] | None:
    if cp_model is None:
        return None

    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    kg_per_box = max(0.0, _to_float(kg_per_box))
    boxes_per_container = max(1, _to_int(boxes_per_container, 1))
    if kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return _empty_min_bunch_result(
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "ortools_cp_sat",
            hand_weights,
        )

    normalized_rows = normalize_sku_rows(sku_rows)
    positive_rows = [row for row in normalized_rows if row["demand"] > 0 and row["sku"]]
    candidate_rows = _build_candidate_rows(positive_rows, hands_per_bunch)
    if not positive_rows or len(candidate_rows) != len(positive_rows):
        return _empty_min_bunch_result(
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "ortools_cp_sat",
            hand_weights,
        )

    total_requested_boxes = sum(
        _requested_boxes(row, boxes_per_container)
        for _, row, _ in candidate_rows
    )
    upper_bound = _minimum_bunch_upper_bound(
        positive_rows,
        hands_per_bunch,
        hand_weights,
        kg_per_box,
        boxes_per_container,
    )
    if total_requested_boxes <= 0 or upper_bound <= 0:
        return _empty_min_bunch_result(
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "ortools_cp_sat",
            hand_weights,
        )

    model = cp_model.CpModel()
    hand_weight_units = {
        hand: max(1, int(round(weight * WEIGHT_SCALE)))
        for hand, weight in hand_weights.items()
    }
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
            kg_per_bunch_units = _range_weight_units(hand_from, hand_to, hand_weight_units)
            var_prefix = f"min_r{processing_order}_c{range_rank}"
            bunches_var = model.NewIntVar(0, upper_bound, f"{var_prefix}_bunches")
            used_var = model.NewBoolVar(f"{var_prefix}_used")
            model.Add(bunches_var <= upper_bound * used_var)
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
                "used_var": used_var,
            }
            row_record["segments"].append(segment)
            all_segments.append(segment)

        row_capacity_units = sum(
            segment["bunches_var"] * segment["kg_per_bunch_units"]
            for segment in row_record["segments"]
        )
        model.Add(row_capacity_units >= requested_boxes * kg_per_box_units)
        row_records.append(row_record)

    hand_usage_exprs = {}
    for hand in range(1, hands_per_bunch + 1):
        hand_usage_exprs[hand] = sum(
            segment["bunches_var"] for segment in all_segments if hand in segment["hands"]
        )
        model.Add(hand_usage_exprs[hand] <= upper_bound)

    active_bunches_var = model.NewIntVar(0, upper_bound, "min_required_active_bunches")
    for hand_usage_expr in hand_usage_exprs.values():
        model.Add(active_bunches_var >= hand_usage_expr)

    capacity_units_expr = sum(
        segment["bunches_var"] * segment["kg_per_bunch_units"]
        for segment in all_segments
    )
    segment_count_expr = sum(segment["used_var"] for segment in all_segments)
    target_units_expr = total_requested_boxes * kg_per_box_units
    extra_units_expr = capacity_units_expr - target_units_expr
    range_preference_expr = sum(
        segment["used_var"] * (segment["range_rank"] + 1)
        for segment in all_segments
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1, _to_int(time_limit_seconds, CP_SAT_TIME_LIMIT_SECONDS))
    solver.parameters.num_search_workers = 8
    final_status_name = "OPTIMAL"
    for objective_expr in (active_bunches_var, segment_count_expr, capacity_units_expr, extra_units_expr):
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

    active_bunches = solver.Value(active_bunches_var)
    remaining_hands = {hand: active_bunches for hand in range(1, hands_per_bunch + 1)}
    rows = []
    detail_rows = []

    for row_record in row_records:
        row = row_record["row"]
        requested_boxes = row_record["requested_boxes"]
        segment_rows = []
        for segment in row_record["segments"]:
            bunches_allocated = solver.Value(segment["bunches_var"])
            if bunches_allocated <= 0:
                continue
            for hand in segment["hands"]:
                remaining_hands[hand] -= bunches_allocated
            kg_allocated = (bunches_allocated * segment["kg_per_bunch_units"]) / WEIGHT_SCALE
            boxes_capacity = (
                bunches_allocated * segment["kg_per_bunch_units"]
            ) // kg_per_box_units
            boxes_equivalent = kg_allocated / kg_per_box if kg_per_box > 0 else 0.0
            segment_row = {
                "processing_order": row_record["processing_order"],
                "original_index": row_record["original_index"],
                "customer_priority": row.get("customer_priority", row["market_priority"]),
                "customer": row.get("customer", ""),
                "market_priority": row["market_priority"],
                "market": row["market"],
                "sku_priority": row["sku_priority"],
                "sku": row["sku"].upper(),
                "hand_from": segment["hand_from"],
                "hand_to": segment["hand_to"],
                "hand_count": segment["hand_count"],
                "range_rank": segment["range_rank"],
                "range_label": f"{segment['hand_from']}-{segment['hand_to']}",
                "requested_boxes": 0,
                "order_requested_boxes": requested_boxes,
                "kg_per_bunch_for_sku": segment["kg_per_bunch_units"] / WEIGHT_SCALE,
                "bunches_needed": 0,
                "bunches_allocated": bunches_allocated,
                "kg_allocated": kg_allocated,
                "boxes_capacity": int(boxes_capacity),
                "boxes_equivalent": boxes_equivalent,
                "boxes_fulfilled": 0,
                "containers_fulfilled": 0.0,
                "short_boxes": 0,
                "short_containers": 0.0,
                "extra_kg_from_rounding": 0.0,
                "hand_units_consumed": bunches_allocated * segment["hand_count"],
                "is_fulfilled": True,
            }
            segment_rows.append(segment_row)

        remaining_segment_boxes = requested_boxes
        for segment_row in segment_rows:
            assigned_boxes = min(segment_row["boxes_capacity"], remaining_segment_boxes)
            segment_row["boxes_fulfilled"] = assigned_boxes
            remaining_segment_boxes -= assigned_boxes
        if remaining_segment_boxes > 0:
            fractional_rows = sorted(
                segment_rows,
                key=lambda item: item["boxes_equivalent"] - math.floor(item["boxes_equivalent"]),
                reverse=True,
            )
            for segment_row in fractional_rows:
                if remaining_segment_boxes <= 0:
                    break
                segment_row["boxes_fulfilled"] += 1
                remaining_segment_boxes -= 1

        for segment_row in segment_rows:
            segment_row["requested_boxes"] = segment_row["boxes_fulfilled"]
            segment_row["containers_fulfilled"] = segment_row["boxes_fulfilled"] / boxes_per_container
            segment_row["bunches_needed"] = (
                int(math.ceil((segment_row["boxes_fulfilled"] * kg_per_box) / segment_row["kg_per_bunch_for_sku"]))
                if segment_row["boxes_fulfilled"] > 0 and segment_row["kg_per_bunch_for_sku"] > 0
                else 0
            )
            segment_row["extra_kg_from_rounding"] = max(
                0.0,
                segment_row["kg_allocated"] - segment_row["boxes_fulfilled"] * kg_per_box,
            )
        detail_rows.extend(segment_rows)

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
        boxes_capacity = int(math.floor(kg_allocated / kg_per_box)) if kg_per_box > 0 else 0
        extra_kg_from_rounding = max(0.0, kg_allocated - requested_boxes * kg_per_box)
        range_labels = ", ".join(segment["range_label"] for segment in segment_rows)
        rows.append({
            "processing_order": row_record["processing_order"],
            "original_index": row_record["original_index"],
            "customer_priority": row.get("customer_priority", row["market_priority"]),
            "customer": row.get("customer", ""),
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
            "bunches_needed": bunches_allocated if requested_boxes else 0,
            "bunches_allocated": bunches_allocated,
            "kg_allocated": kg_allocated,
            "boxes_capacity": boxes_capacity,
            "boxes_fulfilled": requested_boxes,
            "containers_fulfilled": requested_boxes / boxes_per_container,
            "short_boxes": 0,
            "short_containers": 0.0,
            "extra_kg_from_rounding": extra_kg_from_rounding,
            "hand_units_consumed": hand_units_consumed,
            "is_fulfilled": True,
        })

    kg_allocated_total = sum(row["kg_allocated"] for row in rows)
    extra_kg_total = max(0.0, kg_allocated_total - total_requested_boxes * kg_per_box)
    source_kg = active_bunches * kg_per_bunch
    source_boxes_capacity = int(math.floor(source_kg / kg_per_box)) if kg_per_box > 0 else 0
    summary = {
        "total_bunches": active_bunches,
        "target_containers": total_requested_boxes // boxes_per_container,
        "requested_boxes": total_requested_boxes,
        "source_kg": source_kg,
        "kg_per_hand": kg_per_hand,
        "hand_weights": hand_weights,
        "source_boxes_capacity": source_boxes_capacity,
        "source_cont_capacity": source_boxes_capacity / boxes_per_container,
        "active_bunches_estimated": active_bunches,
        "segment_count": solver.Value(segment_count_expr),
        "fulfilled_boxes": total_requested_boxes,
        "fulfilled_containers": total_requested_boxes / boxes_per_container,
        "short_boxes": 0,
        "short_containers": 0.0,
        "kg_allocated": kg_allocated_total,
        "extra_kg_from_rounding": extra_kg_total,
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }
    return {
        "rows": rows,
        "detail_rows": detail_rows,
        "remaining_hands": remaining_hands,
        "summary": summary,
        "loss": {
            "active_bunches_estimated": active_bunches,
            "segment_count": solver.Value(segment_count_expr),
            "kg_allocated": kg_allocated_total,
            "extra_kg_from_rounding": extra_kg_total,
            "solver_status": final_status_name,
            "solver_backend": "ortools_cp_sat",
        },
        "solver_status": final_status_name,
        "solver_backend": "ortools_cp_sat",
    }


def calculate_min_bunches_for_container_plan(
    sku_rows: list[dict[str, Any]],
    kg_per_bunch: float,
    hands_per_bunch: int,
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Calculate the minimum whole bunches needed to satisfy fixed box demand."""
    cp_result = _calculate_min_bunches_cpsat(
        sku_rows,
        kg_per_bunch,
        hands_per_bunch,
        kg_per_box=kg_per_box,
        boxes_per_container=boxes_per_container,
        hand_weights=hand_weights,
    )
    if cp_result is not None:
        return cp_result

    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
    upper_bound = _minimum_bunch_upper_bound(
        normalize_sku_rows(sku_rows),
        hands_per_bunch,
        hand_weights,
        kg_per_box,
        boxes_per_container,
    )
    if upper_bound <= 0:
        return _empty_min_bunch_result(
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "beam_search_fallback",
            hand_weights,
        )

    requested_boxes = sum(
        _requested_boxes(row, boxes_per_container)
        for row in normalize_sku_rows(sku_rows)
        if row["demand"] > 0 and row["sku"]
    )
    best_result = None
    low, high = 0, upper_bound
    while low <= high:
        mid = (low + high) // 2
        result = allocate_bunches_optimized(
            mid,
            kg_per_bunch,
            hands_per_bunch,
            sku_rows,
            kg_per_box=kg_per_box,
            boxes_per_container=boxes_per_container,
            hand_weights=hand_weights,
        )
        summary = result.get("summary", {})
        feasible = (
            int(summary.get("short_boxes", 0)) == 0
            and int(summary.get("fulfilled_boxes", 0)) >= requested_boxes
        )
        if feasible:
            best_result = result
            high = mid - 1
        else:
            low = mid + 1

    if best_result is None:
        return _empty_min_bunch_result(
            kg_per_bunch,
            hands_per_bunch,
            kg_per_box,
            boxes_per_container,
            "NO_SOLUTION",
            "beam_search_fallback",
            hand_weights,
        )

    summary = best_result["summary"]
    active_bunches = int(summary.get("active_bunches_estimated", summary.get("total_bunches", 0)))
    summary["total_bunches"] = active_bunches
    summary["target_containers"] = requested_boxes // boxes_per_container
    summary["requested_boxes"] = requested_boxes
    summary["source_kg"] = active_bunches * kg_per_bunch
    summary["source_boxes_capacity"] = int(math.floor(summary["source_kg"] / kg_per_box)) if kg_per_box > 0 else 0
    summary["source_cont_capacity"] = summary["source_boxes_capacity"] / boxes_per_container
    summary["kg_allocated"] = sum(float(row.get("kg_allocated", 0)) for row in best_result.get("rows", []))
    summary["extra_kg_from_rounding"] = max(0.0, summary["kg_allocated"] - requested_boxes * kg_per_box)
    summary["solver_status"] = "APPROXIMATE"
    summary["solver_backend"] = "beam_search_fallback"
    best_result["solver_status"] = "APPROXIMATE"
    best_result["solver_backend"] = "beam_search_fallback"
    return best_result


def allocate_bunches_by_hands(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    hand_weights: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Allocate bunches to SKUs by remaining stock at each hand position.

    The allocator processes rows by market priority, then SKU priority, then
    original row order. Non-overlapping SKU ranges can use the same bunches;
    overlapping ranges compete for the same hand-position inventory.
    """
    total_bunches = max(0, _to_int(total_bunches))
    kg_per_bunch = max(0.0, _to_float(kg_per_bunch))
    hands_per_bunch = max(0, _to_int(hands_per_bunch))
    hand_weights, kg_per_bunch, kg_per_hand = _resolve_hand_weights(
        hands_per_bunch, kg_per_bunch, hand_weights
    )
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
                "hand_weights": hand_weights,
                "source_boxes_capacity": 0,
                "source_cont_capacity": 0.0,
                "fulfilled_boxes": 0,
                "fulfilled_containers": 0.0,
                "short_boxes": 0,
            },
        }

    normalized_rows = normalize_sku_rows(sku_rows)
    remaining_hands = {hand: total_bunches for hand in range(1, hands_per_bunch + 1)}
    results: list[dict[str, Any]] = []

    sorted_rows = sorted(
        enumerate(normalized_rows),
        key=lambda item: (
            item[1]["customer_priority"],
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
        kg_per_bunch_for_sku = range_weight(hand_from, hand_to, hand_weights)
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
                "customer_priority": row.get("customer_priority", row["market_priority"]),
                "customer": row.get("customer", ""),
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
        "hand_weights": hand_weights,
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
