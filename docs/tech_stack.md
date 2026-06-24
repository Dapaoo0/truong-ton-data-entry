# Tech Stack

Danh sách công cụ, framework và công nghệ đang được sử dụng trong dự án `truong-ton-data-entry` (Banana Tracker).

## Frontend & Framework
- Về Dashboard phân tích và nhập liệu: **Streamlit** (Python).
- Về UI Components: **Pandas Styler**, HTML/Markdown qua Streamlit.
- Về Prototype/Thiết kế sau này (quy hoạch chuyển đổi): Theo kiến trúc **Next.js**.

## Backend & Database
- BaaS (Backend as a Service): **Supabase** (Postgres DB).
- Data processing, ETL pipeline: **Pandas**, Python.
- Backend tách dần: **FastAPI** trong `services/api`, chạy bằng Uvicorn/Docker, hiện mới read-only để phục vụ lộ trình web/mobile.

## Version Control & Management
- Repo: GitHub.
- Environment/Runtime: IDE cursor/windsurf/gemini.
