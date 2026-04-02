-- Update Đội (Team) and Diện tích (Area) cho Farm 157

-- AREA (Diện Tích) cho base_lots
UPDATE base_lots SET dien_tich = 6.72 WHERE farm = 'Farm 157' AND lo = '1A';
UPDATE base_lots SET dien_tich = 6.59 WHERE farm = 'Farm 157' AND lo = '1B';
UPDATE base_lots SET dien_tich = 8.73 WHERE farm = 'Farm 157' AND lo = '2';
UPDATE base_lots SET dien_tich = 4.20 WHERE farm = 'Farm 157' AND lo = '3A';
UPDATE base_lots SET dien_tich = 4.50 WHERE farm = 'Farm 157' AND lo = '3B';
UPDATE base_lots SET dien_tich = 7.90 WHERE farm = 'Farm 157' AND lo = '4';
UPDATE base_lots SET dien_tich = 4.98 WHERE farm = 'Farm 157' AND lo = '5';
UPDATE base_lots SET dien_tich = 5.10 WHERE farm = 'Farm 157' AND lo = '6';
UPDATE base_lots SET dien_tich = 6.38 WHERE farm = 'Farm 157' AND lo = '7A';
UPDATE base_lots SET dien_tich = 8.28 WHERE farm = 'Farm 157' AND lo = '7B';
UPDATE base_lots SET dien_tich = 5.73 WHERE farm = 'Farm 157' AND lo = '8A';
UPDATE base_lots SET dien_tich = 6.40 WHERE farm = 'Farm 157' AND lo = '8B';
UPDATE base_lots SET dien_tich = 5.77 WHERE farm = 'Farm 157' AND lo = '9';
UPDATE base_lots SET dien_tich = 6.05 WHERE farm = 'Farm 157' AND lo = '10';
UPDATE base_lots SET dien_tich = 5.14 WHERE farm = 'Farm 157' AND lo = '11';
UPDATE base_lots SET dien_tich = 5.91 WHERE farm = 'Farm 157' AND lo = '12A';
UPDATE base_lots SET dien_tich = 5.40 WHERE farm = 'Farm 157' AND lo = '12B';
UPDATE base_lots SET dien_tich = 6.11 WHERE farm = 'Farm 157' AND lo = '14A';
UPDATE base_lots SET dien_tich = 8.25 WHERE farm = 'Farm 157' AND lo = '14B';
UPDATE base_lots SET dien_tich = 7.59 WHERE farm = 'Farm 157' AND lo = '15A';
UPDATE base_lots SET dien_tich = 2.79 WHERE farm = 'Farm 157' AND lo = '15B';

-- TEAM (Đội)
-- Viết hàm helper cho việc update 4 bảng
DO $$ 
DECLARE
  v_table_names text[] := ARRAY['base_lots', 'stage_logs', 'harvest_logs', 'destruction_logs'];
  v_tbl text;
BEGIN
  FOREACH v_tbl IN ARRAY v_table_names LOOP
    IF v_tbl = 'base_lots' THEN
        EXECUTE format('UPDATE %I SET team = ''NT1'' WHERE farm = ''Farm 157'' AND lo IN (''1A'', ''1B'', ''2'', ''2A'', ''2B'', ''3A'', ''3B'', ''4'', ''5'', ''6'', ''7A'', ''7B'', ''NT1'', ''NT2'');', v_tbl);
        EXECUTE format('UPDATE %I SET team = ''NT2'' WHERE farm = ''Farm 157'' AND lo IN (''8A'', ''8B'', ''9'', ''10'', ''11'', ''12A'', ''12B'', ''14A'', ''14B'', ''15A'', ''15B'', ''NT3'', ''NT4'');', v_tbl);
    ELSE
        EXECUTE format('UPDATE %I SET team = ''NT1'' WHERE farm = ''Farm 157'' AND lot_id IN (SELECT lot_id FROM base_lots WHERE farm = ''Farm 157'' AND lo IN (''1A'', ''1B'', ''2'', ''2A'', ''2B'', ''3A'', ''3B'', ''4'', ''5'', ''6'', ''7A'', ''7B'', ''NT1'', ''NT2''));', v_tbl);
        EXECUTE format('UPDATE %I SET team = ''NT2'' WHERE farm = ''Farm 157'' AND lot_id IN (SELECT lot_id FROM base_lots WHERE farm = ''Farm 157'' AND lo IN (''8A'', ''8B'', ''9'', ''10'', ''11'', ''12A'', ''12B'', ''14A'', ''14B'', ''15A'', ''15B'', ''NT3'', ''NT4''));', v_tbl);
    END IF;
  END LOOP;
END $$;
