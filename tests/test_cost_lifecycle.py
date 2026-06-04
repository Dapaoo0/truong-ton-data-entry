import cost_lifecycle as cl


def test_batch_lifecycle_ends_old_batch_by_closed_season():
    plantings = [
        {"id": 1, "dim_lo_id": 10, "ngay_trong": "2025-01-01", "so_luong": 1000, "dien_tich_trong": 1.0},
        {"id": 2, "dim_lo_id": 10, "ngay_trong": "2026-01-01", "so_luong": 500, "dien_tich_trong": 0.5},
    ]
    seasons = [
        {"base_lot_id": 1, "ngay_ket_thuc_thuc_te": "2025-12-31"},
        {"base_lot_id": 2, "ngay_ket_thuc_thuc_te": None},
    ]

    batches = cl.build_batch_lifecycle(plantings, seasons)
    old_batch, new_batch = batches

    assert not cl.is_batch_active_on_date(old_batch, "2026-02-01")
    assert cl.is_batch_active_on_date(new_batch, "2026-02-01")


def test_lot_weight_uses_only_active_batch_area():
    plantings = [
        {"id": 1, "dim_lo_id": 10, "ngay_trong": "2025-01-01", "so_luong": 1000, "dien_tich_trong": 1.0},
        {"id": 2, "dim_lo_id": 10, "ngay_trong": "2026-01-01", "so_luong": 500, "dien_tich_trong": 0.5},
    ]
    seasons = [
        {"base_lot_id": 1, "ngay_ket_thuc_thuc_te": "2025-12-31"},
        {"base_lot_id": 2, "ngay_ket_thuc_thuc_te": None},
    ]

    batches = cl.build_batch_lifecycle(plantings, seasons)
    weight = cl.lot_weight_on_date(10, "2026-02-01", {10: batches}, {10: {"area_ha": 1.5}})

    assert weight == 0.5


def test_harvest_cost_detection_is_conservative():
    assert cl.is_harvest_related_cost({"cong_doan": "Thu hoạch"})
    assert cl.is_harvest_related_cost({"category": "Chi phí thu hoạch"})
    assert cl.is_harvest_related_cost({"scope_label": "Thu hoạch"})
    assert not cl.is_harvest_related_cost({"category": "Chăm sóc buồng"})
    assert not cl.is_harvest_related_cost({"detail": "Công vườn ươm"})


def test_harvest_quantity_only_counts_past_harvest_for_batch():
    harvest_rows = [
        {"base_lot_id": 1, "ngay_thu_hoach": "2026-01-10", "so_luong": 100},
        {"base_lot_id": 1, "ngay_thu_hoach": "2026-02-10", "so_luong": 50},
        {"base_lot_id": 2, "ngay_thu_hoach": "2026-01-10", "so_luong": 999},
    ]
    grouped = cl.build_harvest_rows_by_batch(harvest_rows)

    assert cl.harvest_quantity_for_batch_until(grouped, 1, "2026-01-31") == 100
    assert cl.harvest_quantity_for_batch_until(grouped, 1, "2026-02-28") == 150
    assert cl.harvest_quantity_for_batch_until(grouped, 3, "2026-02-28") == 0
