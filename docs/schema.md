# Database Schema

Tài liệu này ghi lại chi tiết toàn bộ cấu trúc cơ sở dữ liệu trên Supabase được dùng cho dự án phân tích dữ liệu Banana Tracker và Ghi nhận Nhật ký nông vụ. Tài liệu này liệt kê toàn bộ các bảng, giải nghĩa từng bảng và từng trường một cách chi tiết.

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
**Ý nghĩa:** Bảng theo dõi thông tin gốc của các lô trồng lúc ban đầu (số lượng, ngày trồng).

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_trong | date | Có | - |
| so_luong | integer | Có | - |
| trang_thai | text | Không | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| so_luong_con_lai | integer | Không | - |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.stage_logs
**Ý nghĩa:** Log lưu quá trình sinh trưởng (cắt bắp, chích bắp).

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| giai_doan | text | Có | - |
| ngay_thuc_hien | date | Có | - |
| so_luong | integer | Có | - |
| mau_day | text | Không | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.destruction_logs
**Ý nghĩa:** Log lưu quá trình xuất hủy cây chuối.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_xuat_huy | date | Có | - |
| giai_doan | text | Có | - |
| ly_do | text | Có | - |
| so_luong | integer | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| mau_day | text | Không | - |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

## public.harvest_logs
**Ý nghĩa:** Log lưu quá trình thu hoạch chuối.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| ngay_thu_hoach | date | Có | - |
| so_luong | integer | Có | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| tuan | integer | Không | - |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| hinh_thuc_thu_hoach | text | Không | - |
| mau_day | text | Không | - |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

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

## public.seasons
**Ý nghĩa:** Bảng định nghĩa các vụ mùa (F0, F1...) của từng lô.

| Tên Trường (Field) | Kiểu Dữ Liệu (Type) | Bắt Buộc (Required) | Ý Nghĩa / Ghi Chú |
|---|---|---|---|
| id | integer | Có | - |
| vu | text | Có | - |
| loai_trong | text | Có | - |
| ngay_bat_dau | date | Có | - |
| ngay_ket_thuc_thuc_te | date | Không | - |
| ngay_ket_thuc_du_kien | date | Không | - |
| created_at | timestamp with time zone | Không | Thời gian tạo record |
| is_deleted | boolean | Không | Cờ đánh dấu soft delete (True=Đã xóa) |
| dim_lo_id | integer | Không | ID định danh/Khóa ngoại |

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

