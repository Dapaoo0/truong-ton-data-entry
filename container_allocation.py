"""Pure helpers for allocating harvested banana bunches by hand position."""

from __future__ import annotations

import math
from typing import Any


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
        "description": "Quả to, mập nhất. Yêu cầu khắt khe nhất, ưu tiên cắt phần ngọn đẹp nhất.",
        "ranges": [(1, 4), (1, 5), (1, 9)],
    },
    "8H": {
        "markets": ["Hàn"],
        "group": "Phần Ngọn",
        "description": "Lấy phần ngọn tương tự 27CP nhưng dùng để ráp container Hàn.",
        "ranges": [(1, 4)],
    },
    "6H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Quả thon đều, cố định ở khúc giữa trên.",
        "ranges": [(5, 7)],
    },
    "30CP": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Quả cỡ trung bình lớn, thường ráp nối tiếp sau khi 27CP đã lấy phần ngọn.",
        "ranges": [(6, 9), (1, 9)],
    },
    "5H": {
        "markets": ["Nhật"],
        "group": "Khúc Giữa",
        "description": "Cố định ở khúc giữa dưới, gần đuôi.",
        "ranges": [(8, 10)],
    },
    "5/6H": {
        "markets": ["Hàn"],
        "group": "Khúc Giữa",
        "description": "Cắt dải dài xuyên suốt khúc giữa buồng, tốc độ gom hàng nhanh.",
        "ranges": [(5, 10)],
    },
    "15CP": {
        "markets": ["Hàn"],
        "group": "Phần Đuôi",
        "description": "Mã tận dụng chiến lược, gom vét các nải nhỏ cuối buồng.",
        "ranges": [(10, 12), (11, 12)],
    },
}

BEAM_WIDTH = 250


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


def _valid_optimizer_ranges(row: dict[str, Any], hands_per_bunch: int) -> list[tuple[int, int]]:
    sku = row["sku"].upper()
    sku_rule = OPTIMIZER_SKU_RULES.get(sku, {})
    allowed_markets = sku_rule.get("markets", [])
    if allowed_markets and row.get("market") not in allowed_markets:
        return []
    ranges = sku_rule.get("ranges")
    if not ranges and row.get("hand_from") and row.get("hand_to"):
        ranges = [(row["hand_from"], row["hand_to"])]

    valid_ranges = []
    for hand_from, hand_to in ranges or []:
        if 1 <= hand_from <= hand_to <= hands_per_bunch:
            valid_ranges.append((hand_from, hand_to))
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
        state["hand_units_consumed"],
        state["range_preference"],
        round(state["extra_kg_from_rounding"], 6),
    )


def allocate_bunches_optimized(
    total_bunches: int,
    kg_per_bunch: float,
    hands_per_bunch: int,
    sku_rows: list[dict[str, Any]],
    kg_per_box: float = 13,
    boxes_per_container: int = 1320,
    beam_width: int = BEAM_WIDTH,
) -> dict[str, Any]:
    """Optimize SKU allocation by trying candidate hand ranges per SKU.

    The search keeps a beam of low-loss plans. The loss is lexicographic:
    shortage for higher-priority rows dominates shortage for lower-priority
    rows, then the optimizer minimizes hand units consumed, less-preferred
    ranges, and rounding waste.
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
    }
    if total_bunches <= 0 or kg_per_bunch <= 0 or hands_per_bunch <= 0 or kg_per_box <= 0:
        return {"rows": [], "remaining_hands": {}, "summary": empty_summary, "loss": {}}

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
                next_states.append({
                    "remaining_hands": next_remaining,
                    "rows": state["rows"] + [result_row],
                    "shortage_vector": state["shortage_vector"] + [result_row["short_boxes"]],
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
        return {"rows": [], "remaining_hands": remaining_hands, "summary": empty_summary, "loss": {}}

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
    }
    loss = {
        "shortage_vector": best_state["shortage_vector"],
        "shortage_loss": shortage_loss,
        "hand_units_consumed": best_state["hand_units_consumed"],
        "range_preference": best_state["range_preference"],
        "extra_kg_from_rounding": best_state["extra_kg_from_rounding"],
        "optimizer_loss": optimizer_loss,
    }
    return {
        "rows": best_state["rows"],
        "remaining_hands": best_state["remaining_hands"],
        "summary": summary,
        "loss": loss,
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
