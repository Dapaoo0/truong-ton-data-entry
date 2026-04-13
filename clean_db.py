import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def log(msg):
    print(msg)
    sys.stdout.flush()

try:
    log("Fetching base lots...")
    res_lots = supabase.table("base_lots").select("*").execute()
    lots = res_lots.data
    log(f"Found {len(lots)} lots.")

    for lot in lots:
        lot_id = lot["lot_id"]
        total_planted = int(lot["so_luong"])
        log(f"--- Processing Lot {lot_id} (Planted: {total_planted}) ---")
        
        # Check Chich bap
        res_cb = supabase.table("stage_logs").select("*").eq("lot_id", lot_id).eq("giai_doan", "Chích bắp").order("created_at", desc=True).execute()
        cb_logs = res_cb.data
        cb_logs.reverse() # Oldest to newest
        
        total_cb = 0
        for log_entry in cb_logs:
            if total_cb + int(log_entry["so_luong"]) <= total_planted:
                total_cb += int(log_entry["so_luong"])
            else:
                log(f"Deleting Chích bắp {log_entry['id']} (Amount: {log_entry['so_luong']} exceeds max {total_planted - total_cb})")
                supabase.table("stage_logs").delete().eq("id", log_entry["id"]).execute()
                
        # Check Cat bap
        res_cut = supabase.table("stage_logs").select("*").eq("lot_id", lot_id).eq("giai_doan", "Cắt bắp").order("created_at", desc=True).execute()
        cut_logs = res_cut.data
        cut_logs.reverse()
        
        total_cut = 0
        for log_entry in cut_logs:
            if total_cut + int(log_entry["so_luong"]) <= total_cb:
                total_cut += int(log_entry["so_luong"])
            else:
                log(f"Deleting Cắt bắp {log_entry['id']} (Amount: {log_entry['so_luong']} exceeds max {total_cb - total_cut})")
                supabase.table("stage_logs").delete().eq("id", log_entry["id"]).execute()

        # Check Harvest
        res_har = supabase.table("harvest_logs").select("*").eq("lot_id", lot_id).order("created_at", desc=True).execute()
        har_logs = res_har.data
        har_logs.reverse()
        
        total_har = 0
        for log_entry in har_logs:
            if total_har + int(log_entry["so_luong"]) <= total_cut:
                total_har += int(log_entry["so_luong"])
            else:
                log(f"Deleting Thu hoạch {log_entry['id']} (Amount: {log_entry['so_luong']} exceeds max {total_cut - total_har})")
                supabase.table("harvest_logs").delete().eq("id", log_entry["id"]).execute()
                
        # Check destruction
        res_des = supabase.table("destruction_logs").select("*").eq("lot_id", lot_id).order("created_at", desc=True).execute()
        des_logs = res_des.data
        des_logs.reverse()
        
        total_des = 0
        for log_entry in des_logs:
            if total_des + int(log_entry["so_luong"]) <= total_planted:
                total_des += int(log_entry["so_luong"])
            else:
                log(f"Deleting Xuất hủy {log_entry['id']} (Amount: {log_entry['so_luong']} exceeds max {total_planted - total_des})")
                supabase.table("destruction_logs").delete().eq("id", log_entry["id"]).execute()

    log("Done cleaning data!")

except Exception as e:
    log(f"Error: {e}")
