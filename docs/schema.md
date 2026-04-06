# Database Schema

Danh sách và ý nghĩa các trường cấu trúc dữ liệu chính (thông qua Supabase Data source).

## `base_lots`
- Bảng mapping lưu trữ các ID lô cơ sở và diện tích của chúng.
- fields tiêu biểu: `lot_id`, `dien_tich`, `so_luong` (cây đã trồng).

## `stage_logs` & `harvest_logs`
- Lưu log thông số chăm sóc (như "Chích bắp", "Cắt bắp") và nhật ký thu hoạch tương ứng.
- fields tiêu biểu: `giai_doan` (tên giai đoạn), `so_luong`, `ngay_thuc_hien` / `ngay_thu_hoach`.

## `seasons`
- Bảng vòng đời vụ, mapping từng mùa sinh trưởng với Lô theo ngày tháng thực tế và dự kiến.
- fields tiêu biểu: `vu` (F0, F1...), `ngay_bat_dau`, `ngay_ket_thuc_du_kien`, `ngay_ket_thuc_thuc_te`.

## `dictionary_cv` & `dictionary_lo`
- Các bảng từ điển phục vụ đồng bộ ETL Pipeline, mapping tên Gsheet với mã định danh chuẩn.
