-- Migration: Create fusarium_logs table
CREATE TABLE IF NOT EXISTS fusarium_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  farm TEXT NOT NULL,
  team TEXT NOT NULL,
  lot_id TEXT NOT NULL,
  ngay_kiem_tra DATE NOT NULL,
  so_cay_fusarium INTEGER NOT NULL,
  tuan INTEGER,
  is_deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fusarium_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all" ON fusarium_logs;
CREATE POLICY "Allow all" ON fusarium_logs FOR ALL USING (true);
