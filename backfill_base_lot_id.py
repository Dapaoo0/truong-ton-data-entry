"""
Dry-run Backfill script: Kiểm tra thuật toán resolve_base_lot_id()
trước khi ghi vào database.
Chạy: python backfill_base_lot_id.py [--commit]
  Mặc định: dry-run (chỉ in kết quả)
  --commit: Ghi thật vào DB
"""
import os, sys
from datetime import timedelta
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# === CONSTANTS (giống app.py) ===
F0_DAYS_TO_CHICH = 180
F0_DAYS_TO_CAT = 194
F0_DAYS_TO_THU = 264
FN_CYCLE_DAYS = 174
FN_DAYS_CHICH_OFFSET = 90
FN_DAYS_CAT_OFFSET = 104
FN_DAYS_THU_OFFSET = 174
MAX_GENERATION = 5

_STAGE_OFFSETS = {
    "Chích bắp": {"f0": F0_DAYS_TO_CHICH, "fn": FN_DAYS_CHICH_OFFSET},
    "Cắt bắp":   {"f0": F0_DAYS_TO_CAT,   "fn": FN_DAYS_CAT_OFFSET},
    "Thu hoạch":  {"f0": F0_DAYS_TO_THU,   "fn": FN_DAYS_THU_OFFSET},
}

# Cache base_lots per dim_lo_id
_base_lots_cache = {}

def get_base_lots(dim_lo_id):
    if dim_lo_id not in _base_lots_cache:
        res = supabase.table("base_lots") \
            .select("id, ngay_trong, so_luong") \
            .eq("dim_lo_id", dim_lo_id) \
            .eq("is_deleted", False) \
            .execute()
        _base_lots_cache[dim_lo_id] = res.data or []
    return _base_lots_cache[dim_lo_id]


# Map giai đoạn xuất hủy → stage tương ứng để dùng timeline matching
_DESTRUCTION_STAGE_MAP = {
    "Trước chích bắp": "Chích bắp",
    "Trước cắt bắp": "Cắt bắp",
    "Trước thu hoạch": "Thu hoạch",
}


def resolve_base_lot_id(dim_lo_id, action_date, giai_doan):
    batches = get_base_lots(dim_lo_id)
    if not batches:
        return None, "NO_BATCHES"

    action_dt = pd.to_datetime(action_date)
    best_match_id = None
    best_distance = float('inf')
    best_info = ""

    # Nếu là giai đoạn xuất hủy → map sang stage tương ứng để dùng timeline
    effective_giai_doan = _DESTRUCTION_STAGE_MAP.get(giai_doan, giai_doan)

    for batch in batches:
        trong_dt = pd.to_datetime(batch["ngay_trong"])

        if effective_giai_doan in _STAGE_OFFSETS:
            offsets = _STAGE_OFFSETS[effective_giai_doan]

            # F0
            f0_expected = trong_dt + timedelta(days=offsets["f0"])
            dist = abs((action_dt - f0_expected).days)
            if dist < best_distance:
                best_distance = dist
                best_match_id = batch["id"]
                best_info = f"F0 (trồng {batch['ngay_trong']}, expected {f0_expected.date()}, Δ{dist}d)"

            # F1→F5
            f0_harvest_dt = trong_dt + timedelta(days=F0_DAYS_TO_THU)
            for n in range(1, MAX_GENERATION + 1):
                prev_harvest = f0_harvest_dt + timedelta(days=FN_CYCLE_DAYS * (n - 1))
                fn_expected = prev_harvest + timedelta(days=offsets["fn"])
                dist = abs((action_dt - fn_expected).days)
                if dist < best_distance:
                    best_distance = dist
                    best_match_id = batch["id"]
                    best_info = f"F{n} (trồng {batch['ngay_trong']}, expected {fn_expected.date()}, Δ{dist}d)"
        else:
            # Giai đoạn không xác định → chọn đợt trồng gần nhất trước ngày hành động
            if trong_dt <= action_dt:
                dist = (action_dt - trong_dt).days
                if dist < best_distance:
                    best_distance = dist
                    best_match_id = batch["id"]
                    best_info = f"Closest planted (trồng {batch['ngay_trong']}, Δ{dist}d)"

    if best_match_id is None:
        best_match_id = sorted(batches, key=lambda b: b["ngay_trong"])[0]["id"]
        best_info = f"Fallback → earliest batch"

    return best_match_id, best_info


def backfill_seasons():
    """Backfill seasons: F0 match bằng ngay_bat_dau=ngay_trong, Fn match bằng expected harvest F(n-1)."""
    print("\n" + "="*80)
    print("BACKFILL: seasons")
    print("="*80)
    
    res = supabase.table("seasons") \
        .select("id, vu, ngay_bat_dau, dim_lo_id") \
        .eq("is_deleted", False) \
        .is_("base_lot_id", "null") \
        .execute()
    
    results = []
    for s in (res.data or []):
        dim_lo_id = s["dim_lo_id"]
        if not dim_lo_id:
            print(f"  ⚠️  Season #{s['id']} ({s['vu']}): dim_lo_id is NULL, skip")
            continue
        
        batches = get_base_lots(dim_lo_id)
        if not batches:
            print(f"  ⚠️  Season #{s['id']} ({s['vu']}): lô chưa có đợt trồng, skip")
            continue
        
        vu = s.get("vu", "F0")
        ngay_bd = pd.to_datetime(s["ngay_bat_dau"])
        
        # Thử exact match trước (ngay_bat_dau = ngay_trong) — cho F0
        exact = [b for b in batches if b["ngay_trong"] == s["ngay_bat_dau"]]
        if exact:
            match_id = exact[0]["id"]
            info = f"EXACT match (ngay_bat_dau={s['ngay_bat_dau']})"
        elif vu == "F0":
            # F0 nhưng không exact → closest ngay_trong
            candidates = [(abs((ngay_bd - pd.to_datetime(b["ngay_trong"])).days), b["id"], b["ngay_trong"]) 
                         for b in batches]
            candidates.sort(key=lambda x: x[0])
            match_id = candidates[0][1]
            info = f"F0 CLOSEST (trồng {candidates[0][2]}, Δ{candidates[0][0]}d)"
        else:
            # Fn (F1, F2, ...) → tìm batch có expected F(n-1) harvest gần nhất với ngay_bat_dau
            # Fn bắt đầu ≈ ngay thu hoạch F(n-1) → ngay_bat_dau ≈ expected harvest F(n-1)
            n = int(vu.replace("F", "")) if vu.startswith("F") and vu[1:].isdigit() else 1
            
            best_id = None
            best_dist = float('inf')
            best_detail = ""
            for b in batches:
                trong_dt = pd.to_datetime(b["ngay_trong"])
                # Expected harvest cho F(n-1):
                # F0 harvest = trong + 264
                # F1 harvest = trong + 264 + 174
                # F(n-1) harvest = trong + 264 + 174*(n-2) nếu n>=2, hoặc trong + 264 nếu n=1
                if n == 1:
                    prev_harvest = trong_dt + timedelta(days=F0_DAYS_TO_THU)
                else:
                    prev_harvest = trong_dt + timedelta(days=F0_DAYS_TO_THU + FN_CYCLE_DAYS * (n - 1))
                
                dist = abs((ngay_bd - prev_harvest).days)
                if dist < best_dist:
                    best_dist = dist
                    best_id = b["id"]
                    best_detail = f"{vu} TIMELINE (trồng {b['ngay_trong']}, F{n-1} harvest expected {prev_harvest.date()}, Δ{dist}d)"
            
            match_id = best_id
            info = best_detail
        
        results.append({"id": s["id"], "base_lot_id": match_id})
        print(f"  Season #{s['id']:3d} ({s['vu']:3s}, {s['ngay_bat_dau']}) → base_lot #{match_id} | {info}")
    
    return results


def backfill_table(table_name, date_col, giai_doan_col=None, fixed_giai_doan=None):
    print(f"\n{'='*80}")
    print(f"BACKFILL: {table_name}")
    print(f"{'='*80}")
    
    cols = f"id, {date_col}, dim_lo_id"
    if giai_doan_col:
        cols += f", {giai_doan_col}"
    
    res = supabase.table(table_name) \
        .select(cols) \
        .eq("is_deleted", False) \
        .is_("base_lot_id", "null") \
        .execute()
    
    results = []
    for r in (res.data or []):
        dim_lo_id = r.get("dim_lo_id")
        if not dim_lo_id:
            print(f"  ⚠️  {table_name} #{r['id']}: dim_lo_id is NULL, skip")
            continue
        
        action_date = r[date_col]
        if giai_doan_col:
            giai_doan = r[giai_doan_col]
        else:
            giai_doan = fixed_giai_doan
        
        match_id, info = resolve_base_lot_id(dim_lo_id, action_date, giai_doan)
        if match_id:
            results.append({"id": r["id"], "base_lot_id": match_id})
            print(f"  {table_name} #{r['id']:3d} ({action_date}, {giai_doan:12s}) → base_lot #{match_id} | {info}")
        else:
            print(f"  ⚠️  {table_name} #{r['id']:3d}: NO MATCH (lô chưa trồng)")
    
    return results


def main():
    commit = "--commit" in sys.argv
    mode = "COMMIT" if commit else "DRY-RUN"
    print(f"\n🏁 Backfill base_lot_id — Mode: {mode}")
    print(f"{'='*80}")
    
    # 1. Seasons
    season_results = backfill_seasons()
    
    # 2. Stage logs
    stage_results = backfill_table("stage_logs", "ngay_thuc_hien", giai_doan_col="giai_doan")
    
    # 3. Harvest logs
    harvest_results = backfill_table("harvest_logs", "ngay_thu_hoach", fixed_giai_doan="Thu hoạch")
    
    # 4. Destruction logs
    destruction_results = backfill_table("destruction_logs", "ngay_xuat_huy", giai_doan_col="giai_doan")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY")
    print(f"{'='*80}")
    print(f"  Seasons:      {len(season_results)} records to update")
    print(f"  Stage logs:   {len(stage_results)} records to update")
    print(f"  Harvest logs: {len(harvest_results)} records to update")
    print(f"  Destruction:  {len(destruction_results)} records to update")
    total = len(season_results) + len(stage_results) + len(harvest_results) + len(destruction_results)
    print(f"  TOTAL:        {total} records")
    
    if commit and total > 0:
        print(f"\n🔧 Committing to database...")
        for table, results in [
            ("seasons", season_results),
            ("stage_logs", stage_results),
            ("harvest_logs", harvest_results),
            ("destruction_logs", destruction_results),
        ]:
            for r in results:
                supabase.table(table).update({"base_lot_id": r["base_lot_id"]}).eq("id", r["id"]).execute()
            print(f"  ✅ {table}: {len(results)} updated")
        print(f"\n✅ Backfill complete!")
    elif not commit:
        print(f"\n⚠️  DRY-RUN complete. Run with --commit to apply changes.")


if __name__ == "__main__":
    main()
