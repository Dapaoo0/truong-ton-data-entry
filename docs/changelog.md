# Changelog

Lịch sử các thay đổi và tính năng mới được triển khai vào dự án.

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
