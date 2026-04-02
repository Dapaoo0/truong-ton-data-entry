-- Cập nhật diện tích và đội cho Farm 126
DO $$ 
DECLARE
  v_table_names text[] := ARRAY['base_lots', 'stage_logs', 'harvest_logs', 'destruction_logs', 'size_measure_logs', 'bsr_logs', 'tree_inventory_logs'];
  v_tbl text;
BEGIN

  -- Cập nhật diện tích vào base_lots
  UPDATE base_lots SET dien_tich = 3.30 WHERE farm = 'Farm 126' AND lo = 'A1';
  UPDATE base_lots SET dien_tich = 4.45 WHERE farm = 'Farm 126' AND lo = 'A2';
  UPDATE base_lots SET dien_tich = 4.10 WHERE farm = 'Farm 126' AND lo = 'A3';
  UPDATE base_lots SET dien_tich = 3.70 WHERE farm = 'Farm 126' AND lo = 'A4';
  UPDATE base_lots SET dien_tich = 3.65 WHERE farm = 'Farm 126' AND lo = 'A5';
  UPDATE base_lots SET dien_tich = 6.80 WHERE farm = 'Farm 126' AND lo = 'A6';
  UPDATE base_lots SET dien_tich = 6.60 WHERE farm = 'Farm 126' AND lo = 'A7';
  UPDATE base_lots SET dien_tich = 3.80 WHERE farm = 'Farm 126' AND lo = 'B1';
  UPDATE base_lots SET dien_tich = 6.60 WHERE farm = 'Farm 126' AND lo = 'B2';
  UPDATE base_lots SET dien_tich = 3.40 WHERE farm = 'Farm 126' AND lo = 'B3';
  UPDATE base_lots SET dien_tich = 3.20 WHERE farm = 'Farm 126' AND lo = 'B4';
  UPDATE base_lots SET dien_tich = 5.90 WHERE farm = 'Farm 126' AND lo = 'B5';
  UPDATE base_lots SET dien_tich = 2.40 WHERE farm = 'Farm 126' AND lo = 'B6';
  UPDATE base_lots SET dien_tich = 4.20 WHERE farm = 'Farm 126' AND lo = 'B7';
  
  UPDATE base_lots SET dien_tich = 8.25 WHERE farm = 'Farm 126' AND lo = 'C1';
  UPDATE base_lots SET dien_tich = 7.43 WHERE farm = 'Farm 126' AND lo = 'C2';
  UPDATE base_lots SET dien_tich = 4.88 WHERE farm = 'Farm 126' AND lo = 'C3';
  UPDATE base_lots SET dien_tich = 3.35 WHERE farm = 'Farm 126' AND lo = 'C4';
  UPDATE base_lots SET dien_tich = 3.75 WHERE farm = 'Farm 126' AND lo = 'C5';
  
  UPDATE base_lots SET dien_tich = 4.82 WHERE farm = 'Farm 126' AND lo = 'D1';
  UPDATE base_lots SET dien_tich = 2.76 WHERE farm = 'Farm 126' AND lo = 'D2';
  UPDATE base_lots SET dien_tich = 1.20 WHERE farm = 'Farm 126' AND lo = 'D3';
  UPDATE base_lots SET dien_tich = 4.00 WHERE farm = 'Farm 126' AND lo = 'D4';
  UPDATE base_lots SET dien_tich = 5.00 WHERE farm = 'Farm 126' AND lo = 'D5';
  
  UPDATE base_lots SET dien_tich = 62.10 WHERE farm = 'Farm 126' AND lo = 'NT1';
  UPDATE base_lots SET dien_tich = 45.44 WHERE farm = 'Farm 126' AND lo = 'NT2';

  -- Cập nhật Team cho tất cả các bảng liên quan đến lô trồng
  FOREACH v_tbl IN ARRAY v_table_names LOOP
      -- Các lô thuộc NT1
      IF v_tbl = 'base_lots' THEN
          EXECUTE format('UPDATE %I SET team = ''NT1'' WHERE farm = ''Farm 126'' AND lo IN (''A1'', ''A2'', ''A3'', ''A4'', ''A5'', ''A6'', ''A7'', ''B1'', ''B2'', ''B3'', ''B4'', ''B5'', ''B6'', ''B7'', ''NT1'', ''A8'');', v_tbl);
      ELSE
          -- Nếu bảng log có cột 'farm' thì ta dùng điều kiện cẩn thận, nhưng thông qua 'lot_id' là chuẩn nhất
          EXECUTE format('UPDATE %I SET team = ''NT1'' WHERE lot_id IN (SELECT lot_id FROM base_lots WHERE farm = ''Farm 126'' AND lo IN (''A1'', ''A2'', ''A3'', ''A4'', ''A5'', ''A6'', ''A7'', ''B1'', ''B2'', ''B3'', ''B4'', ''B5'', ''B6'', ''B7'', ''NT1'', ''A8''));', v_tbl);
      END IF;

      -- Các lô thuộc NT2
      IF v_tbl = 'base_lots' THEN
          EXECUTE format('UPDATE %I SET team = ''NT2'' WHERE farm = ''Farm 126'' AND lo IN (''C1'', ''C2'', ''C3'', ''C4'', ''C5'', ''D1'', ''D2'', ''D3'', ''D4'', ''D5'', ''NT2'', ''D6'');', v_tbl);
      ELSE
          EXECUTE format('UPDATE %I SET team = ''NT2'' WHERE lot_id IN (SELECT lot_id FROM base_lots WHERE farm = ''Farm 126'' AND lo IN (''C1'', ''C2'', ''C3'', ''C4'', ''C5'', ''D1'', ''D2'', ''D3'', ''D4'', ''D5'', ''NT2'', ''D6''));', v_tbl);
      END IF;
  END LOOP;

END $$;
