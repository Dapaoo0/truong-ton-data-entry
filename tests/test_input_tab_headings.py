from pathlib import Path


def test_operational_input_tabs_do_not_repeat_intro_headings():
    app_source = Path("app.py").read_text(encoding="utf-8")

    redundant_headings = [
        "#### Đăng ký đợt xuống giống mới",
        "#### Đo kích thước buồng mẫu",
        "#### Báo cáo số lượng cây thực tế",
        "#### Ghi nhận kết quả Đo pH Đất",
        "#### Ghi nhận: Chích bắp / Cắt bắp",
        "#### Ghi nhận số lượng cây chết / hư hỏng",
        "#### Ghi nhận số lượng cây bị bệnh Fusarium",
        "#### Ghi nhận Sản lượng Thu hoạch hàng ngày",
        "#### Ghi nhận Tỷ lệ BSR thành phẩm",
    ]

    for heading in redundant_headings:
        assert heading not in app_source
