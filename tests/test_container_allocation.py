import container_allocation as ca

from container_allocation import (
    allocate_bunches_by_hands,
    allocate_bunches_optimized,
    build_hand_weight_profile,
    calculate_min_bunches_for_container_plan,
    calculate_max_containers_by_market,
    range_weight,
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


def test_scaled_hand_weight_profiles_match_target_kg():
    profile_12_18 = build_hand_weight_profile(12, 18)
    profile_12_20 = build_hand_weight_profile(12, 20)
    profile_9_156 = build_hand_weight_profile(9, 15.6)

    assert round(sum(profile_12_18["hand_weights"].values()), 6) == 18
    assert round(sum(profile_12_20["hand_weights"].values()), 6) == 20
    assert round(sum(profile_9_156["hand_weights"].values()), 6) == 15.6
    assert round(range_weight(5, 7, profile_12_18["hand_weights"]), 2) == 4.31
    assert round(range_weight(5, 7, profile_12_20["hand_weights"]), 2) == 4.79
    assert round(range_weight(8, 9, profile_9_156["hand_weights"]), 2) == 4.60


def test_allocation_can_use_scaled_hand_weight_profile():
    profile = build_hand_weight_profile(12, 18)
    result = allocate_bunches_by_hands(
        5000,
        profile["kg_per_bunch"],
        profile["hands_per_bunch"],
        [_row(1, 1, "6H", 5, 7, 240)],
        hand_weights=profile["hand_weights"],
    )
    row = result["rows"][0]

    assert round(row["kg_per_bunch_for_sku"], 2) == 4.31
    assert row["bunches_needed"] == 724
    assert row["boxes_fulfilled"] == 240


def test_optimizer_can_use_scaled_hand_weight_profile():
    profile = build_hand_weight_profile(12, 18)
    result = allocate_bunches_optimized(
        5000,
        profile["kg_per_bunch"],
        profile["hands_per_bunch"],
        [_optimizer_row(1, 1, "6H", 240)],
        hand_weights=profile["hand_weights"],
    )
    row = result["rows"][0]

    assert row["range_label"] == "5-7"
    assert round(row["kg_per_bunch_for_sku"], 2) == 4.31
    assert row["bunches_allocated"] == 724
    assert row["boxes_fulfilled"] == 240


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


def test_nine_hand_profile_uses_inferred_parent_ranges():
    ranges_30cp = _valid_optimizer_ranges(_optimizer_row(1, 1, "30CP", 100), 9)
    ranges_15cp = _valid_optimizer_ranges(_optimizer_row(1, 1, "15CP", 100, market="Hàn"), 9)

    assert (1, 7) in ranges_30cp
    assert (6, 9) in ranges_15cp
    assert (6, 6) in ranges_15cp
    assert (7, 9) in ranges_15cp
    assert (8, 9) in ranges_15cp
    assert (5, 5) not in ranges_15cp
    assert (10, 10) not in ranges_15cp


def test_fixed_specs_are_parent_ranges_too():
    for sku, market, expected_count in [
        ("5H", "Nhật", 6),
        ("6H", "Nhật", 6),
        ("15CP", "Hàn", 6),
        ("12CP", "Hàn", 6),
        ("10CP", "Hàn", 6),
    ]:
        ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, sku, 100, market=market), 12)
        assert len(ranges) == expected_count


def test_korea_cp_skus_use_six_to_nine_parent_range_for_nine_hand_bunches():
    for sku in ["15CP", "12CP", "10CP"]:
        ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, sku, 100, market="Hàn"), 9)

        assert (6, 9) in ranges
        assert (6, 6) in ranges
        assert (9, 9) in ranges
        assert (5, 9) not in ranges
        assert (10, 10) not in ranges
        assert len(ranges) == 10


def test_korea_cp_skus_are_not_available_for_japan():
    for sku in ["15CP", "12CP", "10CP"]:
        ranges = _valid_optimizer_ranges(_optimizer_row(1, 1, sku, 100, market="Nhật"), 9)

        assert ranges == []


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
    assert set(by_sku["27CP"]["range_label"].split(", ")) == {"5-5", "1-4"}
    assert set(by_sku["6H"]["range_label"].split(", ")) == {"5-5", "6-7"}
    assert by_sku["27CP"]["boxes_fulfilled"] == 520
    assert by_sku["6H"]["boxes_fulfilled"] == 240
    assert result["summary"]["active_bunches_estimated"] == 941
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
    assert result["summary"]["active_bunches_estimated"] == 99


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
    result = allocate_bunches_optimized(2000, 18, 12, [
        _optimizer_row(1, 1, "8H", 300, market="Hàn"),
        _optimizer_row(1, 2, "5/6H", 600, market="Hàn"),
        _optimizer_row(1, 3, "15CP", 300, market="Hàn"),
        _optimizer_row(1, 4, "12CP", 100, market="Hàn"),
        _optimizer_row(1, 5, "10CP", 100, market="Hàn"),
    ])

    by_sku = {row["sku"]: row for row in result["rows"]}
    parent_ranges = {
        "8H": (1, 4),
        "5/6H": (5, 9),
        "15CP": (10, 12),
        "12CP": (10, 12),
        "10CP": (10, 12),
    }
    for sku, parent_range in parent_ranges.items():
        assert by_sku[sku]["boxes_fulfilled"] > 0
        detail_rows = [row for row in result["detail_rows"] if row["sku"] == sku]
        assert detail_rows
        for detail_row in detail_rows:
            assert parent_range[0] <= detail_row["hand_from"] <= detail_row["hand_to"] <= parent_range[1]


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


def test_max_container_market_rows_report_active_bunches_not_segment_sum():
    result = calculate_max_containers_by_market(3342, 18, 12, ["Nhật", "Hàn"])

    assert result["summary"]["active_bunches_estimated"] <= 3342
    for row in result["rows"]:
        assert row["active_bunches_used"] <= 3342


def test_max_container_mode_matches_15kg_4000_bunch_scenario():
    result = calculate_max_containers_by_market(4000, 15, 12, ["Nhật", "Hàn"])
    by_market = {row["market"]: row for row in result["rows"]}

    assert by_market["Nhật"]["full_containers"] == 2
    assert by_market["Hàn"]["full_containers"] == 1


def test_min_bunch_mode_satisfies_one_fixed_container():
    result = calculate_min_bunches_for_container_plan(
        [
            _optimizer_customer_row(1, "Wismettac (Nhật 1)", 1, "27CP", 660, "Nhật"),
            _optimizer_customer_row(1, "Wismettac (Nhật 1)", 2, "6H", 660, "Nhật"),
        ],
        18,
        12,
    )

    summary = result["summary"]
    assert summary["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    assert summary["requested_boxes"] == 1320
    assert summary["fulfilled_boxes"] == 1320
    assert summary["short_boxes"] == 0
    assert summary["active_bunches_estimated"] == summary["total_bunches"]
    assert summary["active_bunches_estimated"] > 0


def test_min_bunch_mode_handles_multiple_container_demands():
    result = calculate_min_bunches_for_container_plan(
        [
            _optimizer_customer_row(1, "Wismettac (Nhật 1)", 1, "27CP", 1320, "Nhật"),
            _optimizer_customer_row(2, "Uone", 1, "8H", 660, "Hàn"),
            _optimizer_customer_row(2, "Uone", 2, "15CP", 660, "Hàn"),
        ],
        18,
        12,
    )

    by_sku = {row["sku"]: row for row in result["rows"]}
    assert result["summary"]["requested_boxes"] == 2640
    assert result["summary"]["fulfilled_boxes"] == 2640
    assert by_sku["27CP"]["boxes_fulfilled"] == 1320
    assert by_sku["8H"]["boxes_fulfilled"] == 660
    assert by_sku["15CP"]["boxes_fulfilled"] == 660
    assert result["summary"]["short_boxes"] == 0


def test_min_bunch_mode_rejects_wrong_market_sku():
    result = calculate_min_bunches_for_container_plan(
        [_optimizer_customer_row(1, "Wismettac (Nhật 1)", 1, "15CP", 1320, "Nhật")],
        18,
        12,
    )

    assert result["rows"] == []
    assert result["summary"]["solver_status"] == "NO_SOLUTION"


def test_min_bunch_mode_allows_split_when_it_reduces_opened_bunches():
    result = calculate_min_bunches_for_container_plan(
        [
            _optimizer_row(1, 1, "6H", 34),
            _optimizer_row(1, 2, "30CP", 69),
        ],
        18,
        12,
    )

    by_sku = {row["sku"]: row for row in result["rows"]}
    selected_30cp_ranges = {
        range_label.strip()
        for range_label in by_sku["30CP"]["range_label"].split(",")
    }
    assert by_sku["6H"]["range_label"] == "5-7"
    assert selected_30cp_ranges == {"1-4", "8-9"}
    assert result["summary"]["active_bunches_estimated"] == 100


def test_min_bunch_mode_uses_korea_cp_skus_on_six_to_nine_for_nine_hand_profile():
    profile = build_hand_weight_profile(9, 15.6)
    result = calculate_min_bunches_for_container_plan(
        [
            _optimizer_row(1, 1, "15CP", 440, market="Hàn"),
            _optimizer_row(1, 2, "12CP", 440, market="Hàn"),
            _optimizer_row(1, 3, "10CP", 440, market="Hàn"),
        ],
        profile["kg_per_bunch"],
        profile["hands_per_bunch"],
        hand_weights=profile["hand_weights"],
    )

    assert result["summary"]["fulfilled_boxes"] == 1320
    assert result["summary"]["short_boxes"] == 0
    for detail_row in result["detail_rows"]:
        assert 6 <= detail_row["hand_from"] <= detail_row["hand_to"] <= 9
