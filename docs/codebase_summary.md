# Codebase Summary

Tài liệu cung cấp tóm tắt về cấu trúc, ý nghĩa các hàm chức năng và luồng hoạt động chính của dự án.

## File `app.py`
Trái tim của Streamlit framework, điều hướng nhiều tabs phân tích tổng và biểu đồ.
- `render_global_data_tab()`: Nơi thao tác giao diện biểu đồ và dữ liệu toàn cầu. Có logic filter, gom nhóm bảng theo vụ, render KPI dự toán và render chi tiết từng lô.
- `apply_filters_local()`: Hàm filter dữ liệu nhận vào (Dataframe) theo nhiều tiêu chí cục bộ khác nhau (Ví dụ farm, season, team, lot_id...). Tối ưu tốc độ mà không cần gọi SQL Database lại nhiều lần.
- `get_dynamic_lot_options()`: Hàm util trích xuất và sinh ra list option combo-box.

## File DB / Backend logic (Tách dần về sau)
- Pipeline sync data: Chứa các script convert bảng tính google sheet thành dictionary và data warehouse supabase.
