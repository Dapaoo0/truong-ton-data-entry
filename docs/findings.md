# Findings

Những khám phá, cấu hình cứng và lưu ý kinh nghiệm tìm được trong quá trình code và phân tích.

- Cấu hình sản lượng dự toán: `KG_PER_TREE_F0 = 15` (F0: 15 kg/buồng), `KG_PER_TREE_FN = 18` (Fn: 18 kg/buồng). Helper: `get_kg_per_tree(vu)`. Hằng số đóng gói: `KG_PER_BOX = 13`, `BOXES_PER_CONTAINER = 1320`.
- **Quy tắc DRY cho constants**: Không hardcode cùng một giá trị ở nhiều nơi. Gom thành 1 định nghĩa duy nhất ở đầu file + helper function.
- Data source Pipeline (ETL): Tình trạng `missing CV` (Công việc) và `missing LO` ảnh hưởng trực tiếp tới tracking. Pipeline cần làm sạch và fetch từ GSheet trước khi đẩy vào Supabase Dimension.
- Sự đồng bộ Map: Dữ liệu `lot_id` và `lo` trong table `seasons` và `base_lots` phải được đồng bộ chính xác. Bất cứ ai thay đổi mapping này sai đều có thể dẫn tới bảng chi tiết dữ liệu hiện lên trống (empty dataframe).
- Việc chia tách bảng dữ liệu chi tiết theo 'Vụ' sẽ yêu cầu code thao tác mượt mà thông qua việc gom nhóm (group by dictionaries) từ lúc tạo list vòng lặp, tốt hơn nhiều so với việc trích xuất và gọi lệnh DataFrame `drop()` ẩn cột về sau.
- Cấu hình hiển thị bảng Streamlit (`st.dataframe`): Có thể tương thích kiểu Style text-alignment căn giữa của Pandas `df.style.set_properties(**{'text-align': 'center'})`, dù đôi khi nó phụ thuộc vào định dạng Arrow của Streamlit core.
- Kiểm soát formating hiển thị: Tại các trường hiển thị Float như `Diện tích (ha)`, nên dùng F-String formating `f"{dien_tich:.2f}"` (biến nó thành chuỗi rập khuôn hiển thị) khi không cần tính toán sort, thay vì hàm số học `round()` vì `round()` sẽ triệt tiêu số dư 0 tạo ra view không đồng nhất.
- **Auto Batch Mapping**: Hệ thống tự động liên kết log entries với đợt trồng (`base_lot_id`) dựa trên timeline sinh trưởng. Không yêu cầu user nhập chọn thủ công. Thuật toán closest-match so sánh expected dates của F0→F5 với ngày hành động thực tế.
- **Xử lý chồng chập timeline**: Khi 2 đợt trồng có expected date chồng chập (≤15 ngày), hệ thống gán theo đợt gần nhất. Trường hợp Fn: F1 bắt đầu = ngày harvest F0, nên Season Fn match bằng expected harvest F(n-1), không phải ngày trồng.
- **Destruction timeline**: Giai đoạn xuất hủy ("Trước chích bắp/cắt bắp/thu hoạch") được map sang stage tương ứng để dùng timeline matching chính xác, thay vì fallback closest-planted có thể match sai đợt mới trồng.
- **Harvest 3 Phases**: Dự báo thu hoạch dùng mô hình Normal Distribution truncated. Cửa sổ 54 ngày = Thu bói (14d, 10%) + Thu rộ (26d, 80%) + Thu vét (14d, 10%). Mỗi phase được gán vào tháng chứa midpoint của khoảng thời gian.
- **Hao hụt không kép**: Mỗi vụ Fn reset về số cây trồng gốc (không lấy 10% kép từ vụ trước), vì cây Fn mọc mới thay thế cây mẹ.
- **CSS Streamlit padding**: Khoảng trắng thừa đầu trang do Streamlit header mặc định. Fix bằng CSS: `.stMainBlockContainer { padding-top: 1rem }` + `header[data-testid="stHeader"] { height: 0 }`.
