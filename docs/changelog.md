# Changelog

Lịch sử các thay đổi và tính năng mới được triển khai vào dự án.

## [Version 26.1 - RBAC Kinh doanh Role] - 2026-04-14

#### Security & RBAC (`app.py`, Supabase)
- **[Quyền truy cập mở rộng]**: Thiết lập thêm role "Phòng Kinh doanh" (team "Kinh doanh").
- **[Dashboard chuyên biệt]**: Cho phép tài khoản này truy cập màn hình dữ liệu toàn cục giống như Admin nhưng không sở hữu các quyền chỉnh sửa trực tiếp thông tin farm.
- **[Bug Fix]**:
  - Khắc phục lỗi hiển thị 0 số lượng cây trồng cho các Season Fn (không phải F0) do date range filter. Điều hướng property "cây đã trồng" thành hằng số từ base_lot.
  - Fix logic overlap window đối với thời gian harvest season khi F0 vượt quá ngày kết thúc hành chính.

#### Tính năng mới (`app.py`)
- **[Container Count]**: Thêm hiển thị số container dự kiến trên Lịch Thu hoạch. Công thức: `số thùng / 1320 = số container`. Hiển thị tại 2 vị trí:
  1. Thẻ card tổng hợp hàng tháng (🚛 ~X.X cont).
  2. Dialog chi tiết khi click vào từng tháng.

#### Refactoring (`app.py`)
- **[Clean-up KG_PER_TREE]**: Gộp 3 hằng số phân tán (`KG_PER_TREE_DETAIL`, `KG_PER_TREE`, `KG_PER_TREE_CHART`) thành 1 bộ constants trung tâm + helper function `get_kg_per_tree(vu)`. Logic mới: **F0 = 15 kg/buồng**, **Fn = 18 kg/buồng**.
- **[Magic Numbers]**: Gom `13 kg/thùng` → `KG_PER_BOX`, `1320 thùng/container` → `BOXES_PER_CONTAINER`.
- **[Loss Rates]**: Gom `LOSS_RATE = 0.10` local thành bộ constants trung tâm: `LOSS_RATE_TO_CHICH = 0.05` (5% từ trồng→chích) + `LOSS_RATE_TO_THU = 0.10` (10% tổng). Helper: `get_estimated_rate(stage)`.
- **[Detail Table Fix]**: Áp dụng hao hụt vào cột Dự toán (Chích bắp: 95%, Cắt bắp: 95%, Thu hoạch: 90%) thay vì hiển thị 100% cho tất cả.
- **[Caption]**: Thêm dòng ghi chú tỉ lệ hao hụt ngay dưới tiêu đề bảng chi tiết lô.

## [Version 26.0 - Harvest Forecast 3 Phases] - 2026-04-13

#### UI/CSS (`app.py`)
- **[Fix padding]**: Inject CSS loại bỏ khoảng trắng mặc định ở đầu trang Streamlit (ẩn `stHeader`, giảm `padding-top` container).

#### Tính năng mới: Lịch Thu hoạch Dự kiến (`app.py`)
- **[3 đợt thu]**: Phân tách thu hoạch thành Thu bói (10%) → Thu rộ (80%) → Thu vét (10%):
  - Mốc: `harvest_midpoint` (F0: +264d, Fn: +174d)
  - Thu rộ: ±13 ngày quanh mốc (26 ngày). Thu bói: 14 ngày trước. Thu vét: 14 ngày sau.
  - Tổng cửa sổ: 54 ngày/vụ. Hao hụt 10%/vụ (không kép).
- **[Filter Năm]**: Thêm selectbox lọc theo năm (default: năm hiện tại).
- **[Popover chi tiết]**: Click "🔍 Xem chi tiết" dưới mỗi thẻ tháng → hiện bảng breakdown: Lô, Vụ, Loại thu, Số buồng, Khoảng thời gian.

## [2026-04-09]
## [Version 25.0 - Auto Batch Mapping] - 2026-04-09

#### Database Migration
- **[DDL]**: Thêm cột `base_lot_id` (FK → base_lots.id) vào 4 bảng: `seasons`, `stage_logs`, `harvest_logs`, `destruction_logs`. Mục đích: liên kết trực tiếp từng record với đợt trồng cụ thể.

#### Logic nghiệp vụ (`app.py`)
- **[Auto-resolve base_lot_id]**: Triển khai hàm `resolve_base_lot_id()` sử dụng thuật toán closest-match dựa trên timeline sinh trưởng chuối:
  - F0: 180d (Chích bắp) → 194d (Cắt bắp) → 264d (Thu hoạch) tính từ ngày trồng.
  - Fn: +90d (Chích bắp) → +104d (Cắt bắp) → +174d (Thu hoạch) tính từ harvest F(n-1).
  - Destruction logs: map giai đoạn xuất hủy → stage tương ứng để dùng timeline matching.
- **[insert_to_db()]**: Tự động gọi `resolve_base_lot_id()` khi insert stage_logs, harvest_logs, destruction_logs.
- **[Edit dialogs]**: Thêm `base_lot_id` auto-resolved vào data dict khi update 3 loại log (stage, destruction, harvest).

#### Backfill dữ liệu
- **[backfill_base_lot_id.py]**: Script backfill 65 records hiện có. Kết quả verified: 100% chính xác (0 NULL trừ 4 seasons của lô chưa trồng).

## [2026-04-06]
## [Version 24.3 - Refactoring & Fix UI] - 2026-04-06

#### Refactor (`app.py`)
- **[Fix UI/Data Formatter]**: Sửa lỗi giao diện hiển thị bảng "Toàn bộ thông tin vụ". Thay đổi `st.dataframe` sang render bằng `st.markdown` với chuỗi `df.to_html()`. Xử lý đồng thời 2 lỗi: 
  1. Header (`Thông tin`, `Cắt bắp`...) bị căn trái (Do Streamlit sử dụng Glide Data Grid không hỗ trợ nhận HTML css text-align từ Styler).
  2. Trường `Diện tích` dù đã ép kiểu String Formatter `f-str` nhưng vẫn bị Streamlit Arrow backend ép ngược lại thành Object numbers (hiển thị 6 chữ số 0 dư).
- **[Logic Code]**: Loại bỏ phương thức `.drop()` của Pandas (tránh các warning khi gọi trên MultiIndex DataFrame) khi truy xuất dữ liệu danh sách `detail_rows`. Chuyển sang thu thập dictionary collection độc lập từng trường theo `{"Vụ" : rows_dict_list}`, tối ưu memory mapping.
- **[Layout Table]**: Áp dụng Styler `set_properties(**{'text-align': 'center'})` và ép f-string formatting `f"{dien_tich:.2f}"` ở phần tử diện tích để chốt cứng display UI. Mặc dù mất ưu thế Sortable by values của `st.dataframe()`, bù lại đem về thẩm mỹ tối ưu cho Dashboard.
