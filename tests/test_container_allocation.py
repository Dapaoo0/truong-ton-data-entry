import container_allocation as ca

from container_allocation import (
    allocate_bunches_by_hands,
    allocate_bunches_optimized,
    calculate_max_containers_by_market,
    _valid_optimizer_ranges,
)


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


def _optimizer_row(market_priority, sku_priority, sku, demand, unit="Thùng", market="Nhật"):
    return {
        "market_priority": market_priority,
        "market": market,
        "sku_priority": sku_priority,
        "sku": sku,
        "demand": demand,
        "unit": unit,
    }


def _optimizer_customer_row(customer_priority, customer, sku_priority, sku, demand, market, unit="Thùng"):
    return {
        "customer_priority": customer_priority,
        "customer": customer,
        "market_priority": customer_priority,
        "market": market,
        "sku_priority": sku_priority,
        "sku": sku,
        "demand": demand,
        "unit": unit,
    }


def test_parent_ranges_generate_all_contiguous_subranges():
    ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, "30CP", 100), 12)

    assert (1, 1) in ranges
    assert (1, 2) in ranges
    assert (4, 9) in ranges
    assert (6, 9) in ranges
    assert (1, 9) in ranges
    assert len(ranges) == 45


def test_fixed_specs_are_parent_ranges_too():
    for sku, market, expected_count in [
        ("5H", "Nhật", 6),
        ("6H", "Nhật", 6),
        ("15CP", "Hàn", 6),
    ]:
        ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, sku, 100, market=market), 12)
        assert len(ranges) == expected_count


def test_27cp_is_not_available_for_korea():
    ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, "27CP", 100, market="Hàn"), 12)

    assert ranges == []


def test_optimizer_selects_27cp_parent_range_when_needed():
    result = allocate_bunches_optimized(922, 20, 12, [
        _optimizer_row(1, 1, "27CP", 591),
    ])

    row = result["rows"][0]
    assert row["sku"] == "27CP"
    assert row["hand_from"] == 1
    assert row["hand_to"] == 5
    assert row["boxes_fulfilled"] == 591


def test_optimizer_can_choose_contiguous_subrange_inside_parent_range():
    result = allocate_bunches_optimized(922, 20, 12, [
        _optimizer_row(1, 1, "27CP", 591),
        _optimizer_row(1, 2, "30CP", 300),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["27CP"]["range_label"] == "1-5"
    assert by_sku["30CP"]["range_label"] == "6-8"
    assert by_sku["27CP"]["boxes_fulfilled"] == 591
    assert by_sku["30CP"]["boxes_fulfilled"] == 300
    assert result["summary"]["active_bunches_estimated"] == 922


def test_optimizer_prefers_single_full_range_over_split_or_partial_bunches():
    result = allocate_bunches_optimized(65, 18, 12, [
        _optimizer_row(1, 1, "27CP", 520),
        _optimizer_row(1, 2, "6H", 240),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["27CP"]["range_label"] == "1-5"
    assert by_sku["27CP"]["bunches_allocated"] == 65
    assert by_sku["27CP"]["boxes_fulfilled"] == 37
    assert by_sku["6H"]["range_label"] == "6-7"
    assert by_sku["6H"]["boxes_fulfilled"] == 15
    assert result["summary"]["active_bunches_estimated"] == 65


def test_optimizer_allows_split_when_it_reduces_opened_bunches():
    if ca.cp_model is None:
        return

    result = allocate_bunches_optimized(100, 18, 12, [
        _optimizer_row(1, 1, "6H", 34),
        _optimizer_row(1, 2, "30CP", 69),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    selected_30cp_ranges = {
        range_label.strip()
        for range_label in by_sku["30CP"]["range_label"].split(",")
    }

    assert by_sku["6H"]["range_label"] == "5-7"
    assert selected_30cp_ranges == {"1-4", "8-9"}
    assert by_sku["30CP"]["boxes_fulfilled"] == 69
    assert result["summary"]["active_bunches_estimated"] == 100
    assert result["summary"]["segment_count"] == 3


def test_optimizer_reports_minimum_opened_bunches_when_source_is_surplus():
    result = allocate_bunches_optimized(5000, 18, 12, [
        _optimizer_row(1, 1, "27CP", 520),
        _optimizer_row(1, 2, "6H", 240),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["27CP"]["range_label"] == "1-5"
    assert by_sku["6H"]["range_label"] == "6-7"
    assert by_sku["27CP"]["boxes_fulfilled"] == 520
    assert by_sku["6H"]["boxes_fulfilled"] == 240
    assert result["summary"]["active_bunches_estimated"] == 1040
    assert result["summary"]["total_bunches"] == 5000


def test_optimizer_prioritizes_higher_market_before_opened_bunch_minimization():
    result = allocate_bunches_optimized(100, 18, 12, [
        _optimizer_row(1, 1, "27CP", 100),
        _optimizer_row(2, 1, "8H", 100, market="Hàn"),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["27CP"]["range_label"] == "1-5"
    assert by_sku["27CP"]["boxes_fulfilled"] == 57
    assert by_sku["8H"]["boxes_fulfilled"] == 0
    assert result["summary"]["active_bunches_estimated"] == 100


def test_optimizer_prioritizes_customer_before_market_grouping():
    result = allocate_bunches_optimized(100, 18, 12, [
        _optimizer_customer_row(2, "Wismettac (Nhật 1)", 1, "27CP", 100, "Nhật"),
        _optimizer_customer_row(1, "Uone", 1, "8H", 100, "Hàn"),
    ])

    assert result["rows"][0]["customer"] == "Uone"
    assert result["rows"][0]["market"] == "Hàn"
    assert result["rows"][0]["boxes_fulfilled"] >= result["rows"][1]["boxes_fulfilled"]


def test_optimizer_uses_tail_for_15cp_without_extra_bunches():
    result = allocate_bunches_optimized(922, 20, 12, [
        _optimizer_row(1, 1, "27CP", 591),
        _optimizer_row(1, 2, "30CP", 300),
        _optimizer_row(2, 1, "15CP", 354, market="Hàn"),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["15CP"]["range_label"] == "10-12"
    assert by_sku["15CP"]["boxes_fulfilled"] == 354
    assert by_sku["15CP"]["bunches_allocated"] <= 922


def test_optimizer_expands_30cp_to_needed_subrange_when_shorter_ranges_are_not_enough():
    result = allocate_bunches_optimized(1000, 20, 12, [
        _optimizer_row(1, 1, "30CP", 1000),
    ])

    row = result["rows"][0]
    assert row["range_label"] == "1-9"
    assert row["bunches_allocated"] == 867
    assert row["boxes_fulfilled"] == 1000
    assert result["summary"]["active_bunches_estimated"] == 867


def test_optimizer_supports_korea_skus_from_spec():
    result = allocate_bunches_optimized(1000, 18, 12, [
        _optimizer_row(1, 1, "8H", 300, market="Hàn"),
        _optimizer_row(1, 2, "5/6H", 600, market="Hàn"),
        _optimizer_row(1, 3, "15CP", 300, market="Hàn"),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert by_sku["8H"]["range_label"] == "1-4"
    assert by_sku["5/6H"]["range_label"] == "5-9"
    assert by_sku["15CP"]["range_label"] == "10-12"


def test_optimizer_does_not_allocate_sku_to_wrong_market():
    result = allocate_bunches_optimized(1000, 18, 12, [
        _optimizer_row(1, 1, "8H", 300, market="Nhật"),
    ])

    assert result["rows"] == []


def test_max_container_mode_allocates_week_28_example_by_market_priority():
    result = calculate_max_containers_by_market(3342, 18, 12, ["Nhật", "Hàn"])
    by_market = {row["market"]: row for row in result["rows"]}

    assert by_market["Nhật"]["full_containers"] == 2
    assert by_market["Hàn"]["full_containers"] == 1
    assert result["summary"]["fulfilled_containers"] == 3


def test_max_container_mode_matches_15kg_4000_bunch_scenario():
    result = calculate_max_containers_by_market(4000, 15, 12, ["Nhật", "Hàn"])
    by_market = {row["market"]: row for row in result["rows"]}

    assert by_market["Nhật"]["full_containers"] == 2
    assert by_market["Hàn"]["full_containers"] == 1
