# Codebase Summary

Tài liệu cung cấp tóm tắt chi tiết cấu trúc các file, framework và chức năng logic chính cho nền tảng lập kế hoạch nông nghiệp.

## Môi trường & Framework
- Ứng dụng trung tâm được dựng bằng **Streamlit**.
- Database Interface thông qua API client của **Supabase** kết nối cùng PostgreSQL backend.

## Thành phần Chính

### 1. File `app.py` (Core Dashboard)
> Đây là Gateway kiêm Controller duy nhất cho giao diện phân tích tổng quát dành cho Farm, sử dụng pandas xử lý logic local.
- **`apply_filters_local()`**: Cơ chế siêu lọc. Nhận raw pandas Dataframes tải trực tiếp từ DB memory và áp dụng filter theo (Farm, Đội, Vụ, Lô). Rất quan trọng vì giúp user lướt biểu đồ siêu tốc độ mà ko phải SQL Refresh liên tục.
- **`get_dynamic_lot_options()`**: Hàm Util trích lọc tự động các Option hiển thị ở selectbox (Chỉ lọc những Đội/Lô khả dụng từ dataset).
- **Khối chức năng Authentication (Role-based access)**: Đọc thông qua `st.secrets` và logic session_state để cung cấp phân quyền `user_roles`.
- **`render_global_data_tab()`**: Hàm render chính. Nhiệm vụ gồm: Gộp Data, tính ra tổng cây, bắp chích, bắp cắt, số thu hoạch. Tách bảng chi tiết lô con vào expander (render ra Multiple Markdown tables cho các Vụ - F0, F1).
- **Styling**: Sử dụng thư viện Pandas `Styler` (như `.set_table_styles()`) để can thiệp css CSS, căn chỉnh font chữ và UI trực tiếp trên Streamlit framework mà ko cần thẻ html.

### 2. Các thư mục Migration Scripts/ Backend ETL tools (`clean_db.sql`, `migration_*.sql`)
- Các scripts này đảm nhận việc chuyển đổi DB / Thêm sửa xoá các Table/ Dimension qua các Giai đoạn update dự án.
- VD: `migration_update_teams_areas.sql` (Update diện tích mapping sang cơ chế multi-team map).

### 3. Cấu hình định lý và Hướng dẫn Agent (`.agents/rules/`, `skills/`)
- Cấu trúc hệ thống Agentic coding. Hệ thống đòi hỏi AI/Bot phải thực hiện read `SKILL.md` hoặc rule config mỗi lúc boot để duy trì format code chặt chẽ và không lạm dụng SQL commands khi chưa được đồng bộ (`docs/`).

### 4. Code thiết kế Prototype Next.js (Dự kiến chuyển đổi Frontend tương lai)
- Tài liệu quy hoạch kiến trúc tại file `frontend_migration_specs.md/txt` cho việc tái xây dựng ứng dụng dựa trên công nghệ NextJS kết hợp UI Tailwind/Shadcn để đáp ứng perfomance siêu mạnh và responsive thiết bị cầm tay. Lộ trình sẽ bóc tách `app.py` khổng lồ thành `utils.ts`, `components/charts.tsx`, v.v.
