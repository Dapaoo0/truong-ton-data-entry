# Changelog

Lịch sử các thay đổi và tính năng mới được triển khai vào dự án.

## [2026-04-06]
### Thay đổi quy trình (Docs/Rules)
- Cập nhật `.agents/rules/rule.md` bắt buộc duy trì 6 file theo dõi tiến độ trong thư mục `docs/`.
- Khởi tạo thư mục `docs/` cùng cấu trúc markdown cơ bản sửa lỗi font UTF-8.

### Tính năng mới (Features)
- [app.py] Tạo bảng chi tiết thông tin các lô và tích hợp tính toán (Tổng cây trồng, chích bắp thực tế/dự kiến, cắt bắp thực tế/dự kiến, harvest, tổng khối lượng).
- [app.py] Phân loại, tách biệt bảng chi tiết theo nhóm Vụ (F0, F1...) qua expander giao diện.
- [app.py] Thêm bộ filter độc lập (Trang trại, Vụ, Đội, Lô) cấu hình riêng cho bảng chi tiết lô ở "Global Data".

### Tinh chỉnh UI/UX (Fixes / Improvements)
- Căn giữa (align center) nội dung cho các bảng theo MultiIndex headers.
- Giới hạn rút ngắn số thập phân bị trôi ở cột "Diện tích (ha)" xuống còn 2 chữ số (sử dụng format chuỗi `f"{dien_tich:.2f}"` thay vì lệnh `round()` để giữ ổn định số 0 đuôi).
- Refactor tiến trình tách bảng bằng cách gom nhóm dữ liệu dictionary `detail_rows_by_vu` theo "Vụ", loại bỏ việc phải dùng pandas drop cột, từ đó tránh warning và lỗi form.
