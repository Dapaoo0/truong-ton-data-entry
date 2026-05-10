# Changelog

Lịch sử các thay đổi và tính năng mới được triển khai vào dự án.

## [10/05/2026] - Responsive Map Overhaul (6 Breakpoints)

#### Fix: Bản đồ farm bị cắt bên phải trên iPad (`app.py`)
- **[Root Cause]**: Thiếu `overflow-x: hidden` trên `html/body` trong iframe, thiếu `<meta viewport>`, và chỉ có 3 breakpoint (mobile/desktop/XL) — bỏ sót iPad (769–1024px).
- **[Fix — CSS]**: Viết lại toàn bộ responsive system với **6 breakpoints chuẩn công nghiệp**:
  - **Mobile** (320–480px): `border-radius: 6px`, font 9–10px
  - **Small tablet** (481–768px): `border-radius: 8px`, font 10–11px
  - **Tablet / iPad portrait** (769–1024px): `border-radius: 10px`, font 11–12px
  - **Default** (1025–1199px): Base styles (iPad landscape, small laptops)
  - **Large** (1200–1799px): Desktop/laptop full styling
  - **XL** (1800px+): 4K/ultrawide, font 14–15px
- **[Fix — HTML]**: Thêm `<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">` trong iframe HTML.
- **[Fix — iOS]**: `overflow-x: hidden` trên `html` + `body`, `-webkit-text-size-adjust: 100%` chống text inflation.
- **[SVG]**: Thêm `preserveAspectRatio="xMidYMid meet"` cho SVG element.

---

## [09/05/2026] - Excel Export Refactor (Cắt bắp / Trồng mới)

#### Refactor: Viết lại `generate_cut_bap_excel()` (`app.py`)
- **[Xóa]**: Param `df_des` (destruction data) — báo cáo Cắt bắp giờ chỉ hiển thị **số cắt thực tế**, không bao gồm xuất hủy.
- **[Xóa]**: Cột "XUẤT HỦY" khỏi sheet Excel — mỗi tuần = 1 cột duy nhất (số bắp cắt).
- **[Xóa]**: `lot_id_map` alias mapping — thay bằng so khớp trực tiếp `df_cut["lo"] == lo_name`.
- **[Thêm]**: Cột **Lũy kế** cuối bảng — tổng cộng dồn theo lô.
- **[Fix]**: Type casting `tuan` → `pd.to_numeric(...).astype(int)` và `_year` → `.astype(int)` — chống lọc sai do float/string.
- **[Fix]**: Union tên lô từ CẢ `df_lots` VÀ `df_cut` — tránh miss lô chỉ tồn tại trong 1 nguồn.
- **[Layout]**: 2 header rows (Tuần + Màu dây), `freeze_panes = "B3"`.

#### Fix: `generate_planting_excel()` — Bỏ `lot_id`, dùng `loai_trong` trực tiếp (`app.py`)
- **[Trước đó]**: Dùng `lot_id` (alias từ PostgREST join) + join `df_seasons` để lấy `loai_trong`.
- **[Sau]**: Bỏ `lot_id` khỏi danh sách cột. Ưu tiên `loai_trong` trực tiếp từ `base_lots` (cột đã tồn tại trong bảng), fallback sang `df_seasons` join nếu không có.

#### Cleanup: Xóa debug code, cập nhật caller sites (`app.py`)
- **[Xóa]**: Debug `st.caption` blocks (6 dòng) trong popover Cắt bắp.
- **[Update]**: Caller Admin popover + User thường → bỏ `df_des` param, gọi `generate_cut_bap_excel(df_lots, df_stg)` 2 param.

---

## [08/05/2026] - Micro-PDF Forecast Engine (Mốc ②③)

#### Refactor: Thay thế Cumulative Threshold → Micro-PDF ±7d cho dự báo từ Chích/Cắt bắp (`app.py`)
- **[Xóa]**: `threshold_boi`, `threshold_boi_ro` — không còn dùng `so_luong_trong` làm ngưỡng tích lũy.
- **[Thêm]**: Constants `MICRO_WINDOW_HALF=7`, `MICRO_SIGMA=3.0` — spread ±7d Normal Distribution (fixed).
- **[Logic mới]**: Mỗi record chích/cắt bắp → shift +84d/+70d → spread ±7d Normal Distribution → gộp tất cả mini-PDFs → xác định phase bằng diện tích tích lũy 10/80/10.
- **[Boundary-day splitting]**: Ngày ranh giới bói/rộ và rộ/vét được chia chính xác thành 2 phần để đảm bảo tỷ lệ đúng 10.0/80.0/10.0%.
- **[Rounding]**: Largest Remainder Method áp dụng cho cả 3 mốc (trước đây chỉ Mốc ①).
- **[Test]**: 11/11 test cases passed — uniform, skewed, bimodal, destruction, custom ratios, small/large quantities.

---

## [08/05/2026] - Ribbon Schedule Centralization (Chuẩn hóa Màu dây)

#### Schema Migration: Xóa cột `mau_day` từ 3 bảng, tập trung vào `ribbon_schedule` (DB, `app.py`)
- **[DB DDL]**: DROP COLUMN `mau_day` từ `stage_logs`, `destruction_logs`, `harvest_logs`. Cột chỉ còn tồn tại ở `size_measure_logs`.
- **[Nguồn dữ liệu mới]**: Bảng `ribbon_schedule` (`farm_id`, `year`, `week_number`, `color_name`) là **single source of truth** cho màu dây. Mỗi farm × tuần = 1 màu dây duy nhất.
- **[Lý do]**: Màu dây là thuộc tính cấp (farm, tuần), không phải cấp record. Lưu per-record tạo dư thừa và nguy cơ mâu thuẫn.

#### Refactor: FIFO Strategy 3 — "Trước thu hoạch" (`app.py`)
- **[Trước đó]**: Query `stage_logs.mau_day` và `destruction_logs.mau_day` (đã xóa) → crash.
- **[Sau]**: Resolve `farm_id` từ `dim_lo_id` → query `ribbon_schedule` cho tất cả tuần khớp màu dây → match `stage_logs.tuan` → FIFO allocation.
- **[Impact]**: Logic phân bổ không đổi, chỉ thay nguồn dữ liệu màu dây.

#### Refactor: Forecast Engine — Mốc ③ Pro-rata mau_day (`app.py`)
- **[Trước đó]**: `d_row.get("mau_day")` và `s_row.get("mau_day")` trả về `None` (silent failure, mất tất cả pro-rata).
- **[Sau]**: Pre-compute `_ribbon_lookup = {(year, week): color}` từ `ribbon_schedule`. Helper `_resolve_ribbon_color(row)` resolve từ `tuan` + date year.
- **[Impact]**: Pro-rata phân bổ xuất hủy theo màu dây ở Mốc ③ hoạt động chính xác trở lại.

#### Refactor: Excel Export — Week-color mapping (`app.py`)
- **[Trước đó]**: Trích `mau_day` từ `df_cut_yr["mau_day"]` (đã xóa) → mất màu header.
- **[Sau]**: Query `ribbon_schedule` trực tiếp cho farm và năm.

#### Refactor: UI Display — Bỏ cột `mau_day` khỏi render (`app.py`)
- **[Mô tả]**: Loại `mau_day` khỏi danh sách cột hiển thị `render_team_dataframe()` cho `stage_logs` và `destruction_logs`.

#### Docs: Cập nhật toàn bộ tài liệu
- **[schema.md]**: Xóa `mau_day` từ schema `stage_logs`, `destruction_logs`, `harvest_logs`. Thêm bảng `ribbon_schedule`.
- **[business_logic.md]**: Cập nhật §3.3, §3.4, §4.5 dùng `ribbon_schedule`. Thêm §4.6 Ribbon Schedule architecture.
- **[codebase_summary.md]**: Thêm `mau_day` param cho `allocate_fifo_quantity`, mô tả `_resolve_ribbon_color`.

## [06/05/2026] - Tooltip Diện Tích Lô/Trồng, Sort Fix, Data Correction

#### Feature: Tách tooltip "Diện tích" thành "Diện tích lô" + "Diện tích trồng" (`app.py`)
- **[Trước đó]**: Tooltip bản đồ chỉ hiện 1 dòng "Diện tích" lấy từ `base_lots.dien_tich` (NULL nếu lô chưa trồng).
- **[Sau]**: 2 dòng riêng biệt:
  - **Diện tích lô**: từ `dim_lo.area_ha` — luôn có, kể cả lô chưa trồng (VD: Lô 10).
  - **Diện tích trồng**: tổng `base_lots.dien_tich_trong` — chỉ có khi lô đã trồng.
- **[Data source]**: Query `dim_lo` riêng cho tất cả lô active Farm 157 → `_dim_lo_area_map`.
- **[Backfill]**: Lô có polygon nhưng chưa có `base_lots` (VD: Lô 10) giờ được thêm vào `lot_info_map` với `area_ha` từ `dim_lo`.
- **[SVG]**: Data attributes đổi từ `data-dt` → `data-area-ha` + `data-dt-trong`.

#### Fix: Sort "Thời gian vụ" theo ngày thực tế thay vì string (`app.py`)
- **[Root Cause]**: Cột "Thời gian vụ" = `"DD/MM/YYYY - Hiện tại"`. Sort cũ cố parse float → thất bại → fallback string sort. String sort theo ký tự đầu (DD) → `"06/12"` < `"08/11"` = tháng 12 xếp trước tháng 11.
- **[Fix]**: Thêm trường ẩn `_sort_start_date` (pd.Timestamp) vào mỗi row. Khi sort theo "Thời gian vụ", dùng `_sort_start_date` thay vì string → sort chronological.
- **[Cleanup]**: `_sort_start_date` được pop ra trước khi render DataFrame.

#### Fix: Tổng số cây chỉ cộng F0, không tính trùng F1/F2 (`app.py`)
- **[Root Cause]**: Lô có nhiều vụ (F0 + F1), tổng số cây cộng cả F0 lẫn F1 → phình to. Nhưng F1 mọc từ cùng gốc F0.
- **[Fix]**: `total_cay = sum(b["so_cay"] for b in batches if b["vu"] == "F0")`.

#### Fix: Tổng DT lô tính từ tất cả lô active (`app.py`)
- **[Trước đó]**: Chỉ cộng area_ha của lô có polygon → 58.63 ha.
- **[Sau]**: Query tất cả lô `is_active=True` trong `dim_lo` → 125.83 ha.

#### Fix: Filter inactive lots (lô 11) (`app.py`)
- **[Mô tả]**: Thêm `.eq("dim_lo.is_active", True)` vào tất cả query `fetch_table_data()`.
- **[Impact]**: Lô 11 (trùng 11A + 11B) bị loại khỏi mọi aggregation.

#### Data Correction (Supabase)
- **[Hard delete]**: `base_lots` ID 24 (3B, test data, 200 cây) — đã soft-delete trước đó.
- **[Update]**: `base_lots` ID 25 (3B đợt 1): `dien_tich_trong` 0.96 → **0.88 ha** (tổng 3 đợt = 4.42 ha = area_ha).
- **[Move lot]**: `base_lots` ID 17 + `seasons` ID 17: `dim_lo_id` 43 (8B) → **98 (8C)**. Record này thuộc lô 8C, không phải 8B.
- **[Kiểm tra]**: Sau sửa, không còn lô nào có tổng `dien_tich_trong` > `area_ha`.

## [05/05/2026] - Shift-based Forecast cho Mốc ②③ (Chích/Cắt bắp)

#### Refactor: Chuyển Mốc ②③ từ Normal Distribution → Shift-based (`app.py`)
- **[Trước đó]**: Mốc ② (Chích bắp) và ③ (Cắt bắp) dùng Normal Distribution PDF weights giống Mốc ①. Tổng chích/cắt bắp × (1 - 5% hao hụt) × weight → phân bổ theo đường cong lý thuyết.
- **[Sau]**: Dùng dữ liệu chích/cắt bắp **thực tế theo ngày** từ `stage_logs`, shift ngày chích +84d (`DAYS_CHICH_TO_THU`) / cắt +70d (`DAYS_CAT_TO_THU`) → ra ngày thu hoạch dự kiến.
- **[Phase Classification]**: Xác định Bói/Rộ/Vét bằng **tích lũy %** so với `base_lots.so_luong` (10/80/10 mặc định). Tách record khi vượt ranh giới phase (while loop).
- **[Bỏ hao hụt ước tính]**: Loại bỏ `LOSS_RATE_TO_CHICH = 0.05` khỏi Mốc ②③. Dùng qty trực tiếp — xuất hủy thực tế đã tính riêng qua `destruction_logs`.
- **[Constants]**: Thêm `DAYS_CHICH_TO_THU = 84`, `DAYS_CAT_TO_THU = 70`.
- **[Mốc ① (Trồng)]**: Giữ nguyên Normal Distribution, không ảnh hưởng.
- **[Aggregation]**: Shift data đã là integer → bỏ Largest Remainder rounding cho Mốc ②③.
- **[Docs]**: Cập nhật `business_logic.md` §3.3.
- **[Edge Cases Tested]**: Nhiều đợt trồng (3B Farm 157: 2 batches), chích >90% (có Thu vét), 1 record duy nhất, boundary split.

#### Fix: Map Farm 157 bị overlap lên section bên dưới trên màn hình lớn (`app.py`)
- **[Root Cause]**: JS `ResizeObserver` + `window.frameElement.style.height` có thể **giảm** iframe height sau khi SVG responsive co lại → iframe nhỏ hơn nội dung → tràn đè lên section phía dưới.
- **[Fix]**: Thay JS resize cũ bằng **grow-only** observer (chỉ tăng, không bao giờ giảm). Tăng fallback height từ `1400px` → `2400px` content width assumption (~1410px iframe) để cover ultrawide screens.

#### Fix: Bỏ làm tròn diện tích trồng (`app.py`)
- **[Mô tả]**: Cột "DT trồng (ha)" trong Bảng chi tiết lô hiển thị 2 chữ số thập phân (`:.2f`).
- **[Root Cause]**: Guard condition kiểm tra `c[1] != "Diện tích (ha)"` nhưng cột đã đổi tên thành `"DT trồng (ha)"` → vẫn bị `int()` cast.

#### Feature: Hiển thị số container cho tất cả 4 mốc dự báo (`app.py`)
- **[Mô tả]**: Số container (~X.X cont) giờ hiện **inline** trên dòng của từng mốc ①②③④ thay vì chỉ mốc ① ở footer.
- **[Mốc ④]**: Tính `kg_tt` chính xác theo `get_kg_per_tree(vu)` thay vì dùng `KG_PER_TREE_F0` approx.
- **[Footer]**: Bỏ dòng footer `🚛 X lô` vì thông tin cont đã nằm inline.

#### Feature: Caption giải thích 4 mốc dự báo (`app.py`)
- **[Mô tả]**: Thêm `st.caption` ngay dưới header "📅 Lịch Thu hoạch Dự kiến" giải thích ý nghĩa ①②③④ cho người dùng.

## [04/05/2026] - Sort Controls, Season Status Filter, Bỏ Màu Dây Chích Bắp

#### Feature: Filter trạng thái vụ cho Bảng chi tiết lô (`app.py`)
- **[Mô tả]**: Thêm `st.radio` horizontal ("Chưa kết thúc vụ" / "Tất cả") phía trên bảng chi tiết. Mặc định chỉ hiện lô chưa chốt vụ (`ngay_ket_thuc_thuc_te IS NULL`). Chọn "Tất cả" hiện cả lô đã thu hoạch (highlight xanh lá pastel).
- **[Key]**: `dt_season_status`. Hoạt động kết hợp với các filter Farm/Vụ/Đội/Lô hiện có.

#### Feature: Sort controls cho Bảng chi tiết lô (`app.py`)
- **[Mô tả]**: Thêm `st.selectbox` (12 cột) + `st.radio` (↑ Tăng / ↓ Giảm) để user sort bảng chi tiết theo bất kỳ trường nào.
- **[Giữ format cũ]**: Vẫn dùng HTML table (MultiIndex header, dòng TỔNG bold, highlight pastel). Sort áp dụng trên data rows trước khi render, TỔNG luôn ở cuối.
- **[Mặc định]**: "Tên lô (mặc định)" — natural sort (3B < 4A < 12A).
- **[Lựa chọn sort]**: Thời gian vụ, DT trồng, Cây đã trồng, CB/CắtB/TH/KG (Dự toán & Thực tế).

#### Feature: Bỏ yêu cầu nhập Màu dây cho Chích bắp (`app.py`, DB)
- **[UI]**: Ẩn ô "🎨 Màu dây" khi Đội BVTV nhập Chích bắp (cả form thêm mới lẫn edit dialog). Chỉ hiện cho Cắt bắp.
- **[App Logic]**: `mau_day = None` khi giai đoạn = Chích bắp. Validation chỉ bắt buộc màu dây cho Cắt bắp.
- **[DB Migration]**: `enforce_no_mau_day_for_chich_bap` — UPDATE tất cả chích bắp cũ `mau_day = NULL` + thêm CHECK constraint `chk_chich_bap_no_mau_day` (giai_doan ≠ 'Chích bắp' OR mau_day IS NULL).



#### Fix: Tooltip responsive trên mobile (`app.py`)
- **[Mô tả]**: Tooltip trên bản đồ Farm 157 bị tràn khi mở trên điện thoại (min-width 240px > viewport). Thêm CSS `@media (max-width: 600px)` để scale down toàn bộ tooltip + legend bar.
- **[CSS]**: `min-width: 150px`, `max-width: 200px`, `font-size: 11px`, title `13px`, stage badge `10px`. Legend: gap `8px`, font `10px`, dot `9px`.
- **[JS Positioning]**: Bỏ hardcoded pixel values (`300`, `310`, `490`). Dùng `tooltip.offsetWidth/Height` thực tế để tính vị trí. Clamp trong container bounds (`Math.max(4, ...)`). Pinned tooltip: `maxHeight` dynamic theo container height.

#### Fix: Map iframe height (`app.py`)
- **[Mô tả]**: Thử nghiệm `postMessage` auto-resize (`streamlit:setFrameHeight`) → không hoạt động với `components.html` (chỉ hỗ trợ Streamlit Custom Components chính thức). Revert về `height=700` cố định.
- **[Kết luận]**: `components.html` = iframe cố định, không thể auto-resize. Giữ `height=700` làm giải pháp ổn định. `st.image` hỗ trợ SVG responsive nhưng mất interactive tooltips.

#### Verification: Chích bắp Farm 157 vs Excel source
- **[Kết quả]**: Khớp 100% từng lô: 3A=2636, 3B(đợt2)=1044, 3BF(đợt1)=85, 8A=308, 8B=525. Tổng DB=4,598. 7A (827) = vụ cũ, đúng ý bỏ qua.
- **[Phát hiện]**: Dòng TỔNG trong Excel ghi 5,384 nhưng cộng 6 lô = 5,425 → Excel tính sai dòng tổng, data từng lô đúng.

## [24/04/2026] - Farm Selector Popover cho Admin/KD Download Buttons

#### Feature: Popover chọn Farm khi tải Excel (`app.py`)
- **[Mô tả]**: Admin và Phòng Kinh doanh giờ thấy popover khi click nút download — phải chọn farm trước rồi mới tải file Excel tương ứng. User thường (1 farm) giữ nguyên download trực tiếp.
- **[Trước đó]**: File download chứa data tất cả farm gộp chung, tên file là `Bao_cao_Admin_...xlsx` — không phân biệt được farm nào.
- **[Sau]**: Mỗi nút dùng `st.popover` + `st.radio` chọn farm → filter data → `st.download_button` tải file filtered. Tên file: `Bao_cao_{farm_name}_...xlsx`.
- **[Helper]**: `_filter_by_farm()` DRY filter function, `_gen_dl_link()` cho HTML download links (user thường).

## [24/04/2026] - Reset & Re-insert Chích Bắp từ Excel nguồn gốc

#### Data: Xóa toàn bộ chích bắp cũ, insert mới từ "mặt bằng chích bắp tuần 16" (`stage_logs`)
- **[Mô tả]**: Xóa 68 records chích bắp cũ (hỗn hợp vụ cũ + vụ mới, không chính xác). Insert lại 42 records từ file Excel gốc (tuần 14-16, 30/03-19/04/2026).
- **[Phân loại vụ]**: Dùng timeline `ngay_trong + 120..240 ngày` → xác định 3A, 8A fact data = vụ cũ (bỏ qua). 7A = vụ cũ (bỏ qua).
- **[3BF convention]**: 3BF = lô 3B đợt 1 (batch 25, F1), 3B = đợt 2 (batch 7, F0). Set `base_lot_id` thủ công (FIFO trigger skip khi đã set).
- **[Kết quả]**: 3A=2636 (batch 6), 3B đợt 1=85 (batch 25), 3B đợt 2=1044 (batch 7), 8A=308 (batch 14), 8B=525 (batch 15). Tổng 4,598 cây.

## [24/04/2026] - FIFO Batch Allocation cho Stage/Harvest/Destruction Logs

#### Feature: FIFO phân bổ tự động theo đợt trồng (`app.py`)
- **[Mô tả]**: `allocate_fifo_quantity()` giờ phân bổ số lượng chích bắp/cắt bắp/thu hoạch vào đúng `base_lot_id` theo thứ tự FIFO (đợt trồng cũ nhất trước).
- **[Trước đó]**: Toàn bộ số lượng gán vào 1 record duy nhất, `base_lot_id = NULL` (hoặc nhờ `resolve_base_lot_id` closest-match). Khi 1 lô có nhiều đợt trồng cùng chích bắp → không phân biệt được.
- **[Sau]**: Capacity tính per-batch: Chích = planted − used, Cắt = chích − cắt, Thu = cắt − thu. Tràn đợt cũ → overflow sang đợt mới. Insert kèm `base_lot_id`.
- **[Impact]**: Data integrity: mỗi stage_log/harvest_log/destruction_log có `base_lot_id` chính xác. Dashboard, Map, Table đều hiển thị đúng theo đợt trồng.

## [24/04/2026] - Đồng bộ logic Map & Table via compute_batch_stats()

#### Refactor: Shared `compute_batch_stats()` function (`app.py`)
- **[Mô tả]**: Extract hàm `compute_batch_stats()` dùng chung cho cả "🗺️ Bản đồ Farm 157" và "📋 Bảng chi tiết thông tin các lô (Theo Vụ)".
- **[Trước đó]**: Map dùng `_get_batch_stage()` (thiếu 2 business rules: season date range filter, F1+ no-chích safety check). Table tính inline với ~35 dòng logic riêng.
- **[Sau]**: Cả 2 sections gọi `compute_batch_stats()` — áp dụng đầy đủ 4 rules: (1) Filter stage/harvest theo season start date, (2) Harvest Growth Buffer 18w cho F1+, (3) Harvest upper bound = next_season_start + 18w, (4) F1+ chưa chích bắp → thu hoạch = 0.
- **[Impact]**: Map giờ hiển thị giai đoạn chính xác như Table (ví dụ: 3B F1 không còn hiện "Thu hoạch" sai). Giảm ~35 dòng code trùng lặp.

## [24/04/2026] - Interactive Farm 157 Map on Dashboard

#### Feature: Bản đồ tương tác Farm 157 (`app.py`)
- **[Mô tả]**: Section "🗺️ Bản đồ Farm 157" ở đầu dashboard, hiển thị 24 lô dưới dạng SVG polygon trên nền tối.
- **[Data source]**: Tọa độ từ `farm_157_polygons.json` (traced bằng `polygon_tracer.html`). Thông tin lô real-time từ DB (seasons, base_lots, stage_logs, harvest_logs).
- **[Tính năng]**: Hover hiển thị tooltip (Vụ, Ngày bắt đầu, Diện tích, Số cây, Giai đoạn, Chích/Cắt/Thu hoạch). Màu polygon theo giai đoạn: xanh lá (sinh trưởng), vàng (chích bắp), cam (cắt bắp), xanh dương (thu hoạch), xám (chưa có data).
- **[Kỹ thuật]**: `streamlit.components.v1.html()` render SVG+CSS+JS inline. Chỉ hiển thị khi user là Farm 157, Admin, hoặc Phòng KD.

#### Enhancement: Polygon Tracer hỗ trợ JPG (`polygon_tracer.html`)
- **[Fix]**: Auto-try multiple image extensions (png, jpg, jpeg) thay vì hardcode `.png`.

## [23/04/2026] - Fix Harvest F0→F1 Bleeding + Interactive Farm Map Tool

#### Bugfix: Thu hoạch F0 bị gán nhầm vào vụ F1 (`app.py`)
- **[Root Cause]**: Khi vụ F1 bắt đầu (11/01/2026) nhưng F0 vẫn đang thu hoạch (đến 02/2026), filter `harvest >= season_start` hớt lấy 772 cây thu hoạch F0 gán vào F1. Guard `so_chich_bap == 0` không chặn được vì F1 đã có 85 chích bắp.
- **[Fix]**: Thêm `HARVEST_MIN_GROWTH_WEEKS = 18` — với vụ F1+, harvest chỉ được tính nếu `ngay >= season_start + 18 tuần` (thời gian sinh trưởng tối thiểu). F0 upper bound cũng nới ra `+ 18 tuần` để không mất harvest cuối vụ.
- **[Impact]**: F1 lô 3B (base_lot_id=25): Thu hoạch 772 → 0 (đúng). F0: giữ đủ 6 lần thu hoạch.

#### Feature: Polygon Tracer Tool (`polygon_tracer.html`)
- **[Mục đích]**: Công cụ HTML vẽ polygon lên ảnh bản đồ farm để tạo tọa độ cho interactive map component.
- **[Tính năng]**: Click to trace, undo, delete, export/import JSON, drag-drop image, keyboard shortcuts.

## [22/04/2026] - Excel Reports Multi-Year + Button Styling

#### Feature: Phân chia báo cáo Excel theo năm (`app.py`)
- **[Chích bắp/Cắt bắp/Trồng mới]**: Tự động chia dữ liệu thành nhiều sheet theo năm (VD: "2025", "2026"). Sort theo tuần/ngày trong mỗi sheet.
- **[Logic]**: Năm trích từ `ngay_thuc_hien` (chích/cắt) hoặc `ngay_trong` (trồng).

#### Style: Tô màu nút tải Excel (`app.py`)
- **[Approach]**: Thay `st.download_button` bằng HTML `<a>` base64-encoded với CSS classes riêng (Streamlit không hỗ trợ custom button styling trực tiếp).
- **[Bỏ emoji]**: Xóa icon emoji khỏi text nút.
- **[Màu sắc]**: Xuất Excel (xanh dương), Chích bắp (vàng cam), Cắt bắp (đỏ nhạt), Trồng mới (xanh lá). Min-height đồng nhất.

## [20/04/2026] - Diện tích trồng thực tế (per-batch)

#### Feature: Chuyển từ `dim_lo.area_ha` → `base_lots.dien_tich_trong` (`app.py`)
- **[Detail Table]**: Cột "DT trồng (ha)" hiển thị diện tích trồng thực tế của từng đợt (không còn là diện tích tối đa của lô).
- **[Sum Logic]**: Sum trực tiếp (mỗi đợt có area riêng), bỏ dedup cũ theo tên lô.
- **[Fallback]**: Nếu `dien_tich_trong` NULL → fallback `dim_lo.area_ha` (Farm 126 chưa có data).
- **[Charts]**: Cập nhật tất cả biểu đồ (Dự toán, Thực tế, Pipeline, Timeline, Kiểm kê) dùng `dien_tich_trong`.

## [18/04/2026] - 4-Milestone Harvest Forecast (Chích bắp)

#### Feature: Thêm Mốc ② Chích bắp vào dự báo (`app.py`)
- **[Data Pipeline]**: Extract `chich_bap_records` từ `stage_logs` (giai_doan = 'Chích bắp'), match vào generation nearest-midpoint.
- **[Mốc ② Computation]**: `daily_qty_chich = so_chich_bap × 0.95 × pdf_weight`. Largest Remainder rounding đảm bảo tổng chính xác.
- **[UI Cards]**: 4 dòng: ① Trồng → ② Chích → ③ Cắt → ④ TT (thay vì 3 dòng cũ).
- **[Dialog]**: 4 metric columns (thay vì 3), bảng chi tiết 8 cột (thêm ② Chích bắp).
- **[Expander Table]**: Thêm cột ② Chích bắp giữa ① Trồng và ③ Cắt bắp.
- **[Constants]**: `LOSS_RATE_TO_CHICH = 0.05` áp dụng cho cả Chích bắp lẫn Cắt bắp.

## [18/04/2026] - Customizable Harvest Window Days

#### Feature: Tùy chỉnh số ngày thu hoạch (`app.py`)
- **[UI]**: Thêm 3 `number_input` (Thu bói ngày, Thu rộ ngày, Thu vét ngày) trong expander "Tùy chỉnh tỷ lệ phân phối thu hoạch".
- **[Logic]**: `DAYS_RO_HALF`, `WINDOW_HALF`, `WINDOW_HALF_RIGHT`, `SIGMA` tính động từ input user thay vì hardcode.
- **[Asymmetric]**: Hỗ trợ window bất đối xứng (Thu bói ≠ Thu vét), `day_offsets` tạo từ `[-WINDOW_HALF .. +WINDOW_HALF_RIGHT]`.
- **[Mặc định]**: 14/26/14 ngày (tổng 54 ngày), giữ nguyên hiển thị như cũ nếu không chỉnh.
- **[DB]**: Cập nhật `area_ha` cho D6 (2.50).

## [17/04/2026] - 3-Milestone Harvest Forecast

#### Bugfix: Thu hoạch thực tế (Mốc ③) bị nhân bản qua các tháng (`app.py`)
- **[Root Cause]**: `harvest_logs` là dữ liệu nhập hàng ngày, nhưng code cũ gộp tổng cả vụ rồi gán cùng 1 số cho mọi tháng.
- **[Fix]**: Match từng record `harvest_logs` vào đúng (generation, phase, tháng) dựa trên `ngay_thu_hoach` → closest midpoint → phase (Thu bói/rộ/vét) → group by `(base_lot_id, vu, loai_thu, thang)`.
- **[Lưu midpoints]**: Thêm dict `lot_gen_midpoints` để tra cứu midpoint sau khi tạo daily rows.

#### Bugfix: Dòng TỔNG sum diện tích trùng khi lô có nhiều đợt trồng (`app.py`)
- **[Root Cause]**: Lô 3B có 3 đợt trồng → 3 dòng × 4.50 ha = TỔNG hiện 13.50 ha thay vì 4.50 ha.
- **[Fix]**: Strip suffix `(đợt N)` để lấy base lot name, rồi `drop_duplicates` trước khi sum diện tích.
- **[DB]**: Cập nhật `area_ha` cho 2B (3.58), 8A (3.55), A8 (2.20).

#### Feature: Ba Mốc Dự báo trên Thẻ Thu hoạch (`app.py`)
- **[Mốc ① Từ Trồng]**: Dự báo từ `base_lots.so_luong` − xuất hủy thực tế × (1 − hao hụt 10%). Trừ destruction trực tiếp hoặc phân bổ tỉ lệ (proportional allocation).
- **[Mốc ② Từ Cắt bắp]**: Dự báo từ `stage_logs` (Cắt bắp). Hiển thị "Chưa có TT" nếu chưa có data.
- **[Mốc ③ Thực tế]**: Số buồng thực tế từ `harvest_logs`. Hiển thị "Chưa có TT" nếu chưa chốt.
- **[Card UI]**: Mỗi thẻ tháng hiển thị 3 hàng (①②③), min-height 180px.
- **[Dialog]**: `st.metric` 3 cột + bảng 7 cột (Lô, Vụ, Loại thu, ①, ②, ③, Khoảng TG).
- **[Bảng tổng hợp]**: 10 cột bao gồm Trồng, Xuất hủy, ① ② ③.
- **[Bảng chi tiết lô]**: Thêm dòng "TỔNG" ở cuối mỗi bảng chi tiết lô (theo Vụ), tính tổng Diện tích, số lượng cây, và các mốc dự toán/thực tế.
- **[Formatting]**: Định dạng số có dấu phẩy (thousand separator) cho các con số trong bảng chi tiết lô.

#### Logic: Phân bổ Xuất hủy theo Tỉ lệ (`app.py`)
- **[Direct]**: `destruction_logs` có `base_lot_id` → trừ trực tiếp.
- **[Proportional]**: Chỉ có `dim_lo_id` (lô nhiều đợt) → phân bổ: `hủy × (batch/tổng_lô)`.
- **[Docs]**: Cập nhật `business_logic.md` §3.3 + §3.4.

## [15/04/2026] - Custom Harvest Phase Percentages & Chích Bắp Data

#### Feature: Tùy chỉnh tỷ lệ Thu bói / Thu rộ / Thu vét (`app.py`)
- **[Custom Ratios]**: Người xem có thể tùy chỉnh tỷ lệ phân phối thu hoạch (mặc định 10/80/10%). Thay đổi realtime, validation tổng = 100%.
- **[Rescale Logic]**: Giữ nguyên cửa sổ 55 ngày (14/26/14 ngày) cố định theo chu kỳ sinh trưởng. Chỉ rescale trọng số PDF Normal Distribution cho mỗi phase khớp tỷ lệ % mong muốn.
- **[Stage Logs Insert]**: Insert 7 records chích bắp đợt mới (3A đợt #6, 3B đợt #7, 8B đợt #15) vào `stage_logs` từ dữ liệu `fact_nhat_ky_san_xuat` đã validate.

#### Feature: Tách Trồng dặm khỏi Trồng mới (`app.py`)
- **[Forecast Filter]**: Trồng dặm không còn tạo chu kỳ F0→F3 riêng trong Lịch thu hoạch dự kiến. Chỉ trồng mới mới được forecast.
- **[Detail Table Filter]**: Bảng chi tiết chỉ hiển thị đợt Trồng mới. Trồng dặm hiện ở bảng riêng.
- **[Trồng dặm Table]**: Thêm bảng "📋 Lịch sử Trồng dặm" (expander) bên dưới bảng chi tiết, hiển thị chi tiết từng đợt + tổng hợp theo lô.

#### Schema Migration: `add_loai_trong_to_base_lots`
- **[DB]**: Thêm cột `loai_trong` (text, NOT NULL, default "Trồng mới") vào `base_lots`. Copy data từ `seasons.loai_trong` qua `base_lot_id`.
- **[Code]**: Loại bỏ logic merge `seasons → base_lots` trong `app.py`. Đọc `loai_trong` trực tiếp từ `base_lots`.
- **[Hotfix]**: Xử lý triệt để lỗi `KeyError: 'loai_trong'` trên UI Dashboard (Tab Global Data > Phễu tiến độ & Biểu đồ Multi-line) do sót lại khai báo `pd.merge(... df_seasons)` cũ gây xung đột cột tự sinh (`loai_trong_x`, `loai_trong_y`).
- **[Insert Flow]**: Khi tạo lô mới, `loai_trong` được set đồng thời trên cả `base_lots` và `seasons` (backward compat).
- **[Lý do]**: `loai_trong` là thuộc tính đợt trồng (không thay đổi giữa F0→Fn), thuộc về `base_lots` chứ không phải `seasons`. Loại bỏ unnecessary join.

## [15/04/2026] - ETL Bug Fix & Chích Bắp Analysis

#### Data Investigation (Supabase MCP)
- **[ETL Bug — Chích Bắp `lo_id = NULL`]**: Phát hiện 575/576 records "Chích Bắp" Farm 157 bị mất `lo_id`. Root cause: ETL ưu tiên cột "Lô 2" (tên nhóm đội) thay vì cột "Lô" (lô thực). Đã viết bug report chi tiết cho workspace ETL → **đã fix** (87% coverage, 87 records NULL = GSheet trống).
- **[Cross-mapping Chích Bắp × Base Lots]**: Phân tích timeline so sánh expected window chích bắp (5-7 tháng sau trồng) với dữ liệu thực tế. Kết luận: dữ liệu chích hiện tại (09/2025 - 03/2026) thuộc vụ cũ, chưa thuộc đợt trồng mới. Các lô không có `base_lot` = lô cũ, không ảnh hưởng dự báo.

## [Version 26.1 - RBAC Kinh doanh Role] - 2026-04-14

#### Security & RBAC (`app.py`, Supabase)
- **[Quyền truy cập mở rộng]**: Thiết lập thêm role "Phòng Kinh doanh" (team "Kinh doanh").
- **[Dashboard chuyên biệt]**: Cho phép tài khoản này truy cập màn hình dữ liệu toàn cục giống như Admin nhưng không sở hữu các quyền chỉnh sửa trực tiếp thông tin farm.
- **[Bug Fix]**:
  - Khắc phục lỗi hiển thị 0 số lượng cây trồng cho các Season Fn (không phải F0) do date range filter. Điều hướng property "cây đã trồng" thành hằng số từ base_lot.
  - Fix logic overlap window đối với thời gian harvest season khi F0 vượt quá ngày kết thúc hành chính.

#### Tính năng mới (`app.py`)
- **[Container Count]**: Thêm hiển thị số container dự kiến trên Lịch Thu hoạch. Công thức: `số thùng / 1320 = số container`. Hiển thị tại 2 vị trí:
  1. Thẻ card tổng hợp hàng tháng (🚛 ~X.X cont).
  2. Dialog chi tiết khi click vào từng tháng.

#### Refactoring (`app.py`)
- **[Clean-up KG_PER_TREE]**: Gộp 3 hằng số phân tán (`KG_PER_TREE_DETAIL`, `KG_PER_TREE`, `KG_PER_TREE_CHART`) thành 1 bộ constants trung tâm + helper function `get_kg_per_tree(vu)`. Logic mới: **F0 = 15 kg/buồng**, **Fn = 18 kg/buồng**.
- **[Magic Numbers]**: Gom `13 kg/thùng` → `KG_PER_BOX`, `1320 thùng/container` → `BOXES_PER_CONTAINER`.
- **[Loss Rates]**: Gom `LOSS_RATE = 0.10` local thành bộ constants trung tâm: `LOSS_RATE_TO_CHICH = 0.05` (5% từ trồng→chích) + `LOSS_RATE_TO_THU = 0.10` (10% tổng). Helper: `get_estimated_rate(stage)`.
- **[Detail Table Fix]**: Áp dụng hao hụt vào cột Dự toán (Chích bắp: 95%, Cắt bắp: 95%, Thu hoạch: 90%) thay vì hiển thị 100% cho tất cả.
- **[Caption]**: Thêm dòng ghi chú tỉ lệ hao hụt ngay dưới tiêu đề bảng chi tiết lô.
- **[Filter DRY]**: Extract `render_chart_filters()` + `get_filtered_dfs()` helpers, thay thế 6 filter blocks lặp lại → giảm ~160 dòng code trùng.
- **[Estimation Consistency]**: Đồng bộ rounding method (`int(round())`) giữa Bảng chi tiết, Lịch thu hoạch, và Dự toán sản lượng. Áp dụng loss rate 10% vào section ⚖️ Dự toán Sản lượng.

## [Version 26.0 - Harvest Forecast 3 Phases] - 2026-04-13

#### UI/CSS (`app.py`)
- **[Fix padding]**: Inject CSS loại bỏ khoảng trắng mặc định ở đầu trang Streamlit (ẩn `stHeader`, giảm `padding-top` container).

#### Tính năng mới: Lịch Thu hoạch Dự kiến (`app.py`)
- **[3 đợt thu]**: Phân tách thu hoạch thành Thu bói (10%) → Thu rộ (80%) → Thu vét (10%):
  - Mốc: `harvest_midpoint` (F0: +264d, Fn: +174d)
  - Thu rộ: ±13 ngày quanh mốc (26 ngày). Thu bói: 14 ngày trước. Thu vét: 14 ngày sau.
  - Tổng cửa sổ: 54 ngày/vụ. Hao hụt 10%/vụ (không kép).
- **[Filter Năm]**: Thêm selectbox lọc theo năm (default: năm hiện tại).
- **[Popover chi tiết]**: Click "🔍 Xem chi tiết" dưới mỗi thẻ tháng → hiện bảng breakdown: Lô, Vụ, Loại thu, Số buồng, Khoảng thời gian.

## [2026-04-09]
## [Version 25.0 - Auto Batch Mapping] - 2026-04-09

#### Database Migration
- **[DDL]**: Thêm cột `base_lot_id` (FK → base_lots.id) vào 4 bảng: `seasons`, `stage_logs`, `harvest_logs`, `destruction_logs`. Mục đích: liên kết trực tiếp từng record với đợt trồng cụ thể.

#### Logic nghiệp vụ (`app.py`)
- **[Auto-resolve base_lot_id]**: Triển khai hàm `resolve_base_lot_id()` sử dụng thuật toán closest-match dựa trên timeline sinh trưởng chuối:
  - F0: 180d (Chích bắp) → 194d (Cắt bắp) → 264d (Thu hoạch) tính từ ngày trồng.
  - Fn: +90d (Chích bắp) → +104d (Cắt bắp) → +174d (Thu hoạch) tính từ harvest F(n-1).
  - Destruction logs: map giai đoạn xuất hủy → stage tương ứng để dùng timeline matching.
- **[insert_to_db()]**: Tự động gọi `resolve_base_lot_id()` khi insert stage_logs, harvest_logs, destruction_logs.
- **[Edit dialogs]**: Thêm `base_lot_id` auto-resolved vào data dict khi update 3 loại log (stage, destruction, harvest).

#### Backfill dữ liệu
- **[backfill_base_lot_id.py]**: Script backfill 65 records hiện có. Kết quả verified: 100% chính xác (0 NULL trừ 4 seasons của lô chưa trồng).

## [2026-04-06]
## [Version 24.3 - Refactoring & Fix UI] - 2026-04-06

#### Refactor (`app.py`)
- **[Fix UI/Data Formatter]**: Sửa lỗi giao diện hiển thị bảng "Toàn bộ thông tin vụ". Thay đổi `st.dataframe` sang render bằng `st.markdown` với chuỗi `df.to_html()`. Xử lý đồng thời 2 lỗi: 
  1. Header (`Thông tin`, `Cắt bắp`...) bị căn trái (Do Streamlit sử dụng Glide Data Grid không hỗ trợ nhận HTML css text-align từ Styler).
  2. Trường `Diện tích` dù đã ép kiểu String Formatter `f-str` nhưng vẫn bị Streamlit Arrow backend ép ngược lại thành Object numbers (hiển thị 6 chữ số 0 dư).
- **[Logic Code]**: Loại bỏ phương thức `.drop()` của Pandas (tránh các warning khi gọi trên MultiIndex DataFrame) khi truy xuất dữ liệu danh sách `detail_rows`. Chuyển sang thu thập dictionary collection độc lập từng trường theo `{"Vụ" : rows_dict_list}`, tối ưu memory mapping.
- **[Layout Table]**: Áp dụng Styler `set_properties(**{'text-align': 'center'})` và ép f-string formatting `f"{dien_tich:.2f}"` ở phần tử diện tích để chốt cứng display UI. Mặc dù mất ưu thế Sortable by values của `st.dataframe()`, bù lại đem về thẩm mỹ tối ưu cho Dashboard.
