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
