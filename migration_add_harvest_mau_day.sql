-- Migration: Thêm màu dây vào bảng harvest_logs
-- Dùng để map thu hoạch thực tế về tuần cắt bắp nguồn trong báo cáo cắt bắp.

ALTER TABLE public.harvest_logs
  ADD COLUMN IF NOT EXISTS mau_day TEXT;

COMMENT ON COLUMN public.harvest_logs.mau_day IS
  'Màu dây nguồn của lứa thu hoạch, dùng để đối chiếu với ribbon_schedule và báo cáo cắt bắp.';
