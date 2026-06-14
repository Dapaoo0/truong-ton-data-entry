# Codebase Summary

Tài liệu cung cấp tóm tắt chi tiết cấu trúc các file, framework và chức năng logic chính cho hệ thống phân tích dữ liệu và ghi nhận nông vụ Banana Tracker.

## Môi trường & Framework
- Lõi ứng dụng được phát triển bằng **Streamlit** (giao diện Python).
- Giao tiếp Cơ sở dữ liệu và Xác thực qua Client API của **Supabase** (PostgreSQL backend).
- Pipeline Xử lý Dữ liệu với **Pandas** để tổng hợp, chuyển đổi và vẽ biểu đồ.

## Thành phần Chính

### 1. Ứng dụng Bảng Điều Khiển (Streamlit App)
- **`app.py` (Dashboard cốt lõi)**: 
  Đây là Gateway kiêm Controller cho giao diện Farm. Các hàm chính bao gồm:
  - `apply_filters_local()`: Cơ chế siêu lọc trên raw pandas Dataframe tải trực tiếp từ DB. Cải thiện hiệu suất, giúp biểu đồ phản hồi lập tức mà không phải query SQL lại từ đầu.
  - `get_dynamic_lot_options()`: Hàm util cập nhật tự động các lựa chọn dropdown tuỳ theo các cấp độ Đội/Lô khả dụng.
  - `get_nt_tab_options()`: Nguồn menu vận hành cho NT1/NT2/BVTV. UI không expose form `Khởi tạo Lô trồng` và `Kiểm tra Fusarium`; hai loại dữ liệu này được nhập trực tiếp ở database nhưng backend/schema cũ vẫn được giữ để đọc lịch sử.
  - Phân quyền (Authentication): Quản lý đăng nhập, session_state và RBAC (trích từ bảng `user_roles`). Đặc biệt hỗ trợ các Account quản trị như "Admin" và "Phòng Kinh doanh" để có Data Dashboard riêng biệt.
  - `allocate_fifo_quantity(farm_name, lo_name, new_sl, log_type, target_date, action_type, giai_doan, mau_day)`: Phân bổ FIFO theo `ngay_trong`. Query tất cả base_lots active, tính capacity per-batch, split allocations. Trả về list `[{dim_lo_id, base_lot_id, so_luong, lot_id}]`. **Hai chế độ**: (1) User chỉ định `base_lot_id` → trigger skip FIFO, (2) Không chỉ định → FIFO mặc định. Destruction delegate sang `allocate_destruction_fifo()` với 3 chiến lược theo giai_doan.
  - `render_global_data_tab()`: Module vẽ dữ liệu toàn cầu. Aggregate dữ liệu thống kê tổng hợp (tổng cây, lượng chích/cắt, lượng thu hoạch). Đặc biệt hỗ trợ chia bảng phân rã chi tiết (Expander) theo từng mùa cụ thể (vu = F0, F1).
  - `generate_destruction_excel()`: Tạo báo cáo Xuất hủy read-only riêng. Sheet `Theo lô` dùng bố cục ngang theo tuần/ngày, có tổng tuần và lũy kế; sheet `Chi tiết` giữ ngày, giai đoạn, số lượng và lý do của từng record. UI tải tách theo farm cho cả account farm và account đa farm.
  - `render_container_allocation_calculator()`: Page Kinh doanh "Máy tính phân bổ cont". Có 3 mode: `Tính số hàng từ số buồng`, `Tính số cont tối đa từ số buồng`, `Tính số buồng từ số cont`. Kết quả trung tâm là `Buồng xẻ tối thiểu`, tức số buồng nguyên ít nhất cần mở để đáp ứng đơn hàng/cont theo ưu tiên. Kế hoạch đã bấm lưu được persist ở bảng `container_allocation_plans` theo account đăng nhập.
  - `render_cost_dashboard()` (`cost_dashboard.py`): Page/tab read-only `Chi phí` dùng chung cho mọi account. Dashboard đọc raw `fact_nhat_ky_san_xuat.thanh_tien` + `fact_vat_tu.thanh_tien` qua Supabase REST client hiện tại, join dim bằng pandas, cache 5 phút và scope farm theo account. Admin/Kinh doanh xem được nhiều farm; account farm/đội chỉ xem farm đang đăng nhập. Đây là dashboard tổng chi phí raw, tách biệt với popup `chi phí/cây` đã clean theo lifecycle trên bản đồ.
  - `build_next_season_maps()` và `build_batch_label_map()`: Helper shared cho boundary vụ kế tiếp và label đợt trồng; Map/Chart/Table dùng cùng một nguồn để tránh lệch logic F0/F1.
  - `compute_batch_stats(lo_name, base_lot_id, vu, season_start, season_end, next_season_start, next_vu_producing)`: **Hàm shared** dùng chung cho Map & Table. Áp dụng 4 business rules: (1) Season date range filter, (2) Harvest Growth Buffer 18w (F1+), (3) Next-season upper bound, (4) F1+ no-chích safety. Returns `(giai_doan, so_chich, so_cat, so_thu)`.
  - `render_chart_filters(prefix, include_date, use_dynamic_lots)`: Bộ lọc DRY chuẩn (Farm/Vụ/Đội/Lô/Date) dùng chung cho 6/7 chart sections. Harvest Schedule dùng filter Year/Month riêng.
  - Styling với `pandas.Styler`: tinh chỉnh CSS và bố cục.
  
  **Luồng dữ liệu chính (Data Flow):**
  - `df_lots_all` ← `fetch_table_data("base_lots")` — toàn bộ đợt trồng (cả trồng mới + trồng dặm). `loai_trong` nằm trực tiếp trong cột `base_lots` (không cần join `seasons`).
  - `df_lots_trong_moi` ← chỉ giữ `loai_trong == "Trồng mới"` → dùng cho **Bảng chi tiết**, **Lịch thu hoạch**, **batch_label_map**.
  - `batch_label_map` ← build bằng `build_batch_label_map(df_lots_trong_moi)`. Lô nhiều đợt → `"3B (đợt 1)"`, lô 1 đợt → `"3B"`. **Shared** giữa Map tooltip và Bảng chi tiết (DRY). Map tooltip hiển thị `"Đợt X (FY)"` cho multi-batch, `"FY"` cho single-batch.
  - **Excel import caveat**: một số file vận hành dùng label ngoài hệ DB để phân biệt đợt, ví dụ Farm 157 `3B` = 3B đợt 2/F0 (`base_lot_id=7`) còn `3BF` = 3B đợt 1/F1 (`base_lot_id=25`). Khi kiểm tra/import phải lấy `base_lot_id` làm khóa, không chỉ dùng `lo_name`.
  - **Seasons join caveat**: `base_lot_id` có thể có nhiều dòng `seasons` (F0/F1/...). Join log với `seasons` theo `base_lot_id` mà không lọc `vu` hoặc dedupe theo id log sẽ nhân đôi số lượng.
  - `df_lots_trong_dam` ← chỉ giữ `loai_trong == "Trồng dặm"` → hiển thị riêng ở **📋 Lịch sử Trồng dặm** (expander).
  
  **Mô hình Dự báo Thu hoạch (Harvest Forecast — 4 Mốc, Dual-Model):**
  - **Mốc ① (Từ Trồng)**: Normal Distribution truncated: cửa sổ cố định 55 ngày = Thu bói (14d) + Thu rộ (26d) + Thu vét (14d). Rescale PDF weights theo tỷ lệ custom (mặc định 10/80/10).
  - **Mốc ②③ (Chích/Cắt bắp — Micro-PDF)**: Dùng dữ liệu thực tế theo ngày từ `stage_logs`. Mỗi record → shift +84d/+70d → spread ±7d Normal Distribution (σ=3, fixed) → gộp tất cả mini-PDFs thành harvest curve → phase xác định bằng diện tích tích lũy 10/80/10 với boundary-day splitting. Không trừ hao hụt ước tính.
  - **Mốc ④ (Thực tế)**: `harvest_logs` match vào (generation, phase, tháng).
  - Chỉ iterate `df_lots_trong_moi` (trồng dặm bị loại khỏi forecast).
  - **Phân bổ Xuất hủy**: Direct (có `base_lot_id`) hoặc Proportional (`hủy × batch/tổng_lô`).
  - **Ribbon Schedule**: Màu dây resolve từ `ribbon_schedule` qua `_resolve_ribbon_color(row)` — pre-computed `_ribbon_lookup` dict `{(year, week): color}`. `harvest_logs` lưu riêng `mau_day` ở cấp record để chia thu hoạch thực tế theo màu dây.
  - **Helper `_build_shift_rows()`**: Nested function Micro-PDF cho chích/cắt bắp. 3 bước: (1) Spread ±7d mỗi record qua `micro_weights` (norm.pdf σ=3), (2) Aggregate daily harvest curve, (3) Phase assignment bằng cumulative area + boundary-day splitting (đảm bảo đúng tỷ lệ). Destruction deduction: Pro-rata mau_day (Mốc ③) hoặc Aggregate Ratio (Mốc ②). Largest Remainder rounding cho float→int.

  **Excel Export Functions:**
  - `generate_cut_bap_excel(df_lots, df_stg, df_des, df_har)`: Báo cáo Cắt bắp + Xuất hủy + Thu hoạch thực tế theo màu dây, chia sheet theo năm. **4-row header**: Row 1 = Dự báo tuần thu hoạch theo farm (`Farm 126 = +8`, `Farm 157 = +9`, farm khác fallback `+8/+9`), Row 2 = Tuần X, Row 3 = CẮT BẮP/XUẤT HỦY/Thu hoạch/Tồn trên lô, Row 4 = màu dây (từ `ribbon_schedule`). Trên UI Admin/Phòng Kinh doanh, báo cáo Cắt bắp tải tách biệt theo farm qua popover chọn farm; hàm vẫn hỗ trợ input nhiều farm và thêm cột `Farm` nếu được gọi trực tiếp với nhiều farm. Cột Lũy kế cuối bảng. `data_start_row = 5`, `freeze_panes = "B5"` hoặc `"C5"` khi có cột Farm. Type-safe: `tuan` + `_year` cast `int`. Lot matching by `base_lot_id`; fallback theo `farm + lo`. Harvest matching by `harvest_logs.mau_day` trong đúng farm với offset riêng của farm. `destruction_logs.giai_doan == "Sau thu hoạch"` vẫn cộng vào XUẤT HỦY nhưng trừ khỏi Thu hoạch ròng để không làm âm tồn/lặp trừ sau khi màu dây đã thu. Dòng `Dự kiến thu hoạch` nằm dưới `Tổng`, điền cột Thu hoạch bằng `round(Tổng CẮT BẮP × 97%)`.
  - `generate_harvest_forecast_excel(df_lots, df_stg)`: Báo cáo Dự báo Thu hoạch riêng từ dữ liệu Cắt bắp. Farm 126 dùng `+8` tuần inclusive, Farm 157 dùng `+9`; số lượng dự báo là `round(Số cắt bắp × 97%)`. Workbook có sheet `Tổng hợp` dạng ngang, mỗi tuần thu hoạch dự báo là một cột: dòng tổng gom toàn bộ farm/màu dây, dòng nguồn ghi `Farm - màu: số cây`; sheet `Chi tiết nguồn` truy ngược farm/tuần cắt/màu dây/lô, không phơi cột kỹ thuật `base_lot`. UI Admin/Phòng Kinh doanh tải một file gộp tất cả farm; account farm tải theo scope hiện tại.
  - `generate_chich_bap_excel(df_lots, df_stg)`: Báo cáo Chích bắp. Natural sort, date-based grouping.
  - `generate_planting_excel(df_lots, df_seasons)`: Báo cáo Trồng mới. Ưu tiên `loai_trong` trực tiếp từ `base_lots`, fallback `df_seasons` join.

- **`container_allocation.py` (Optimizer phân bổ container)**:
  - Chứa cấu hình quy cách mã hàng theo profile: 12 nải dùng `27CP Nhật 1-5`, `30CP Nhật 1-9`, `6H Nhật 5-7`, `5H Nhật 8-10`, `8H Hàn 1-4`, `5/6H Hàn 5-9`, `15CP/12CP/10CP Hàn 10-12`; 9 nải dùng mapping suy luận theo vùng tương đối, trong đó `15CP/12CP/10CP Hàn` dùng vùng mẹ `6-9`.
  - Chứa profile khối lượng nải gốc 12 nải (`28.4kg`) và 9 nải (`19.0kg`); app scale profile về kịch bản `12 nải - 18/20kg` hoặc `9 nải - 15.6kg` rồi cộng kg từng nải trong dải cắt.
  - Các khoảng là khoảng mẹ; helper `_valid_optimizer_ranges()` sinh mọi khoảng con liền kề.
  - `allocate_bunches_optimized()` dùng OR-Tools CP-SAT khi khả dụng. Objective lexicographic: giảm thiếu thùng theo `customer_priority` khi có, fallback `market_priority` → giảm `active_bunches_estimated` (số buồng nguyên cần xẻ) → giảm số segment → giảm kg tiêu thụ → giảm kg dư. Một dòng đơn hàng có thể bẻ thành nhiều khoảng con nếu điều đó cải thiện thiếu hàng hoặc giảm buồng xẻ, nhưng segment penalty ngăn bẻ vụn không cần thiết.
  - `calculate_min_bunches_for_container_plan()` là mode tính ngược từ cơ cấu cont sang số buồng xẻ tối thiểu; demand là hard constraint. Mode này ưu tiên OR-Tools linear MIP (`SCIP/CBC`) ở cấp vị trí nải để chứng minh exact số buồng nguyên tối thiểu, rồi ghép lại thành các dải nải liền kề để hiển thị. Chỉ `OPTIMAL` mới được xem là kết quả hợp lệ cho số buồng; nếu chưa chứng minh được tối thiểu thì trả `NO_SOLUTION`, không trả `FEASIBLE/APPROXIMATE`. Các bước phụ chỉ phục vụ trình bày và không được phép làm UI chờ vô hạn.
  - Không cấm split tuyệt đối: cùng một dòng/mã có thể dùng nhiều khoảng con khi split giúp giảm thiếu hàng hoặc giảm số buồng xẻ; nếu số buồng xẻ không đổi thì segment penalty ưu tiên một dải liền kề.
  - Fallback beam search `APPROXIMATE` chỉ dùng cho các mode phân bổ từ số buồng khi thiếu solver tối ưu. Riêng mode `Tính số buồng từ số cont` không dùng kết quả approximate; thiếu solver exact hoặc hết giới hạn chứng minh thì báo chưa có kết quả tối ưu chính xác.

  **Bản đồ Farm (SVG Interactive Map):**
  - Farm 126/157/195 render qua cùng `_render_generic_farm_map(...)`; khác biệt giữa farm nằm ở file polygon JSON và kích thước viewBox.
  - `get_map_lots_by_farm()` đọc tên lô từ polygon JSON. `get_lots_by_farm()` lấy giao giữa danh sách này và `dim_lo.is_active=True`, nên mọi dropdown nhập tác vụ chỉ hiện các lô thực sự có trên bản đồ; farm chưa có polygon fallback về `dim_lo` active.
  - Render qua custom component `farm_map_component` (`components/farm_map/index.html`) — SVG inline với `viewBox` + `preserveAspectRatio="xMidYMid meet"`.
  - 6 CSS breakpoints: Mobile (≤480px), Small tablet (481–768px), Tablet/iPad (769–1024px), Default (1025–1199px), Large (1200–1799px), XL (1800px+).
  - iOS compatibility: `overflow-x: hidden`, `-webkit-text-size-adjust: 100%`, viewport meta tag.
  - Auto-fit iframe height: `ResizeObserver` + `window.resize` + aggressive polling (50–3000ms).
  - Tooltip ghim của từng lô có nút `Xem chi phí/cây`, gửi event `farm-map:costClick` về custom component rồi lưu `cost_dialog_farm/cost_dialog_lot` trong `st.session_state` để mở `@st.dialog` mà không reload trình duyệt. Query params `cost_farm` + `cost_lot` chỉ còn là fallback cho URL cũ. Dashboard cộng `fact_nhat_ky_san_xuat` + `fact_vat_tu`, giữ cả dòng gộp, phân bổ scope theo **cột lô** (lô thật = trực tiếp, `NT1/NT2` = chia theo đội, `Farm/Vườn Ươm/Nhà Đội/Cơ giới/Điện nước/...` = chia toàn farm), rồi chia tiếp vào từng `base_lot` trồng mới bằng tỷ lệ số cây của các đợt active tại ngày phát sinh chi phí. Nhóm chăm sóc buồng như bao buồng/bẻ hoa/lặt râu chỉ được phân bổ sau mốc `Cắt bắp` của batch và `klcv` nhân công bị cap theo số cắt bắp lũy kế để cây mới không gánh chi phí cây cũ. Scope phi nông nghiệp như xưởng/kho/công trình bị tách khỏi cost/cây; nhóm phân bón/chăm sóc/cơ giới/dầu DO vượt ngưỡng theo cây active cũng bị đưa vào audit nền. UI popup được tối giản để chỉ hiển thị chi phí/cây, tổng chi phí tính vào cây, tổng cây tính và bảng theo đợt; các dòng bị tách được giữ cho audit nền, không phơi bảng kỹ thuật cho user.

- **`app_temp.py`**: Phiên bản phát triển / Testing sandbox tạm thời cho dashboard trước khi merge vào logic chính.

### 2. Thành phần ETL & Chuyển Đổi Dữ Liệu
- **`tong_hop_v2.py` / `tong_hop.py`** *(script off-dashboard)*: Script nền chạy cron-job / manual trigger dùng để tính toán và biến đổi dữ liệu (Unpivot) từ nhật ký GSheet sang hệ Data Warehouse Long-format (`fact_195_tong`). Phục vụ riêng cho biểu đồ BI.
- **`clean_db.py` / `clean_db.sql`**: Script dọn dẹp các bản ghi mồ côi (soft-deleted hoặc orphaned records) nhằm bảo vệ tính toàn vẹn của Constraint trong PostgreSQL.

### 3. Thành phần Kiểm tử & CI (Tests)
Nằm trong thư mục `tests/` cùng những tệp kiểm thử tự do thư mục gốc:
- `test_supabase.py`, `test_supabase3.py`, `test_supabase4.py`, `test_supabase_schema.py`: Kiểm thử luồng gửi / nhận JSON từ các REST endpoints của Supabase (Insert batching, RLS testing).

### 4. Thành phần Lịch sử Migration (SQL)
- Quản lý versioning cho Schema tại Supabase DB. Tất cả thay đổi lớn đều có file SQL backup.
  - `migration_update_126.sql`
  - `migration_update_teams_areas.sql` (Chuyển đổi multi-team mapping logic).
  - `migration_fusarium.sql`, `migration_add_mau_day.sql` (Thêm bảng đo kiểm sinh trưởng).
  - `migration_user_roles.sql` (Tạo RBAC structure).

### 5. Cấu hình định lý và Hướng dẫn Agent (`.agents/rules/`, `skills/`, `docs/`)
- Môi trường Agentic coding: Yêu cầu AI/Bot duy trì format chặt chẽ. Hệ thống bắt buộc bot phải tham chiếu qua `skills/` hoặc `rule.md` để đảm bảo Development Standard.
- Toàn bộ Documentation nằm gọn trong thư mục `docs/`.

### 6. Kiến Trúc Frontend Migration (Next.js) tương lai
- **`frontend_migration_specs.md` & `business_logic_vi.txt`**: Đặc tả yêu cầu kỹ thuật chi tiết để team dev thực hiện tái thiết kế `app.py` sang hệ sinh thái React Next.js + TailwindCSS + Vercel Deployment. Lộ trình là chia nhỏ dashboard thành `components/charts.tsx`, `lib/supabase.ts`, v.v.
