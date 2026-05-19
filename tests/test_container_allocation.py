from container_allocation import allocate_bunches_by_hands


def _row(market_priority, sku_priority, sku, hand_from, hand_to, demand, unit="Thùng", market="Nhật"):
    return {
        "market_priority": market_priority,
        "market": market,
        "sku_priority": sku_priority,
        "sku": sku,
        "hand_from": hand_from,
        "hand_to": hand_to,
        "demand": demand,
        "unit": unit,
    }


def _first_result(total_bunches, kg_per_bunch, row):
    result = allocate_bunches_by_hands(total_bunches, kg_per_bunch, 12, [row])
    return result["rows"][0]


def test_6h_examples_from_guide():
    r18 = _first_result(5000, 18, _row(1, 1, "6H", 5, 7, 240))
    r20 = _first_result(5000, 20, _row(1, 1, "6H", 5, 7, 240))

    assert r18["bunches_needed"] == 694
    assert r18["boxes_fulfilled"] == 240
    assert r20["bunches_needed"] == 624
    assert r20["boxes_fulfilled"] == 240


def test_27cp_examples_from_guide():
    r18 = _first_result(5000, 18, _row(1, 1, "27CP", 1, 4, 520))
    r20 = _first_result(5000, 20, _row(1, 1, "27CP", 1, 4, 520))

    assert r18["bunches_needed"] == 1127
    assert r18["boxes_fulfilled"] == 520
    assert r20["bunches_needed"] == 1014
    assert r20["boxes_fulfilled"] == 520


def test_non_overlapping_skus_do_not_consume_each_other():
    result = allocate_bunches_by_hands(1200, 18, 12, [
        _row(1, 1, "27CP", 1, 4, 520),
        _row(1, 2, "6H", 5, 7, 240),
    ])

    by_sku = {r["sku"]: r for r in result["rows"]}
    assert by_sku["27CP"]["bunches_allocated"] == 1127
    assert by_sku["6H"]["bunches_allocated"] == 694
    assert result["remaining_hands"][1] == 73
    assert result["remaining_hands"][5] == 506


def test_sku_priority_controls_overlapping_hand_ranges():
    result_5h_first = allocate_bunches_by_hands(1000, 18, 12, [
        _row(1, 1, "5H", 4, 6, 400),
        _row(1, 2, "6H", 5, 7, 400),
    ])
    result_6h_first = allocate_bunches_by_hands(1000, 18, 12, [
        _row(1, 1, "6H", 5, 7, 400),
        _row(1, 2, "5H", 4, 6, 400),
    ])

    assert result_5h_first["rows"][0]["sku"] == "5H"
    assert result_5h_first["rows"][0]["bunches_allocated"] == 1000
    assert result_5h_first["rows"][1]["sku"] == "6H"
    assert result_5h_first["rows"][1]["bunches_allocated"] == 0

    assert result_6h_first["rows"][0]["sku"] == "6H"
    assert result_6h_first["rows"][0]["bunches_allocated"] == 1000
    assert result_6h_first["rows"][1]["sku"] == "5H"
    assert result_6h_first["rows"][1]["bunches_allocated"] == 0


def test_market_priority_is_applied_before_sku_priority():
    result = allocate_bunches_by_hands(1000, 18, 12, [
        _row(2, 1, "Japan 5H", 4, 6, 400, market="Nhật"),
        _row(1, 9, "Korea 6H", 5, 7, 400, market="Hàn"),
    ])

    assert result["rows"][0]["sku"] == "Korea 6H"
    assert result["rows"][0]["bunches_allocated"] == 1000
    assert result["rows"][1]["sku"] == "Japan 5H"
    assert result["rows"][1]["bunches_allocated"] == 0


def test_rounding_extra_kg_does_not_over_report_customer_boxes():
    result = allocate_bunches_by_hands(1000, 18, 12, [
        _row(1, 1, "FULL", 1, 12, 1000),
    ])
    row = result["rows"][0]

    assert row["bunches_needed"] == 723
    assert row["boxes_capacity"] == 1001
    assert row["boxes_fulfilled"] == 1000
    assert row["short_boxes"] == 0
    assert row["extra_kg_from_rounding"] == 14
