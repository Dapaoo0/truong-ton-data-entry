import app


def test_nt_input_menu_hides_planting_and_fusarium():
    options = app.get_nt_tab_options("NT1")

    assert "🌱 Khởi tạo Lô trồng" not in options
    assert "🦠 Kiểm tra Fusarium" not in options
    assert "📈 Cập nhật Tiến độ" in options
    assert "🗑️ Cập nhật Xuất hủy" in options


def test_bvtv_menu_remains_read_and_progress_only():
    assert app.get_nt_tab_options("Đội BVTV") == [
        "🌐 Dữ liệu toàn cục",
        app.COST_DASH_TAB_LABEL,
        "📈 Cập nhật Tiến độ",
    ]
