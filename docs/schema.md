# Database Schema

Tài liệu này ghi lại chi tiết toàn bộ cấu trúc cơ sở dữ liệu trên Supabase được dùng cho dự án phân tích dữ liệu Banana Tracker và Ghi nhận Nhật ký nông vụ. Tài liệu này liệt kê toàn bộ các bảng, giải nghĩa từng bảng và từng trường một cách chi tiết.

**Snapshot DB:** đối chiếu trực tiếp với Supabase ngày 26/05/2026 sau các migration gần đây.

**Nhóm bảng đang tồn tại trong `public`:**
- Core nông vụ/app: `dim_farm`, `dim_doi`, `dim_lo`, `base_lots`, `seasons`, `stage_logs`, `destruction_logs`, `harvest_logs`, `ribbon_schedule`, `tree_inventory_logs`, `soil_ph_logs`, `fusarium_logs`, `bsr_logs`, `size_measure_logs`, `access_logs`, `user_roles`, `container_allocation_plans`.
- Nhật ký sản xuất/vật tư: `dim_cong_viec`, `dim_vat_tu`, `fact_nhat_ky_san_xuat`, `fact_vat_tu`, `fact_dtbd`, `fact_195_tong`, `stg_xuat_kho`, `stg_vat_tu_bvtv_farm157_daily_temp`.
- Chuẩn hóa công việc: `dim_hang_muc_cong_viec_chuan`, `dim_cong_viec_chuan`, `dim_cong_viec_dinh_muc`, `map_cong_viec_source`, `map_dim_cong_viec_legacy_to_chuan`, `audit_cong_viec_chuan_can_bo_sung`, `log_outliers_thanh_tien`.

**Guardrail quan trọng:** DB hiện chặn mọi record active `stage_logs` của `Chích bắp`/`Cắt bắp` nếu thiếu `base_lot_id`. Lô chưa có đợt trồng hợp lệ không được nhập vào hai giai đoạn này.

## public.dim_farm
**Ý nghĩa:** Dimension table chứa danh sách các trang trại (Farms), quản lý thực thể farm cốt lõi.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| farm_code | text | Có | - |
| farm_name | text | Có | - |
| location | text | Không | - |
| area_ha | numeric | Không | - |
| manager | text | Không | - |
| phone | text | Không | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.dim_lo
**Ý nghĩa:** Dimension table chứa danh sách các Lô trồng chuối, có thuộc về Farm và Đội tương ứng.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| lo_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| lo_code | text | Có | - |
| lo_name | text | Không | - |
| area_ha | numeric | Không | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |
| lo_type | text | Không | Loại lô: Lô thực | Lô ảo - Đội | Khu vực | Farm | Liên Farm |
| doi_id | integer | Không | ID định danh/Khóa ngoại |

## public.dim_doi
**Ý nghĩa:** Dimension table chứa danh sách các Đội (Teams) thuộc từng Farm.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| doi_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| doi_code | text | Có | - |
| doi_name | text | Không | - |
| team_leader | text | Không | - |
| member_count | integer | Không | - |
| specialization | text | Không | - |
| phone | text | Không | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.dim_cong_viec
**Ý nghĩa:** Từ điển/Dimension table chứa các danh mục công việc chuẩn.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| cong_viec_id | integer | Có | ID định danh/Khóa ngoại |
| ma_cv | text | Có | - |
| ten_cong_viec | text | Không | - |
| cong_doan | text | Không | - |
| loai_cong | text | Không | - |
| don_gia_chuan | numeric | Không | - |
| dvt | text | Không | - |
| mo_ta | text | Không | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.dim_hang_muc_cong_viec_chuan
**Ý nghĩa:** Danh mục hạng mục công việc chuẩn, dùng làm tầng cha cho bộ mã công việc chuẩn.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| hang_muc_code | text | Có | Khóa hạng mục chuẩn |
| ten_hang_muc_chuan | text | Có | Tên hạng mục chuẩn |
| ten_hang_muc_norm | text | Có | Tên đã chuẩn hóa để match dữ liệu nguồn |
| nhom_cong_viec | text | Không | Nhóm nghiệp vụ |
| mo_ta | text | Không | Mô tả |
| is_active | boolean | Có | Default `true` |
| created_at | timestamp without time zone | Có | Default `now()` |
| updated_at | timestamp without time zone | Có | Default `now()` |

## public.dim_cong_viec_chuan
**Ý nghĩa:** Danh mục công việc chuẩn sau khi chuẩn hóa từ nhiều nguồn mã/tên công việc legacy.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| ma_cv_chuan | text | Có | Khóa mã công việc chuẩn |
| hang_muc_code | text | Có | FK logic sang `dim_hang_muc_cong_viec_chuan.hang_muc_code` |
| ten_cong_viec_chuan | text | Có | Tên công việc chuẩn |
| loai_cong | text | Có | Loại công |
| dvt | text | Không | Đơn vị tính |
| don_gia_chuan | numeric | Không | Đơn giá chuẩn nếu có |
| dinh_muc_chuan | numeric | Không | Định mức chuẩn nếu có |
| is_active | boolean | Có | Default `true` |
| created_at | timestamp without time zone | Có | Default `now()` |
| updated_at | timestamp without time zone | Có | Default `now()` |

## public.dim_cong_viec_dinh_muc
**Ý nghĩa:** Bảng version hóa định mức/đơn giá theo công việc legacy, dùng khi một công việc có nhiều mức áp dụng theo thời gian hoặc nguồn file.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| dinh_muc_id | bigint | Có | Primary key |
| cong_viec_id | integer | Có | Công việc legacy tương ứng |
| version_no | integer | Có | Version, default `1` |
| dinh_muc_chuan | numeric | Không | Định mức |
| dvt_dinh_muc | text | Không | Đơn vị định mức |
| don_gia_chuan | numeric | Không | Đơn giá |
| effective_from | date | Không | Ngày bắt đầu hiệu lực |
| effective_to | date | Không | Ngày hết hiệu lực |
| is_current | boolean | Có | Dòng hiện hành, default `false` |
| status | text | Có | Trạng thái, default `proposed` |
| source_file | text | Không | File nguồn |
| source_sheet | text | Không | Sheet nguồn |
| source_row | integer | Không | Dòng nguồn |
| ghi_chu | text | Không | Ghi chú |
| ten_hang_muc_source | text | Không | Tên hạng mục gốc từ file |
| created_at | timestamp without time zone | Không | Default `now()` |
| updated_at | timestamp without time zone | Không | Default `now()` |

## public.dim_vat_tu
**Ý nghĩa:** Từ điển/Dimension table chứa danh mục vật tư chuẩn sử dụng trong dự án.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| vat_tu_id | integer | Có | ID định danh/Khóa ngoại |
| ma_vat_tu | text | Không | - |
| ten_vat_tu | text | Có | - |
| loai_vat_tu | text | Không | - |
| dvt | text | Có | - |
| don_gia_chuan | numeric | Không | - |
| nha_cung_cap | text | Không | - |
| quy_cach | text | Không | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.fact_nhat_ky_san_xuat
**Ý nghĩa:** Fact table chứa nhật ký sản xuất hằng ngày, lượng công việc hoàn thành và chi phí nhân công.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| nhat_ky_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| lo_id | integer | Không | ID định danh/Khóa ngoại |
| doi_id | integer | Không | ID định danh/Khóa ngoại |
| cong_viec_id | integer | Không | ID định danh/Khóa ngoại |
| ngay | date | Có | - |
| so_cong | numeric | Không | - |
| klcv | numeric | Không | - |
| dinh_muc | numeric | Không | - |
| don_gia | numeric | Không | - |
| thanh_tien | numeric | Không | - |
| ghi_chu | text | Không | - |
| hang_muc_du_toan_cong | text | Không | - |
| lo_2 | text | Không | - |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |
| is_ho_tro | boolean | Không | TRUE = đội thực hiện không phải đội sở hữu lô (hỗ trợ chéo đội). Chỉ áp dụng cho lô thực. |
| ti_le_display | numeric | Không | Tỉ lệ hoàn thành định mức (%). Logic: (klcv / so_cong / dinh_muc * 100). Outlier > 200% bị cap về 99 để tránh làm lệch thống kê. NULL khi dinh_muc = 0 hoặc so_cong = 0 hoặc klcv IS NULL. |

## public.fact_vat_tu
**Ý nghĩa:** Fact table chứa nhật ký cấp phát và sử dụng vật tư hằng ngày.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| vat_tu_fact_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| lo_id | integer | Không | ID định danh/Khóa ngoại |
| cong_viec_id | integer | Không | ID định danh/Khóa ngoại |
| vat_tu_id | integer | Không | ID định danh/Khóa ngoại |
| ngay | date | Có | - |
| so_luong | numeric | Không | - |
| don_gia | numeric | Không | - |
| thanh_tien | numeric | Không | - |
| hang_muc_du_toan_vat_tu | text | Không | - |
| lo_2 | text | Không | - |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |
| is_ho_tro | boolean | Không | - |

## public.stg_xuat_kho
**Ý nghĩa:** Bảng staging dữ liệu xuất kho vật tư trước khi map sang lô/vật tư chuẩn.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | Primary key |
| source_file | text | Có | File nguồn |
| nhom_vat_tu | text | Có | Nhóm vật tư |
| ngay | date | Có | Ngày xuất |
| so_chung_tu | text | Không | Số chứng từ |
| ma_hang | text | Không | Mã hàng nguồn |
| ten_hang | text | Không | Tên hàng nguồn |
| dvt | text | Không | Đơn vị tính |
| so_luong | numeric | Không | Số lượng |
| don_gia | numeric | Không | Đơn giá |
| thanh_tien | numeric | Không | Thành tiền |
| ma_khoan_muc_cp | text | Không | Mã khoản mục chi phí |
| ma_thong_ke | text | Không | Mã thống kê |
| ten_thong_ke | text | Không | Tên thống kê |
| mapped_lo_id | integer | Không | Lô đã map |
| mapped_vat_tu_id | integer | Không | Vật tư đã map |
| imported_at | timestamp with time zone | Không | Default `now()` |

## public.stg_vat_tu_bvtv_farm157_daily_temp
**Ý nghĩa:** Bảng staging tạm cho dữ liệu vật tư BVTV Farm 157 theo ngày; giữ dữ liệu nguồn, mapping và cờ outlier trước khi đưa vào fact/chuẩn hóa.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| temp_id | bigint | Có | Primary key |
| farm_id | integer | Có | Farm |
| doi_name | text | Có | Tên đội nguồn |
| doi_id | integer | Không | Đội đã map |
| lo_id | integer | Không | Lô đã map |
| lo_source | text | Không | Lô nguồn |
| cong_viec_id | integer | Không | Công việc đã map |
| ma_cv_source | text | Không | Mã công việc nguồn |
| hang_muc_source | text | Không | Hạng mục nguồn |
| vat_tu_id | integer | Không | Vật tư đã map |
| ma_vat_tu_source | text | Không | Mã vật tư nguồn |
| ten_vat_tu_source | text | Không | Tên vật tư nguồn |
| ngay | date | Có | Ngày phát sinh |
| so_luong | numeric | Không | Số lượng |
| don_gia | numeric | Không | Đơn giá |
| thanh_tien | numeric | Không | Thành tiền sau xử lý |
| thanh_tien_original | numeric | Không | Thành tiền gốc |
| is_outlier | boolean | Có | Default `false` |
| outlier_reason | text | Không | Lý do outlier |
| data_source | text | Có | Nguồn dữ liệu |
| source_doc_id | text | Có | ID tài liệu nguồn |
| source_sheet | text | Có | Sheet nguồn |
| source_row | integer | Có | Dòng nguồn |
| raw_data | jsonb | Không | Dữ liệu thô |
| loaded_at | timestamp without time zone | Có | Default `now()` |

## public.log_outliers_thanh_tien
**Ý nghĩa:** Bảng audit log dùng để theo dõi và phát hiện các chi phí (Thành Tiền) bất thường.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| log_id | integer | Có | ID định danh/Khóa ngoại |
| source_table | text | Không | - |
| source_id | integer | Không | ID định danh/Khóa ngoại |
| farm_id | integer | Không | ID định danh/Khóa ngoại |
| ngay | date | Không | - |
| hang_muc | text | Không | - |
| so_luong_or_cong | numeric | Không | - |
| don_gia | numeric | Không | - |
| thanh_tien_cu | numeric | Không | - |
| thanh_tien_moi | numeric | Không | - |
| ghi_chu | text | Không | - |
| logged_at | timestamp without time zone | Không | - |

## public.map_cong_viec_source
**Ý nghĩa:** Mapping từ tên/mã công việc nguồn sang `ma_cv_chuan`; lưu kèm mẫu dữ liệu, độ tin cậy và ngày thấy đầu/cuối.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| map_id | bigint | Có | Primary key |
| farm_id | integer | Không | Farm áp dụng nếu mapping theo farm |
| source_system | text | Có | Hệ/file nguồn |
| source_doc_id | text | Không | ID tài liệu nguồn |
| source_sheet | text | Không | Sheet nguồn |
| source_ma_cv | text | Không | Mã công việc nguồn |
| source_ma_cv_base | text | Không | Mã nguồn đã normalize base |
| source_ten_cong_viec | text | Có | Tên công việc nguồn |
| source_ten_norm | text | Có | Tên nguồn đã normalize |
| source_loai_cong | text | Không | Loại công nguồn |
| source_dvt | text | Không | Đơn vị tính nguồn |
| source_don_gia | numeric | Không | Đơn giá nguồn |
| source_dinh_muc | numeric | Không | Định mức nguồn |
| ma_cv_chuan | text | Có | Mã công việc chuẩn được map |
| sample_count | integer | Có | Số mẫu dùng để map, default `0` |
| first_seen_date | date | Không | Ngày thấy đầu tiên |
| last_seen_date | date | Không | Ngày thấy gần nhất |
| source_rows | jsonb | Không | Mẫu dòng nguồn |
| confidence | numeric | Có | Độ tin cậy mapping, default `1.0` |
| is_active | boolean | Có | Default `true` |
| created_at | timestamp without time zone | Có | Default `now()` |
| updated_at | timestamp without time zone | Có | Default `now()` |

## public.map_dim_cong_viec_legacy_to_chuan
**Ý nghĩa:** Mapping trực tiếp từ `dim_cong_viec.cong_viec_id` legacy sang `dim_cong_viec_chuan.ma_cv_chuan`.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| cong_viec_id | integer | Có | ID công việc legacy |
| ma_cv_chuan | text | Có | Mã công việc chuẩn |
| match_method | text | Có | Cách match |
| confidence | numeric | Có | Độ tin cậy, default `1.0` |
| ghi_chu | text | Không | Ghi chú |
| created_at | timestamp without time zone | Có | Default `now()` |
| updated_at | timestamp without time zone | Có | Default `now()` |

## public.audit_cong_viec_chuan_can_bo_sung
**Ý nghĩa:** Audit các công việc/định mức chuẩn còn thiếu hoặc cần kiểm tra khi ingest dữ liệu nguồn.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| audit_id | bigint | Có | Primary key |
| issue_type | text | Có | Loại vấn đề |
| severity | text | Có | Mức độ, default `needs_review` |
| fact_table | text | Không | Fact table liên quan |
| farm_id | integer | Không | Farm liên quan |
| cong_viec_id | integer | Không | Công việc legacy nếu có |
| source_table | text | Không | Bảng nguồn |
| source_key | text | Không | Khóa nguồn |
| old_ma_cv | text | Không | Mã cũ |
| old_ten_cong_viec | text | Không | Tên cũ |
| ma_cv_chuan | text | Không | Mã chuẩn đề xuất |
| hang_muc_code | text | Không | Hạng mục chuẩn đề xuất |
| ten_cong_viec_chuan | text | Không | Tên chuẩn đề xuất |
| loai_cong | text | Không | Loại công |
| dvt | text | Không | Đơn vị tính |
| don_gia_chuan | numeric | Không | Đơn giá đề xuất |
| dinh_muc_chuan | numeric | Không | Định mức đề xuất |
| rows_count | integer | Không | Số dòng ảnh hưởng |
| total_thanh_tien | numeric | Không | Tổng thành tiền ảnh hưởng |
| first_seen_date | date | Không | Ngày thấy đầu tiên |
| last_seen_date | date | Không | Ngày thấy gần nhất |
| detail | jsonb | Không | Chi tiết audit |
| created_at | timestamp without time zone | Không | Default `now()` |
| updated_at | timestamp without time zone | Không | Default `now()` |

## public.fact_dtbd
**Ý nghĩa:** Fact table lưu thông tin Đầu tư ban đầu và khấu hao.

**Ghi chú hệ thống:** Đầu tư ban đầu - Khấu hao. Source: sheet ĐTBĐ (fact) Farm 195. farm_id=3.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| dtbd_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| ma_dtbd | text | Có | - |
| ngay_bat_dau_khau_hao | date | Không | - |
| ten_vt_dtbd | text | Không | - |
| dvt | text | Không | - |
| thanh_tien | numeric | Không | - |
| so_nam_khau_hao | integer | Không | - |
| khau_hao_tich_luy | numeric | Không | - |
| phan_loai_dtbd | text | Không | - |
| hang_muc_du_toan_dtbd | text | Không | - |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.fact_195_tong
**Ý nghĩa:** Fact table tổng hợp pre-computed cho Dashboard Farm 195. Đây là bảng denormalized dể dùng cho BI.

**Ghi chú hệ thống:** Pre-computed long format cho Farm 195 dashboard. Grain: 1 giao dịch gốc → 2 rows (Thực tế + Dự toán). Source: output của tong_hop_v2.py sau unpivot_for_visualization(). Truncate + reload mỗi lần script chạy.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| tong_id | integer | Có | ID định danh/Khóa ngoại |
| farm_id | integer | Có | ID định danh/Khóa ngoại |
| loai_du_lieu | text | Không | - |
| loai_chi_phi | text | Không | - |
| gia_tri | numeric | Không | - |
| ngay | date | Không | - |
| lo | text | Không | - |
| lo_2 | text | Không | - |
| loai_lo | text | Không | - |
| dien_tich_ha | numeric | Không | - |
| hang_muc_du_toan_cong | text | Không | - |
| hang_muc_du_toan_vat_tu | text | Không | - |
| hang_muc_du_toan_dtbd | text | Không | - |
| ma_cv | text | Không | - |
| doi_thuc_hien | text | Không | - |
| hang_muc_cong_viec | text | Không | - |
| loai_cong | text | Không | - |
| so_cong | numeric | Không | - |
| klcv | numeric | Không | - |
| dvt | text | Không | - |
| don_gia | numeric | Không | - |
| dinh_muc | numeric | Không | - |
| cong_doan | text | Không | - |
| ghi_chu | text | Không | - |
| ho_tro_doi_khac | text | Không | - |
| vat_tu | text | Không | - |
| so_luong | numeric | Không | - |
| loai_vat_tu | text | Không | - |
| ma_dtbd | text | Không | - |
| phan_loai_dtbd | text | Không | - |
| ten_vt_dtbd | text | Không | - |
| so_nam_khau_hao | numeric | Không | - |
| khau_hao_tich_luy | numeric | Không | - |
| ngay_bat_dau_khau_hao | date | Không | - |
| ngoai_du_toan | text | Không | - |
| vu | text | Không | - |
| tien_do_vu | numeric | Không | - |
| computed_at | timestamp without time zone | Không | - |
| created_at | timestamp without time zone | Không | Thời gian tạo record |
| updated_at | timestamp without time zone | Không | Thời gian cập nhật record |

## public.base_lots
**Ý nghĩa:** Bảng theo dõi thông tin gốc của các đợt trồng (số lượng, ngày trồng). Bao gồm cả đợt **Trồng mới** và **Trồng dặm**.

**Ghi chú nghiệp vụ:**
- `loai_trong` nằm trực tiếp trong `base_lots` (migration `add_loai_trong_to_base_lots`). Không cần join seasons để lấy.
- **Trồng dặm** là bổ sung cây vào lô đã có trồng mới → KHÔNG tạo chu kỳ F0→F3 riêng trong forecast.
- Trong Dashboard: Trồng dặm bị loại khỏi Bảng chi tiết & Lịch thu hoạch, hiển thị riêng ở bảng "📋 Lịch sử Trồng dặm".

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_trong | date | Có | Ngày xuống giống thực tế |
| so_luong | integer | Có | Số cây trồng ban đầu |
| trang_thai | text | Không | Trạng thái hiện tại (default: "Đã trồng") |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | Tuần trong năm (ISO week) |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| so_luong_con_lai | integer | Không | Số cây còn sống sau hao hụt |
| dim_lo_id | integer | Không | FK → dim_lo.lo_id — Lô thuộc về |
| loai_trong | text | Có | "Trồng mới" hoặc "Trồng dặm" (default: "Trồng mới"). Trồng dặm bị loại khỏi forecast. |
| dien_tich_trong | numeric | Không | Diện tích thực tế của đợt trồng. Nếu nguồn chỉ có số cây thì quy đổi theo mật độ 2,190 cây/ha. |

## public.stage_logs
**Ý nghĩa:** Log lưu quá trình sinh trưởng (cắt bắp, chích bắp).

**Ghi chú nghiệp vụ:**
- Cột `mau_day` đã được xóa (migration 08/05/2026). Màu dây giờ được resolve từ `ribbon_schedule` qua `(farm_id, year, tuan)`.
- Cắt bắp gắn liền với màu dây theo tuần — dùng `tuan` join `ribbon_schedule` để xác định.
- DB constraint `chk_stage_logs_active_stage_requires_base_lot`: mọi record active (`is_deleted != true`) của `Chích bắp` hoặc `Cắt bắp` bắt buộc phải có `base_lot_id`. Lô chưa có đợt trồng hợp lệ không được insert vào `stage_logs` cho hai giai đoạn này.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| giai_doan | text | Có | "Chích bắp" hoặc "Cắt bắp" |
| ngay_thuc_hien | date | Có | - |
| so_luong | integer | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | Tuần trong năm (ISO week). Dùng để join `ribbon_schedule` lấy màu dây. |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |
| base_lot_id | integer | Không | FK → base_lots.id — Đợt trồng tương ứng, auto-resolved bằng timeline sinh trưởng |

## public.destruction_logs
**Ý nghĩa:** Log lưu quá trình xuất hủy cây chuối.

**Ghi chú nghiệp vụ:**
- Cột `mau_day` đã được xóa (migration 08/05/2026). Khi cần xác định màu dây cho xuất hủy trước/sau thu hoạch, user chọn từ `ribbon_schedule` và hệ thống dùng `tuan` để cross-reference.
- `Sau thu hoạch` dùng cho trường hợp hủy được ghi nhận sau khi màu dây/lứa đó đã thu. Báo cáo cắt bắp vẫn hiển thị ở cột XUẤT HỦY nhưng bù vào Thu hoạch ròng để không làm âm tồn trên lô.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_xuat_huy | date | Có | - |
| giai_doan | text | Có | "Trước chích bắp" / "Trước cắt bắp" / "Trước thu hoạch" / "Sau thu hoạch" |
| ly_do | text | Có | - |
| so_luong | integer | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | Tuần trong năm (ISO week) |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |
| base_lot_id | integer | Không | FK → base_lots.id — Đợt trồng tương ứng, auto-resolved bằng timeline sinh trưởng |

## public.harvest_logs
**Ý nghĩa:** Log lưu quá trình thu hoạch chuối.

**Ghi chú nghiệp vụ:**
- `mau_day` là màu dây nguồn của lứa thu hoạch. Thu hoạch có thể xảy ra cùng ngày/cùng lô nhưng nhiều màu dây, nên cần lưu ở cấp record để đối chiếu về tuần cắt bắp trong báo cáo.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_thu_hoach | date | Có | - |
| so_luong | integer | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | Tuần trong năm (ISO week). Dùng join `ribbon_schedule` lấy màu dây. |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| hinh_thuc_thu_hoach | text | Không | - |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |
| base_lot_id | integer | Không | FK → base_lots.id — Đợt trồng tương ứng, auto-resolved bằng timeline sinh trưởng |
| mau_day | text | Không | Màu dây nguồn, chọn từ `ribbon_schedule.color_name`; dùng để map thu hoạch thực tế về tuần cắt bắp nguồn |

## public.ribbon_schedule
**Ý nghĩa:** Bảng lịch trình màu dây (ribbon color) chuẩn hóa theo farm, năm và tuần. Đây là nguồn chuẩn cho màu dây theo tuần cắt bắp; `harvest_logs.mau_day` lưu màu thực tế người dùng chọn để đối chiếu về tuần nguồn.

**Ghi chú nghiệp vụ:**
- Mỗi farm chỉ có **1 màu dây cho 1 tuần cụ thể**. Màu dây có thể được tái sử dụng ở các tuần khác nhau (VD: tuần 2 = cam, tuần 22 = cam).
- Auto-create: Khi user nhập dữ liệu mới (cắt bắp, đo size...) với màu dây cho tuần chưa có record → tự động tạo `ribbon_schedule` entry.
- Conflict prevention: Nếu tuần đó đã có màu dây khác → chặn entry, yêu cầu user sử dụng đúng màu.
- UI: Tất cả selectbox màu dây đều dùng `build_color_selectbox()` helper để đảm bảo chuẩn hóa.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| farm_id | integer | Có | FK → dim_farm.farm_id |
| year | integer | Có | Năm (ISO year) |
| week_number | integer | Có | Tuần trong năm (ISO week) |
| color_name | text | Có | Tên màu dây chuẩn hóa (viết thường, không viết tắt). VD: "cam", "xanh lá", "đỏ" |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |

## public.bsr_logs
**Ý nghĩa:** Log đo lường chỉ số BSR.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_nhap | date | Có | - |
| bsr | numeric | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.access_logs
**Ý nghĩa:** Log lưu vết hệ thống, hành động truy cập của user.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| farm | text | Có | - |
| team | text | Có | - |
| action | text | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |

## public.container_allocation_plans
**Ý nghĩa:** Lưu kế hoạch máy tính phân bổ container theo nải cho account Kinh doanh. Mỗi record giữ snapshot đầy đủ của input, output và thuật toán tại thời điểm bấm `Lưu kế hoạch`.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | uuid | Có | Primary key, default `gen_random_uuid()` |
| account_farm | text | Có | Farm/account đăng nhập, ví dụ `Phòng Kinh doanh` |
| account_team | text | Có | Team/account đăng nhập, ví dụ `Kinh doanh` |
| plan_name | text | Có | Tên thẻ kế hoạch hiển thị trên UI |
| mode | text | Có | Chế độ tính: `Tính số hàng từ số buồng`, `Tính số cont tối đa từ số buồng`, hoặc `Tính số buồng từ số cont` |
| source_mode | text | Không | Nguồn số buồng: dự báo từ cắt bắp hoặc nhập tay |
| source_label | text | Không | Nhãn nguồn dữ liệu đã chọn |
| source_bunches | integer | Có | Số buồng nguồn tại thời điểm lưu |
| hands_per_bunch | integer | Có | Loại buồng: 12 nải hoặc 9 nải |
| kg_per_bunch | numeric | Có | Kịch bản kg/buồng sau khi chọn profile |
| input_data | jsonb | Có | Snapshot input: kg từng nải, đơn hàng, ưu tiên khách hàng/thị trường/mã hàng |
| result_data | jsonb | Có | Snapshot output đầy đủ từ optimizer |
| summary | jsonb | Có | Summary chính để render nhanh thẻ kế hoạch |
| full_plan | jsonb | Có | Toàn bộ payload kế hoạch để mở popup chi tiết |
| is_deleted | boolean | Có | Soft delete thẻ kế hoạch |
| created_at | timestamp with time zone | Có | Thời điểm lưu kế hoạch |
| updated_at | timestamp with time zone | Có | Thời điểm cập nhật/xóa mềm |

## public.seasons
**Ý nghĩa:** Bảng định nghĩa các vụ mùa (F0, F1...) của từng lô. Mỗi base_lot tạo ra 1 season F0 khi khởi tạo.

**Ghi chú nghiệp vụ:**
- `loai_trong` trên seasons được giữ lại cho backward compatibility, nhưng **canonical source** giờ là `base_lots.loai_trong`.
- Dashboard đọc `loai_trong` từ `base_lots` trực tiếp (không join seasons nữa).
- Khi tạo lô mới, `loai_trong` được set đồng thời trên cả `base_lots` và `seasons`.
- Một `base_lot_id` có thể có nhiều dòng `seasons` theo vòng đời F0/F1/F2. Vì vậy khi join log (`stage_logs`, `harvest_logs`, `destruction_logs`) với `seasons`, phải lọc đúng `vu`/window ngày hoặc dedupe theo id log trước khi cộng số lượng. Nếu chỉ join theo `base_lot_id`, cùng một log có thể bị nhân đôi.
- Ví dụ Farm 157: `3BF` trong file Excel vẫn là lô `3B`, nhưng gắn `base_lot_id = 25` và season F1; `3B` thường gắn `base_lot_id = 7` và season F0.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| vu | text | Có | Mã vụ: F0, F1, F2... (default: "F0") |
| loai_trong | text | Có | "Trồng mới" hoặc "Trồng dặm" — xác định đợt trồng có tạo forecast riêng không |
| ngay_bat_dau | date | Có | Ngày bắt đầu vụ |
| ngay_ket_thuc_thuc_te | date | Không | Ngày kết thúc vụ thực tế |
| ngay_ket_thuc_du_kien | date | Không | Ngày kết thúc vụ dự kiến |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | FK → dim_lo.lo_id — Lô thuộc về |
| base_lot_id | integer | Không | FK → base_lots.id — Đợt trồng gốc tương ứng (F0 exact match, Fn timeline match) |

## public.size_measure_logs
**Ý nghĩa:** Log đo kích thước / độ dày của nải/bắp.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| mau_day | text | Có | - |
| lan_do | integer | Có | - |
| so_luong_mau | integer | Có | - |
| ngay_do | date | Có | - |
| tuan | integer | Không | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| hang_kiem_tra | text | Không | - |
| size_cal | numeric | Không | - |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.tree_inventory_logs
**Ý nghĩa:** Log kiểm kê số lượng cây sống thực tế.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| so_luong_cay_thuc_te | integer | Có | - |
| ngay_kiem_ke | date | Có | - |
| tuan | integer | Không | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.soil_ph_logs
**Ý nghĩa:** Log đo lường độ pH của đất trồng.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | uuid | Có | - |
| ngay_do | date | Có | - |
| tuan | integer | Có | - |
| lan_do | integer | Có | - |
| ph_value | numeric | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.fusarium_logs
**Ý nghĩa:** Log theo dõi lượng cây bị nhiễm bệnh Fusarium.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | uuid | Có | - |
| ngay_kiem_tra | date | Có | - |
| so_cay_fusarium | integer | Có | - |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.user_roles
**Ý nghĩa:** Bảng phân quyền người dùng theo farm và team.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| farm | text | Có | - |
| team | text | Có | - |
| password | text | Có | - |
| is_active | boolean | Không | Cờ đánh dấu record còn hiệu lực không (True=Có) |
| created_at | timestamp with time zone | Không | Thời gian tạo record |

---

## Database Constraints

Các constraint hiện có đã được đối chiếu trực tiếp từ Supabase ngày 23/05/2026.

| Bảng | Constraint | Loại | Ý nghĩa |
|---|---|---|---|
| `dim_farm` | `dim_farm_pkey` | PK | Khóa chính `farm_id` |
| `dim_farm` | `dim_farm_farm_code_key` | UNIQUE | Không trùng `farm_code` |
| `dim_doi` | `dim_doi_pkey` | PK | Khóa chính `doi_id` |
| `dim_doi` | `uq_farm_doi` | UNIQUE | Không trùng `(farm_id, doi_code)` |
| `dim_doi` | `dim_doi_farm_id_fkey` | FK | `farm_id` → `dim_farm(farm_id)`; cascade khi xóa farm |
| `dim_lo` | `dim_lo_pkey` | PK | Khóa chính `lo_id` |
| `dim_lo` | `uq_farm_lo` | UNIQUE | Không trùng `(farm_id, lo_code)` |
| `dim_lo` | `dim_lo_farm_id_fkey` | FK | `farm_id` → `dim_farm(farm_id)`; cascade khi xóa farm |
| `dim_lo` | `dim_lo_doi_id_fkey` | FK | `doi_id` → `dim_doi(doi_id)` |
| `base_lots` | `base_lots_pkey` | PK | Khóa chính `id` |
| `base_lots` | `base_lots_dim_lo_id_fkey` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `seasons` | `seasons_pkey` | PK | Khóa chính `id` |
| `seasons` | `fk_season_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `seasons` | `seasons_base_lot_id_fkey` | FK | `base_lot_id` → `base_lots(id)` |
| `stage_logs` | `stage_logs_pkey` | PK | Khóa chính `id` |
| `stage_logs` | `fk_stage_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `stage_logs` | `stage_logs_base_lot_id_fkey` | FK | `base_lot_id` → `base_lots(id)` |
| `stage_logs` | `chk_stage_logs_active_stage_requires_base_lot` | CHECK | Dòng active của `Chích bắp`/`Cắt bắp` bắt buộc có `base_lot_id` |
| `destruction_logs` | `destruction_logs_pkey` | PK | Khóa chính `id` |
| `destruction_logs` | `fk_destr_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `destruction_logs` | `destruction_logs_base_lot_id_fkey` | FK | `base_lot_id` → `base_lots(id)` |
| `harvest_logs` | `harvest_logs_pkey` | PK | Khóa chính `id` |
| `harvest_logs` | `fk_harvest_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `harvest_logs` | `harvest_logs_base_lot_id_fkey` | FK | `base_lot_id` → `base_lots(id)` |
| `ribbon_schedule` | `ribbon_schedule_pkey` | PK | Khóa chính `id` |
| `ribbon_schedule` | `ribbon_schedule_farm_id_year_week_number_key` | UNIQUE | Mỗi farm/năm/tuần chỉ có một màu dây |
| `ribbon_schedule` | `ribbon_schedule_week_number_check` | CHECK | `week_number` nằm trong `1..53` |
| `ribbon_schedule` | `ribbon_schedule_farm_id_fkey` | FK | `farm_id` → `dim_farm(farm_id)` |
| `size_measure_logs` | `size_measure_logs_pkey` | PK | Khóa chính `id` |
| `size_measure_logs` | `size_measure_logs_lan_do_check` | CHECK | `lan_do` chỉ nhận `1` hoặc `2` |
| `size_measure_logs` | `fk_size_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |
| `bsr_logs` | `bsr_logs_pkey` | PK | Khóa chính `id` |
| `bsr_logs` | `fk_bsr_dim_lo` | FK | `dim_lo_id` → `dim_lo(lo_id)` |

## Database Triggers

### `auto_assign_base_lot_id()` — FIFO Auto-assign

**Áp dụng trên:** `stage_logs`, `harvest_logs`, `destruction_logs` (BEFORE INSERT)

**Mục đích:** Tự động gán `base_lot_id` khi record insert KHÔNG có `base_lot_id` (NULL). Sử dụng logic FIFO: đợt trồng cũ nhất (`ngay_trong` ascending) có remaining capacity > 0 được chọn.

**Capacity per giai_doan:**
| Giai đoạn | Bảng | Capacity |
|---|---|---|
| Chích bắp | `stage_logs` | `planted - SUM(chích bắp đã ghi cho batch)` |
| Cắt bắp | `stage_logs` | `SUM(chích) - SUM(cắt) cho batch` |
| Thu hoạch | `harvest_logs` | `SUM(cắt) - SUM(thu hoạch) cho batch` |

**Trigger names:**
- `trg_auto_base_lot_stage` → `stage_logs`
- `trg_auto_base_lot_harvest` → `harvest_logs`
- `trg_auto_base_lot_destruction` → `destruction_logs`

### `update_lot_inventory()` — cập nhật tồn cây

**Áp dụng trên:** `destruction_logs` (AFTER INSERT/UPDATE/DELETE)

**Mục đích:** Cập nhật tồn cây theo `base_lot_id` khi có xuất hủy. Logic hiện tại scope theo `base_lot_id`, không trừ nhầm toàn bộ `dim_lo_id` khi một lô có nhiều đợt trồng.

**Trigger name:** `trigger_update_lot_inventory`

### `fn_compute_ti_le_display()` — tính tỷ lệ hiển thị

**Áp dụng trên:** `fact_nhat_ky_san_xuat` (BEFORE INSERT/UPDATE)

**Mục đích:** Tính/cap `ti_le_display` từ `klcv`, `so_cong`, `dinh_muc`; outlier quá lớn được cap để không làm lệch thống kê.

**Trigger name:** `trg_compute_ti_le_display`

### `set_updated_at()` — cập nhật timestamp

**Áp dụng trên:** `dim_cong_viec_dinh_muc` (BEFORE UPDATE)

**Mục đích:** Tự động cập nhật `updated_at`.

**Trigger name:** `trg_dim_cong_viec_dinh_muc_updated_at`
