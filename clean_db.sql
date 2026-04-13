-- 1. Xóa toàn bộ Dữ liệu cũ khỏi các bảng vì đổi ID structure và loại bỏ logic "A1-F0-M"
TRUNCATE TABLE base_lots RESTART IDENTITY CASCADE;
TRUNCATE TABLE stage_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE destruction_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE harvest_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE bsr_logs RESTART IDENTITY CASCADE;

-- 2. Thêm trường dien_tich vào base_lots
ALTER TABLE base_lots ADD COLUMN IF NOT EXISTS dien_tich NUMERIC;

-- 3. Tạo bảng seasons để quản lý các vụ
CREATE TABLE IF NOT EXISTS seasons (
    id SERIAL PRIMARY KEY,
    farm TEXT NOT NULL,
    lo TEXT NOT NULL,
    vu TEXT NOT NULL DEFAULT 'F0',
    loai_trong TEXT NOT NULL,
    ngay_bat_dau DATE NOT NULL,
    ngay_ket_thuc_thuc_te DATE,
    ngay_ket_thuc_du_kien DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);
