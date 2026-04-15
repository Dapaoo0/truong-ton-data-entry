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
  - `render_global_data_tab()`: Module vẽ dữ liệu toàn cầu. Aggregate dữ liệu thống kê tổng hợp (tổng cây, lượng chích/cắt, lượng thu hoạch). Đặc biệt hỗ trợ chia bảng phân rã chi tiết (Expander) theo từng mùa cụ thể (vu = F0, F1).
  - `render_chart_filters(prefix, include_date, use_dynamic_lots)`: Bộ lọc DRY chuẩn (Farm/Vụ/Đội/Lô/Date) dùng chung cho 6/7 chart sections. Harvest Schedule dùng filter Year/Month riêng.
  - Styling với `pandas.Styler`: tinh chỉnh CSS và bố cục.
  
  **Luồng dữ liệu chính (Data Flow):**
  - `df_lots_all` ← `fetch_table_data("base_lots")` — toàn bộ đợt trồng (cả trồng mới + trồng dặm). `loai_trong` nằm trực tiếp trong cột (sau migration).
  - `df_lots_trong_moi` ← chỉ giữ `loai_trong == "Trồng mới"` → dùng cho **Bảng chi tiết**, **Lịch thu hoạch**, **batch_label_map**.
  - `df_lots_trong_dam` ← chỉ giữ `loai_trong == "Trồng dặm"` → hiển thị riêng ở **📋 Lịch sử Trồng dặm** (expander).
  
  **Mô hình Dự báo Thu hoạch (Harvest Forecast):**
  - Normal Distribution truncated: cửa sổ cố định 55 ngày = Thu bói (14d) + Thu rộ (26d) + Thu vét (14d).
  - Tỷ lệ mặc định 10/80/10, có thể tùy chỉnh qua `st.number_input` trong `st.expander`.
  - Rescale PDF weights cho mỗi phase khớp % mong muốn, giữ nguyên timeline cố định.
  - Chỉ iterate `df_lots_trong_moi` (trồng dặm bị loại khỏi forecast).

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
