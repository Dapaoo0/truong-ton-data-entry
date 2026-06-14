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

### 3.5 Máy tính phân bổ container theo nải (Kinh doanh)

Mục tiêu nghiệp vụ của máy tính này là **tính số buồng nguyên tối thiểu cần xẻ** để đáp ứng đơn hàng theo khách hàng/mã hàng. Nguồn buồng nhập vào là giới hạn khả dụng; kết quả `Buồng xẻ tối thiểu` có thể nhỏ hơn nguồn nếu đơn hàng không cần dùng hết sản lượng.

**Định nghĩa buồng xẻ nguyên**
- Một buồng đã xẻ có đủ 12 nải. Các mã hàng không trùng nải có thể lấy trên cùng một buồng.
- Thuật toán tính `active_bunches_estimated = max(số buồng đã dùng ở từng vị trí nải)`. Đây là số buồng nguyên tối thiểu cần mở để có các nải đã phân bổ.
- Ví dụ: 27CP dùng nải 1-5 của 902 buồng và 6H dùng nải 6-7 của 1,040 buồng → chỉ cần mở 1,040 buồng, không phải 1,942 buồng, vì 902 buồng đầu có thể đồng thời cho 27CP và 6H.

**Profile khối lượng nải**
- Bảng kg từng nải là profile tỷ trọng, không dùng trực tiếp như kg/buồng. App scale profile theo kịch bản: `kg_nải = kg_profile_gốc * target_kg_buồng / tổng_profile_gốc`.
- Profile 12 nải có tổng gốc `28.4kg`, dùng cho kịch bản `18kg` và `20kg`.
- Profile 9 nải có tổng gốc `19.0kg`, dùng làm tỷ trọng và scale về kịch bản `15.6kg`.
- Khi tính một dải cắt, thuật toán cộng kg từng nải sau scale trong dải đó. Ví dụ `12 nải - 18kg`, `6H 5-7` ≈ `4.31kg/buồng`.

**Quy cách hiện tại**
| Mã hàng | Thị trường | Khoảng mẹ |
|---|---|---|
| 27CP | Nhật | 1-5 |
| 30CP | Nhật | 1-9 |
| 6H | Nhật | 5-7 |
| 5H | Nhật | 8-10 |
| 8H | Hàn | 1-4 |
| 5/6H | Hàn | 5-9 |
| 15CP | Hàn | 10-12 |
| 12CP | Hàn | 10-12 |
| 10CP | Hàn | 10-12 |

Với buồng 9 nải, hệ thống dùng mapping suy luận theo vùng tương đối: `27CP Nhật 1-4`, `30CP Nhật 1-7`, `6H Nhật 4-5`, `5H Nhật 6-8`, `8H Hàn 1-3`, `5/6H Hàn 4-7`, `15CP/12CP/10CP Hàn 6-9`.

Các khoảng trên là **khoảng mẹ**. Thuật toán được phép chọn mọi khoảng con liền kề trong khoảng mẹ. Một dòng đơn hàng cũng có thể được tách thành nhiều khoảng con nếu việc tách đó giúp giảm thiếu hàng hoặc giảm số buồng nguyên phải xẻ. Tuy nhiên số đoạn cắt là penalty vận hành đứng ngay sau `active_bunches_estimated`, nên thuật toán sẽ ưu tiên một dải liền kề duy nhất khi số buồng xẻ không đổi.

**Khách hàng trong mode Tính số hàng từ số buồng**
| Khách hàng | Thị trường vận chuyển |
|---|---|
| Wismettac (Nhật 1) | Nhật |
| Advance (Nhật 2) | Nhật |
| Uone | Hàn |

Khách hàng quyết định thị trường và danh sách mã hàng hợp lệ. Khi người dùng chưa chọn khách hàng/mã hàng/ưu tiên, UI giữ trạng thái trống; các dòng chưa đủ `Khách hàng + Mã hàng + Nhu cầu` không được gửi vào optimizer.

**Thứ tự tối ưu trong mode Tính số hàng từ số buồng**
1. Giảm thiếu thùng theo thứ tự ưu tiên khách hàng, ưu tiên mã hàng trong khách hàng, thứ tự dòng.
2. Với mức đáp ứng đã chốt, giảm số buồng nguyên cần xẻ (`active_bunches_estimated`).
3. Giảm số đoạn cắt để tránh bẻ dòng đơn hàng không cần thiết.
4. Giảm tổng kg/nải-buồng tiêu thụ, kg dư do làm tròn.
5. Tie-break ổn định theo thứ tự khoảng con.

Nếu nguồn buồng không đủ, thuật toán vẫn ưu tiên đáp ứng dòng ưu tiên cao nhất trước, sau đó báo thiếu thùng cho các dòng còn lại. Nếu nguồn dư, thuật toán không dùng hết nguồn mà báo số buồng xẻ tối thiểu.

**Mode Tính số cont tối đa từ số buồng**
- Mục tiêu chính là tối đa số container nguyên theo thứ tự ưu tiên thị trường.
- Sau khi số container đã chốt, thuật toán tiếp tục giảm số buồng nguyên cần xẻ và số đoạn cắt.

**Mode Tính số buồng từ số cont**
- Người dùng nhập từng container mục tiêu riêng. Mỗi cont bắt buộc chọn khách hàng và khai báo các dòng mã hàng + số thùng.
- Khách hàng quyết định thị trường: `Wismettac (Nhật 1)` và `Advance (Nhật 2)` thuộc Nhật, `Uone` thuộc Hàn. SKU dropdown chỉ cho mã hợp lệ với thị trường đó.
- Mỗi cont phải có tổng đúng `1,320 thùng`. Nếu thiếu hoặc vượt, hệ thống cảnh báo ngay tại input và không chạy solver.
- Solver cộng gộp demand theo `khách hàng + thị trường + mã hàng`, bắt buộc đáp ứng đủ số thùng đã nhập, rồi tối thiểu hóa số buồng nguyên cần xẻ.
- Objective của mode này tách rõ phần bắt buộc và phần trình bày: bắt buộc chứng minh `active_bunches_estimated` tối thiểu; sau đó ghép dải nải nhanh để bảng dễ đọc và hạn chế bẻ vụn không cần thiết.
- Để UI không bị chờ vô hạn với cơ cấu nhiều cont/nhiều mã, mode này dùng MIP exact ở cấp vị trí nải để chứng minh số buồng tối thiểu. Chỉ trạng thái `OPTIMAL` mới được xem là kết quả hợp lệ. Nếu chưa chứng minh được số buồng tối thiểu, hệ thống không hiển thị số buồng xấp xỉ. Sau khi số buồng đã được chứng minh, bước ghép dải hiển thị chạy nhanh và không làm mất tính đúng của số buồng tối thiểu.

**Lưu kế hoạch**
- Nút `Lưu kế hoạch` lưu snapshot vào bảng `container_allocation_plans`, gắn với account đăng nhập qua `account_farm` + `account_team`.
- Snapshot gồm nguồn buồng, profile kg/nải, input đơn hàng/ưu tiên, output optimizer, quá trình chọn nải và tồn nải còn lại.
- Kế hoạch đã lưu vẫn hiển thị lại sau F5/đăng nhập lại. Xóa thẻ kế hoạch là soft delete (`is_deleted = true`).

**Dự báo từ cắt bắp trong calculator**
- Người dùng chọn `Dự báo +8 tuần` hoặc `Dự báo +9 tuần`.
- Cách đếm là inclusive, tính cả tuần cắt bắp: cắt tuần 20, chọn `+8` thì tuần thu hoạch dự báo là tuần 27.

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

**Bảng `ribbon_schedule`** là nguồn chuẩn cho màu dây theo `(farm_id, year, week_number)`. `stage_logs` và `destruction_logs` resolve màu dây qua tuần; riêng `harvest_logs` lưu thêm `mau_day` ở cấp record vì một lô có thể thu nhiều màu dây trong cùng ngày.

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
- Thu hoạch: user chọn `mau_day` từ các màu dây đang có; hệ thống map về tuần cắt có cùng màu dây, ưu tiên cửa sổ dự báo `+8/+9`.
- Excel export: Resolve week-color từ `ribbon_schedule`; cột `Thu hoạch` lấy `harvest_logs.mau_day` để quy về tuần cắt nguồn.
- UI display: Selectbox `build_color_selectbox` + `get_or_create_ribbon` validation

---

## 5. Chích bắp Cross-mapping

### 5.1 Kỳ vọng timeline
- Chích bắp xuất hiện **5–7 tháng** (150–210 ngày) sau trồng.

### 5.2 Giải pháp: FIFO Allocation
- **Đã giải quyết**: `allocate_fifo_quantity()` tự động phân bổ chích bắp vào đúng đợt trồng theo FIFO (đợt cũ nhất trước).
- Mỗi record `stage_logs` giờ có `base_lot_id` chính xác → phân biệt được chích bắp thuộc đợt nào.
- Xem chi tiết thuật toán tại §4.2.

### 5.2.1 Quy ước 3B / 3BF trong file Excel
- Trong file "mặt bằng chích bắp", `3B` và `3BF` không phải 2 lô khác nhau. Cả hai cùng là `dim_lo.lo_name = "3B"`.
- `3B` = 3B đợt 2, đang là F0 → gắn `base_lot_id = 7`.
- `3BF` = 3B đợt 1, đang là F1 → gắn `base_lot_id = 25`.
- Khi import dữ liệu có ký hiệu `3BF`, phải set `base_lot_id` thủ công. Không để FIFO tự chọn, vì FIFO theo đợt cũ nhất có thể gán sai ý nghĩa khi cùng lô có nhiều đợt/vụ.
- Khi query kiểm tra, tránh join thẳng `stage_logs -> seasons` rồi cộng số lượng nếu không lọc `seasons.vu` hoặc không dedupe theo `stage_logs.id`. Một `base_lot_id` có thể có nhiều dòng `seasons` (F0, F1...), nên join như vậy sẽ nhân đôi record log.

### 5.3 Edge case: Lô F vụ cũ (không có base_lot)
- Một số lô vẫn đang thu hoạch chuối Fn từ đợt trồng trước khi hệ thống được triển khai. Các lô này **không có record `base_lots`** trong database.
- VD: Lô D3 Farm 126 — chích bắp 43 cây ngày 30/04/2026 nhưng không có đợt trồng nào.
- **Xử lý hiện tại**: Không insert `Chích bắp`/`Cắt bắp` vào `stage_logs` nếu lô không có `base_lot_id` hợp lệ. Đây là dữ liệu ngoài phạm vi tracking hiện tại; nếu cần theo dõi legacy riêng thì phải có cơ chế/bảng riêng.
- **DB guardrail**: Constraint `chk_stage_logs_active_stage_requires_base_lot` chặn mọi record active của `Chích bắp` hoặc `Cắt bắp` khi `base_lot_id IS NULL`. Điều này ngăn lỗi nhập trực tiếp SQL/API bỏ qua logic app.

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
- **Fallback khi thiếu `dien_tich_trong`**: ước tính theo mật độ chuẩn `so_luong / 2190` ha, sau đó chặn tổng batch không vượt `dim_lo.area_ha`.
- **Panel mốc sinh trưởng**: `Chích bắp`, `Cắt bắp`, `Thu hoạch` là diện tích **lũy kế đã đạt mốc đó**. Diện tích đã cắt vẫn nằm trong tổng đã chích; diện tích đã thu vẫn nằm trong tổng đã cắt và đã chích. `Sinh trưởng` chỉ là phần đã trồng nhưng chưa chích.
- **Tooltip bản đồ**: Hiển thị cả 2 dòng ("Diện tích lô" + "Diện tích trồng") để user phân biệt.

### 8.2 Tổng số cây (Map tooltip)
- Chỉ cộng số cây của **vụ F0** (`vu == "F0"`), **KHÔNG cộng F1/F2/F3**.
- Lý do: cây Fn mọc từ **cùng gốc** F0 (ratoon), không phải cây mới → cộng sẽ tính trùng.
- Formula: `total_cay = SUM(so_cay) WHERE vu = "F0"`.

### 8.3 Inactive lots
- Tất cả query đều filter `dim_lo.is_active = True`.
- Lô bị vô hiệu hóa (VD: Lô 11 = gộp 11A + 11B) bị loại khỏi mọi aggregation.
- Dropdown nhập tác vụ chỉ hiển thị giao của hai tập: lô `dim_lo` đang active và tên lô có polygon trên bản đồ của farm. Vì vậy lô lịch sử còn sót trong DB nhưng không còn trên bản đồ sẽ không xuất hiện để người dùng nhập nhầm.
- Nếu một farm chưa có file polygon, dropdown fallback về danh sách `dim_lo` active để không chặn vận hành.

### 8.4 Lô chưa có dữ liệu trồng
- Lô có polygon trên bản đồ nhưng chưa có record trong `base_lots` (VD: Lô 10):
  - Hiển thị `area_ha` từ `dim_lo` (Diện tích lô).
  - Diện tích trồng = "—", Tổng số cây = 0.
  - Giai đoạn = "Chưa có dữ liệu" (màu xám).

---

## 9. Báo cáo Excel (Excel Export)

### 9.1 Nguyên tắc chung
- Báo cáo Excel Cắt bắp hiển thị **4 cột mỗi tuần**: CẮT BẮP, XUẤT HỦY, Thu hoạch, Tồn trên lô.
- XUẤT HỦY có thể gồm hai nhóm:
  - `Trước thu hoạch`: cây/buồng hủy khi còn nằm trên lô, nên làm giảm tồn trên lô.
  - `Sau thu hoạch`: hủy sau khi màu dây/lứa đó đã thu. Nhóm này vẫn hiển thị trong cột XUẤT HỦY nhưng được bù vào Thu hoạch ròng để không trừ tồn hai lần.
- Công thức theo từng lô + tuần màu dây:
  - `Thu hoạch hiển thị = max(0, Thu hoạch gốc - Xuất hủy sau thu hoạch)`.
  - `Tồn trên lô = Cắt bắp - Xuất hủy trước thu hoạch - Thu hoạch gốc - max(0, Xuất hủy sau thu hoạch - Thu hoạch gốc)`.
- Ví dụ: Cắt 55, hủy trước thu 9, thu hoạch gốc 46, hủy sau thu 2 → Excel hiển thị `CẮT 55 | HỦY 11 | THU 44 | TỒN 0`.
- Cột Lũy kế cuối bảng tổng cộng dồn riêng CẮT, HỦY, THU ròng và TỒN.

### 9.2 Báo cáo Cắt bắp (`generate_cut_bap_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_stg` (stage_logs filtered), `df_des` (destruction_logs, `giai_doan in ["Trước thu hoạch", "Sau thu hoạch"]`), `df_har` (harvest_logs).
- **Layout**: Chia sheet theo năm. Mỗi sheet = 1 năm.
  - Khi export 1 farm: Cột A là tên lô (sorted tự nhiên: 1A, 2A, 3A... không phải 10A, 11A, 1A).
  - Trên UI Admin/Phòng Kinh doanh: báo cáo Cắt bắp tải tách biệt theo farm qua popover chọn farm; mỗi file chỉ chứa dữ liệu của farm đã chọn.
  - Hàm vẫn hỗ trợ input nhiều farm nếu được gọi trực tiếp: khi đó thêm cột `Farm` trước cột `Lô` để tránh trộn lô cùng tên giữa các farm.
  - Mỗi tuần = 4 cột (CẮT BẮP | XUẤT HỦY | Thu hoạch | Tồn trên lô).
  - Cột cuối: **Lũy kế** = tổng cộng dồn theo lô (CẮT, HỦY, THU, TỒN).
- **Header 4 dòng** (`data_start_row = 5`, `freeze_panes = "B5"`):
  - **Row 1 — Dự báo thu hoạch**: `_forecast_harvest_label(cut_week, year)` theo farm. Farm 126 dùng `+8`, Farm 157 dùng `+9`; farm khác giữ fallback `+8/+9`. Cách tính `+8/+9` tính cả tuần cắt bắp. Nền vàng pastel (`#FFF9C4`), chữ bold italic. Xử lý chuyển năm ISO (52/53 tuần): `"5-2027 (+8)"`.
  - **Row 2 — Tuần X**: Số tuần ISO, merged 4 cột, nền xanh dương header (`#D9E1F2`).
  - **Row 3 — Sub-headers**: "CẮT BẮP" | "XUẤT HỦY" | "Thu hoạch" | "Tồn trên lô", nền trắng.
  - **Row 4 — Màu dây**: Từ `ribbon_schedule` (farm_id, year, week_number), nền theo COLOR_MAP. Khi file gộp nhiều farm và cùng tuần có màu khác nhau, cell màu dây hiển thị nhiều dòng theo farm.
- **Data matching**: `base_lot_id` (ưu tiên) hoặc fallback `df_cut["farm"] + df_cut["lo"]`. Thu hoạch map bằng `harvest_logs.mau_day` về tuần cắt cùng màu dây trong đúng farm, ưu tiên tuần có dự báo theo offset farm (`+8` cho 126, `+9` cho 157) trùng tuần thu hoạch thực tế.
- **Dòng `Dự kiến thu hoạch`**: nằm ngay dưới dòng `Tổng`. Mỗi tuần chỉ điền ở cột `Thu hoạch`, công thức `round(Tổng CẮT BẮP của tuần × 97%)`, chưa trừ xuất hủy và chưa trừ thu hoạch thực tế. Các cột còn lại hiển thị `-`.
- **Type safety**: `tuan` → `pd.to_numeric().astype(int)`, `_year` → `.astype(int)`.
- **Lot union**: Tên lô lấy từ CẢ `base_lots` VÀ `stage_logs`/`destruction_logs` (tránh miss lô chỉ tồn tại trong 1 nguồn).

### 9.3 Báo cáo Dự báo Thu hoạch (`generate_harvest_forecast_excel`)
- **Mục đích**: Tải một file riêng để xem mỗi tuần thu hoạch dự báo có bao nhiêu buồng, tách được nguồn đến từ farm nào và màu dây nào.
- **Input**: `df_lots`, `df_stg` với `stage_logs.giai_doan == "Cắt bắp"`.
- **Cách dịch tuần**:
  - Farm 126: `+8` tuần inclusive, tức cắt tuần 20 → dự báo thu hoạch tuần 27.
  - Farm 157: `+9` tuần inclusive, tức cắt tuần 20 → dự báo thu hoạch tuần 28.
  - Farm khác: fallback `+8/+9` nếu gọi trực tiếp ngoài luồng hiện tại.
- **Số lượng dự báo**: `round(Số cắt bắp × 97%)`. Đây là số sau khi nhân 97%, không phải số cắt bắp gốc.
- **Sheet `Tổng hợp`**: dạng ngang để dễ đọc; mỗi cột là một tuần thu hoạch dự báo. Dòng `Dự kiến thu hoạch` là tổng đã gom toàn bộ farm/màu dây trong tuần đó; dòng `Nguồn` ghi rõ từng phần đóng góp dạng `Farm 126 - Cam: 500 cây`.
- **Sheet `Chi tiết nguồn`**: mỗi dòng truy ngược về `Farm`, `Năm/Tuần cắt bắp`, `Màu dây`, `Lô`, `Số cắt bắp`, `Dự kiến thu hoạch 97%`, `Cách dự báo`. Không hiển thị cột kỹ thuật `Base lot`.
- **UI**: Admin/Phòng Kinh doanh tải một file gộp tất cả farm; account farm tải theo scope farm đang đăng nhập. Báo cáo Cắt bắp vẫn tải tách biệt theo farm.

### 9.4 Báo cáo Chích bắp (`generate_chich_bap_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_stg` (stage_logs filtered, `giai_doan == "Chích bắp"`).
- **Layout**: Tương tự Cắt bắp — chia sheet theo năm, 1 cột/tuần, có Lũy kế.

### 9.5 Báo cáo Trồng mới (`generate_planting_excel`)
- **Input**: `df_lots` (base_lots filtered), `df_seasons` (seasons data).
- **`loai_trong`**: Ưu tiên lấy trực tiếp từ `base_lots.loai_trong` (không cần join `seasons`). Fallback join nếu cột không tồn tại.
- **Layout**: Danh sách đợt trồng kèm ngày, farm, lô, số lượng, loại trồng.

---

## 10. Chi Phí

### 10.1 Dashboard Chi phí raw

Tab `Chi phí` trong app input là dashboard đọc số liệu raw để phân tích tổng chi phí vận hành.

- **Nguồn chi phí**: cộng trực tiếp `fact_nhat_ky_san_xuat.thanh_tien` và `fact_vat_tu.thanh_tien`.
- **Không clean theo lifecycle**: dashboard này không loại chi phí cây cũ, không cap theo cắt bắp, không chia lại chi phí/cây. Mục tiêu là xem tổng chi phí ghi nhận theo farm/lô/đội/tháng/hạng mục.
- **Phân quyền farm**: Admin và Phòng Kinh doanh xem được nhiều farm; account farm/đội chỉ xem farm đang đăng nhập.
- **Data access**: dùng Supabase REST client hiện tại, cache 5 phút, join dimension bằng pandas trong app.
- **Tách biệt với popup chi phí/cây**: popup trên bản đồ dùng logic clean/lifecycle ở mục 10.2, nên số tổng có thể khác dashboard raw.

### 10.2 Chi Phí/Cây Trên Bản Đồ

Dashboard chi phí/cây được mở từ tooltip của bản đồ Farm 126/157/195.

- **Nguồn chi phí**: cộng `fact_nhat_ky_san_xuat.thanh_tien` và `fact_vat_tu.thanh_tien`.
- **Phạm vi lô**: cột lô (`lo_id`/tên lô nguồn) quyết định chi phí thuộc đâu; `doi_id` chỉ là đội thực hiện, không dùng để suy ra lô chịu chi phí.
- **Lô cụ thể**: nếu dòng chi phí ghi lô thật (`A8`, `D4`, `3B`, `8A`...) thì cộng 100% vào lô đó, bất kể đội nào thực hiện.
- **Lô chung theo đội**: nếu dòng ghi `NT1`, `NT2` hoặc tên cũ `NT3+NT4` thì chia cho các lô thuộc nhóm đó theo tỷ lệ diện tích. Farm 157: `8A` thuộc nhóm `NT2` (tên cũ `NT3+NT4`).
- **Chi phí chung toàn farm**: nếu dòng ghi `Farm xxx`, `Vườn Ươm`, `Nhà Đội`, `Cơ giới`, `Điện nước`, `BVTV`, `Trồng mới`, hoặc `lo_id` rỗng/mô tả chung farm thì chia toàn farm theo tỷ lệ diện tích active. Farm 195 hiện chưa lập đội NT nên mọi chi phí chung không phải lô cụ thể đều chia toàn farm.
- **Không xác định**: nhãn lô không phải lô thật, không phải đội, và không phải phạm vi chung farm thì không tự động chia toàn farm để tránh làm lệch chi phí/cây.
- **Giữ dữ liệu gốc**: không loại trừ dòng gộp/rollup như `Chăm sóc vườn`, `Chăm sóc buồng`, `Điện, Phân, và Nước`; số liệu phản ánh tổng hiện có trong fact table.
- **Mẫu số**: tính theo từng đợt `base_lots.loai_trong = "Trồng mới"`. Trồng dặm không tạo đợt chi phí riêng trong v1.
- **Vòng đời đợt trồng**: mỗi đợt nhận chi phí từ `ngay_trong` đến `seasons.ngay_ket_thuc_thuc_te`; nếu chưa có ngày kết thúc thì đợt vẫn active. Nếu không có season mở, ngày thu hoạch/xuất hủy đủ cây có thể đóng vòng đời đợt.
- **Cổng sinh trưởng cho chăm sóc buồng**: các hạng mục chỉ hợp lý sau khi đã có mốc `Cắt bắp` của đúng `base_lot_id` như `Bao buồng`, `Bao búp`, `Bẻ hoa`, `Lặt râu`, `Chăm sóc buồng`, `Gỡ/Sửa bao`, `Vệ sinh buồng`, `Vén lá`, `Đo size chuối` sẽ không được phân bổ vào đợt nếu tại ngày phát sinh chi phí chưa có `stage_logs.giai_doan = "Cắt bắp"` lũy kế cho đợt đó.
- **Cap KL theo Cắt bắp**: với chi phí nhân công có `klcv` thuộc nhóm trên hoặc chính hạng mục `Cắt bắp`, lượng phân bổ vào một đợt không được vượt số `Cắt bắp` lũy kế đến ngày chi phí và không vượt `so_luong` của đợt. Phần vượt được đưa vào nhóm chi phí chưa phân bổ/cây cũ, tránh trường hợp cây mới gánh chi phí của buồng/cây cũ.
- **Trọng số phân bổ lô**: ưu tiên `base_lots.dien_tich_trong` của các đợt active tại ngày phát sinh chi phí; nếu thiếu thì fallback theo tỷ lệ số cây active hoặc `dim_lo.area_ha`. Lô/đợt cũ đã kết thúc không còn nhận chi phí mới.
- **Phân bổ nhiều đợt**: vì fact chi phí hiện chỉ có `lo_id`, không có `base_lot_id`, mỗi dòng chi phí theo ngày được chia cho các đợt trồng đang active tại ngày đó theo tỷ lệ `so_luong` của từng đợt.
- **Chi phí thu hoạch**: chỉ nhận diện khi `công đoạn/hạng mục/công việc/mã chuẩn` có nghĩa là `Thu hoạch`; không coi `Chăm sóc buồng` là thu hoạch. Dòng thu hoạch chỉ phân bổ cho đợt đã có `harvest_logs` tương ứng và chia theo sản lượng thu hoạch; nếu chưa có harvest phù hợp thì đưa vào chi phí chưa phân bổ, không ép vào cây mới.
- **Công thức**:
  - `chi_phi_lot = chi_phi_dong * dien_tich_lot_active / tong_dien_tich_scope_active`
  - `chi_phi_phan_bo_dot = chi_phi_dong * so_cay_dot / tong_so_cay_cac_dot_active`
  - `chi_phi_cay_dot = tong_chi_phi_phan_bo_dot / so_cay_dot`
- **Scope loại khỏi chi phí/cây**: các phạm vi không trực tiếp là chi phí nuôi cây như `Xưởng đóng gói`, `Kho`, `Kho Hóc Môn`, `Công trình`, `Xây dựng`, `Nhà xưởng`, `Bán hàng`, `Văn phòng` được tách khỏi dashboard chi phí/cây. Dữ liệu gốc vẫn giữ trong DB để audit, nhưng không chia vào lô/farm.
- **Ngưỡng loại theo cây active**: sau khi phân bổ, hệ thống hậu kiểm theo nhóm `source + scope + category + detail`. Nhóm `Phân bón/Chăm sóc cây` bị tách nếu vượt `80,000 đ/cây active`; nhóm `Cơ giới/Điện nước/Dầu DO` bị tách nếu vượt `50,000 đ/cây active`. Ở cấp từng dòng, `Phân bón/Chăm sóc cây` trên `20,000 đ/cây active`, `Cơ giới/Điện nước/Dầu DO` trên `30,000 đ/cây active`, hoặc chi phí `Trồng mới/Vườn ươm` cách ngày trồng active quá 60 ngày cũng được đưa vào audit nền thay vì cộng lên UI.
- **Không phân bổ**: dòng chi phí trước mọi ngày trồng, thiếu ngày, ngoài vòng đời đợt trồng, hoặc chi phí thu hoạch chưa có harvest tương ứng được đưa vào nhóm "Chi phí chưa phân bổ" trong kết quả tính nền để audit nội bộ, không dùng làm chi phí/cây hiển thị.
- **UI popup**: popup trên bản đồ là màn hình xem nhanh cho người dùng vận hành, chỉ hiển thị `Chi phí/cây TB`, tổng chi phí được tính vào cây, tổng cây tính và bảng chi phí/cây theo từng đợt. Các dòng bị tách khỏi chi phí/cây vì sai vòng đời/giai đoạn vẫn được giữ trong kết quả tính nền để audit, nhưng không hiển thị số dòng hay bảng kỹ thuật trong UI.
