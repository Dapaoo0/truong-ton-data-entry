# Business Logic

Tài liệu tổng hợp toàn bộ quy tắc nghiệp vụ (business rules) của hệ thống dự báo sản lượng chuối.

---

## 1. Chu kỳ sinh trưởng chuối

### 1.1 Vụ mùa (Seasons)
- **F0**: Vụ đầu tiên từ cây con → thu hoạch.
- **F1, F2, F3...** (Fn): Vụ tái sinh từ cây con (chồi) mọc lại sau khi cây mẹ được thu hoạch.
- Mỗi vụ Fn reset về số cây trồng gốc (`base_lots.so_luong`) — **không lấy hao hụt kép** từ vụ trước, vì cây Fn mọc mới thay thế cây mẹ.
- **Reset bao gồm**: Xuất hủy (destruction) của vụ trước **KHÔNG ảnh hưởng** capacity vụ sau. Ví dụ: đợt trồng 1,502 cây, F0 hủy 184 cây → F1 vẫn có capacity = 1,502 (không phải 1,318).
- **Chích bắp**: Cả F0 lẫn Fn đều cần chích bắp. F0 dùng hóa chất xúc tiến ra hoa, Fn cây có thể tự ra hoa nhưng vẫn được chích để đồng bộ thời gian thu hoạch.

### 1.2 Timeline sinh trưởng
- **Trồng → Chích bắp**: ~5–7 tháng (150–210 ngày).
- **Chích bắp → Cắt bắp**: ~14 ngày.
- **Cắt bắp → Thu hoạch**: phụ thuộc vào kích thước buồng và điều kiện thời tiết.

### 1.2.1 Harvest Growth Buffer (Anti-Bleeding)
- Vụ **F1+**: Thu hoạch chỉ được tính nếu `ngay_thu_hoach >= season_start + 18 tuần` (`HARVEST_MIN_GROWTH_WEEKS = 18`).
- Nguyên nhân: khi F0 kết thúc hành chính nhưng thu hoạch F0 vẫn kéo dài, filter đơn thuần `harvest >= F1_start` sẽ gán nhầm harvest F0 vào F1.
- **F0 upper bound**: harvest F0 được giữ đến `F1_start + 18 tuần` (thay vì cắt tại `F1_start`), đảm bảo không mất harvest cuối vụ.


### 1.3 Hao hụt theo giai đoạn (so với số cây trồng gốc)
| Giai đoạn | Tỉ lệ hao hụt | Tỉ lệ còn lại | Constant |
|-----------|---------------|----------------|----------|
| Trồng → Chích bắp | 5% | 95% | `LOSS_RATE_TO_CHICH = 0.05` |
| Chích bắp → Thu hoạch | thêm 5% | 90% | `LOSS_RATE_TO_THU = 0.10` |
| Cắt bắp | (= Chích bắp) | 95% | — |

- Helper: `get_estimated_rate(stage)` trả về tỉ lệ còn lại (0.95 hoặc 0.90).
- Rounding thống nhất: `int(round(cây × rate))` — KHÔNG dùng `int()` truncate.

---

## 2. Phân loại đợt trồng

### 2.1 Trồng mới vs Trồng dặm
| | Trồng mới | Trồng dặm |
|---|-----------|-----------|
| **Ý nghĩa** | Đợt trồng chính, xuống giống cây con mới trên lô | Bổ sung cây vào lô đã có trồng mới (thay cây chết/yếu) |
| **Tạo forecast** | ✅ Tạo chu kỳ F0→F3 riêng | ❌ KHÔNG tạo forecast riêng |
| **Dashboard** | Hiển thị trong Bảng chi tiết + Lịch thu hoạch | Hiển thị riêng ở bảng "📋 Lịch sử Trồng dặm" |
| **Lưu trữ** | `base_lots.loai_trong = "Trồng mới"` | `base_lots.loai_trong = "Trồng dặm"` |

### 2.2 Ví dụ thực tế
Farm 126 lô D6: 4,900 cây trồng mới + 607 cây dặm (5 đợt nhỏ) → chỉ 4,900 cây vào forecast.

---

## 3. Dự báo thu hoạch (Harvest Forecast)

### 3.1 Mô hình Normal Distribution Truncated
Cửa sổ thu hoạch mặc định **54 ngày**, chia 3 phase:

| Phase | Thời gian (mặc định) | Tỷ lệ mặc định | Ý nghĩa |
|-------|-----------|----------------|---------|
| Thu bói | 14 ngày đầu | 10% | Buồng chín sớm, quả nhỏ |
| Thu rộ | 26 ngày giữa | 80% | Giai đoạn thu hoạch chính |
| Thu vét | 14 ngày cuối | 10% | Buồng chín muộn, quả nhỏ |

- **Tỷ lệ % có thể tùy chỉnh** bởi người dùng (mặc định 10/80/10, validation tổng = 100%).
- **Số ngày mỗi phase có thể tùy chỉnh** bởi người dùng (mặc định 14/26/14). Hỗ trợ bất đối xứng (Thu bói ≠ Thu vét).
- Kỹ thuật: Rescale PDF weights cho mỗi phase khớp % mong muốn. SIGMA tự động tính lại theo `DAYS_RO_HALF / Φ⁻¹(0.90)`.
- Mỗi phase được gán vào **tháng chứa midpoint** của khoảng thời gian.

### 3.2 Sản lượng dự toán
| Vụ | Kg/buồng | Constant |
|----|----------|----------|
| F0 | 15 kg | `KG_PER_TREE_F0 = 15` |
| Fn (F1, F2...) | 18 kg | `KG_PER_TREE_FN = 18` |

- Helper: `get_kg_per_tree(vu)` trả về 15 hoặc 18.
- Hằng số đóng gói: `KG_PER_BOX = 13` kg/thùng, `BOXES_PER_CONTAINER = 1,320` thùng/container.

### 3.3 Bốn Mốc Dự báo (4-Milestone Forecast)
Mỗi thẻ tháng thu hoạch hiển thị **4 mốc** để so sánh chênh lệch:

| Mốc | Ký hiệu | Nguồn dữ liệu | Phương pháp | Trừ xuất hủy |
|-----|---------|---------------|-------------|-------------|
| Từ Trồng | ① | `base_lots.so_luong` − xuất hủy | Normal Distribution: `(trồng − hủy) × (1 − LOSS_RATE) × pdf_weight` | Chỉ "Trước chích bắp" |
| Từ Chích bắp | ② | `stage_logs` (Chích bắp) theo ngày | **Shift-based**: dịch ngày chích +84d (`DAYS_CHICH_TO_THU`), phase theo tích lũy % | "Trước cắt bắp" (Aggregate Ratio) |
| Từ Cắt bắp | ③ | `stage_logs` (Cắt bắp) theo ngày | **Shift-based**: dịch ngày cắt +70d (`DAYS_CAT_TO_THU`), phase theo tích lũy % | "Trước thu hoạch" (Pro-rata theo `ribbon_schedule`) |
| Thực tế | ④ | `harvest_logs` | `so_luong` thu hoạch thực tế | — |

- **Mốc ①** dùng Normal Distribution (không đổi). Tỷ lệ hao hụt: `LOSS_RATE_TO_THU = 10%`.
- **Mốc ②③** dùng dữ liệu thực tế theo ngày, **không trừ hao hụt ước tính** (xuất hủy thực tế đã tính riêng qua `destruction_logs`).
- **Phase (Bói/Rộ/Vét) cho Mốc ②③ — Micro-PDF** (08/05/2026):
  - Mỗi record chích/cắt bắp → shift +84d/+70d → spread ±7d Normal Distribution (σ=3, fixed)
  - Gộp tất cả mini-PDFs thành 1 đường cong harvest tổng hợp
  - Phase xác định bằng **diện tích tích lũy** trên đường cong tổng hợp:
    - 0% → 10% diện tích = Thu Bói
    - 10% → 90% diện tích = Thu Rộ
    - 90% → 100% diện tích = Thu Vét
  - **Boundary-day splitting**: Ngày ranh giới được chia thành 2 phần để đảm bảo tỷ lệ chính xác
  - **Largest Remainder Method**: Làm tròn float→int mà bảo toàn tổng
  - Tỷ lệ 10/80/10 configurable bởi user (dùng chung setting Mốc ①)
  - Window ±7d là **fixed**, user không điều chỉnh được (khác Mốc ① có thể chỉnh)
- Nếu mốc ②③④ chưa có dữ liệu → hiển thị "Chưa có TT".
- Chích bắp xảy ra ở **cả F0 lẫn Fn**. F0 dùng hóa chất xúc tiến ra hoa, Fn vẫn được chích để đồng bộ thời gian thu hoạch.
- **Xuất hủy giảm DỰ BÁO, không giảm số thực tế** đã chích/cắt. VD: cắt 100 cây + hủy 5 cây → dự báo thu hoạch = 95 (vẫn ghi nhận cắt 100).
- **Cross-season isolation**: Xuất hủy match vào generation bằng closest-midpoint (cùng logic chích/cắt). Hủy F0 KHÔNG ảnh hưởng F1+.

### 3.4 Phân bổ Xuất hủy theo Giai đoạn (Stage-Aware Destruction)

Mỗi `destruction_logs.giai_doan` chỉ ảnh hưởng **đúng 1 mốc** dự báo:

| Giai đoạn hủy | Mốc bị ảnh hưởng | Cách phân bổ phase |
|---------------|-------------------|-------------------|
| Trước chích bắp | Mốc ① (Từ Trồng) | Trừ trực tiếp từ `so_luong`, Normal Distribution tự phân bổ phase |
| Trước cắt bắp | Mốc ② (Từ Chích) | **Aggregate Ratio**: `ratio = 1 − hủy/tổng_chích`, mỗi record × ratio |
| Trước thu hoạch | Mốc ③ (Từ Cắt) | **Pro-rata theo `ribbon_schedule`**: resolve `mau_day` từ `(farm_id, year, tuan)` qua `ribbon_schedule`, trừ destruction cùng màu dây. Fallback Aggregate Ratio nếu không resolve được |

**Per-generation matching**: Destruction records match vào generation gần nhất bằng `closest_gen = min(range(N), key=|midpoint[g] − ngay_xuat_huy|)`.

**Proportional allocation** (records thiếu `base_lot_id`): Tách theo `giai_doan` trước khi phân bổ tỉ lệ. Default vào F0.

Khi `destruction_logs` có `base_lot_id` → trừ trực tiếp cho đợt trồng đó.

Khi chỉ có `dim_lo_id` (nhiều đợt trồng chung 1 lô, thiếu `base_lot_id`):
```
total_lot_trees = SUM(base_lots.so_luong) WHERE dim_lo_id = same lot
lot_ratio = this_batch.so_luong / total_lot_trees
destruction_share = lot_level_destruction × lot_ratio
```
Ví dụ: Lô 1000 cây, 3 đợt (300/600/100), hủy 100 → mỗi đợt giảm 10% → 270/540/90.

---

## 4. Auto Batch Mapping

### 4.1 Nguyên tắc
Hệ thống tự động liên kết log entries (stage_logs, harvest_logs, destruction_logs) với đợt trồng (`base_lot_id`) dựa trên timeline sinh trưởng. **Không yêu cầu user nhập chọn thủ công.**

### 4.2 Thuật toán FIFO Allocation (allocate_fifo_quantity)
- **FIFO theo ngày trồng**: Đợt trồng cũ nhất (`ngay_trong` ascending) được ưu tiên phân bổ trước.
- **Season-aware planted** (fix 06/05/2026): `planted = so_luong - get_current_season_destruction(bid, "Trước chích bắp")`. Không dùng `so_luong_con_lai` (bị nhiễm destruction F0).
- **Capacity per batch**:
  - Chích bắp: `planted - already_chich_this_batch`
  - Cắt bắp: `chich_this_batch - cat_this_batch`
  - Thu hoạch: `cat_this_batch - har_this_batch`
  - Xuất hủy: delegate sang `allocate_destruction_fifo()` (xem §4.5)
- Nếu đợt cũ đã full → tự động tràn sang đợt kế tiếp.
- Kết quả: mỗi allocation kèm `base_lot_id` → ghi chính xác vào DB.
- **Ví dụ**: Lô 3B có đợt 1 (1376 cây, đã chích 1149, còn 227) và đợt 2 (500 cây, chưa chích). User nhập "chích bắp 3B = 300" → đợt 1 nhận 227, đợt 2 nhận 73.
- **Hai chế độ phân bổ**:
  1. **User chỉ định đợt trồng** → set `base_lot_id` thủ công. Trigger FIFO skip (`IF NEW.base_lot_id IS NOT NULL`).
  2. **Không chỉ định** → FIFO mặc định (trigger tự gán batch cũ nhất có capacity).

### 4.3 Closest-match fallback (resolve_base_lot_id)
- Dùng cho trường hợp auto-resolve khi `base_lot_id` chưa được set bởi FIFO.
- So sánh expected dates của F0→F5 với ngày hành động thực tế.
- **Chồng chập timeline** (≤15 ngày giữa 2 đợt): gán theo đợt gần nhất.

### 4.4 Season-aware Capacity (`get_current_season_destruction`)
- Tìm `MAX(seasons.ngay_bat_dau)` cho batch → lấy destruction `WHERE ngay_xuat_huy >= season_start`.
- **Filter by `giai_doan`**: Chỉ trừ destruction cùng giai_doan. VD: hủy "Trước cắt bắp" KHÔNG trừ capacity chích bắp.
- Giải quyết bug: F0 hủy 184 cây → F1 vẫn có capacity = so_luong gốc (1,502), không phải 1,318.
- Trigger `update_lot_inventory` scope fix: `WHERE id = NEW.base_lot_id` (thay vì `dim_lo_id` cũ gây cross-batch).
- Trigger `auto_assign_base_lot_id` cũng đã được cập nhật dùng season-aware planted.

### 4.5 Destruction FIFO — 3 Chiến lược (`allocate_destruction_fifo`)

| Giai đoạn | Ý nghĩa | Chiến lược FIFO | Pool/Capacity |
|-----------|---------|-----------------|---------------|
| **Trước chích bắp** | Cây chết trước khi chích | FIFO by `ngay_trong` ASC | `planted - đã_chích - hủy_trước_chích_vụ_HT` |
| **Trước cắt bắp** | Cây chết sau chích, trước cắt | Record-level FIFO cross-batch by `ngay_thuc_hien` | `đã_chích_batch - hủy_trước_cắt_batch` |
| **Trước thu hoạch** | Cây chết sau cắt, trước thu | Match `mau_day` via `ribbon_schedule` → closest week → FIFO | `cắt_bắp_cùng_tuần_mau_day - hủy_TH_cùng_batch - harvest_cùng_batch` |

- **Trước chích bắp**: FIFO theo đợt trồng cũ nhất. Capacity = cây chưa chích và chưa hủy.
- **Trước cắt bắp**: Gộp tất cả record chích bắp từ mọi batch, sort by `ngay_thuc_hien` ASC (tiebreak `ngay_trong`). Phân bổ record-level để handle xen-kẽ giữa các đợt.
- **Trước thu hoạch**: Bắt buộc chọn `mau_day` từ `ribbon_schedule`. Tìm tất cả record cắt bắp có `tuan` khớp với tuần của màu dây đó, chọn tuần gần nhất với ngày xuất hủy (closest-date). Trừ harvest + destruction cùng `base_lot_id` đã có.

### 4.6 Ribbon Schedule (Quản lý Màu dây Tập trung)

**Bảng `ribbon_schedule`** là nguồn dữ liệu duy nhất cho màu dây, thay thế cột `mau_day` cũ trên `stage_logs`, `destruction_logs`, `harvest_logs` (đã xóa).

| Thuộc tính | Giá trị |
|---|---|
| **Grain** | `(farm_id, year, week_number)` — 1 farm × 1 tuần = 1 màu dây |
| **Resolve logic** | Join `stage_logs.tuan` + date year → `ribbon_schedule.(year, week_number)` → `color_name` |
| **Auto-create** | Khi user nhập cắt bắp/đo size với màu dây mới cho tuần chưa có → tự động insert |
| **Conflict guard** | Chặn nếu tuần đó đã có màu dây khác |
| **UI** | Tất cả selectbox dùng `build_color_selectbox()` helper (chuẩn hóa viết thường, không viết tắt) |

**Nơi sử dụng:**
- Forecast engine: `_resolve_ribbon_color(row)` dùng `_ribbon_lookup` dict pre-computed
- FIFO Strategy 3: Query `ribbon_schedule` để tìm tuần khớp màu dây → match `stage_logs.tuan`
- Excel export: Resolve week-color từ `ribbon_schedule` thay vì `df_cut["mau_day"]`
- UI display: Selectbox `build_color_selectbox` + `get_or_create_ribbon` validation

---

## 5. Chích bắp Cross-mapping

### 5.1 Kỳ vọng timeline
- Chích bắp xuất hiện **5–7 tháng** (150–210 ngày) sau trồng.

### 5.2 Giải pháp: FIFO Allocation
- **Đã giải quyết**: `allocate_fifo_quantity()` tự động phân bổ chích bắp vào đúng đợt trồng theo FIFO (đợt cũ nhất trước).
- Mỗi record `stage_logs` giờ có `base_lot_id` chính xác → phân biệt được chích bắp thuộc đợt nào.
- Xem chi tiết thuật toán tại §4.2.

### 5.3 Edge case: Lô F vụ cũ (không có base_lot)
- Một số lô vẫn đang thu hoạch chuối Fn từ đợt trồng trước khi hệ thống được triển khai. Các lô này **không có record `base_lots`** trong database.
- VD: Lô D3 Farm 126 — chích bắp 43 cây ngày 30/04/2026 nhưng không có đợt trồng nào.
- **Xử lý**: Insert `stage_logs` với `base_lot_id = NULL`. Record vẫn được lưu để tracking nhưng **không ảnh hưởng forecast** (forecast chỉ tạo cho `loai_trong = 'Trồng mới'`).
- **Lưu ý**: `base_lot_id` trong `stage_logs` là **nullable** (`is_nullable = YES`). FIFO trigger skip khi `base_lot_id IS NOT NULL`, và không auto-assign nếu không tìm thấy batch phù hợp.

---

## 6. Quản lý Farm & Phân quyền

### 6.1 Cấu trúc tổ chức
```
Liên Farm
└── Farm (126, 157, 195)
    └── Đội (NT1, NT2, CSHS...)
        └── Lô (A1, B2, 3A...)
            └── Đợt trồng (base_lots)
                └── Vụ mùa (seasons: F0, F1...)
```

### 6.2 Phân quyền (RBAC)
| Vai trò | Quyền | Scope |
|---------|-------|-------|
| Admin | Xem tất cả farm, dashboard riêng | Toàn hệ thống |
| Phòng Kinh doanh | Xem tất cả farm (read-only) | Toàn hệ thống |
| Quản lý farm | Xem farm mình (read-only) | 1 farm |
| Đội Nông trường (NT1, NT2) | Xem + nhập liệu farm mình | 1 farm, 1 đội |

### 6.3 Soft Deletion
- Tất cả bảng dùng cờ `is_deleted = True/False`. **KHÔNG BAO GIỜ** hard delete.
- Query luôn append `.eq("is_deleted", False)`.

---

## 7. ETL Pipeline

### 7.1 Nguồn dữ liệu
- **GSheet**: Master Sheet + Team Sheets → ETL (`etl_sync.py`) → Supabase.
- **Banana Tracker App** (Streamlit): Nhập trực tiếp vào Supabase.

### 7.2 Quy tắc ETL
- Ưu tiên cột `lo_raw` (lô thực) trước `lo_code` (tên nhóm đội) khi mapping.
- Case-insensitive lookup cho `dim_lo`.
- Missing CV/LO cần được làm sạch trước khi đẩy vào Supabase Dimension.

---

## 8. Bản đồ Farm & Dashboard Aggregation

### 8.1 Diện tích
Hệ thống phân biệt **2 loại diện tích**:

| Loại | Nguồn | Ý nghĩa |
|------|-------|---------|
| **Diện tích lô** | `dim_lo.area_ha` | Diện tích đất thực tế của lô (bao gồm cả lô chưa trồng) |
| **Diện tích trồng** | `SUM(base_lots.dien_tich_trong)` | Diện tích thực tế đã trồng (per-batch) |

- **Ràng buộc**: Tổng `dien_tich_trong` của các đợt trồng trong 1 lô **không được vượt quá** `area_ha`.
- **Panel "Diện tích Farm"**: "Tổng DT lô" = `SUM(dim_lo.area_ha)` cho tất cả lô `is_active=True`.
- **Panel "Đã trồng"**: = `SUM(base_lots.dien_tich_trong)` cho tất cả đợt trồng active.
- **Tooltip bản đồ**: Hiển thị cả 2 dòng ("Diện tích lô" + "Diện tích trồng") để user phân biệt.

### 8.2 Tổng số cây (Map tooltip)
- Chỉ cộng số cây của **vụ F0** (`vu == "F0"`), **KHÔNG cộng F1/F2/F3**.
- Lý do: cây Fn mọc từ **cùng gốc** F0 (ratoon), không phải cây mới → cộng sẽ tính trùng.
- Formula: `total_cay = SUM(so_cay) WHERE vu = "F0"`.

### 8.3 Inactive lots
- Tất cả query đều filter `dim_lo.is_active = True`.
- Lô bị vô hiệu hóa (VD: Lô 11 = gộp 11A + 11B) bị loại khỏi mọi aggregation.

### 8.4 Lô chưa có dữ liệu trồng
- Lô có polygon trên bản đồ nhưng chưa có record trong `base_lots` (VD: Lô 10):
  - Hiển thị `area_ha` từ `dim_lo` (Diện tích lô).
  - Diện tích trồng = "—", Tổng số cây = 0.
  - Giai đoạn = "Chưa có dữ liệu" (màu xám).

---

## 9. Báo cáo Excel (Excel Export)

### 9.1 Nguyên tắc chung
- Báo cáo Excel chỉ hiển thị **số liệu thực tế đã xảy ra** — không bao gồm xuất hủy hoặc hao hụt ước tính.
- Ví dụ: Tuần 10 cắt 100 bắp → báo cáo hiển thị 100. Xuất hủy trước/sau đó không ảnh hưởng.
- Dữ liệu xuất hủy (destruction) được xem ở dashboard riêng, không nằm trong báo cáo Excel.

### 9.2 Báo cáo Cắt bắp (`generate_cut_bap_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_stg` (stage_logs filtered, `giai_doan == "Cắt bắp"`).
- **Layout**: Chia sheet theo năm. Mỗi sheet = 1 năm.
  - Cột A: Tên lô (sorted tự nhiên: 1A, 2A, 3A... không phải 10A, 11A, 1A).
  - Mỗi tuần = 1 cột. Header 2 dòng: Tuần (số) + Màu dây (từ `ribbon_schedule`).
  - Cột cuối: **Lũy kế** = tổng cộng dồn theo lô.
- **Data matching**: `df_cut["lo"] == lo_name` — so khớp trực tiếp, không qua `lot_id`.
- **Type safety**: `tuan` → `pd.to_numeric().astype(int)`, `_year` → `.astype(int)`.
- **Lot union**: Tên lô lấy từ CẢ `base_lots` VÀ `stage_logs` (tránh miss lô chỉ tồn tại trong 1 nguồn).

### 9.3 Báo cáo Chích bắp (`generate_chich_bap_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_stg` (stage_logs filtered, `giai_doan == "Chích bắp"`).
- **Layout**: Tương tự Cắt bắp — chia sheet theo năm, 1 cột/tuần, có Lũy kế.

### 9.4 Báo cáo Trồng mới (`generate_planting_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_seasons` (seasons data).
- **`loai_trong`**: Ưu tiên lấy trực tiếp từ `base_lots.loai_trong` (không cần join `seasons`). Fallback join nếu cột không tồn tại.
- **Layout**: Danh sách đợt trồng kèm ngày, farm, lô, số lượng, loại trồng.
