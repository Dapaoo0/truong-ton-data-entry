# Command Summary

Tài liệu này lưu lại tóm tắt các yêu cầu của người dùng để theo dõi tiến độ và nhiệm vụ.

## Ngày 17/04/2026

- Nâng cấp thẻ Lịch Thu hoạch Dự kiến: Thêm 3 mốc dự báo (① Từ Trồng − xuất hủy, ② Từ Cắt bắp, ③ Thực tế). Card UI, dialog, bảng tổng hợp đều hiển thị 3 mốc. Fallback "Chưa có TT" khi thiếu data.
- Implement logic phân bổ xuất hủy theo tỉ lệ (proportional allocation): trừ trực tiếp nếu có `base_lot_id`, phân bổ `hủy × (batch/tổng_lô)` nếu chỉ có `dim_lo_id`.
- Thêm dòng tổng cộng (TỔNG) cho Bảng chi tiết thông tin các lô (Theo Vụ), tự động tính tổng diện tích, số cây, các chỉ số dự toán/thực tế và định dạng số có dấu phẩy.
- Cập nhật `business_logic.md` §3.3 + §3.4, `changelog.md`, `command.md`.

## Ngày 15/04/2026

- Kiểm tra cấu trúc dữ liệu chích bắp (báo cáo chi phí hàng ngày) trong `fact_nhat_ky_san_xuat` Farm 157 — phát hiện 575/576 records `lo_id = NULL`.
- Viết prompt chi tiết mô tả ETL bug (lo_id NULL cho Chích Bắp) để đưa vào workspace ETL.
- Sau khi ETL fix: Kiểm tra cấu trúc dữ liệu, cross-mapping chích bắp từ nhật ký hàng ngày với `base_lots` (đợt trồng mới).
- Phân tích tính hợp lý theo timeline: so sánh expected window chích bắp (5-7 tháng sau trồng) với dữ liệu thực tế từng lô, suy luận xem data thuộc đợt trồng nào. Kết luận: data hiện tại thuộc vụ cũ.
- Ghi chú: Các lô không được khởi tạo trong app Input Dự báo = lô cũ, không cần quan tâm cho dự báo.
- Tìm kiếm ngày ghi chép dữ liệu mới nhất về hạng mục "chích bắp" của Farm 157 trong `fact_nhat_ky_san_xuat`. Kết quả là ngày 13/03/2026.
- Kiểm tra lại chích bắp Farm 157 sau cập nhật ETL T4/2026: Data mới nhất đến 09/04, 3 lô mới (3A, 3B, 8B) đã có data in-window hợp lý. ETL fix thành công (100% coverage T3-T4). Phát hiện 10 base_lots đang trong window.
- Tạo báo cáo chi tiết tập trung Farm 157: cross-mapping 25 đợt trồng, tiến trình theo tuần, phân loại lô cũ/mới, khuyến nghị theo dõi.
- Insert dữ liệu chích bắp từ `fact_nhat_ky_san_xuat` vào `stage_logs` cho 3 lô đợt mới: 3A (đợt #6), 3B (đợt #7), 8B (đợt #15). Tổng hợp theo tuần, `mau_day` = NULL. 7 records (ID 36-42).
- Thêm tính năng tùy chỉnh tỷ lệ % Thu bói / Thu rộ / Thu vét (mặc định 10/80/10). Giữ nguyên cửa sổ 55 ngày cố định, rescale PDF weights theo tỷ lệ custom. Nằm trong `st.expander` để không chiếm diện tích.
- Tách Trồng dặm khỏi Trồng mới: Trồng dặm không tạo chu kỳ F0→F3 riêng trong forecast. Loại khỏi bảng chi tiết & lịch thu hoạch. Thêm bảng riêng "📋 Lịch sử Trồng dặm" (expander) hiển thị chi tiết + tổng hợp theo lô.
- Migration `add_loai_trong_to_base_lots`: Di chuyển `loai_trong` từ `seasons` sang `base_lots`. Sửa `app.py` đọc trực tiếp, thêm `loai_trong` vào insert flow.
- Fix lỗi `KeyError: 'loai_trong'` do xung đột dữ liệu sinh ra bởi Pandas `pd.merge` cũ chưa được xoá sau Migration.

## Ngày 14/04/2026

- Tối ưu hóa hệ thống dự báo: Sửa lỗi phân bổ dữ liệu harvest bị mất khi vụ F0 kéo dài; đảm bảo dữ liệu "Cây đã trồng" cố định cho tất cả các vụ.
- Thiết lập Role-Based Access Control (RBAC): Thêm tài khoản bộ phận kinh doanh `"Kinh doanh"` có quyền xem dashboard global (tương tự Admin) nhưng không xem/quản trị form nhập liệu cụ thể của nông trường.
- Tự động thay đổi tên Farm tham chiếu thành "Phòng Kinh doanh" và push code trực tiếp lên git branch main.
- Thêm hiển thị số container trên Lịch Thu hoạch dự kiến. Quy đổi: 1320 thùng = 1 container.
- Clean up và refactor constants: F0 = 15 kg/buồng, Fn = 18 kg/buồng. Gom về 1 nơi duy nhất.
- Áp dụng tỉ lệ hao hụt theo giai đoạn vào bảng chi tiết lô: Chích bắp trừ 5%, Thu hoạch trừ 10%. Gom constants loss rate về đầu file, không hardcode.
- Thêm ghi chú tỉ lệ hao hụt (5% trồng→chích, 5% chích→thu) ngay dưới tiêu đề bảng chi tiết lô.

## Ngày 06/04/2026

- Tạo một giao diện bảng chi tiết về thông tin các lô có trên farm gồm nhiều trường dữ liệu phức tạp (Chích bắp, cắt bắp, thu hoạch, khối lượng - có thực tế và dự toán).
- Tách bảng thông tin lô độc lập với phần Dự toán sản lượng và đưa lên trên cùng với bộ filter riêng.
- Căn giữa (middle align) text trong bảng chi tiết lô.
- Tách (split) bảng chi tiết lô ra thành nhiều bảng theo nhóm "Vụ" (ví dụ vụ F0, F1).
- Giới hạn độ dài số thập phân hiển thị ở trường "Diện tích (ha)" về còn tối đa 2 chữ số.
- Ẩn cột "Vụ" ở các bảng con (sub table) do đã có heading Markdown.
- Cập nhật rule bắt buộc duy trì và update các thư mục `docs/`.
- [Task Phụ] Brainstorm kiểm tra các rủi ro (edge cases) có thể xảy ra và thực hiện sửa lại Data structure cũng như F-string formatting để code trơn tru, logic đẹp mắt.
