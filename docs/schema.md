# Database Schema

Tài liệu này ghi lại toàn bộ cấu trúc cơ sở dữ liệu trên Supabase được dùng cho dự án phân tích dữ liệu Banana Tracker và Ghi nhận Nhật ký nông vụ.

## 1. Các bảng phân cấp (Dimension Tables)
Giải quyết vấn đề Mapping (ETL), quản lý thực thể lõi Farm.
- **`dim_farm`**: Danh sách trang trại. Cấu trúc `farm_id` (PK), `farm_code`, `farm_name`, `area_ha`.
- **`dim_doi`**: Quản lý các Đội (Team). Cấu trúc `doi_id` (PK), `farm_id` (FK), `doi_code`, `doi_name`, `team_leader`.
- **`dim_lo`**: Quản lý Lô thực tế. Cấu trúc `lo_id` (PK), `farm_id` (FK), `doi_id` (FK), `lo_code`, `lo_name`, `area_ha`, `lo_type` (Lô thực/Lô ảo).
- **`dim_cong_viec`**: Từ điển chuẩn các danh mục công việc (`ma_cv`, `ten_cong_viec`, `don_gia_chuan`).
- **`dim_vat_tu`**: Từ điển chuẩn về các loại vật tư (`ma_vat_tu`, `ten_vat_tu`, `don_gia_chuan`).

## 2. Nhật Ký Sản Xuất (Fact Tables)
Nhận data đổ về từ Google Sheet (ETL).
- **`fact_nhat_ky_san_xuat`**: Nhật ký công việc hằng ngày. FKs trỏ đến Farm, Lô, Đội, Công việc. Lưu số công (`so_cong`), định mức, khối lượng công việc thực tế (`klcv`), đơn giá, và tỷ lệ hoàn thành công việc (`ti_le_display`). Hỗ trợ cờ đánh dấu hỗ trợ chéo (`is_ho_tro`).
- **`fact_vat_tu`**: Nhật ký cấp phát/sử dụng vật tư hằng ngày. Lưu lượng sử dụng (`so_luong`), `don_gia`, `thanh_tien`.

## 3. Nhật Ký Sinh Trưởng Lô (Field Tracking Logs)
Công cụ nhập liệu phân tích trực tiếp cho quá trình từ Trồng -> Thu hoạch (Banana Lifecycle).
- **`base_lots`**: Thông tin cây lúc trồng ban đầu. `ngay_trong`, `so_luong` (cây), liên kết trực tiếp `dim_lo_id`.
- **`seasons`**: Khai báo Vòng đời/Mùa vụ cho Lô. Gồm `vu` (F0, F1...), `ngay_bat_dau`, `ngay_ket_thuc_du_kien`, `ngay_ket_thuc_thuc_te`.
- **`stage_logs`**: Log quá trình (VD: "Chích bắp", "Cắt bắp"), với số lượng (`so_luong`), ngày, theo `dim_lo_id`.
- **`harvest_logs`**: Thu hoạch, `so_luong`, `ngay_thu_hoach`, `dim_lo_id`.
- **`destruction_logs`**: Cây bị xuất hủy, do bão hòa, thiên tai hoặc lý do khác. `ly_do`, `so_luong`.
- **Các bảng phụ đo đạc**: `size_measure_logs` (Đo độ dày/size), `soil_ph_logs` (Đo pH đất), `fusarium_logs` (Lượng cây nhiễm Fusa), `tree_inventory_logs` (Kiểm kê sống/thực tế), `bsr_logs`.

## 4. Bảng tính toán Dashboard (Analytics / Aggregation)
- **`fact_195_tong`**: Pre-computed (Dữ liệu đã chốt) chuyên phục vụ BI Dashboard Farm 195. Flatten ra dưới dạng long-format (1 record bao gồm cả view thực tế và dự toán cho từng lô/thứ tự ngày). Update thường xuyên bằng python aggregation scripts (`tong_hop_v2.py`).
- **`fact_dtbd`**: Bảng dữ liệu đầu tư ban đầu / Khấu hao. Tính bằng thời gian khấu hao và giá trị tài sản.

## 5. Security và Settings
- **`user_roles`**: Phân quyền (`farm`, `team`, `password`).
- **`access_logs`**: Lưu nhật ký truy cập (audit trail).
- **`log_outliers_thanh_tien`**: Bảng audit phát hiện những hóa đơn có Outlier về Thành Tiền cần review lại.
