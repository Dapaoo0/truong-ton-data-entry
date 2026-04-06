# Findings

Những khám phá, cấu hình cứng và lưu ý kinh nghiệm tìm được trong quá trình code và phân tích.

- Cấu hình chung quy đổi sản lượng: `KG_PER_TREE = 18` (18kg/1 cây).
- Data source Pipeline (ETL): Tình trạng `missing CV` (Công việc) và `missing LO` ảnh hưởng trực tiếp tới tracking. Pipeline cần làm sạch và fetch từ GSheet trước khi đẩy vào Supabase Dimension.
- Sự đồng bộ Map: Dữ liệu `lot_id` và `lo` trong table `seasons` và `base_lots` phải được đồng bộ chính xác. Bất cứ ai thay đổi mapping này sai đều có thể dẫn tới bảng chi tiết dữ liệu hiện lên trống (empty dataframe).
- Việc chia tách bảng dữ liệu chi tiết theo 'Vụ' sẽ yêu cầu code thao tác mượt mà thông qua việc gom nhóm (group by dictionaries) từ lúc tạo list vòng lặp, tốt hơn nhiều so với việc trích xuất và gọi lệnh DataFrame `drop()` ẩn cột về sau.
- Cấu hình hiển thị bảng Streamlit (`st.dataframe`): Có thể tương thích kiểu Style text-alignment căn giữa của Pandas `df.style.set_properties(**{'text-align': 'center'})`, dù đôi khi nó phụ thuộc vào định dạng Arrow của Streamlit core.
- Kiểm soát formating hiển thị: Tại các trường hiển thị Float như `Diện tích (ha)`, nên dùng F-String formating `f"{dien_tich:.2f}"` (biến nó thành chuỗi rập khuôn hiển thị) khi không cần tính toán sort, thay vì hàm số học `round()` vì `round()` sẽ triệt tiêu số dư 0 tạo ra view không đồng nhất.
