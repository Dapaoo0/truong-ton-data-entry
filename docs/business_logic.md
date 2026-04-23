# Business Logic

Tài liệu tổng hợp toàn bộ quy tắc nghiệp vụ (business rules) của hệ thống dự báo sản lượng chuối.

---

## 1. Chu kỳ sinh trưởng chuối

### 1.1 Vụ mùa (Seasons)
- **F0**: Vụ đầu tiên từ cây con → thu hoạch.
- **F1, F2, F3...** (Fn): Vụ tái sinh từ cây con (chồi) mọc lại sau khi cây mẹ được thu hoạch.
- Mỗi vụ Fn reset về số cây trồng gốc — **không lấy hao hụt kép** từ vụ trước, vì cây Fn mọc mới thay thế cây mẹ.

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

| Mốc | Ký hiệu | Nguồn dữ liệu | Công thức |
|-----|---------|---------------|-----------|
| Từ Trồng | ① | `base_lots.so_luong` − xuất hủy | `(trồng − hủy) × (1 − LOSS_RATE)` |
| Từ Chích bắp | ② | `stage_logs` (Chích bắp) | `chích_bắp × (1 − LOSS_RATE_TO_CHICH)` |
| Từ Cắt bắp | ③ | `stage_logs` (Cắt bắp) | `cắt_bắp × (1 − LOSS_RATE_TO_CHICH)` |
| Thực tế | ④ | `harvest_logs` | `so_luong` thu hoạch thực tế |

- Nếu mốc ②③④ chưa có dữ liệu → hiển thị "Chưa có TT".
- Dialog chi tiết: `st.metric` 4 cột + bảng 8 cột (Lô, Vụ, Loại thu, ①, ②, ③, ④, Khoảng TG).
- `LOSS_RATE_TO_CHICH = 0.05` (5% hao hụt) áp dụng cho cả Mốc ② và ③.
- Chích bắp thường chỉ xảy ra ở F0 (xúc tiến ra hoa), Fn cây tự ra hoa tự nhiên.

### 3.4 Phân bổ Xuất hủy theo Tỉ lệ
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

### 4.2 Thuật toán
- Closest-match: So sánh expected dates của F0→F5 với ngày hành động thực tế.
- **Chồng chập timeline** (≤15 ngày giữa 2 đợt): gán theo đợt gần nhất.
- **Fn**: F1 bắt đầu = ngày harvest F0, nên Season Fn match bằng expected harvest F(n-1), không phải ngày trồng.

### 4.3 Destruction mapping
- Giai đoạn xuất hủy ("Trước chích bắp/cắt bắp/thu hoạch") được map sang stage tương ứng để dùng timeline matching chính xác.
- Không dùng fallback closest-planted (có thể match sai đợt mới trồng).

---

## 5. Chích bắp Cross-mapping

### 5.1 Kỳ vọng timeline
- Chích bắp xuất hiện **5–7 tháng** (150–210 ngày) sau trồng.

### 5.2 Hạn chế hiện tại
- Nhật ký (`fact_nhat_ky_san_xuat`) chỉ ghi `lo_id` (cấp lô), **không ghi** `base_lot_id`.
- 1 lô có nhiều đợt trồng → không phân biệt được chích bắp thuộc đợt nào. Cần logic **time window** khi data đợt mới bắt đầu có.
- Các lô chích bắp không có `base_lot` tương ứng = lô cũ, **không cần quan tâm** cho dự báo sản lượng mới.

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
