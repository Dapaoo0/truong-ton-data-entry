# Backend API tách dần

## Mục tiêu

Streamlit vẫn chạy song song, nhưng logic nghiệp vụ cốt lõi được tách dần để backend mới có thể phục vụ web/mobile trong tương lai. API đầu tiên là read-only, chưa thay thế luồng nhập liệu hiện tại.

## Cấu trúc

- `services/api/`: FastAPI service.
- `domain/`: logic thuần Python dùng chung giữa Streamlit và API.
- `services/api/app/deps.py`: tạo Supabase REST client từ `SUPABASE_URL` và `SUPABASE_KEY`.

## Endpoint hiện tại

### `GET /health`

Kiểm tra service sống.

### `GET /forecasts/cut-bud-weekly`

Trả dự báo thu hoạch theo tuần ISO từ dữ liệu `stage_logs` giai đoạn `Cắt bắp`.

Query params:

- `farm`: optional, ví dụ `Farm 126`.
- `weeks`: `8` hoặc `9`; giá trị khác sẽ fallback về `8`.

Response chính:

- `farm`: farm đã lọc, hoặc `null`.
- `weeks_inclusive`: số tuần cắt bắp -> thu hoạch đang dùng.
- `rows`: danh sách `{farm, year, week, forecast_bunches}`.

## Chạy local

```bash
uvicorn services.api.app.main:api --reload --host 0.0.0.0 --port 8000
```

Hoặc build Docker từ root repo:

```bash
docker build -f services/api/Dockerfile -t truong-ton-api .
docker run --env-file .env -p 8000:8000 truong-ton-api
```

## Nguyên tắc

- API không copy công thức từ `app.py`; mọi logic có thể dùng chung phải đi qua `domain/`.
- Test API không chạm database thật; dùng dependency override cho Supabase client.
- Các endpoint ghi dữ liệu sẽ được tách sau, khi đã có auth/RLS/API service role rõ ràng.
