import app


def test_pdf_instruction_explains_signature_size_and_batch_scope():
    instruction = app.get_destruction_pdf_instruction()

    assert "PDF" in instruction
    assert "10 MB" in instruction
    assert "chữ ký của người phụ trách" in instruction
    assert "tất cả dữ liệu xuất hủy trong cùng lần lưu" in instruction


def test_prepare_destruction_rows_expands_all_fifo_allocations_before_persistence():
    queue = [
        {
            "Lô": "A8", "Giai đoạn": "Trước thu hoạch", "Màu dây": "Đỏ",
            "Lý do": "Bệnh", "Ngày": "2026-06-08", "Số lượng": 15, "Tuần": 24,
        },
        {
            "Lô": "D4", "Giai đoạn": "Trước chích bắp", "Màu dây": "",
            "Lý do": "Đổ Ngã", "Ngày": "2026-06-08", "Số lượng": 5, "Tuần": 24,
        },
    ]
    calls = []

    def allocator(*args, **kwargs):
        calls.append((args, kwargs))
        lot = args[1]
        if lot == "A8":
            return True, "", [
                {"dim_lo_id": 1, "base_lot_id": 10, "so_luong": 10, "lot_id": "A8"},
                {"dim_lo_id": 1, "base_lot_id": 11, "so_luong": 5, "lot_id": "A8"},
            ]
        return True, "", [
            {"dim_lo_id": 2, "base_lot_id": 20, "so_luong": 5, "lot_id": "D4"},
        ]

    rows = app.prepare_destruction_rows(queue, "Farm 126", allocator)

    assert len(calls) == 2
    assert [row["so_luong"] for row in rows] == [10, 5, 5]
    assert [row["base_lot_id"] for row in rows] == [10, 11, 20]
    assert all(row["ngay_xuat_huy"] == "2026-06-08" for row in rows)
    assert all("document_id" not in row for row in rows)


def test_prepare_destruction_rows_stops_before_persistence_when_allocation_fails():
    queue = [{
        "Lô": "A8", "Giai đoạn": "Trước thu hoạch", "Màu dây": "Đỏ",
        "Lý do": "Bệnh", "Ngày": "2026-06-08", "Số lượng": 15, "Tuần": 24,
    }]

    def allocator(*args, **kwargs):
        return False, "Không đủ tồn", []

    try:
        app.prepare_destruction_rows(queue, "Farm 126", allocator)
    except ValueError as exc:
        assert str(exc) == "Không đủ tồn"
    else:
        raise AssertionError("Expected allocation failure")
