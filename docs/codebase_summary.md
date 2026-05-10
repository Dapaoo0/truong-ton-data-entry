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
  - Phân quyền (Authentication): Quản lý đăng nhập, session_state và RBAC (trích từ bảng `user_roles`). Đặc biệt hỗ trợ các Account quản trị như "Admin" và "Phòng Kinh doanh" để có Data Dashboard riêng biệt.
  - `allocate_fifo_quantity(farm_name, lo_name, new_sl, log_type, target_date, action_type, giai_doan, mau_day)`: Phân bổ FIFO theo `ngay_trong`. Query tất cả base_lots active, tính capacity per-batch, split allocations. Trả về list `[{dim_lo_id, base_lot_id, so_luong, lot_id}]`. **Hai chế độ**: (1) User chỉ định `base_lot_id` → trigger skip FIFO, (2) Không chỉ định → FIFO mặc định. Destruction delegate sang `allocate_destruction_fifo()` với 3 chiến lược theo giai_doan.
  - `render_global_data_tab()`: Module vẽ dữ liệu toàn cầu. Aggregate dữ liệu thống kê tổng hợp (tổng cây, lượng chích/cắt, lượng thu hoạch). Đặc biệt hỗ trợ chia bảng phân rã chi tiết (Expander) theo từng mùa cụ thể (vu = F0, F1).
  - `compute_batch_stats(lo_name, base_lot_id, vu, season_start, season_end, next_season_start, next_vu_producing)`: **Hàm shared** dùng chung cho Map & Table. Áp dụng 4 business rules: (1) Season date range filter, (2) Harvest Growth Buffer 18w (F1+), (3) Next-season upper bound, (4) F1+ no-chích safety. Returns `(giai_doan, so_chich, so_cat, so_thu)`.
  - `render_chart_filters(prefix, include_date, use_dynamic_lots)`: Bộ lọc DRY chuẩn (Farm/Vụ/Đội/Lô/Date) dùng chung cho 6/7 chart sections. Harvest Schedule dùng filter Year/Month riêng.
  - Styling với `pandas.Styler`: tinh chỉnh CSS và bố cục.
  
  **Luồng dữ liệu chính (Data Flow):**
  - `df_lots_all` ← `fetch_table_data("base_lots")` — toàn bộ đợt trồng (cả trồng mới + trồng dặm). `loai_trong` nằm trực tiếp trong cột `base_lots` (không cần join `seasons`).
  - `df_lots_trong_moi` ← chỉ giữ `loai_trong == "Trồng mới"` → dùng cho **Bảng chi tiết**, **Lịch thu hoạch**, **batch_label_map**.
  - `batch_label_map` ← build từ `df_lots_trong_moi.groupby("lo")`. Lô nhiều đợt → `"3B (đợt 1)"`, lô 1 đợt → `"3B"`. **Shared** giữa Map tooltip và Bảng chi tiết (DRY). Map tooltip hiển thị `"Đợt X (FY)"` cho multi-batch, `"FY"` cho single-batch.
  - `df_lots_trong_dam` ← chỉ giữ `loai_trong == "Trồng dặm"` → hiển thị riêng ở **📋 Lịch sử Trồng dặm** (expander).
  
  **Mô hình Dự báo Thu hoạch (Harvest Forecast — 4 Mốc, Dual-Model):**
  - **Mốc ① (Từ Trồng)**: Normal Distribution truncated: cửa sổ cố định 55 ngày = Thu bói (14d) + Thu rộ (26d) + Thu vét (14d). Rescale PDF weights theo tỷ lệ custom (mặc định 10/80/10).
  - **Mốc ②③ (Chích/Cắt bắp — Micro-PDF)**: Dùng dữ liệu thực tế theo ngày từ `stage_logs`. Mỗi record → shift +84d/+70d → spread ±7d Normal Distribution (σ=3, fixed) → gộp tất cả mini-PDFs thành harvest curve → phase xác định bằng diện tích tích lũy 10/80/10 với boundary-day splitting. Không trừ hao hụt ước tính.
  - **Mốc ④ (Thực tế)**: `harvest_logs` match vào (generation, phase, tháng).
  - Chỉ iterate `df_lots_trong_moi` (trồng dặm bị loại khỏi forecast).
  - **Phân bổ Xuất hủy**: Direct (có `base_lot_id`) hoặc Proportional (`hủy × batch/tổng_lô`).
  - **Ribbon Schedule**: Màu dây resolve từ `ribbon_schedule` qua `_resolve_ribbon_color(row)` — pre-computed `_ribbon_lookup` dict `{(year, week): color}`. Thay thế cột `mau_day` cũ (đã xóa từ `stage_logs`, `destruction_logs`, `harvest_logs`).
  - **Helper `_build_shift_rows()`**: Nested function Micro-PDF cho chích/cắt bắp. 3 bước: (1) Spread ±7d mỗi record qua `micro_weights` (norm.pdf σ=3), (2) Aggregate daily harvest curve, (3) Phase assignment bằng cumulative area + boundary-day splitting (đảm bảo đúng tỷ lệ). Destruction deduction: Pro-rata mau_day (Mốc ③) hoặc Aggregate Ratio (Mốc ②). Largest Remainder rounding cho float→int.

  **Excel Export Functions:**
  - `generate_cut_bap_excel(df_lots, df_stg)`: Báo cáo Cắt bắp theo tuần, chia sheet theo năm. **2 params** (không có `df_des`). Dùng so khớp trực tiếp `df_cut["lo"] == lo_name` (không dùng `lot_id` alias). Bao gồm cột Lũy kế. Type-safe: `tuan` + `_year` cast `int`.
  - `generate_chich_bap_excel(df_lots, df_stg)`: Báo cáo Chích bắp. Natural sort, date-based grouping.
  - `generate_planting_excel(df_lots, df_seasons)`: Báo cáo Trồng mới. Ưu tiên `loai_trong` trực tiếp từ `base_lots`, fallback `df_seasons` join.

  **Bản đồ Farm (SVG Interactive Map):**
  - Render qua `streamlit.components.v1.html()` — SVG inline với `viewBox` + `preserveAspectRatio="xMidYMid meet"`.
  - 6 CSS breakpoints: Mobile (≤480px), Small tablet (481–768px), Tablet/iPad (769–1024px), Default (1025–1199px), Large (1200–1799px), XL (1800px+).
  - iOS compatibility: `overflow-x: hidden`, `-webkit-text-size-adjust: 100%`, viewport meta tag.
  - Auto-fit iframe height: `ResizeObserver` + `window.resize` + aggressive polling (50–3000ms).

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
