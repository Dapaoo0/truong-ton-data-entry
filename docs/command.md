# Command Summary

Tài liệu này lưu lại tóm tắt các yêu cầu của người dùng để theo dõi tiến độ và nhiệm vụ.

## Ngày 25/04/2026

- Fix tooltip bản đồ Farm 157 bị tràn trên mobile: thêm `@media (max-width: 600px)` CSS, scale down font/padding/width. JS positioning dùng `offsetWidth/Height` thay vì hardcoded pixels.
- Thử nghiệm `postMessage` auto-resize iframe cho map → thất bại (chỉ hoạt động với Streamlit Custom Components). Revert `height=700`.
- Đọc docs `st.image` theo gợi ý user: `st.image` hỗ trợ SVG + `width="stretch"` responsive, nhưng mất interactive JS. User quyết định giữ nguyên `components.html`.
- Verify chích bắp Farm 157 vs Excel nguồn: khớp 100% từng lô (3A, 3B, 3BF, 8A, 8B). Tổng DB = 4,598. Excel dòng TỔNG bị sai (5,384 thay vì 5,425).
- Cập nhật docs theo rule.md.



- User cung cấp JSON polygon data (24 lô Farm 157) từ Polygon Tracer tool.
- Tích hợp interactive SVG map vào dashboard (`app.py`): 24 polygon, hover tooltip, màu theo giai đoạn, legend bar.
- Polygon Tracer hỗ trợ thêm JPG/JPEG image format.
- Đồng bộ logic Map & Table: extract `compute_batch_stats()` shared function, add upper bound filter cho stage_logs.
- Implement FIFO batch allocation: `allocate_fifo_quantity()` phân bổ chích bắp/cắt bắp/thu hoạch theo đợt trồng cũ nhất trước. Insert kèm `base_lot_id`.
- Reset & re-insert chích bắp từ Excel "mặt bằng chích bắp tuần 16": xóa 68 records cũ, insert 42 records mới. 3BF=đợt 1 (F1, batch 25), 3B=đợt 2 (F0, batch 7). 7A=vụ cũ (bỏ qua).
- Cập nhật docs: `changelog.md`, `command.md`, `business_logic.md`, `codebase_summary.md`, `findings.md`.

## Ngày 23/04/2026

- Phát hiện và fix bug thu hoạch F0 bị gán nhầm vào F1 (lô 3B, base_lot_id=25, 772 cây). Thêm `HARVEST_MIN_GROWTH_WEEKS = 18` vào logic filter.
- Tạo công cụ Polygon Tracer (`polygon_tracer.html`) để vẽ tọa độ polygon lên ảnh bản đồ Farm 157 cho interactive map component.
- Cập nhật docs: `changelog.md`, `findings.md`, `business_logic.md`, `command.md`.

## Ngày 22/04/2026

- Phân chia báo cáo Excel (Chích bắp, Cắt bắp, Trồng mới) thành nhiều sheet theo năm.
- Bỏ emoji khỏi text nút tải Excel.
- Tô màu cho 4 nút tải báo cáo Excel (pastel colors) — dùng HTML `<a>` base64 thay `st.download_button`.
- Căn giữa (align) các nút tải Excel bằng `min-height` đồng nhất.


## Ngày 20/04/2026

- Chuyển hiển thị diện tích từ `dim_lo.area_ha` (tối đa lô) sang `base_lots.dien_tich_trong` (diện tích trồng thực tế per-batch). Fallback area_ha nếu NULL.
- Đổi header cột "Diện tích (ha)" → "DT trồng (ha)". Bỏ dedup sum (mỗi đợt có area riêng).
- Cập nhật tất cả charts (Dự toán, Thực tế, Pipeline, Timeline, Kiểm kê).

## Ngày 18/04/2026

- Cập nhật diện tích D6 = 2.50 ha trong DB.
- Thêm tính năng tùy chỉnh số ngày thu hoạch (Thu bói/Thu rộ/Thu vét) bên cạnh tỷ lệ % hiện có. Mặc định 14/26/14 ngày. Hỗ trợ bất đối xứng. SIGMA tính động.
- **Nâng cấp 3 → 4 mốc dự báo**: Thêm Mốc ② Chích bắp (giữa Trồng và Cắt bắp). Pipeline: ① Trồng → ② Chích bắp → ③ Cắt bắp → ④ Thực tế. Match chích bắp vào generation bằng closest-midpoint.
- Cập nhật `business_logic.md` §3.3, `findings.md`, `changelog.md`, `command.md`.

## Ngày 17/04/2026

- Nâng cấp thẻ Lịch Thu hoạch Dự kiến: Thêm 3 mốc dự báo (① Từ Trồng − xuất hủy, ② Từ Cắt bắp, ③ Thực tế). Card UI, dialog, bảng tổng hợp đều hiển thị 3 mốc. Fallback "Chưa có TT" khi thiếu data.
- Implement logic phân bổ xuất hủy theo tỉ lệ (proportional allocation): trừ trực tiếp nếu có `base_lot_id`, phân bổ `hủy × (batch/tổng_lô)` nếu chỉ có `dim_lo_id`.
- Thêm dòng tổng cộng (TỔNG) cho Bảng chi tiết thông tin các lô (Theo Vụ), tự động tính tổng diện tích, số cây, các chỉ số dự toán/thực tế và định dạng số có dấu phẩy.
- Fix Mốc ③ (Thực tế) bị nhân bản: harvest_logs là dữ liệu hàng ngày, phải match từng record vào đúng (generation, phase, tháng) dựa trên ngày thu hoạch thực tế thay vì gộp tổng cả vụ.
- Fix TỔNG sum diện tích trùng khi lô có nhiều đợt trồng (3B: 3 đợt × 4.50 = 13.50 → fix: sum unique = 4.50). Cập nhật area_ha cho 2B, 8A, A8.
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
