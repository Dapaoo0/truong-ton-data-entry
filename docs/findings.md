# Findings

Những khám phá, cấu hình cứng và lưu ý kinh nghiệm tìm được trong quá trình code và phân tích.

- Cấu hình chung quy đổi sản lượng: `KG_PER_TREE = 18` (18kg/1 cây).
- Data source Pipeline (ETL): Tình trạng `missing CV` (Công việc) và `missing LO` ảnh hưởng trực tiếp tới tracking. Pipeline cần làm sạch và fetch từ GSheet trước khi đẩy vào Supabase Dimension.
- Sự đồng bộ Map: Dữ liệu `lot_id` và `lo` trong table `seasons` và `base_lots` phải được đồng bộ chính xác. Bất cứ ai thay đổi mapping này sai đều có thể dẫn tới bảng chi tiết dữ liệu hiện lên trống (empty dataframe).
- Việc chia tách bảng dữ liệu chi tiết theo 'Vụ' sẽ yêu cầu code thao tác mượt mà thông qua `st.expander` kết hợp drop cột để không làm ngộp dữ liệu.
