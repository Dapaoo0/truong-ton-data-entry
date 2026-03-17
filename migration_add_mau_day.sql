-- Migration: Thêm cột mau_day vào bảng destruction_logs
-- Chạy SQL này trong Supabase Dashboard > SQL Editor
ALTER TABLE public.destruction_logs ADD COLUMN IF NOT EXISTS mau_day TEXT;
