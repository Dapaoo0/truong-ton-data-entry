"""
=======================================================================
  ỨNG DỤNG NHẬP LIỆU QUẢN LÝ TIẾN ĐỘ SINH TRƯỞNG CHUỐI XUẤT KHẨU
  Công ty Trường Tồn  |  Streamlit + Supabase (RBAC Version 2.0)
=======================================================================
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px
import io
import uuid
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if hasattr(st, "dialog"):
    dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    dialog_decorator = st.experimental_dialog
else:
    # Fallback to function if strictly not supported
    def dialog_decorator(title):
        def decorator(func):
            return func
        return decorator

# =====================================================
# CẤU HÌNH BAN ĐẦU
# =====================================================

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Trường Tồn - Quản lý Tiến độ Chuối",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# MẢNG MẬT KHẨU CỨNG & QUYỀN (RBAC)
# =====================================================
# Cấu trúc: RBAC_DB[Farm][Team] = Password
RBAC_DB = {
    "Admin": {
        "Quản trị viên": "admin123"
    },
    "Farm 126": {
        "NT1": "6677028",
        "NT2": "040187",
        "Đội BVTV": "123",
        "Đội Thu Hoạch": "123",
        "Xưởng Đóng Gói": "123",
        "Quản lý farm": "ql126"
    },
    "Farm 157": {
        "NT1": "Trung@1985",
        "NT2": "0056",
        "Đội BVTV": "456",
        "Đội Thu Hoạch": "456",
        "Xưởng Đóng Gói": "456",
        "Quản lý farm": "ql157"
    },
    "Farm 195": {
        "NT1": "789",
        "NT2": "789",
        "Đội BVTV": "789",
        "Đội Thu Hoạch": "789",
        "Xưởng Đóng Gói": "789",
        "Quản lý farm": "ql195"
    }
}

FARMS = list(RBAC_DB.keys())
TEAMS = ["NT1", "NT2", "Đội BVTV", "Đội Thu Hoạch", "Xưởng Đóng Gói", "Quản lý farm"]

# =====================================================
# CONFIG OPTIONS
# =====================================================
VU_OPTIONS = ["F0", "F1", "F2", "F3", "F4", "F5"]
LOAI_TRONG_OPTIONS = ["Trồng mới", "Trồng dặm"]
STAGE_NT_OPTIONS = ["Chích bắp", "Cắt bắp"]  # Không còn Thu Hoạch ở đây
DESTRUCTION_STAGE_OPTIONS = ["Trước chích bắp", "Trước cắt bắp", "Trước thu hoạch"]


# =====================================================
# STYLE TÙY CHỈNH (CSS)
# =====================================================
st.markdown("""
<style>
    .main-title { text-align: center; color: #2E7D32; font-size: 2rem; font-weight: 700; margin-bottom: 0.2rem; }
    .sub-title { text-align: center; color: #6D6D6D; font-size: 1rem; margin-bottom: 1.5rem; }
    .farm-badge { display: inline-block; padding: 4px 14px; border-radius: 20px; background: #2E7D32; color: white; font-weight: 600; font-size: 0.9rem; }
    .team-badge { display: inline-block; padding: 4px 14px; border-radius: 20px; background: #FF9800; color: white; font-weight: 600; font-size: 0.9rem; margin-top: 5px; }
    .dataframe-header { font-size: 1.1rem; font-weight: 600; color: #1B5E20; margin: 1rem 0 0.5rem 0; padding-left: 0.5rem; border-left: 4px solid #2E7D32; }
    .section-divider { border: none; border-top: 2px solid #E8F5E9; margin: 2rem 0; }
</style>
""", unsafe_allow_html=True)


# =====================================================
# HÀM TIỆN ÍCH (SESSION & LOG)
# =====================================================
def init_session_state():
    if "logged_in" not in st.session_state:
        if st.query_params.get("logged_in") == "true":
            st.session_state["logged_in"] = True
            st.session_state["current_farm"] = st.query_params.get("farm")
            st.session_state["current_team"] = st.query_params.get("team")
        else:
            st.session_state["logged_in"] = False
            st.session_state["current_farm"] = None
            st.session_state["current_team"] = None
            
    # Bulk entry queues
    for k in ["queue_stg", "queue_des", "queue_har", "queue_sm", "queue_inv", "queue_bsr"]:
        if k not in st.session_state: st.session_state[k] = []

def logout():
    st.session_state["logged_in"] = False
    st.session_state["current_farm"] = None
    st.session_state["current_team"] = None
    st.query_params.clear()

def insert_access_log(farm: str, team: str, action: str):
    try:
        supabase.table("access_logs").insert({"farm": farm, "team": team, "action": action}).execute()
    except Exception as e:
        print(f"Lỗi log: {e}")

# =====================================================
# HÀM TƯƠNG TÁC DB (SUPABASE DATA FETCHERS)
# =====================================================
def get_lots_by_farm(farm: str) -> list:
    """Lấy danh sách Tên Lô gốc của nguyen Farm."""
    res = supabase.table("base_lots").select("lo").eq("farm", farm).eq("is_deleted", False).order("created_at").execute()
    seen = set()
    lots = []
    if res.data:
        for row in res.data:
            l = row["lo"]
            if l not in seen:
                seen.add(l)
                lots.append(l)
    return lots

def fetch_table_data(table_name: str, farm: str) -> pd.DataFrame:
    """Hàm chung lấy dữ liệu. Quản trị viên (Admin) sẽ lấy của tất cả các farm."""
    query = supabase.table(table_name).select("*").eq("is_deleted", False)
    if farm != "Admin":
        query = query.eq("farm", farm)
    res = query.order("created_at", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def insert_to_db(table_name: str, data: dict) -> bool:
    try:
        supabase.table(table_name).insert(data).execute()
        return True
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
            if table_name == "base_lots":
                lot_id = data.get("lot_id")
                # Kiểm tra xem lô này đã tồn tại nhưng có đang bị xóa mềm không
                check_res = supabase.table("base_lots").select("is_deleted").eq("lot_id", lot_id).execute()
                if check_res.data and check_res.data[0].get("is_deleted") is True:
                    # Lô đã bị xóa mềm, tiến hành "Khôi phục" và đè dữ liệu mới
                    data["is_deleted"] = False
                    supabase.table("base_lots").update(data).eq("lot_id", lot_id).execute()
                    return True
            st.error(f"❌ Mã Lô '{data.get('lot_id')}' đã tồn tại trong hệ thống. Vui lòng kiểm tra lại!")
        else:
            st.error(f"❌ Lỗi khi lưu vào {table_name}: {e}")
        return False

def get_available_capacity_for_lot(lot_id, log_type, giai_doan=None, exclude_id=None):
    res_lot = supabase.table("base_lots").select("so_luong, so_luong_con_lai").eq("lot_id", lot_id).eq("is_deleted", False).execute()
    if not res_lot.data: return 0, 0
    val_con_lai = res_lot.data[0].get("so_luong_con_lai")
    total_planted = int(val_con_lai) if val_con_lai is not None else int(res_lot.data[0].get("so_luong", 0))

    max_allowed = total_planted

    if log_type == "stage" and giai_doan == "Cắt bắp":
        res_cb = supabase.table("stage_logs").select("so_luong").eq("lot_id", lot_id).eq("giai_doan", "Chích bắp").eq("is_deleted", False).execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cb.data)
    elif log_type == "harvest":
        res_cut = supabase.table("stage_logs").select("so_luong").eq("lot_id", lot_id).eq("giai_doan", "Cắt bắp").eq("is_deleted", False).execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cut.data)

    total_used = 0
    if log_type == "stage":
        res = supabase.table("stage_logs").select("id, so_luong").eq("lot_id", lot_id).eq("giai_doan", giai_doan).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "harvest":
        res = supabase.table("harvest_logs").select("id, so_luong").eq("lot_id", lot_id).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "destruction":
        res = supabase.table("destruction_logs").select("id, so_luong").eq("lot_id", lot_id).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
        
    return max_allowed, total_used


def allocate_fifo_quantity(farm_name, lo_name, new_sl, log_type, target_date, action_type, giai_doan=None):
    res_lots = supabase.table("base_lots").select("lot_id").eq("farm", farm_name).eq("lo", lo_name).eq("is_deleted", False).order("ngay_trong").execute()
    if not res_lots.data:
        return False, f"❌ Lỗi: Không tìm thấy lô {lo_name} hoặc đã bị xóa.", []
        
    remaining_to_allocate = int(new_sl)
    allocations = []
    total_available_all = 0
    
    for lot_row in res_lots.data:
        lot_id = lot_row["lot_id"]
        
        is_time_valid, _ = validate_timeline_logic(lot_id, target_date, action_type)
        if not is_time_valid:
            continue
            
        max_allowed, total_used = get_available_capacity_for_lot(lot_id, log_type, giai_doan)
        remain = max_allowed - total_used
        
        if remain > 0:
            total_available_all += remain
            if remaining_to_allocate > 0:
                consume = min(remaining_to_allocate, remain)
                allocations.append({"lot_id": lot_id, "so_luong": consume})
                remaining_to_allocate -= consume
                
    if remaining_to_allocate > 0:
        action_name = giai_doan.lower() if log_type == "stage" else ("xuất hủy" if log_type == "destruction" else "thu hoạch")
        return False, f"❌ Yêu cầu {new_sl} nhưng tổng số lượng cho phép của nhánh '{lo_name}' chỉ còn {total_available_all}.", []
        
    return True, "", allocations

def check_quantity_limit(lot_id, new_sl, log_type, giai_doan=None, exclude_id=None):
    max_allowed, total_used = get_available_capacity_for_lot(lot_id, log_type, giai_doan, exclude_id)
    unit = "buồng" if log_type == "harvest" else "cây"
    action_name = giai_doan.lower() if log_type == "stage" else ("xuất hủy" if log_type == "destruction" else "thu hoạch")

    if log_type == "destruction":
        if int(new_sl) > (max_allowed - total_used):
            return False, f"❌ Mã lứa này chỉ còn {max_allowed - total_used} cây sống, không thể xuất hủy {new_sl} cây."
        return True, ""

    if total_used + int(new_sl) > max_allowed:
        remain = max_allowed - total_used
        return False, f"❌ Bạn đã nhập {new_sl} {unit}, nhưng lứa này chỉ có {remain} {unit} cho phép."
    return True, ""

def validate_timeline_logic(lot_id, target_date, action_type):
    target_dt = pd.to_datetime(target_date).tz_localize(None)
    
    if action_type == "Chích bắp":
        res = supabase.table("base_lots").select("ngay_trong").eq("lot_id", lot_id).eq("is_deleted", False).execute()
        if res.data and res.data[0].get("ngay_trong"):
            ngay_trong = pd.to_datetime(res.data[0]["ngay_trong"]).tz_localize(None)
            if target_dt < ngay_trong:
                return False, f"❌ Ngày Chích bắp ({target_dt.date()}) không thể trước Ngày Trồng ({ngay_trong.date()})."
                
    elif action_type == "Cắt bắp":
        res = supabase.table("stage_logs").select("ngay_thuc_hien").eq("lot_id", lot_id).eq("giai_doan", "Chích bắp").eq("is_deleted", False).execute()
        if res.data:
            earliest_cb = min([pd.to_datetime(r["ngay_thuc_hien"]).tz_localize(None) for r in res.data])
            if target_dt < earliest_cb:
                return False, f"❌ Ngày Cắt bắp ({target_dt.date()}) không thể trước Ngày Chích bắp sớm nhất ({earliest_cb.date()})."
        else:
            return False, "❌ Lô này chưa được ghi nhận Chích bắp, không thể Cắt bắp!"
            
    elif action_type == "Thu hoạch":
        res = supabase.table("stage_logs").select("ngay_thuc_hien").eq("lot_id", lot_id).eq("giai_doan", "Cắt bắp").eq("is_deleted", False).execute()
        if res.data:
            earliest_cut = min([pd.to_datetime(r["ngay_thuc_hien"]).tz_localize(None) for r in res.data])
            if target_dt < earliest_cut:
                return False, f"❌ Ngày Thu hoạch ({target_dt.date()}) không thể trước Ngày Cắt bắp sớm nhất ({earliest_cut.date()})."
        else:
            return False, "❌ Lô này chưa được ghi nhận Cắt bắp, không thể Thu hoạch!"
            
    return True, ""


@dialog_decorator("⚠️ Xác nhận")
def confirm_action_dialog(action, table_name, rec_id_or_none, data_dict, success_msg):
    st.warning("Vui lòng kiểm tra kỹ trước khi thực hiện!")
    if not data_dict and action == "DELETE":
        st.error("Xóa dữ liệu vĩnh viễn?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Tôi đã kiểm tra kỹ", use_container_width=True):
            success = False
            if action == "INSERT":
                success = insert_to_db(table_name, data_dict)
            elif action == "INSERT_FIFO":
                db_data = data_dict["base_data"]
                allocations = data_dict["allocations"]
                success = True
                for alloc in allocations:
                    row_data = db_data.copy()
                    row_data["lot_id"] = alloc["lot_id"]
                    row_data["so_luong"] = alloc["so_luong"]
                    try:
                        supabase.table(table_name).insert(row_data).execute()
                    except Exception as e:
                        st.error(f"❌ Lỗi ghi hệ thống FIFO nhánh {alloc['lot_id']}: {e}")
                        success = False
            elif action == "INSERT_BASE":
                db_data, season_data = data_dict
                success = insert_to_db("base_lots", db_data)
                if success:
                    try:
                        supabase.table("seasons").insert(season_data).execute()
                    except Exception as e:
                        st.error(f"❌ Lỗi ghi vụ: {e}")
            elif action == "UPDATE":
                try:
                    supabase.table(table_name).update(data_dict).eq("id", rec_id_or_none).execute()
                    success = True
                except Exception as e:
                    st.error(f"❌ Lỗi cập nhật: {e}")
            elif action == "DELETE":
                try:
                    supabase.table(table_name).update({"is_deleted": True}).eq("id", rec_id_or_none).execute()
                    success = True
                except Exception as e:
                    st.error(f"❌ Lỗi xóa: {e}")
            
            if success:
                st.cache_data.clear()
                st.session_state["toast"] = success_msg
                st.rerun()
    with col2:
        if st.button("❌ Quay lại", use_container_width=True):
            st.rerun()

def get_editing_row(table_name, df):
    idx_list = st.session_state.get(f"sel_{table_name}", {}).get("selection", {}).get("rows", [])
    if idx_list and len(idx_list) > 0 and idx_list[0] < len(df):
        row = df.iloc[idx_list[0]].to_dict()
        created_at = pd.to_datetime(row["created_at"], utc=True)
        is_within_48h = created_at > (pd.Timestamp.utcnow() - pd.Timedelta(hours=48))
        return row, is_within_48h
    return None, False

def render_team_dataframe(table_name, df, display_cols):
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"sel_{table_name}"
    )

def render_queue_ui(queue_key, display_cols, process_func):
    """Render the queue and action buttons for bulk data entry."""
    queue = st.session_state[queue_key]
    if not queue:
        return
        
    st.markdown("#### 📋 Danh sách chờ duyệt")
    df_queue = pd.DataFrame(queue)
    df_queue.insert(0, "Xóa", False) # Thêm cột checkbox
    
    edited_df = st.data_editor(
        df_queue[["Xóa"] + display_cols],
        hide_index=True,
        use_container_width=True,
        disabled=display_cols,
        key=f"editor_{queue_key}"
    )
    
    to_delete_idxs = edited_df.index[edited_df["Xóa"] == True].tolist()
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        if st.button("🚀 Lưu toàn bộ lên Hệ thống", type="primary", use_container_width=True, key=f"btn_sb_{queue_key}"):
            process_func()
    with col_q2:
        if to_delete_idxs:
            if st.button("🗑️ Xóa dòng đã chọn", use_container_width=True, key=f"btn_del_sel_{queue_key}"):
                st.session_state[queue_key] = [item for i, item in enumerate(queue) if i not in to_delete_idxs]
                st.rerun()
        else:
            if st.button("🗑️ Xóa toàn bộ danh sách", use_container_width=True, key=f"btn_del_all_{queue_key}"):
                st.session_state[queue_key] = []
                st.rerun()

# =====================================================
# CÁC DIALOG CHỈNH SỬA
# =====================================================
@dialog_decorator("✏️ Chỉnh sửa Lô Trồng")
def edit_base_lot_dialog(editing_row):
    def_lo = editing_row["lo"]
    def_ngay = pd.to_datetime(editing_row["ngay_trong"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Tên Lô", value=def_lo, key="dlg_lo_base", disabled=True)
            st.info("⚠️ Không thể sửa thông tin Lô/Loại trồng. Nếu sai hãy Xóa và tạo mới Lô.")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay_trong = st.date_input("📆 Ngày trồng", value=def_ngay, key="dlg_dt_base")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay_trong.isocalendar()[1]), disabled=True, key=f"dlg_w_base_{ngay_trong}")
            so_luong = st.number_input("🔢 Số lượng", min_value=0, step=100, value=def_sl, key="dlg_sl_base")

        if st.button("✅ Cập nhật", key="btn_edit_base", use_container_width=True, type="primary"):
            if so_luong <= 0: st.error("❌ Cần nhập số lượng.")
            else:
                data = {
                    "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong,
                    "tuan": ngay_trong.isocalendar()[1]
                }
                supabase.table("base_lots").update(data).eq("id", editing_row["id"]).execute()
                
                # Cập nhật thêm cho season đang chạy nếu cần (tùy chọn)
                supabase.table("seasons").update({"ngay_bat_dau": ngay_trong.isoformat()}).eq("lo", def_lo).eq("vu", "F0").execute()
                
                st.session_state["toast"] = f"✅ Cập nhật {def_lo} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Tiến độ")
def edit_stage_log_dialog(editing_row, available_lots, c_team):
    gd_ops = ["Chích bắp"] if c_team == "Đội BVTV" else ["Cắt bắp"]
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_gd = gd_ops.index(editing_row["giai_doan"]) if editing_row["giai_doan"] in gd_ops else 0
    def_mau = str(editing_row.get("mau_day", ""))
    def_ngay = pd.to_datetime(editing_row["ngay_thuc_hien"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_lot_stg")
            lot_id = editing_row["lot_id"]
            giai_doan = st.radio("📌 Giai đoạn", options=gd_ops, index=def_gd, horizontal=True, key="dlg_gd_stg")
            mau_day = st.text_input("🎨 Màu dây", value=def_mau, key="dlg_mau_stg", placeholder="VD: Đỏ, Xanh lá...")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay_th = st.date_input("📆 Ngày thực hiện", value=def_ngay, key="dlg_dt_stg")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay_th.isocalendar()[1]), disabled=True, key=f"dlg_w_stg_{ngay_th}")
            sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100, value=def_sl, key="dlg_sl_stg")
        
        if st.button("✅ Cập nhật", key="btn_edit_stg", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập số lượng.")
            elif not mau_day.strip(): st.error("❌ Phải nhập màu dây định danh lứa.")
            else:
                mau_day_clean = mau_day.strip().capitalize()
                is_valid, msg = check_quantity_limit(lot_id, sl, "stage", giai_doan=giai_doan, exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    data = {
                        "lot_id": lot_id, "giai_doan": giai_doan, 
                        "ngay_thuc_hien": ngay_th.isoformat(), "so_luong": sl, "mau_day": mau_day_clean,
                        "tuan": ngay_th.isocalendar()[1]
                    }
                    supabase.table("stage_logs").update(data).eq("id", editing_row["id"]).execute()
                    st.session_state["toast"] = f"✅ Cập nhật tiến độ: {lot_id}!"
                    st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Báo cáo Xuất Hủy")
def edit_destruction_log_dialog(editing_row, available_lots):
    gd_ops = DESTRUCTION_STAGE_OPTIONS
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_gd = gd_ops.index(editing_row["giai_doan"]) if editing_row["giai_doan"] in gd_ops else 0
    def_ly_do = str(editing_row["ly_do"])
    def_mau = str(editing_row.get("mau_day", "") or "")
    def_ngay = pd.to_datetime(editing_row["ngay_xuat_huy"]).date()
    def_sl = int(editing_row["so_luong"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_lot_des")
            lot_id = editing_row["lot_id"]
            gxh = st.selectbox("⏱️ Giai đoạn", options=gd_ops, index=def_gd, key="dlg_gxh_des")
            mau_day = st.text_input("🎨 Màu dây", value=def_mau, key="dlg_mau_des", placeholder="VD: Đỏ, Xanh lá...")
            
            predefined_reasons = ["Bệnh", "Đổ Ngã", "Khác"]
            matched_reason = "Khác"
            if def_ly_do in ["Bệnh", "Đổ Ngã"]:
                matched_reason = def_ly_do
            
            if hasattr(st, "pills"):
                selected_reason = st.pills("📝 Nhóm lý do", options=predefined_reasons, default=matched_reason, key="dlg_des_reason_group")
                if not selected_reason:
                    selected_reason = "Khác"
            else:
                selected_reason = st.radio("📝 Nhóm lý do", options=predefined_reasons, index=predefined_reasons.index(matched_reason), horizontal=True, key="dlg_des_reason_group")
            
            if selected_reason == "Khác":
                ly_do = st.text_area("📝 Chi tiết lý do", height=80, value=def_ly_do if matched_reason == "Khác" else "", key="dlg_lydo_des")
            else:
                ly_do = selected_reason
                
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày xuất hủy", value=def_ngay, key="dlg_dt_des")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_des_{ngay}")
            sl = st.number_input("🔢 Số lượng xuất hủy", min_value=0, step=10, value=def_sl, key="dlg_sl_des")

        if st.button("✅ Cập nhật", key="btn_edit_des", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập số lượng.")
            elif not ly_do.strip(): st.error("❌ Cần ghi rõ lý do chi tiết.")
            else:
                mau_day_clean = mau_day.strip().capitalize() if mau_day.strip() else None
                is_valid, msg = check_quantity_limit(lot_id, sl, "destruction", exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    data = {"lot_id": lot_id, "ngay_xuat_huy": ngay.isoformat(), "giai_doan": gxh, "ly_do": ly_do.strip(), "so_luong": sl, "tuan": ngay.isocalendar()[1], "mau_day": mau_day_clean}
                    supabase.table("destruction_logs").update(data).eq("id", editing_row["id"]).execute()
                    st.session_state["toast"] = "✅ Đã cập nhật!"
                    st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Nhật ký Thu Hoạch")
def edit_harvest_log_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_mau = str(editing_row.get("mau_day", ""))
    
    hinh_thuc_opts = ["Bằng xe cày", "Bằng ròng rọc"]
    def_hinh_thuc = hinh_thuc_opts.index(editing_row.get("hinh_thuc_thu_hoach", "")) if editing_row.get("hinh_thuc_thu_hoach") in hinh_thuc_opts else 0
    
    def_ngay = pd.to_datetime(editing_row["ngay_thu_hoach"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_lot_har")
            lot_id = editing_row["lot_id"]
            mau_day = st.text_input("🎨 Màu dây", value=def_mau, key="dlg_mau_har", placeholder="VD: Đỏ, Xanh lá...")
            hinh_thuc_thu_hoach = st.selectbox("🚜 Hình thức thu hoạch", options=hinh_thuc_opts, index=def_hinh_thuc, key="dlg_hinh_thuc_har")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày thu hoạch", value=def_ngay, key="dlg_dt_har")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_har_{ngay}")
            sl = st.number_input("🍌 Số lượng buồng", min_value=0, step=50, value=def_sl, key="dlg_sl_har")

        if st.button("✅ Cập nhật", key="btn_edit_har", use_container_width=True, type="primary"):
            if not mau_day.strip(): st.error("❌ Cần nhập Màu dây.")
            elif sl <= 0: st.error("❌ Số lượng buồng phải > 0")
            else:
                mau_day_clean = mau_day.strip().capitalize()
                res_sm = supabase.table("size_measure_logs").select("id") \
                    .eq("lot_id", lot_id).eq("mau_day", mau_day_clean).eq("lan_do", 1).eq("is_deleted", False).execute()
                if not res_sm.data:
                    st.error(f"❌ Lô `{lot_id}` với màu dây `{mau_day_clean}` chưa trải qua Đo Size lần 1. Xin hãy nhắc Đội NT.")
                else:
                    is_valid, msg = check_quantity_limit(lot_id, sl, "harvest", exclude_id=editing_row["id"])
                    if not is_valid: st.error(msg)
                    else:
                        data = {
                            "lot_id": lot_id, "mau_day": mau_day_clean, 
                            "ngay_thu_hoach": ngay.isoformat(), "so_luong": sl, 
                            "hinh_thuc_thu_hoach": hinh_thuc_thu_hoach, "tuan": ngay.isocalendar()[1]
                        }
                        supabase.table("harvest_logs").update(data).eq("id", editing_row["id"]).execute()
                        st.session_state["toast"] = f"✅ Lưu thu hoạch {lot_id} thành công!"
                        st.rerun()

@dialog_decorator("✏️ Chỉnh sửa BSR")
def edit_bsr_log_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_ngay = pd.to_datetime(editing_row["ngay_nhap"]).date()
    def_bsr = float(editing_row["bsr"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_lot_bsr")
            lot_id = editing_row["lot_id"]
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày đóng gói", value=def_ngay, key="dlg_dt_bsr")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_bsr_{ngay}")
            bsr_val = st.number_input("📐 Tỷ lệ BSR", min_value=0.0, step=0.1, value=def_bsr, format="%.2f", key="dlg_v_bsr")

        if st.button("✅ Cập nhật", key="btn_edit_bsr", use_container_width=True, type="primary"):
            if bsr_val <= 0: st.error("❌ Tỷ lệ BSR phải > 0")
            else:
                data = {"lot_id": lot_id, "ngay_nhap": ngay.isoformat(), "bsr": bsr_val, "tuan": ngay.isocalendar()[1]}
                supabase.table("bsr_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Lưu BSR lô {lot_id} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Đo Size")
def edit_size_measure_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_mau = str(editing_row.get("mau_day", ""))
    def_lan_do = editing_row["lan_do"]
    def_ngay = pd.to_datetime(editing_row["ngay_do"]).date()
    def_sl = int(editing_row["so_luong_mau"])
    def_hkt = str(editing_row.get("hang_kiem_tra", ""))
    def_cal = float(editing_row.get("size_cal", 0.0))
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_sm_lot")
            lot_id = editing_row["lot_id"]
            mau_day = st.text_input("🎨 Màu dây", value=def_mau, key="dlg_sm_mau", placeholder="VD: Đỏ, Xanh lá...")
            lan_do = st.radio("📏 Lần đo", options=[1, 2], index=def_lan_do-1, horizontal=True, key="dlg_sm_lando")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày đo", value=def_ngay, key="dlg_sm_ngay")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_sm_{ngay}")
            col_b3, col_b4 = st.columns(2)
            with col_b3:
                hang_kiem_tra = st.text_input("📏 Hàng kiểm tra", value=def_hkt, key="dlg_sm_hkt")
            with col_b4:
                size_cal = st.number_input("📏 Size (Cal)", min_value=0.0, step=0.1, value=def_cal, key="dlg_sm_cal")
            sl = st.number_input("🔢 Số lượng buồng mẫu", min_value=0, step=10, value=def_sl, key="dlg_sm_sl")

        if st.button("✅ Cập nhật", key="btn_edit_sm", use_container_width=True, type="primary"):
            if not mau_day.strip(): st.error("❌ Cần nhập màu dây")
            elif sl <= 0: st.error("❌ Số lượng buồng mẫu > 0")
            else:
                mau_day_clean = mau_day.strip().capitalize()
                data = {
                    "lot_id": lot_id, "mau_day": mau_day_clean, "lan_do": lan_do,
                    "ngay_do": ngay.isoformat(), "so_luong_mau": sl, "tuan": ngay.isocalendar()[1],
                    "hang_kiem_tra": hang_kiem_tra.strip(), "size_cal": size_cal
                }
                supabase.table("size_measure_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Sửa đo size {lot_id} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Kiểm kê cây")
def edit_tree_inventory_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_ngay = pd.to_datetime(editing_row["ngay_kiem_ke"]).date()
    def_sl = int(editing_row["so_luong_cay_thuc_te"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_inv_lot")
            lot_id = editing_row["lot_id"]
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày kiểm kê", value=def_ngay, key="dlg_inv_ngay")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_inv_{ngay}")
            sl = st.number_input("🔢 Số lượng cây thực tế", min_value=0, step=100, value=def_sl, key="dlg_inv_sl")

        if st.button("✅ Cập nhật", key="btn_edit_inv", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập Số lượng cây lớn hơn 0.")
            else:
                data = {"lot_id": lot_id, "ngay_kiem_ke": ngay.isoformat(), "so_luong_cay_thuc_te": sl, "tuan": ngay.isocalendar()[1]}
                supabase.table("tree_inventory_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Lưu kiểm kê cây lô {lot_id} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Đo pH Đất")
def edit_soil_ph_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_lan_do = int(editing_row["lan_do"])
    def_ngay = pd.to_datetime(editing_row["ngay_do"]).date()
    def_val = float(editing_row["ph_value"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_ph_lot")
            lot_id = editing_row["lot_id"]
            st.number_input("Lần đo", value=def_lan_do, disabled=True, key="dlg_ph_lando")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày đo", value=def_ngay, key="dlg_ph_ngay")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_ph_{ngay}")
            val = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1, value=def_val, key="dlg_ph_val")

        if st.button("✅ Cập nhật", key="btn_edit_ph", use_container_width=True, type="primary"):
            if val <= 0: st.error("❌ Cần nhập giá trị pH hợp lệ.")
            else:
                data = {"lot_id": lot_id, "ngay_do": ngay.isoformat(), "ph_value": val, "tuan": ngay.isocalendar()[1]}
                supabase.table("soil_ph_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Lưu kết quả pH lô {lot_id} thành công!"
                st.rerun()

# MÀN HÌNH ĐĂNG NHẬP
# =====================================================
def render_login():
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)

    st.markdown('<p class="main-title">🍌 Trường Tồn Banana Tracker</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>🔐 Đăng nhập hệ thống</h3>", unsafe_allow_html=True)
        st.divider()

        # Chọn Farm
        selected_farm = st.selectbox("🏗️ Chọn Farm", options=FARMS, index=None, placeholder="Vui lòng chọn Farm...", key="login_farm")
        
        # Chọn Team thuộc Farm
        av_teams = list(RBAC_DB.get(selected_farm, {}).keys()) if selected_farm else []
        selected_team = st.selectbox("👥 Chọn Đội / Vai trò", options=av_teams, index=None, placeholder="Vui lòng chọn Đội / Vai trò...", key="login_team")

        # Nhập MK
        password = st.text_input("🔑 Mật khẩu", type="password", key="login_pass", placeholder="Nhập mật khẩu...")

        st.markdown("")
        if st.button("🚀 Đăng nhập", use_container_width=True, type="primary"):
            if not selected_farm:
                st.warning("⚠️ Vui lòng chọn Farm.")
            elif not selected_team:
                st.warning("⚠️ Vui lòng chọn Đội / Vai trò.")
            elif not password:
                st.warning("⚠️ Vui lòng nhập mật khẩu.")
            else:
                correct_pass = RBAC_DB.get(selected_farm, {}).get(selected_team)
                if password == correct_pass:
                    st.session_state["logged_in"] = True
                    st.session_state["current_farm"] = selected_farm
                    st.session_state["current_team"] = selected_team
                    
                    # Đăng nhập thành công -> lưu vào URL để tránh mất session khi nhấn F5
                    st.query_params["logged_in"] = "true"
                    st.query_params["farm"] = selected_farm
                    st.query_params["team"] = selected_team
                    
                    insert_access_log(selected_farm, selected_team, "Đăng nhập thành công")
                    st.success(f"✅ Đăng nhập {selected_team} - {selected_farm}!")
                    st.rerun()
                else:
                    insert_access_log(selected_farm, selected_team, "Sai mật khẩu")
                    st.error("❌ Mật khẩu không đúng.")

        st.divider()
        st.markdown("<p style='text-align: center; color: #888888; font-size: 0.85rem;'>💡 Vui lòng chọn đúng vai trò của mình để thao tác đúng nghiệp vụ.</p>", unsafe_allow_html=True)

def generate_cut_bap_excel(df_lots, df_stg, df_des) -> bytes:
    """Tạo file Excel báo cáo Cắt bắp theo tuần.
    Mỗi tuần cắt bắp có 1 màu dây duy nhất → 2 cột: CẮT BẮP + XUẤT HỦY."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo Cắt bắp"
    
    # Styles
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    cut_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    des_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    total_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Bảng màu pastel nhạt cho header Màu dây
    COLOR_MAP = {
        "đỏ": "FFB3B3", "cam": "FFD9B3", "vàng": "FFFFB3",
        "xanh lá": "B3FFB3", "xanh dương": "B3D9FF", "tím": "D9B3FF",
        "đen": "D9D9D9", "trắng": "F5F5F5", "hồng": "FFB3D9", "nâu": "D9C4B3",
    }
    def get_mau_day_fill(mau_day_name):
        base = mau_day_name.split("-")[0].strip().lower() if mau_day_name else ""
        hex_color = COLOR_MAP.get(base)
        if hex_color:
            return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
        return None
    
    # Get unique lots (sorted)
    lot_names = sorted(df_lots["lo"].unique().tolist()) if not df_lots.empty else []
    lot_id_map = {}
    if not df_lots.empty:
        for _, row in df_lots.iterrows():
            lo = row["lo"]
            if lo not in lot_id_map:
                lot_id_map[lo] = []
            lot_id_map[lo].append(row["lot_id"])
    
    # Filter Cắt bắp from stage_logs
    df_cut = df_stg[df_stg["giai_doan"] == "Cắt bắp"].copy() if not df_stg.empty and "giai_doan" in df_stg.columns else pd.DataFrame()
    
    # Determine weeks and their mau_day (1 color per week)
    week_color = {}  # {week_number: "Đỏ"}
    if not df_cut.empty and "tuan" in df_cut.columns and "mau_day" in df_cut.columns:
        for tuan_val in df_cut["tuan"].dropna().unique():
            week_num = int(tuan_val)
            colors_in_week = df_cut[df_cut["tuan"] == tuan_val]["mau_day"].dropna().unique()
            week_color[week_num] = str(colors_in_week[0]) if len(colors_in_week) > 0 else ""
    
    # Also include destruction weeks (they share the same week/color mapping)
    if not df_des.empty and "tuan" in df_des.columns:
        for tuan_val in df_des["tuan"].dropna().unique():
            week_num = int(tuan_val)
            if week_num not in week_color:
                colors_in_week = df_des[df_des["tuan"] == tuan_val]["mau_day"].dropna().unique() if "mau_day" in df_des.columns else []
                week_color[week_num] = str(colors_in_week[0]) if len(colors_in_week) > 0 else ""
    
    weeks = sorted(week_color.keys())
    
    if not weeks:
        # No data at all
        ws.cell(row=1, column=1, value="Chưa có dữ liệu Cắt bắp.")
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
    
    # === BUILD HEADER ===
    # Row 1: "Lô" + Week group headers (each week = 2 cols merged)
    # Row 2: CẮT BẮP | XUẤT HỦY per week
    # Row 3: Màu dây (colored) | Màu dây (colored) per week
    
    ws.cell(row=1, column=1, value="Lô").font = header_font
    ws.cell(row=1, column=1).fill = header_fill
    ws.cell(row=1, column=1).border = thin_border
    ws.cell(row=1, column=1).alignment = center_align
    ws.merge_cells(start_row=1, start_column=1, end_row=3, end_column=1)
    
    col_offset = 2
    week_col_map = {}  # {week: {"cut_col": int, "des_col": int}}
    
    for week in weeks:
        cut_col = col_offset
        des_col = col_offset + 1
        week_col_map[week] = {"cut_col": cut_col, "des_col": des_col}
        
        color_name = week_color.get(week, "")
        color_fill_cell = get_mau_day_fill(color_name)
        
        # Row 1: Week header (merged over 2 cols)
        ws.merge_cells(start_row=1, start_column=cut_col, end_row=1, end_column=des_col)
        c = ws.cell(row=1, column=cut_col, value=f"Tuần {week}")
        c.font = Font(bold=True, size=11)
        c.fill = header_fill
        c.alignment = center_align
        c.border = thin_border
        
        # Row 2: CẮT BẮP | XUẤT HỦY
        c1 = ws.cell(row=2, column=cut_col, value="CẮT BẮP")
        c1.font = Font(bold=True, color="006100")
        c1.fill = cut_fill
        c1.alignment = center_align
        c1.border = thin_border
        
        c2 = ws.cell(row=2, column=des_col, value="XUẤT HỦY")
        c2.font = Font(bold=True, color="9C0006")
        c2.fill = des_fill
        c2.alignment = center_align
        c2.border = thin_border
        
        # Row 3: Màu dây (colored header)
        c3 = ws.cell(row=3, column=cut_col, value=color_name)
        c3.font = Font(bold=True, size=9)
        c3.fill = color_fill_cell if color_fill_cell else cut_fill
        c3.alignment = center_align
        c3.border = thin_border
        
        c4 = ws.cell(row=3, column=des_col, value=color_name)
        c4.font = Font(bold=True, size=9)
        c4.fill = color_fill_cell if color_fill_cell else des_fill
        c4.alignment = center_align
        c4.border = thin_border
        
        col_offset += 2
    
    # Apply borders to merged header cells
    for r in range(1, 4):
        for c_idx in range(1, col_offset):
            ws.cell(row=r, column=c_idx).border = thin_border
    
    # === FILL DATA ROWS ===
    data_start_row = 4
    for li, lo_name in enumerate(lot_names):
        row_idx = data_start_row + li
        c = ws.cell(row=row_idx, column=1, value=lo_name)
        c.font = Font(bold=True)
        c.border = thin_border
        c.alignment = center_align
        
        valid_ids = lot_id_map.get(lo_name, [])
        
        for week in weeks:
            wm = week_col_map[week]
            
            # CẮT BẮP: sum so_luong for this lot × this week
            val_cut = 0
            if not df_cut.empty:
                mask = (df_cut["lot_id"].isin(valid_ids)) & (df_cut["tuan"] == week)
                val_cut = int(df_cut[mask]["so_luong"].sum())
            cell = ws.cell(row=row_idx, column=wm["cut_col"], value=val_cut if val_cut > 0 else "")
            cell.border = thin_border
            cell.alignment = center_align
            
            # XUẤT HỦY: sum so_luong for this lot × this week
            val_des = 0
            if not df_des.empty:
                mask = (df_des["lot_id"].isin(valid_ids)) & (df_des["tuan"] == week)
                val_des = int(df_des[mask]["so_luong"].sum())
            cell = ws.cell(row=row_idx, column=wm["des_col"], value=val_des if val_des > 0 else "")
            cell.border = thin_border
            cell.alignment = center_align
    
    # === TOTAL ROW ===
    total_row = data_start_row + len(lot_names)
    c = ws.cell(row=total_row, column=1, value="Tổng")
    c.font = Font(bold=True, size=11)
    c.fill = total_fill
    c.border = thin_border
    c.alignment = center_align
    
    for week in weeks:
        wm = week_col_map[week]
        for col_idx in [wm["cut_col"], wm["des_col"]]:
            total = 0
            for r in range(data_start_row, total_row):
                v = ws.cell(row=r, column=col_idx).value
                if v and isinstance(v, (int, float)):
                    total += int(v)
            c = ws.cell(row=total_row, column=col_idx, value=total if total > 0 else "")
            c.font = Font(bold=True)
            c.fill = total_fill
            c.border = thin_border
            c.alignment = center_align
    
    # Auto column width
    ws.column_dimensions[get_column_letter(1)].width = 8
    for c_idx in range(2, col_offset):
        ws.column_dimensions[get_column_letter(c_idx)].width = 12
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def render_global_data_tab(c_farm):
    st.markdown("### 🌐 Bảng dữ liệu Toàn cục Farm")
    st.caption("Khám phá dữ liệu tổng quan bằng các Biểu đồ phân tích và Bộ lọc.")
    
    # Fetch all data
    df_lots_all = fetch_table_data("base_lots", c_farm)
    df_stg_all = fetch_table_data("stage_logs", c_farm)
    df_des_all = fetch_table_data("destruction_logs", c_farm)
    df_har_all = fetch_table_data("harvest_logs", c_farm)
    df_bsr_all = fetch_table_data("bsr_logs", c_farm)
    df_tree_inv_all = fetch_table_data("tree_inventory_logs", c_farm)
    df_seasons = fetch_table_data("seasons", c_farm)

    # Nút Xuất Báo cáo Excel (Chứa toàn bộ dữ liệu thô)
    col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
    with col_t2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_lots_all.to_excel(writer, sheet_name='Base Lots (Lô trồng)', index=False)
            df_stg_all.to_excel(writer, sheet_name='Stage Logs (Tiến độ)', index=False)
            df_des_all.to_excel(writer, sheet_name='Destruction Logs', index=False)
            df_har_all.to_excel(writer, sheet_name='Harvest Logs (Thu Hoạch)', index=False)
            df_bsr_all.to_excel(writer, sheet_name='BSR Logs (Tỷ lệ)', index=False)
        output.seek(0)
        st.download_button(
            label="📥 Xuất Báo Cáo Excel",
            data=output.getvalue(),
            file_name=f"Bao_cao_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
    with col_t3:
        # Nút Xuất Báo cáo Cắt bắp
        cut_excel = generate_cut_bap_excel(df_lots_all, df_stg_all, df_des_all)
        st.download_button(
            label="✂️ Báo cáo Cắt bắp",
            data=cut_excel,
            file_name=f"Bao_cao_cat_bap_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
        
    st.divider()

    # Filter helpers
    farms_all = ["Tất cả"] + list(df_lots_all["farm"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    teams_all = ["Tất cả"] + list(df_lots_all["team"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    lots_all = ["Tất cả"] + list(df_lots_all["lo"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    seasons_all = ["Tất cả"] + list(df_seasons["vu"].dropna().unique()) if not df_seasons.empty else ["Tất cả"]

    def apply_filters_local(f_farm, f_vu, f_team, f_lot, f_date, df_dict):
        """Helper function to apply filters locally to a set of dataframes"""
        res = {}
        # Apply Season format
        valid_lots_season = None
        if f_vu != "Tất cả" and not df_seasons.empty:
            valid_lots_season = df_seasons[df_seasons["vu"] == f_vu]["lo"].tolist()

        for name, df in df_dict.items():
            if df.empty:
                res[name] = df
                continue
            
            df_filtered = df.copy()
            if f_farm != "Tất cả" and "farm" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["farm"] == f_farm]
            if valid_lots_season is not None and "lot_id" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["lot_id"].isin(valid_lots_season)]
            if f_team != "Tất cả" and "team" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["team"] == f_team]
            if f_lot != "Tất cả" and "lot_id" in df_filtered.columns:
                valid_ids = df_lots_all[df_lots_all["lo"] == f_lot]["lot_id"].tolist() if not df_lots_all.empty else []
                df_filtered = df_filtered[df_filtered["lot_id"].isin(valid_ids)]
            
            # Apply Date Range filter
            if f_date and len(f_date) == 2:
                start_date, end_date = f_date
                date_col = None
                if name == "lots" and "ngay_trong" in df_filtered.columns:
                    date_col = "ngay_trong"
                elif name == "stg" and "ngay_thuc_hien" in df_filtered.columns:
                    date_col = "ngay_thuc_hien"
                elif name == "des" and "ngay_xuat_huy" in df_filtered.columns:
                    date_col = "ngay_xuat_huy"
                elif name == "har" and "ngay_thu_hoach" in df_filtered.columns:
                    date_col = "ngay_thu_hoach"
                elif name == "inv" and "ngay_kiem_ke" in df_filtered.columns:
                    date_col = "ngay_kiem_ke"
                
                if date_col:
                    # Convert to datetime and then normalize to date for comparison
                    df_filtered[date_col] = pd.to_datetime(df_filtered[date_col])
                    df_filtered = df_filtered[
                        (df_filtered[date_col].dt.date >= start_date) & 
                        (df_filtered[date_col].dt.date <= end_date)
                    ]
            
            res[name] = df_filtered
        return res

    st.divider()

    st.divider()

    # --- BIỂU ĐỒ PHỄU TIẾN ĐỘ THEO LÔ ---
    st.markdown("#### 📊 Biểu đồ Phễu Tiến độ theo Lô (Pipeline Funnel)")
    st.caption("So sánh tương quan Mức độ Hao hụt và Năng suất từ lúc Xuống giống đến khi Thu hoạch.")
    
    # 1. Pipeline Chart Filters
    if c_farm == "Admin":
        cpf0, cpf1, cpf2, cpf3, cpf4 = st.columns([1, 1, 1, 1, 1.5])
        with cpf0:
            pf_farm = st.selectbox("Lọc theo Farm", options=farms_all, key="pf_farm")
        with cpf1:
            pf_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="pf_vu")
        with cpf2:
            pf_team = st.selectbox("Lọc theo Đội", options=teams_all, key="pf_team")
        with cpf3:
            pf_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="pf_lot")
        with cpf4:
            pf_date = st.date_input("Khoảng thời gian", value=(), key="pf_date")
    else:
        pf_farm = c_farm
        cpf1, cpf2, cpf3, cpf4 = st.columns([1, 1, 1, 1.5])
        with cpf1:
            pf_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="pf_vu")
        with cpf2:
            pf_team = st.selectbox("Lọc theo Đội", options=teams_all, key="pf_team")
        with cpf3:
            pf_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="pf_lot")
        with cpf4:
            pf_date = st.date_input("Khoảng thời gian", value=(), key="pf_date")
        
    filtered_pipe_dfs = apply_filters_local(pf_farm, pf_vu, pf_team, pf_lot, pf_date, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })
    
    pipe_lots_df = filtered_pipe_dfs["lots"]
    pipe_stg_df = filtered_pipe_dfs["stg"]
    pipe_har_df = filtered_pipe_dfs["har"]
    pipe_des_df = filtered_pipe_dfs["des"]

    # Gom dữ liệu để vẽ grouped bar chart
    if not pipe_lots_df.empty:
        lots = pipe_lots_df["lo"].unique()
        pipeline_data = []
        for l in lots:
            valid_ids = pipe_lots_df[pipe_lots_df["lo"] == l]["lot_id"].tolist()
            
            # 1. Trồng
            sl_trong = pipe_lots_df[pipe_lots_df["lo"] == l]["so_luong"].sum()
            pipeline_data.append({"Lô": l, "Giai đoạn": "1. Đã trồng", "Số lượng": sl_trong})
            
            # 2. Chích bắp
            if not pipe_stg_df.empty:
                sl_cb = pipe_stg_df[(pipe_stg_df["lot_id"].isin(valid_ids)) & (pipe_stg_df["giai_doan"] == "Chích bắp")]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "2. Chích bắp", "Số lượng": sl_cb})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "2. Chích bắp", "Số lượng": 0})
            
            # 3. Cắt bắp
            if not pipe_stg_df.empty:
                sl_cut = pipe_stg_df[(pipe_stg_df["lot_id"].isin(valid_ids)) & (pipe_stg_df["giai_doan"] == "Cắt bắp")]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "3. Cắt bắp", "Số lượng": sl_cut})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "3. Cắt bắp", "Số lượng": 0})
            
            # 4. Thu hoạch (Buồng ~ Cây)
            if not pipe_har_df.empty:
                sl_har = pipe_har_df[pipe_har_df["lot_id"].isin(valid_ids)]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "4. Thu hoạch", "Số lượng": sl_har})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "4. Thu hoạch", "Số lượng": 0})
                
            # 5. Xuất hủy
            if not pipe_des_df.empty:
                sl_des = pipe_des_df[pipe_des_df["lot_id"].isin(valid_ids)]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "5. Xuất hủy", "Số lượng": sl_des})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "5. Xuất hủy", "Số lượng": 0})
            
        df_pipeline = pd.DataFrame(pipeline_data)
        
        # Color mapping cho 5 giai đoạn
        color_map = {
            "1. Đã trồng": "#4CAF50",      # Green
            "2. Chích bắp": "#FFC107",     # Amber
            "3. Cắt bắp": "#FF9800",       # Orange
            "4. Thu hoạch": "#2196F3",     # Blue
            "5. Xuất hủy": "#F44336"       # Red
        }
        
        fig_pipe = px.bar(
            df_pipeline, x="Lô", y="Số lượng", color="Giai đoạn", barmode="group",
            color_discrete_map=color_map,
            labels={"Lô": "Danh sách Lô", "Số lượng": "Số lượng cây / buồng", "Giai đoạn": "Tiến trình"}
        )
        # Bỏ đi style rườm rà, format sang trọng
        fig_pipe.update_layout(plot_bgcolor="rgba(0,0,0,0)", yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)"})
        st.plotly_chart(fig_pipe, use_container_width=True)
    else:
        st.info("Chưa có danh sách lô để hiển thị biểu đồ Phễu.")

    st.divider()
    st.divider()
    st.markdown("##### 📉 Tiến trình Tổng hợp theo Thời gian")
    st.caption("Biểu đồ gộp thể hiện biến động các công đoạn dọc theo trục ngày. Có thể filter để làm nổi bật.")

    # 2. Multi-line Chart Filters
    if c_farm == "Admin":
        mlf0, mlf1, mlf2, mlf3, mlf4 = st.columns([1, 1, 1, 1, 1.5])
        with mlf0:
            mlf_farm = st.selectbox("Lọc theo Farm", options=farms_all, key="mlf_farm")
        with mlf1:
            mlf_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="mlf_vu")
        with mlf2:
            mlf_team = st.selectbox("Lọc theo Đội", options=teams_all, key="mlf_team")
        with mlf3:
            mlf_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="mlf_lot")
        with mlf4:
            mlf_date = st.date_input("Khoảng thời gian", value=(), key="mlf_date")
    else:
        mlf_farm = c_farm
        mlf1, mlf2, mlf3, mlf4 = st.columns([1, 1, 1, 1.5])
        with mlf1:
            mlf_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="mlf_vu")
        with mlf2:
            mlf_team = st.selectbox("Lọc theo Đội", options=teams_all, key="mlf_team")
        with mlf3:
            mlf_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="mlf_lot")
        with mlf4:
            mlf_date = st.date_input("Khoảng thời gian", value=(), key="mlf_date")
        
    filtered_ml_dfs = apply_filters_local(mlf_farm, mlf_vu, mlf_team, mlf_lot, mlf_date, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })

    ml_lots_df = filtered_ml_dfs["lots"]
    ml_stg_df = filtered_ml_dfs["stg"]
    ml_har_df = filtered_ml_dfs["har"]
    ml_des_df = filtered_ml_dfs["des"]

    plot_dfs = []
    
    # 1. Trồng
    if not ml_lots_df.empty and "ngay_trong" in ml_lots_df.columns:
        cols_to_keep = ["ngay_trong", "so_luong"]
        if "lot_id" in ml_lots_df.columns: cols_to_keep.append("lot_id")
        df_p = ml_lots_df[cols_to_keep].copy()
        df_p.rename(columns={"ngay_trong": "Date"}, inplace=True)
        df_p["Giai đoạn"] = "1. Đã trồng"
        plot_dfs.append(df_p)

    # 2. Chích bắp & Cắt bắp
    if not ml_stg_df.empty and "ngay_thuc_hien" in ml_stg_df.columns:
        cols_to_keep = ["ngay_thuc_hien", "so_luong", "giai_doan"]
        if "lot_id" in ml_stg_df.columns: cols_to_keep.append("lot_id")
        df_p = ml_stg_df[cols_to_keep].copy()
        df_p.rename(columns={"ngay_thuc_hien": "Date"}, inplace=True)
        df_p["Giai đoạn"] = df_p["giai_doan"].apply(lambda x: f"2. {x}" if x == "Chích bắp" else f"3. {x}")
        df_p.drop(columns=["giai_doan"], inplace=True)
        plot_dfs.append(df_p)

    # 3. Thu hoạch
    if not ml_har_df.empty and "ngay_thu_hoach" in ml_har_df.columns:
        cols_to_keep = ["ngay_thu_hoach", "so_luong"]
        if "lot_id" in ml_har_df.columns: cols_to_keep.append("lot_id")
        df_p = ml_har_df[cols_to_keep].copy()
        df_p.rename(columns={"ngay_thu_hoach": "Date"}, inplace=True)
        df_p["Giai đoạn"] = "4. Thu hoạch"
        plot_dfs.append(df_p)

    # 4. Xuất hủy
    if not ml_des_df.empty and "ngay_xuat_huy" in ml_des_df.columns:
        cols_to_keep = ["ngay_xuat_huy", "so_luong"]
        if "lot_id" in ml_des_df.columns: cols_to_keep.append("lot_id")
        df_p = ml_des_df[cols_to_keep].copy()
        df_p.rename(columns={"ngay_xuat_huy": "Date"}, inplace=True)
        df_p["Giai đoạn"] = "5. Xuất hủy"
        plot_dfs.append(df_p)

    if plot_dfs:
        df_combined = pd.concat(plot_dfs)
        df_combined["Date"] = pd.to_datetime(df_combined["Date"])

        # --- Breakdown text: số lượng theo từng Lô, dùng cho tooltip ---
        # Lấy tên lô từ lot_id nếu có (join base_lots)
        lot_name_map = {}
        if not ml_lots_df.empty and "lot_id" in ml_lots_df.columns and "lo" in ml_lots_df.columns:
            lot_name_map = ml_lots_df.set_index("lot_id")["lo"].to_dict()
        
        if "lot_id" in df_combined.columns:
            df_combined["Tên Lô"] = df_combined["lot_id"].map(lot_name_map).fillna(df_combined.get("lot_id", ""))
            df_breakdown = (
                df_combined.groupby(["Date", "Giai đoạn", "Tên Lô"], as_index=False)["so_luong"]
                .sum()
                .sort_values("so_luong", ascending=False)
            )
            def make_breakdown(grp):
                return "<br>".join(f"&nbsp;&nbsp;• {row['Tên Lô']}: {int(row['so_luong']):,}" for _, row in grp.iterrows())
            df_bd_text = (
                df_breakdown.groupby(["Date", "Giai đoạn"])
                .apply(make_breakdown)
                .reset_index(name="breakdown_text")
            )
        else:
            df_bd_text = None

        df_grouped = df_combined.groupby(["Date", "Giai đoạn"], as_index=False)["so_luong"].sum()
        df_grouped.sort_values(by="Date", inplace=True)

        if df_bd_text is not None:
            df_grouped = df_grouped.merge(df_bd_text, on=["Date", "Giai đoạn"], how="left")
            df_grouped["breakdown_text"] = df_grouped["breakdown_text"].fillna("")
        else:
            df_grouped["breakdown_text"] = ""

        all_stages = sorted(df_grouped["Giai đoạn"].unique().tolist())
        selected_stages = st.multiselect("Lọc và Nổi bật Giai đoạn", options=all_stages, default=all_stages, key="global_stage_hl")
        
        # Color mapping matching the funnel defaults
        color_map = {
            "1. Đã trồng": "#4CAF50",      # Green
            "2. Chích bắp": "#FFC107",     # Amber
            "3. Cắt bắp": "#FF9800",       # Orange
            "4. Thu hoạch": "#2196F3",     # Blue
            "5. Xuất hủy": "#F44336"       # Red
        }
        
        fig = px.line(
            df_grouped, x="Date", y="so_luong", color="Giai đoạn",
            markers=True, line_shape="linear", color_discrete_map=color_map,
            custom_data=["breakdown_text"],
            labels={"Date": "Ngày Thực hiện", "so_luong": "Số lượng (Cây/Buồng)"}
        )
        
        # Custom tooltip
        fig.update_traces(
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "📅 %{x|%d/%m/%Y}<br>"
                "Tổng: <b>%{y:,.0f}</b><br>"
                "Chi tiết theo Lô:<br>%{customdata[0]}"
                "<extra></extra>"
            )
        )
        
        # Highlight logic - fade out unselected
        if selected_stages and len(selected_stages) < len(all_stages):
            for trace in fig.data:
                if trace.name not in selected_stages:
                    trace.opacity = 0.15
                    trace.line.width = 1
                else:
                    trace.opacity = 1.0
                    trace.line.width = 3
        
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)"}, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có bất kỳ dữ liệu nào để vẽ biểu đồ dòng thời gian.")

    st.divider()
    st.markdown("##### 🌳 Sự số lượng cây thực tế (Kiểm kê)")
    st.caption("Theo dõi số lượng cây thực tế trên từng Lô qua các lần kiểm đếm.")
    
    # 3. Tree Inventory Filters
    if c_farm == "Admin":
        tif0, tif1, tif2, tif3, tif4 = st.columns([1, 1, 1, 1, 1.5])
        with tif0:
            ti_farm = st.selectbox("Lọc theo Farm", options=farms_all, key="ti_farm")
        with tif1:
            ti_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="ti_vu")
        with tif2:
            ti_team = st.selectbox("Lọc theo Đội", options=teams_all, key="ti_team")
        with tif3:
            ti_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="ti_lot")
        with tif4:
            ti_date = st.date_input("Khoảng thời gian", value=(), key="ti_date")
    else:
        ti_farm = c_farm
        tif1, tif2, tif3, tif4 = st.columns([1, 1, 1, 1.5])
        with tif1:
            ti_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key="ti_vu")
        with tif2:
            ti_team = st.selectbox("Lọc theo Đội", options=teams_all, key="ti_team")
        with tif3:
            ti_lot = st.selectbox("Lọc theo Lô", options=lots_all, key="ti_lot")
        with tif4:
            ti_date = st.date_input("Khoảng thời gian", value=(), key="ti_date")

    filtered_ti_dfs = apply_filters_local(ti_farm, ti_vu, ti_team, ti_lot, ti_date, {"inv": df_tree_inv_all})
    ti_inv_df = filtered_ti_dfs["inv"]
    
    if not ti_inv_df.empty and "ngay_kiem_ke" in ti_inv_df.columns:
        df_inv = ti_inv_df.copy()
        
        # Ánh xạ lot_id sang lo gốc
        mapped_dict = df_lots_all.set_index("lot_id")["lo"].to_dict() if not df_lots_all.empty else {}
        df_inv["Tên Lô"] = df_inv["lot_id"].map(lambda x: mapped_dict.get(x, x))
        
        df_inv["Ngày"] = pd.to_datetime(df_inv["ngay_kiem_ke"])
        df_inv_grouped = df_inv.groupby(["Ngày", "Tên Lô"], as_index=False)["so_luong_cay_thuc_te"].sum()
        df_inv_grouped.sort_values(by="Ngày", inplace=True)
        
        fig_inv = px.line(
            df_inv_grouped, x="Ngày", y="so_luong_cay_thuc_te", color="Tên Lô", 
            markers=True, line_shape="linear",
            labels={"Ngày": "Ngày Kiểm Kê", "so_luong_cay_thuc_te": "Số lượng cây", "Tên Lô": "Lô"},
        )
        fig_inv.update_layout(plot_bgcolor="rgba(0,0,0,0)", yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)"}, hovermode="x unified")
        st.plotly_chart(fig_inv, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu Kiểm kê cây trên farm này.")

# =====================================================
# GIAO DIỆN CHÍNH (MAIN APP) - ROLE BASED 
# =====================================================
def render_main_app():
    c_farm = st.session_state["current_farm"]
    c_team = st.session_state["current_team"]

    # --- SIDEBAR ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        else: st.markdown("### 🍌 Trường Tồn")
        
        st.divider()
        st.markdown(f'<span class="farm-badge">🏭 {c_farm}</span>', unsafe_allow_html=True)
        st.markdown(f'<span class="team-badge">👥 {c_team}</span>', unsafe_allow_html=True)
        st.caption(f"Đăng nhập lúc: {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
        st.divider()

        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            logout()
            st.rerun()
        st.divider()
        st.info("📌 Dữ liệu được lưu trên đám mây Supabase.")

    # --- HEADER ---
    if "toast" in st.session_state:
        st.success(st.session_state.pop("toast"))
        
    st.markdown(f'<p class="main-title">Hệ thống {c_team} - {c_farm}</p>', unsafe_allow_html=True)

    # =================================================
    # MODULE ADMIN
    # =================================================
    if c_farm == "Admin" and c_team == "Quản trị viên":
        tab_opts = ["🌐 Dữ liệu toàn cục", "👑 Quản trị Mùa Vụ"]
        active_tab = st.segmented_control("Chức năng", tab_opts, label_visibility="collapsed", key="tab_admin_menu", default=tab_opts[0])
        if active_tab is None: active_tab = tab_opts[0]
        
        if active_tab == tab_opts[1]:
            st.markdown("## 👑 Admin Dashboard - Quản trị Mùa Vụ & Hệ Thống")
            st.info("👋 Chào mừng Quản trị viên. Tại đây bạn có thể quản lý lịch sử Vụ cho từng lô.")
            
            res = supabase.table("seasons").select("*").eq("is_deleted", False).order("created_at", desc=True).execute()
            df_seasons = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            
            if df_seasons.empty:
                st.warning("Hiện tại hệ thống chưa có dữ liệu Vụ (Seasons). Vui lòng tạo lô ở Nông trường trước!")
                return
                
            f_farm = st.selectbox("Lọc Farm", options=["Tất cả"] + list(df_seasons["farm"].unique()))
            if f_farm != "Tất cả":
                df_seasons = df_seasons[df_seasons["farm"] == f_farm]
                
            st.markdown("### 📋 Danh sách Vụ (Seasons)")
            st.dataframe(
                df_seasons[["farm", "lo", "vu", "loai_trong", "ngay_bat_dau", "ngay_ket_thuc_thuc_te"]], 
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="sel_admin_seasons"
            )
            
            idx_list = st.session_state.get(f"sel_admin_seasons", {}).get("selection", {}).get("rows", [])
            if idx_list and len(idx_list) > 0 and idx_list[0] < len(df_seasons):
                row = df_seasons.iloc[idx_list[0]].to_dict()
                
                with st.container(border=True):
                    st.markdown(f"#### 🛠️ Chốt vụ: `{row['farm']}` - Lô `{row['lo']}` (Hiện tại: `{row['vu']}`)")
                    col1, col2 = st.columns(2)
                    with col1:
                        cur_end = row.get("ngay_ket_thuc_thuc_te")
                        def_date = pd.to_datetime(cur_end).date() if cur_end else date.today()
                        end_date = st.date_input("📆 Ngày kết thúc (Thực tế)", value=def_date)
                    with col2:
                        curr_v = str(row["vu"])
                        try:
                            next_v_num = int(curr_v.replace("F", "")) + 1
                        except:
                            next_v_num = 1
                        next_v = f"F{next_v_num}"
                        
                        auto_next = st.checkbox(f"🚀 Cho phép tự động tạo vụ nối tiếp: {next_v}", value=True)
                    
                    st.markdown("")
                    if st.button("💾 Lưu thay đổi & Chốt vụ", use_container_width=True, type="primary"):
                        try:
                            supabase.table("seasons").update({
                                "ngay_ket_thuc_thuc_te": end_date.isoformat()
                            }).eq("id", row["id"]).execute()
                            
                            if auto_next and not cur_end:
                                new_season = {
                                    "farm": row["farm"],
                                    "lo": row["lo"],
                                    "vu": next_v,
                                    "loai_trong": row["loai_trong"],
                                    "ngay_bat_dau": end_date.isoformat()
                                }
                                supabase.table("seasons").insert(new_season).execute()
                            
                            st.session_state["toast"] = f"✅ Đã chốt vụ {row['vu']} thành công!"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi khi chốt vụ: {e}")
        elif active_tab == tab_opts[0]:
            render_global_data_tab("Admin")
        return

    # =================================================
    # MODULE 4: QUẢN LÝ FARM
    # =================================================
    if c_team == "Quản lý farm":
        st.markdown("## 📊 Dashboard Quản Lý Farm")
        st.info("👋 Chế độ chỉ xem (Read-only). Tương tác với các biểu đồ bên dưới để phân tích dữ liệu.")
        render_global_data_tab(c_farm)
        return

    # =================================================
    # MODULE 1: ĐỘI NÔNG TRƯỜNG (NT1, NT2)
    # =================================================
    # MODULE 1: ĐỘI NÔNG TRƯỜNG (NT1, NT2)
    # =================================================
    if c_team in ["NT1", "NT2", "Đội BVTV"]:
        if c_team == "Đội BVTV":
            tab_opts = ["🌐 Dữ liệu toàn cục", "📈 Cập nhật Tiến độ"]
        else:
            tab_opts = ["🌐 Dữ liệu toàn cục", "🌱 Khởi tạo Lô trồng", "📈 Cập nhật Tiến độ", "📏 Đo Size", "🗑️ Cập nhật Xuất hủy", "🌳 Kiểm kê cây", "🧪 Đo pH Đất"]
            
        active_tab = st.segmented_control("Chức năng", tab_opts, label_visibility="collapsed", key="tab_nt_menu", default=tab_opts[0])
        if active_tab is None: active_tab = tab_opts[0] # Prevent empty state

        # TAB 1: KHỞI TẠO LÔ
        if active_tab == "🌱 Khởi tạo Lô trồng":
            st.markdown("#### Đăng ký đợt xuống giống mới")
            df_lots = fetch_table_data("base_lots", c_farm)
            df_lots_team = df_lots[df_lots["team"] == c_team] if not df_lots.empty else pd.DataFrame()
            editing_row, is_within_48h = get_editing_row("base_lots", df_lots_team)
            is_editing = editing_row is not None
            
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    lo = st.text_input("🏷️ Tên Lô (VD: A1, B3...)", placeholder="Nhập tên lô...", key="add_base_lo")
                    loai_trong = st.selectbox("🌱 Loại trồng", options=LOAI_TRONG_OPTIONS, key="add_base_loai")
                with col_b:
                    col_b1, col_b2 = st.columns([2, 1])
                    with col_b1:
                        ngay_trong = st.date_input("📆 Ngày trồng", value=date.today(), key="add_base_ngay")
                    with col_b2:
                        st.text_input("📍 Tuần", value=str(ngay_trong.isocalendar()[1]), disabled=True, key=f"main_w_base_{ngay_trong}")
                    so_luong = st.number_input("🔢 Số lượng trồng (cây)", min_value=0, step=100, key="add_base_sl")

                if st.button("✅ Tạo Lô Trồng", key="btn_add_base", use_container_width=True, type="primary"):
                    if not lo.strip(): st.error("❌ Nhập tên lô.")
                    elif so_luong <= 0: st.error("❌ Cần nhập số lượng.")
                    else:
                        ten_lo_goc = lo.strip().upper()
                        ngay_trong_str = ngay_trong.strftime('%d%m%Y')
                        lot_id = f"{ten_lo_goc}_{ngay_trong_str}"
                        data_base = {
                            "farm": c_farm, "team": c_team, "lo": ten_lo_goc,
                            "lot_id": lot_id,
                            "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong,
                            "so_luong_con_lai": so_luong,
                            "tuan": ngay_trong.isocalendar()[1]
                        }
                        data_season = {
                            "farm": c_farm, "lo": lot_id, "vu": "F0",
                            "loai_trong": loai_trong,
                            "ngay_bat_dau": ngay_trong.isoformat()
                        }
                        confirm_action_dialog("INSERT_BASE", "base_lots", None, (data_base, data_season), f"✅ Tạo Lô {lot_id} thành công!")

            st.markdown("---")
            col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
            with col_t:
                st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
            if is_editing and is_within_48h:
                with col_e:
                    if st.button("✏️ Chỉnh sửa", key="edit_base_nt", use_container_width=True):
                        edit_base_lot_dialog(editing_row)
                with col_d:
                    if st.button("🗑️ Xóa", key="del_base_nt", use_container_width=True):
                        confirm_action_dialog("DELETE", "base_lots", editing_row["id"], None, f"✅ Đã xóa thành công lô {editing_row.get('lot_id')}!")
            elif is_editing and not is_within_48h:
                with col_e: st.caption("🔒 Quá 48h")

            render_team_dataframe("base_lots", df_lots_team, ["lot_id", "ngay_trong", "so_luong", "created_at"])

        # TAB: ĐO SIZE (DÀNH CHO NT1/NT2)
        elif active_tab == "📏 Đo Size":
            st.markdown("#### Đo kích thước buồng mẫu")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào.")
            else:
                df_sm = fetch_table_data("size_measure_logs", c_farm)
                df_sm_team = df_sm[df_sm["team"] == c_team] if not df_sm.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("size_measure_logs", df_sm_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="add_sm_lot")
                        mau_day = st.text_input("🎨 Màu dây", placeholder="VD: Đỏ, Xanh lá...", key="add_sm_mau")
                        lan_do = st.radio("📏 Lần đo", options=[1, 2], horizontal=True, key="add_sm_lando")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay_do = st.date_input("📆 Ngày đo", value=date.today(), key="add_sm_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay_do.isocalendar()[1]), disabled=True, key=f"main_w_sm_{ngay_do}")
                        col_b3, col_b4 = st.columns(2)
                        with col_b3:
                            hang_kiem_tra = st.text_input("📏 Hàng kiểm tra", placeholder="VD: H1-H5", key="add_sm_hkt")
                        with col_b4:
                            size_cal = st.number_input("📏 Size (Cal)", min_value=0.0, step=0.1, key="add_sm_cal")
                        sl = st.number_input("🔢 Số lượng buồng mẫu", min_value=0, step=10, key="add_sm_sl")
                    
                    if st.button("➕ Thêm vào Danh sách", key="btn_add_sm", use_container_width=True, type="secondary"):
                        if not mau_day.strip(): st.error("❌ Phải nhập màu dây")
                        elif sl <= 0: st.error("❌ Số lượng buồng > 0")
                        else:
                            mau_day_clean = mau_day.strip().capitalize()
                            # Validation: Nếu chọn là Lần 2, phải kiểm tra xem Lần 1 đã có chưa.
                            if lan_do == 2:
                                res_lan1 = supabase.table("size_measure_logs") \
                                    .select("id").eq("lot_id", lot_id).eq("mau_day", mau_day_clean).eq("lan_do", 1).eq("is_deleted", False).execute()
                                if not res_lan1.data:
                                    st.error(f"❌ Không thể đo Lần 2. Lô `{lot_id}` với màu dây `{mau_day_clean}` chưa được đo Lần 1.")
                                    st.stop()
                                    
                            st.session_state["queue_sm"].append({
                                "Lô": lot_id, "Màu dây": mau_day_clean, "Lần đo": lan_do, "Số lượng": sl,
                                "Ngày đo": ngay_do.isoformat(), "Tuần": ngay_do.isocalendar()[1],
                                "Hàng KT": hang_kiem_tra.strip(), "Size": size_cal
                            })
                            st.rerun()

                def process_sm_queue():
                    queue = st.session_state["queue_sm"]
                    success_count = 0
                    for item in queue:
                        data = {
                            "farm": c_farm, "team": c_team, "lot_id": item["Lô"],
                            "mau_day": item["Màu dây"], "lan_do": item["Lần đo"], "so_luong_mau": item["Số lượng"],
                            "ngay_do": item["Ngày đo"], "tuan": item["Tuần"],
                            "hang_kiem_tra": item["Hàng KT"], "size_cal": item["Size"]
                        }
                        try:
                            supabase.table("size_measure_logs").insert(data).execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Lỗi ghi: {e}")
                            return
                    st.session_state["queue_sm"] = []
                    st.session_state["toast"] = f"✅ Đã lưu {success_count} dòng Đo Size!"
                    st.cache_data.clear()
                    st.rerun()

                render_queue_ui("queue_sm", ["Lô", "Màu dây", "Lần đo", "Số lượng", "Hàng KT", "Size", "Ngày đo", "Tuần"], process_sm_queue)
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Sửa", key="edit_sm_nt", use_container_width=True):
                            edit_size_measure_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_sm_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "size_measure_logs", editing_row["id"], None, "✅ Đã xóa Đo Size!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    
                render_team_dataframe("size_measure_logs", df_sm_team, ["lot_id", "mau_day", "lan_do", "hang_kiem_tra", "size_cal", "so_luong_mau", "ngay_do"])

        # TAB: CẬP NHẬT KIỂM KÊ CÂY
        elif active_tab == "🌳 Kiểm kê cây":
            st.markdown("#### Báo cáo số lượng cây thực tế (Ngẫu nhiên / Tháng)")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào.")
            else:
                df_inv = fetch_table_data("tree_inventory_logs", c_farm)
                df_inv_team = df_inv[df_inv["team"] == c_team] if not df_inv.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("tree_inventory_logs", df_inv_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="add_inv_lot")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay_kk = st.date_input("📆 Ngày kiểm kê", value=date.today(), key="add_inv_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay_kk.isocalendar()[1]), disabled=True, key=f"main_w_inv_{ngay_kk}")
                        sl = st.number_input("🔢 Số lượng cây thực tế", min_value=0, step=100, key="add_inv_sl")
                    
                    if st.button("➕ Thêm vào Danh sách", key="btn_add_inv", use_container_width=True, type="secondary"):
                        if sl <= 0: st.error("❌ Số lượng phải lớn hơn 0")
                        else:
                            st.session_state["queue_inv"].append({
                                "Lô": lot_id, "Số lượng": sl, "Ngày": ngay_kk.isoformat(), "Tuần": ngay_kk.isocalendar()[1]
                            })
                            st.rerun()

                def process_inv_queue():
                    queue = st.session_state["queue_inv"]
                    success_count = 0
                    for item in queue:
                        data = {
                            "farm": c_farm, "team": c_team, "lot_id": item["Lô"],
                            "so_luong_cay_thuc_te": item["Số lượng"], "ngay_kiem_ke": item["Ngày"],
                            "tuan": item["Tuần"]
                        }
                        try:
                            supabase.table("tree_inventory_logs").insert(data).execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Lỗi ghi: {e}")
                            return
                    st.session_state["queue_inv"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Đã lưu {success_count} dòng Kiểm kê!"
                    st.rerun()

                render_queue_ui("queue_inv", ["Lô", "Số lượng", "Ngày", "Tuần"], process_inv_queue)
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Sửa", key="edit_inv_nt", use_container_width=True):
                            edit_tree_inventory_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_inv_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "tree_inventory_logs", editing_row["id"], None, "✅ Đã xóa nhật ký kiểm kê!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    
                render_team_dataframe("tree_inventory_logs", df_inv_team, ["lot_id", "ngay_kiem_ke", "so_luong_cay_thuc_te"])

        # TAB: ĐO PH ĐẤT
        elif active_tab == "🧪 Đo pH Đất":
            st.markdown("#### Ghi nhận kết quả Đo pH Đất")
            available_lots = get_lots_by_farm(c_farm)
            
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào trên hệ thống.")
            else:
                df_ph = fetch_table_data("soil_ph_logs", c_farm)
                df_ph_team = df_ph[df_ph["team"] == c_team] if not df_ph.empty else pd.DataFrame()
                
                with st.container(border=True):
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="add_ph_lot")
                    with col_b:
                        ngay_do = st.date_input("📆 Ngày đo", value=date.today(), key="add_ph_ngay")
                    with col_c:
                        tuan_do = st.text_input("📍 Tuần", value=str(ngay_do.isocalendar()[1]), disabled=True, key=f"add_ph_tuan_{ngay_do}")
                    
                    st.markdown("---")
                    
                    @st.fragment
                    def render_ph_inputs():
                        if "ph_measure_count" not in st.session_state:
                            st.session_state.ph_measure_count = 1
                        
                        ph_data = []
                        for i in range(1, st.session_state.ph_measure_count + 1):
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"**Lần đo {i}**")
                            with col2:
                                val = st.number_input(f"pH", min_value=0.0, max_value=14.0, step=0.1, key=f"add_ph_val_{i}", label_visibility="collapsed")
                                ph_data.append(val)
                                
                        st.markdown("")
                        col_btn_add, col_btn_save = st.columns(2)
                        with col_btn_add:
                            if st.button("➕ Thêm lần đo", use_container_width=True, type="secondary"):
                                st.session_state.ph_measure_count += 1
                                st.rerun()
                                
                        with col_btn_save:
                            if st.button("🚀 Lưu kết quả", use_container_width=True, type="primary"):
                                success_count = 0
                                for lan, val in enumerate(ph_data, start=1):
                                    if val > 0:
                                        data = {
                                            "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                            "ngay_do": ngay_do.isoformat(), "tuan": ngay_do.isocalendar()[1],
                                            "lan_do": lan, "ph_value": val
                                        }
                                        try:
                                            supabase.table("soil_ph_logs").insert(data).execute()
                                            success_count += 1
                                        except Exception as e:
                                            st.error(f"❌ Lỗi ghi Lần {lan}: {e}")
                                
                                if success_count > 0:
                                    st.session_state.ph_measure_count = 1
                                    st.cache_data.clear()
                                    st.session_state["toast"] = f"✅ Ghi nhận {success_count} kết quả Đo pH thành công!"
                                    st.rerun()

                    render_ph_inputs()
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                
                editing_row, is_within_48h = get_editing_row("soil_ph_logs", df_ph_team)
                is_editing = editing_row is not None
                
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_ph_nt", use_container_width=True):
                            edit_soil_ph_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_ph_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "soil_ph_logs", editing_row["id"], None, "✅ Đã xóa kết quả đo pH!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    with col_d: st.empty()
                else:
                    with col_e: st.empty()
                    with col_d: st.empty()
                    
                render_team_dataframe("soil_ph_logs", df_ph_team, ["lot_id", "ngay_do", "lan_do", "ph_value"])

        # TAB 2: CẬP NHẬT TIẾN ĐỘ NT
        elif active_tab == "📈 Cập nhật Tiến độ":
            st.markdown("#### Ghi nhận: Chích bắp / Cắt bắp")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào. Hãy tạo ở Tab 1.")
            else:
                df_stg = fetch_table_data("stage_logs", c_farm)
                df_stg_team = df_stg[df_stg["team"] == c_team] if not df_stg.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("stage_logs", df_stg_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="add_stg_lot")
                        if c_team == "Đội BVTV":
                            giai_doan_opts = ["Chích bắp"]
                        else:
                            giai_doan_opts = ["Cắt bắp"]
                        giai_doan = st.radio("📌 Giai đoạn", options=giai_doan_opts, horizontal=True, key="add_stg_gd")
                        mau_day = st.text_input("🎨 Màu dây", placeholder="VD: Đỏ, Xanh lá...", key="add_stg_mau")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay_th = st.date_input("📆 Ngày thực hiện", value=date.today(), key="add_stg_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay_th.isocalendar()[1]), disabled=True, key=f"main_w_stg_{ngay_th}")
                        sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100, key="add_stg_sl")

                    if st.button("➕ Thêm vào Danh sách", key="btn_add_stg", use_container_width=True, type="secondary"):
                        if sl <= 0: st.error("❌ Nhập số lượng > 0.")
                        elif not mau_day.strip(): st.error("❌ Phải nhập màu dây định danh lứa.")
                        else:
                            mau_day_clean = mau_day.strip().capitalize()
                            is_time_valid, msg_time = validate_timeline_logic(lot_id, ngay_th, giai_doan)
                            if not is_time_valid:
                                st.error(msg_time)
                            else:
                                st.session_state["queue_stg"].append({
                                    "Lô": lot_id, "Giai đoạn": giai_doan, "Màu dây": mau_day_clean,
                                    "Ngày": ngay_th.isoformat(), "Số lượng": sl, "Tuần": ngay_th.isocalendar()[1]
                                })
                                st.rerun()

                def process_stg_queue():
                    queue = st.session_state["queue_stg"]
                    lot_reqs = {}
                    for item in queue:
                        k = (item["Lô"], item["Giai đoạn"])
                        lot_reqs[k] = lot_reqs.get(k, 0) + item["Số lượng"]
                    for (l_id, g_doan), req_sl in lot_reqs.items():
                        valid, msg = check_quantity_limit(l_id, req_sl, "stage", giai_doan=g_doan)
                        if not valid:
                            st.error(f"❌ Lỗi tổng số lượng ở Lô {l_id} - {g_doan}: {msg}")
                            return
                    success_count = 0
                    for item in queue:
                        is_valid, msg, allocations = allocate_fifo_quantity(c_farm, item["Lô"], item["Số lượng"], "stage", item["Ngày"], item["Giai đoạn"], item["Giai đoạn"])
                        if is_valid:
                            for alloc in allocations:
                                data = {"farm": c_farm, "team": c_team, "giai_doan": item["Giai đoạn"], "ngay_thuc_hien": item["Ngày"], "mau_day": item["Màu dây"], "tuan": item["Tuần"], "lot_id": alloc["lot_id"], "so_luong": alloc["so_luong"]}
                                try:
                                    supabase.table("stage_logs").insert(data).execute()
                                except Exception as e:
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}: {e}")
                                    return
                            success_count += 1
                        else:
                            st.error(msg)
                            return
                    st.session_state["queue_stg"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Đã lưu {success_count} dòng Tiến độ!"
                    st.rerun()

                render_queue_ui("queue_stg", ["Lô", "Giai đoạn", "Màu dây", "Số lượng", "Ngày", "Tuần"], process_stg_queue)

                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_stg_nt", use_container_width=True):
                            edit_stage_log_dialog(editing_row, available_lots, c_team)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_stg_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "stage_logs", editing_row["id"], None, "✅ Đã xóa thành công!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                
                render_team_dataframe("stage_logs", df_stg_team, ["lot_id", "giai_doan", "ngay_thuc_hien", "so_luong", "mau_day"])

        # TAB 3: XUẤT HỦY
        elif active_tab == "🗑️ Cập nhật Xuất hủy":
            st.markdown("#### Ghi nhận số lượng cây chết / hư hỏng")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào.")
            else:
                df_des = fetch_table_data("destruction_logs", c_farm)
                df_des_team = df_des[df_des["team"] == c_team] if not df_des.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("destruction_logs", df_des_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="add_des_lot")
                        giai_doan_xuat_huy = st.selectbox("⏱️ Giai đoạn xuất hủy", options=DESTRUCTION_STAGE_OPTIONS, key="add_des_gxh")
                        mau_day_des = st.text_input("🎨 Màu dây", placeholder="VD: Đỏ, Xanh lá...", key="add_des_mau")
                        
                        predefined_reasons = ["Bệnh", "Đổ Ngã", "Khác"]
                        if hasattr(st, "pills"):
                            selected_reason = st.pills("📝 Nhóm lý do", options=predefined_reasons, key="add_des_reason_group")
                            if not selected_reason:
                                selected_reason = "Khác"
                        else:
                            selected_reason = st.radio("📝 Nhóm lý do", options=predefined_reasons, horizontal=True, key="add_des_reason_group")
                            
                        if selected_reason == "Khác":
                            ly_do = st.text_area("📝 Chi tiết lý do (Bắt buộc)", height=80, key="add_des_lydo")
                        else:
                            ly_do = selected_reason
                            
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay = st.date_input("📆 Ngày xuất hủy", value=date.today(), key="add_des_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"main_w_des_{ngay}")
                        sl = st.number_input("🔢 Số lượng cây xuất hủy", min_value=0, step=10, key="add_des_sl")

                    if st.button("➕ Thêm vào Danh sách", key="btn_add_des", use_container_width=True, type="secondary"):
                        if sl <= 0: st.error("❌ Nhập số lượng > 0.")
                        elif selected_reason == "Khác" and not ly_do.strip(): st.error("❌ Cần ghi rõ chi tiết lý do (khi chọn Khác).")
                        else:
                            mau_day_clean = mau_day_des.strip().capitalize() if mau_day_des.strip() else ""
                            st.session_state["queue_des"].append({
                                "Lô": lot_id, "Giai đoạn": giai_doan_xuat_huy, "Màu dây": mau_day_clean, "Lý do": ly_do.strip(),
                                "Ngày": ngay.isoformat(), "Số lượng": sl, "Tuần": ngay.isocalendar()[1]
                            })
                            st.rerun()

                def process_des_queue():
                    queue = st.session_state["queue_des"]
                    lot_reqs = {}
                    for item in queue:
                        lot_reqs[item["Lô"]] = lot_reqs.get(item["Lô"], 0) + item["Số lượng"]
                    for l_id, req_sl in lot_reqs.items():
                        valid, msg = check_quantity_limit(l_id, req_sl, "destruction")
                        if not valid:
                            st.error(f"❌ Lỗi tổng số lượng ở Lô {l_id}: {msg}")
                            return
                    success_count = 0
                    for item in queue:
                        is_valid, msg, allocations = allocate_fifo_quantity(c_farm, item["Lô"], item["Số lượng"], "destruction", item["Ngày"], "Xuất hủy")
                        if is_valid:
                            for alloc in allocations:
                                data = {"farm": c_farm, "team": c_team, "ngay_xuat_huy": item["Ngày"], "giai_doan": item["Giai đoạn"], "mau_day": item.get("Màu dây", "") or None, "ly_do": item["Lý do"], "tuan": item["Tuần"], "lot_id": alloc["lot_id"], "so_luong": alloc["so_luong"]}
                                try:
                                    supabase.table("destruction_logs").insert(data).execute()
                                except Exception as e:
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}: {e}")
                                    return
                            success_count += 1
                        else:
                            st.error(msg)
                            return
                    st.session_state["queue_des"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Đã lưu xuất hủy {success_count} dòng!"
                    st.rerun()

                render_queue_ui("queue_des", ["Lô", "Giai đoạn", "Màu dây", "Lý do", "Số lượng", "Ngày", "Tuần"], process_des_queue)

                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_des_nt", use_container_width=True):
                            edit_destruction_log_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_des_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "destruction_logs", editing_row["id"], None, "✅ Đã xóa xuất hủy!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    
                render_team_dataframe("destruction_logs", df_des_team, ["lot_id", "ngay_xuat_huy", "giai_doan", "mau_day", "so_luong", "ly_do"])

        # TAB 4: DỮ LIỆU TOÀN CỤC
        elif active_tab == "🌐 Dữ liệu toàn cục":
            render_global_data_tab(c_farm)

    # =================================================
    # MODULE 2: ĐỘI THU HOẠCH
    # =================================================
    elif c_team == "Đội Thu Hoạch":
        tab_opts = ["🌐 Dữ liệu toàn cục", "🍌 Nhật ký Thu Hoạch"]
        active_tab = st.segmented_control("Chức năng", tab_opts, label_visibility="collapsed", key="tab_har_menu", default=tab_opts[0])
        if active_tab is None: active_tab = tab_opts[0]
        
        if active_tab == tab_opts[1]:
            st.markdown("#### Ghi nhận Sản lượng Thu hoạch hàng ngày")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào trên hệ thống.")
            else:
                df_har = fetch_table_data("harvest_logs", c_farm)
                df_har_team = df_har[df_har["team"] == c_team] if not df_har.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("harvest_logs", df_har_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô thu hoạch", options=available_lots, key="add_har_lot")
                        mau_day = st.text_input("🎨 Màu dây", placeholder="VD: Đỏ, Xanh lá...", key="add_har_mau")
                        hinh_thuc_thu_hoach = st.selectbox("🚜 Hình thức thu hoạch", options=["Bằng xe cày", "Bằng ròng rọc"], key="add_har_hinh_thuc")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay = st.date_input("📆 Ngày thu hoạch", value=date.today(), key="add_har_dt")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"main_w_har_{ngay}")
                        sl = st.number_input("🍌 Số lượng buồng thu hoạch", min_value=0, step=50, key="add_har_sl")
    
                    st.markdown("")
                    if st.button("➕ Thêm vào Danh sách", key="btn_add_har", use_container_width=True, type="secondary"):
                        if not mau_day.strip(): st.error("❌ Cần nhập Màu dây.")
                        elif sl <= 0: st.error("❌ Số lượng buồng phải > 0")
                        else:
                            mau_day_clean = mau_day.strip().capitalize()
                            # Validation: Bắt buộc đã đo size lần 1 cho lô và màu dây này
                            res_sm = supabase.table("size_measure_logs").select("id") \
                                .eq("lot_id", lot_id).eq("mau_day", mau_day_clean).eq("lan_do", 1).eq("is_deleted", False).execute()
                            if not res_sm.data:
                                st.error(f"❌ Cảnh báo: Lô `{lot_id}` với màu dây `{mau_day_clean}` chưa qua Đo Size lần 1. Hãy nhắc NT.")
                                st.stop()
                                
                            st.session_state["queue_har"].append({
                                "Lô": lot_id, "Màu dây": mau_day_clean, "Hình thức": hinh_thuc_thu_hoach,
                                "Số lượng": sl, "Ngày": ngay.isoformat(), "Tuần": ngay.isocalendar()[1]
                            })
                            st.rerun()

                def process_har_queue():
                    queue = st.session_state["queue_har"]
                    lot_reqs = {}
                    for item in queue:
                        lot_reqs[item["Lô"]] = lot_reqs.get(item["Lô"], 0) + item["Số lượng"]
                    for l_id, req_sl in lot_reqs.items():
                        valid, msg = check_quantity_limit(l_id, req_sl, "harvest")
                        if not valid:
                            st.error(f"❌ Lỗi tổng số lượng ở Lô {l_id}: {msg}")
                            return
                    success_count = 0
                    for item in queue:
                        is_valid, msg, allocations = allocate_fifo_quantity(c_farm, item["Lô"], item["Số lượng"], "harvest", item["Ngày"], "Thu hoạch")
                        if is_valid:
                            for alloc in allocations:
                                data = {
                                    "farm": c_farm, "team": c_team, "ngay_thu_hoach": item["Ngày"], "mau_day": item["Màu dây"],
                                    "hinh_thuc_thu_hoach": item["Hình thức"], "tuan": item["Tuần"], "lot_id": alloc["lot_id"], "so_luong": alloc["so_luong"]
                                }
                                try:
                                    supabase.table("harvest_logs").insert(data).execute()
                                except Exception as e:
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}: {e}")
                                    return
                            success_count += 1
                        else:
                            st.error(msg)
                            return
                    st.session_state["queue_har"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Đã lưu thu hoạch {success_count} nhóm Lô thành công!"
                    st.rerun()

                render_queue_ui("queue_har", ["Lô", "Màu dây", "Hình thức", "Số lượng", "Ngày", "Tuần"], process_har_queue)
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_har", use_container_width=True):
                            edit_harvest_log_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_har", use_container_width=True):
                            confirm_action_dialog("DELETE", "harvest_logs", editing_row["id"], None, "✅ Xóa thành công!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    
                render_team_dataframe("harvest_logs", df_har_team, ["lot_id", "ngay_thu_hoach", "so_luong", "hinh_thuc_thu_hoach", "created_at"])

        elif active_tab == tab_opts[1]:
            render_global_data_tab(c_farm)

    # =================================================
    # MODULE 3: XƯỞNG ĐÓNG GÓI
    # =================================================
    elif c_team == "Xưởng Đóng Gói":
        tab_opts = ["🌐 Dữ liệu toàn cục", "📦 Cập nhật BSR"]
        active_tab = st.segmented_control("Chức năng", tab_opts, label_visibility="collapsed", key="tab_bsr_menu", default=tab_opts[0])
        if active_tab is None: active_tab = tab_opts[0]
        
        if active_tab == tab_opts[1]:
            st.markdown("#### Ghi nhận Tỷ lệ BSR thành phẩm")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào trên hệ thống.")
            else:
                df_bsr = fetch_table_data("bsr_logs", c_farm)
                df_bsr_team = df_bsr[df_bsr["team"] == c_team] if not df_bsr.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("bsr_logs", df_bsr_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô đóng gói", options=available_lots, key="add_bsr_lot")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay = st.date_input("📆 Ngày đóng gói", value=date.today(), key="add_bsr_dt")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"main_w_bsr_{ngay}")
                        bsr_val = st.number_input("📐 Nhập tỷ lệ BSR (Buồng / Sản Rạ)", min_value=0.0, value=0.0, step=0.1, format="%.2f", key="add_bsr_val")
    
                    st.markdown("")
                    if st.button("➕ Thêm vào Danh sách", key="btn_add_bsr", use_container_width=True, type="secondary"):
                        if bsr_val <= 0: st.error("❌ Tỷ lệ BSR phải > 0")
                        else:
                            st.session_state["queue_bsr"].append({
                                "Lô": lot_id, "BSR": bsr_val, "Ngày": ngay.isoformat(), "Tuần": ngay.isocalendar()[1]
                            })
                            st.rerun()

                def process_bsr_queue():
                    queue = st.session_state["queue_bsr"]
                    success_count = 0
                    for item in queue:
                        data = {
                            "farm": c_farm, "team": c_team, "lot_id": item["Lô"],
                            "ngay_nhap": item["Ngày"], "bsr": item["BSR"], "tuan": item["Tuần"]
                        }
                        try:
                            supabase.table("bsr_logs").insert(data).execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Lỗi ghi: {e}")
                            return
                    st.session_state["queue_bsr"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Ghi nhận {success_count} bản ghi BSR thành công!"
                    st.rerun()

                render_queue_ui("queue_bsr", ["Lô", "BSR", "Ngày", "Tuần"], process_bsr_queue)
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_bsr", use_container_width=True):
                            edit_bsr_log_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_bsr", use_container_width=True):
                            confirm_action_dialog("DELETE", "bsr_logs", editing_row["id"], None, "✅ Xóa thành công!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    
                render_team_dataframe("bsr_logs", df_bsr_team, ["lot_id", "ngay_nhap", "bsr", "created_at"])

        elif active_tab == tab_opts[0]:
            render_global_data_tab(c_farm)

# =====================================================
# MAIN ROUTING
# =====================================================
if __name__ == "__main__":
    init_session_state()
    if not st.session_state["logged_in"]:
        render_login()
    else:
        render_main_app()

