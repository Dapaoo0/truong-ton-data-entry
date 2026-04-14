# Command Summary

Tài liệu này lưu lại tóm tắt các yêu cầu của người dùng để theo dõi tiến độ và nhiệm vụ.

## Ngày 14/04/2026

- Tối ưu hóa hệ thống dự báo: Sửa lỗi phân bổ dữ liệu harvest bị mất khi vụ F0 kéo dài; đảm bảo dữ liệu "Cây đã trồng" cố định cho tất cả các vụ.
- Thiết lập Role-Based Access Control (RBAC): Thêm tài khoản bộ phận kinh doanh `"Kinh doanh"` có quyền xem dashboard global (tương tự Admin) nhưng không xem/quản trị form nhập liệu cụ thể của nông trường.
- Tự động thay đổi tên Farm tham chiếu thành "Phòng Kinh doanh" và push code trực tiếp lên git branch main.

## Ngày 06/04/2026

- Tạo một giao diện bảng chi tiết về thông tin các lô có trên farm gồm nhiều trường dữ liệu phức tạp (Chích bắp, cắt bắp, thu hoạch, khối lượng - có thực tế và dự toán).
- Tách bảng thông tin lô độc lập với phần Dự toán sản lượng và đưa lên trên cùng với bộ filter riêng.
- Căn giữa (middle align) text trong bảng chi tiết lô.
- Tách (split) bảng chi tiết lô ra thành nhiều bảng theo nhóm "Vụ" (ví dụ vụ F0, F1).
- Giới hạn độ dài số thập phân hiển thị ở trường "Diện tích (ha)" về còn tối đa 2 chữ số.
- Ẩn cột "Vụ" ở các bảng con (sub table) do đã có heading Markdown.
- Cập nhật rule bắt buộc duy trì và update các thư mục `docs/`.
- [Task Phụ] Brainstorm kiểm tra các rủi ro (edge cases) có thể xảy ra và thực hiện sửa lại Data structure cũng như F-string formatting để code trơn tru, logic đẹp mắt.
