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
    "Farm 126": {
        "NT1": "123",
        "NT2": "123",
        "Đội Thu Hoạch": "123",
        "Xưởng Đóng Gói": "123"
    },
    "Farm 157": {
        "NT1": "456",
        "NT2": "456",
        "Đội Thu Hoạch": "456",
        "Xưởng Đóng Gói": "456"
    },
    "Farm 195": {
        "NT1": "789",
        "NT2": "789",
        "Đội Thu Hoạch": "789",
        "Xưởng Đóng Gói": "789"
    }
}

FARMS = list(RBAC_DB.keys())
TEAMS = ["NT1", "NT2", "Đội Thu Hoạch", "Xưởng Đóng Gói"]

# =====================================================
# CONFIG OPTIONS
# =====================================================
VU_OPTIONS = ["F0", "F1", "F2", "F3", "F4", "F5"]
MAU_DAY_OPTIONS = ["Đỏ", "Xanh lá", "Vàng", "Xanh dương", "Trắng", "Cam"]
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
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "current_farm" not in st.session_state: st.session_state["current_farm"] = None
    if "current_team" not in st.session_state: st.session_state["current_team"] = None

def logout():
    st.session_state["logged_in"] = False
    st.session_state["current_farm"] = None
    st.session_state["current_team"] = None

def insert_access_log(farm: str, team: str, action: str):
    try:
        supabase.table("access_logs").insert({"farm": farm, "team": team, "action": action}).execute()
    except Exception as e:
        print(f"Lỗi log: {e}")

# =====================================================
# HÀM TƯƠNG TÁC DB (SUPABASE DATA FETCHERS)
# =====================================================
def get_lots_by_farm(farm: str) -> list:
    """Lấy danh sách lot_id gốc của nguyen Farm (chọn Lô trồng)."""
    res = supabase.table("base_lots").select("lot_id").eq("farm", farm).order("created_at").execute()
    return [row["lot_id"] for row in res.data] if res.data else []

def fetch_table_data(table_name: str, farm: str) -> pd.DataFrame:
    """Hàm chung lấy dữ liệu từ bảng bất kỳ theo farm."""
    res = supabase.table(table_name).select("*").eq("farm", farm).order("created_at", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def insert_to_db(table_name: str, data: dict) -> bool:
    try:
        supabase.table(table_name).insert(data).execute()
        return True
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
            st.error(f"❌ Mã Lô '{data.get('lot_id')}' đã tồn tại trong hệ thống. Vui lòng kiểm tra lại!")
        else:
            st.error(f"❌ Lỗi khi lưu vào {table_name}: {e}")
        return False

def check_quantity_limit(lot_id, new_sl, log_type, giai_doan=None, exclude_id=None):
    res_lot = supabase.table("base_lots").select("so_luong").eq("lot_id", lot_id).execute()
    if not res_lot.data: return False, "❌ Lỗi: Không tìm thấy thông tin Lô."
    total_planted = int(res_lot.data[0]["so_luong"])

    max_allowed = total_planted
    action_name = giai_doan.lower() if log_type == "stage" else ("xuất hủy" if log_type == "destruction" else "thu hoạch")
    base_name = "trồng"
    unit = "buồng" if log_type == "harvest" else "cây"

    if log_type == "stage" and giai_doan == "Cắt bắp":
        res_cb = supabase.table("stage_logs").select("so_luong").eq("lot_id", lot_id).eq("giai_doan", "Chích bắp").execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cb.data)
        base_name = "chích bắp"
        
    elif log_type == "harvest":
        res_cut = supabase.table("stage_logs").select("so_luong").eq("lot_id", lot_id).eq("giai_doan", "Cắt bắp").execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cut.data)
        base_name = "cắt bắp"

    total_used = 0
    if log_type == "stage":
        res = supabase.table("stage_logs").select("id, so_luong").eq("lot_id", lot_id).eq("giai_doan", giai_doan).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "destruction":
        res = supabase.table("destruction_logs").select("id, so_luong").eq("lot_id", lot_id).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "harvest":
        res = supabase.table("harvest_logs").select("id, so_luong").eq("lot_id", lot_id).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)

    if total_used + int(new_sl) > max_allowed:
        remain = max_allowed - total_used
        return False, f"❌ Bạn đã nhập {new_sl} {unit} {action_name}, nhưng số lượng còn lại chưa {action_name} chỉ có {remain} {unit} (trên tổng {max_allowed} {unit} đã {base_name})."
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
            elif action == "UPDATE":
                try:
                    supabase.table(table_name).update(data_dict).eq("id", rec_id_or_none).execute()
                    success = True
                except Exception as e:
                    st.error(f"❌ Lỗi cập nhật: {e}")
            elif action == "DELETE":
                try:
                    supabase.table(table_name).delete().eq("id", rec_id_or_none).execute()
                    success = True
                except Exception as e:
                    st.error(f"❌ Lỗi xóa: {e}")
            
            if success:
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

# =====================================================
# CÁC DIALOG CHỈNH SỬA
# =====================================================
@dialog_decorator("✏️ Chỉnh sửa Lô Trồng")
def edit_base_lot_dialog(editing_row):
    vu_ops = VU_OPTIONS
    loai_ops = LOAI_TRONG_OPTIONS
    def_vu = vu_ops.index(editing_row["vu"]) if editing_row["vu"] in vu_ops else 0
    def_lo = editing_row["lo"]
    def_loai = loai_ops.index(editing_row["loai_trong"]) if editing_row["loai_trong"] in loai_ops else 0
    def_ngay = pd.to_datetime(editing_row["ngay_trong"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            vu = st.selectbox("📅 Vụ", options=vu_ops, index=def_vu, key="dlg_vu_base")
            lo = st.text_input("🏷️ Tên Lô", value=def_lo, key="dlg_lo_base")
            loai_trong = st.selectbox("🌱 Loại trồng", options=loai_ops, index=def_loai, key="dlg_loai_base")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay_trong = st.date_input("📆 Ngày trồng", value=def_ngay, key="dlg_dt_base")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay_trong.isocalendar()[1]), disabled=True, key=f"dlg_w_base_{ngay_trong}")
            so_luong = st.number_input("🔢 Số lượng", min_value=0, step=100, value=def_sl, key="dlg_sl_base")

        if st.button("✅ Cập nhật", key="btn_edit_base", use_container_width=True, type="primary"):
            if not lo.strip(): st.error("❌ Nhập tên lô.")
            elif so_luong <= 0: st.error("❌ Cần nhập số lượng.")
            else:
                suffix = "M" if loai_trong == "Trồng mới" else "D"
                lot_id = f"{vu}-{lo.strip()}-{suffix}".upper()
                data = {
                    "vu": vu, "lo": lo.strip(),
                    "loai_trong": loai_trong, "lot_id": lot_id,
                    "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong,
                    "tuan": ngay_trong.isocalendar()[1]
                }
                supabase.table("base_lots").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Cập nhật {lot_id} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Tiến độ")
def edit_stage_log_dialog(editing_row, available_lots):
    gd_ops = STAGE_NT_OPTIONS
    mau_ops = [""] + MAU_DAY_OPTIONS
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_gd = gd_ops.index(editing_row["giai_doan"]) if editing_row["giai_doan"] in gd_ops else 0
    def_mau = mau_ops.index(editing_row["mau_day"]) if editing_row["mau_day"] in mau_ops else 0
    def_ngay = pd.to_datetime(editing_row["ngay_thuc_hien"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, index=def_lot, key="dlg_lot_stg")
            giai_doan = st.radio("📌 Giai đoạn", options=gd_ops, index=def_gd, horizontal=True, key="dlg_gd_stg")
            mau_day = st.selectbox("🎨 Màu dây", options=mau_ops, index=def_mau, key="dlg_mau_stg")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay_th = st.date_input("📆 Ngày thực hiện", value=def_ngay, key="dlg_dt_stg")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay_th.isocalendar()[1]), disabled=True, key=f"dlg_w_stg_{ngay_th}")
            sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100, value=def_sl, key="dlg_sl_stg")
        
        if st.button("✅ Cập nhật", key="btn_edit_stg", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập số lượng.")
            elif not mau_day: st.error("❌ Phải chọn màu dây định danh lứa.")
            else:
                is_valid, msg = check_quantity_limit(lot_id, sl, "stage", giai_doan=giai_doan, exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    data = {
                        "lot_id": lot_id, "giai_doan": giai_doan, 
                        "ngay_thuc_hien": ngay_th.isoformat(), "so_luong": sl, "mau_day": mau_day,
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
    def_ngay = pd.to_datetime(editing_row["ngay_xuat_huy"]).date()
    def_sl = int(editing_row["so_luong"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, index=def_lot, key="dlg_lot_des")
            gxh = st.selectbox("⏱️ Giai đoạn", options=gd_ops, index=def_gd, key="dlg_gxh_des")
            ly_do = st.text_area("📝 Lý do", height=100, value=def_ly_do, key="dlg_lydo_des")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày xuất hủy", value=def_ngay, key="dlg_dt_des")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_des_{ngay}")
            sl = st.number_input("🔢 Số lượng xuất hủy", min_value=0, step=10, value=def_sl, key="dlg_sl_des")

        if st.button("✅ Cập nhật", key="btn_edit_des", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập số lượng.")
            elif not ly_do.strip(): st.error("❌ Cần ghi rõ lý do.")
            else:
                is_valid, msg = check_quantity_limit(lot_id, sl, "destruction", exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    data = {"lot_id": lot_id, "ngay_xuat_huy": ngay.isoformat(), "giai_doan": gxh, "ly_do": ly_do.strip(), "so_luong": sl, "tuan": ngay.isocalendar()[1]}
                    supabase.table("destruction_logs").update(data).eq("id", editing_row["id"]).execute()
                    st.session_state["toast"] = "✅ Đã cập nhật!"
                    st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Nhật ký Thu Hoạch")
def edit_harvest_log_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_ngay = pd.to_datetime(editing_row["ngay_thu_hoach"]).date()
    def_sl = int(editing_row["so_luong"])

    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, index=def_lot, key="dlg_lot_har")
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày thu hoạch", value=def_ngay, key="dlg_dt_har")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_har_{ngay}")
            sl = st.number_input("🍌 Số lượng buồng", min_value=0, step=50, value=def_sl, key="dlg_sl_har")

        if st.button("✅ Cập nhật", key="btn_edit_har", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Số lượng buồng phải > 0")
            else:
                is_valid, msg = check_quantity_limit(lot_id, sl, "harvest", exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    data = {"lot_id": lot_id, "ngay_thu_hoach": ngay.isoformat(), "so_luong": sl, "tuan": ngay.isocalendar()[1]}
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
            lot_id = st.selectbox("🏷️ Chọn Lô đóng gói", options=available_lots, index=def_lot, key="dlg_lot_bsr")
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

# MÀN HÌNH ĐĂNG NHẬP
# =====================================================
def render_login():
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
    with col_logo2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)

    st.markdown('<p class="main-title">🍌 Trường Tồn Banana Tracker</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Hệ thống quản lý Phân quyền Đa cấp</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>🔐 Đăng nhập hệ thống</h3>", unsafe_allow_html=True)
        st.divider()

        # Chọn Farm
        selected_farm = st.selectbox("🏗️ Chọn Farm", options=FARMS, key="login_farm")
        # Chọn Team thuộc Farm
        selected_team = st.selectbox("👥 Chọn Đội / Vai trò", options=TEAMS, key="login_team")

        # Nhập MK
        password = st.text_input("🔑 Mật khẩu", type="password", key="login_pass", placeholder="Nhập mật khẩu...")

        st.markdown("")
        if st.button("🚀 Đăng nhập", use_container_width=True, type="primary"):
            if not password:
                st.warning("⚠️ Vui lòng nhập mật khẩu.")
            else:
                correct_pass = RBAC_DB.get(selected_farm, {}).get(selected_team)
                if password == correct_pass:
                    st.session_state["logged_in"] = True
                    st.session_state["current_farm"] = selected_farm
                    st.session_state["current_team"] = selected_team
                    insert_access_log(selected_farm, selected_team, "Đăng nhập thành công")
                    st.success(f"✅ Đăng nhập {selected_team} - {selected_farm}!")
                    st.rerun()
                else:
                    insert_access_log(selected_farm, selected_team, "Sai mật khẩu")
                    st.error("❌ Mật khẩu không đúng.")

        st.divider()
        st.markdown("<p style='text-align: center; color: #888888; font-size: 0.85rem;'>💡 Vui lòng chọn đúng vai trò của mình để thao tác đúng nghiệp vụ.</p>", unsafe_allow_html=True)

def render_global_data_tab(c_farm):
    st.markdown("### 🌐 Bảng dữ liệu Toàn cục Farm")
    st.caption("Khám phá dữ liệu tổng quan bằng các Biểu đồ phân tích và Bộ lọc.")
    
    # Fetch all data
    df_lots_all = fetch_table_data("base_lots", c_farm)
    df_stg_all = fetch_table_data("stage_logs", c_farm)
    df_des_all = fetch_table_data("destruction_logs", c_farm)
    df_har_all = fetch_table_data("harvest_logs", c_farm)
    df_bsr_all = fetch_table_data("bsr_logs", c_farm)

    # Filter section
    st.markdown("##### 🔍 Bộ lọc Dữ liệu")
    col_f1, col_f2 = st.columns(2)
    teams = ["Tất cả"] + list(df_lots_all["team"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    lots = ["Tất cả"] + list(df_lots_all["lot_id"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    
    with col_f1:
        f_team = st.selectbox("Lọc theo Đội", options=teams, key="f_glb_team")
    with col_f2:
        f_lot = st.selectbox("Lọc theo Lô", options=lots, key="f_glb_lot")

    # Apply filters
    if f_team != "Tất cả" and not df_lots_all.empty:
        df_lots_all = df_lots_all[df_lots_all["team"] == f_team]
        if not df_stg_all.empty: df_stg_all = df_stg_all[df_stg_all["team"] == f_team]
        if not df_des_all.empty: df_des_all = df_des_all[df_des_all["team"] == f_team]
        if not df_har_all.empty: df_har_all = df_har_all[df_har_all["team"] == f_team]
        if not df_bsr_all.empty: df_bsr_all = df_bsr_all[df_bsr_all["team"] == f_team]
        
    if f_lot != "Tất cả" and not df_lots_all.empty:
        df_lots_all = df_lots_all[df_lots_all["lot_id"] == f_lot]
        if not df_stg_all.empty: df_stg_all = df_stg_all[df_stg_all["lot_id"] == f_lot]
        if not df_des_all.empty: df_des_all = df_des_all[df_des_all["lot_id"] == f_lot]
        if not df_har_all.empty: df_har_all = df_har_all[df_har_all["lot_id"] == f_lot]
        if not df_bsr_all.empty: df_bsr_all = df_bsr_all[df_bsr_all["lot_id"] == f_lot]

    st.divider()

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("**🌱 Trồng mới & Trồng dặm (Cây)**")
        if not df_lots_all.empty and "tuan" in df_lots_all.columns:
            plot_data = df_lots_all.groupby(["tuan", "loai_trong"])["so_luong"].sum().unstack().fillna(0)
            if not plot_data.empty: st.bar_chart(plot_data)
            else: st.info("Không đủ dữ liệu.")
        else: st.info("Chưa có dữ liệu.")

    with col_c2:
        st.markdown("**📈 Tiến độ Chích bắp & Cắt bắp (Cây)**")
        if not df_stg_all.empty and "tuan" in df_stg_all.columns:
            plot_data = df_stg_all.groupby(["tuan", "giai_doan"])["so_luong"].sum().unstack().fillna(0)
            if not plot_data.empty: st.line_chart(plot_data)
            else: st.info("Không đủ dữ liệu.")
        else: st.info("Chưa có dữ liệu.")

    st.markdown("---")
    
    col_c3, col_c4 = st.columns(2)
    with col_c3:
        st.markdown("**🍌 Sản lượng Thu hoạch (Buồng)**")
        if not df_har_all.empty and "tuan" in df_har_all.columns:
            plot_data = df_har_all.groupby("tuan")["so_luong"].sum()
            if not plot_data.empty: 
                # Chuyển sang dạng line_chart / area_chart cho trực quan và sinh động hơn
                st.area_chart(plot_data, color="#FFD700") 
            else: st.info("Không đủ dữ liệu.")
        else: st.info("Chưa có dữ liệu.")

    with col_c4:
        st.markdown("**🗑️ Tỷ lệ Xuất hủy**")
        if not df_des_all.empty:
            plot_data = df_des_all.groupby("giai_doan")["so_luong"].sum()
            if not plot_data.empty: st.bar_chart(plot_data)
            else: st.info("Không đủ dữ liệu.")
        else: st.info("Chưa có dữ liệu.")

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
    # MODULE 1: ĐỘI NÔNG TRƯỜNG (NT1, NT2)
    # =================================================
    if c_team in ["NT1", "NT2"]:
        t1, t2, t3, t4 = st.tabs(["🌱 Khởi tạo Lô trồng", "📈 Cập nhật Tiến độ", "🗑️ Cập nhật Xuất hủy", "🌐 Dữ liệu toàn cục"])

        # TAB 1: KHỞI TẠO LÔ
        with t1:
            st.markdown("#### Đăng ký đợt xuống giống mới")
            df_lots = fetch_table_data("base_lots", c_farm)
            df_lots_team = df_lots[df_lots["team"] == c_team] if not df_lots.empty else pd.DataFrame()
            editing_row, is_within_48h = get_editing_row("base_lots", df_lots_team)
            is_editing = editing_row is not None
            
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    vu = st.selectbox("📅 Vụ", options=VU_OPTIONS, key="add_base_vu")
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
                        suffix = "M" if loai_trong == "Trồng mới" else "D"
                        lot_id = f"{vu}-{lo.strip()}-{suffix}".upper()
                        data = {
                            "farm": c_farm, "team": c_team, "vu": vu, "lo": lo.strip(),
                            "loai_trong": loai_trong, "lot_id": lot_id,
                            "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong,
                            "tuan": ngay_trong.isocalendar()[1]
                        }
                        confirm_action_dialog("INSERT", "base_lots", None, data, f"✅ Tạo Lô {lot_id} thành công!")

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

            render_team_dataframe("base_lots", df_lots_team, ["lot_id", "loai_trong", "ngay_trong", "so_luong", "created_at"])

        # TAB 2: CẬP NHẬT TIẾN ĐỘ NT
        with t2:
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
                        giai_doan = st.radio("📌 Giai đoạn", options=STAGE_NT_OPTIONS, horizontal=True, key="add_stg_gd")
                        mau_day = st.selectbox("🎨 Màu dây", options=[""] + MAU_DAY_OPTIONS, key="add_stg_mau")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay_th = st.date_input("📆 Ngày thực hiện", value=date.today(), key="add_stg_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay_th.isocalendar()[1]), disabled=True, key=f"main_w_stg_{ngay_th}")
                        sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100, key="add_stg_sl")

                    if st.button("✅ Cập nhật Tiến độ", key="btn_add_stg", use_container_width=True, type="primary"):
                        if sl <= 0: st.error("❌ Nhập số lượng > 0.")
                        elif not mau_day: st.error("❌ Phải chọn màu dây định danh lứa.")
                        else:
                            is_valid, msg = check_quantity_limit(lot_id, sl, "stage", giai_doan=giai_doan)
                            if not is_valid: st.error(msg)
                            else:
                                data = {
                                    "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                    "giai_doan": giai_doan, "ngay_thuc_hien": ngay_th.isoformat(),
                                    "so_luong": sl, "mau_day": mau_day, "tuan": ngay_th.isocalendar()[1]
                                }
                                confirm_action_dialog("INSERT", "stage_logs", None, data, f"✅ Lưu tiến độ {giai_doan} {lot_id}!")

                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_stg_nt", use_container_width=True):
                            edit_stage_log_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_stg_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "stage_logs", editing_row["id"], None, "✅ Đã xóa thành công!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                
                render_team_dataframe("stage_logs", df_stg_team, ["lot_id", "giai_doan", "ngay_thuc_hien", "so_luong", "mau_day"])

        # TAB 3: XUẤT HỦY
        with t3:
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
                        ly_do = st.text_area("📝 Lý do (Gió, bệnh...)", height=100, key="add_des_lydo")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay = st.date_input("📆 Ngày xuất hủy", value=date.today(), key="add_des_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"main_w_des_{ngay}")
                        sl = st.number_input("🔢 Số lượng cây xuất hủy", min_value=0, step=10, key="add_des_sl")

                    if st.button("🗑️ Ghi nhận Xuất hủy", key="btn_add_des", use_container_width=True, type="primary"):
                        if sl <= 0: st.error("❌ Nhập số lượng > 0.")
                        elif not ly_do.strip(): st.error("❌ Cần ghi rõ lý do.")
                        else:
                            is_valid, msg = check_quantity_limit(lot_id, sl, "destruction")
                            if not is_valid: st.error(msg)
                            else:
                                data = {
                                    "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                    "ngay_xuat_huy": ngay.isoformat(), "giai_doan": giai_doan_xuat_huy,
                                    "ly_do": ly_do.strip(), "so_luong": sl,
                                    "tuan": ngay.isocalendar()[1]
                                }
                                confirm_action_dialog("INSERT", "destruction_logs", None, data, f"✅ Lưu xuất hủy lô {lot_id} thành công!")

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
                    
                render_team_dataframe("destruction_logs", df_des_team, ["lot_id", "ngay_xuat_huy", "giai_doan", "so_luong", "ly_do"])

        # TAB 4: DỮ LIỆU TOÀN CỤC
        with t4:
            render_global_data_tab(c_farm)

    # =================================================
    # MODULE 2: ĐỘI THU HOẠCH
    # =================================================
    elif c_team == "Đội Thu Hoạch":
        t1, t2 = st.tabs(["🍌 Nhật ký Thu Hoạch", "🌐 Dữ liệu toàn cục"])
        
        with t1:
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
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay = st.date_input("📆 Ngày thu hoạch", value=date.today(), key="add_har_dt")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"main_w_har_{ngay}")
                        sl = st.number_input("🍌 Số lượng buồng thu hoạch", min_value=0, step=50, key="add_har_sl")
    
                    st.markdown("")
                    if st.button("✅ Cập nhật Thu hoạch", key="btn_add_har", use_container_width=True, type="primary"):
                        if sl <= 0: st.error("❌ Số lượng buồng phải > 0")
                        else:
                            is_valid, msg = check_quantity_limit(lot_id, sl, "harvest")
                            if not is_valid: st.error(msg)
                            else:
                                data = {
                                    "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                    "ngay_thu_hoach": ngay.isoformat(), "so_luong": sl, "tuan": ngay.isocalendar()[1]
                                }
                                confirm_action_dialog("INSERT", "harvest_logs", None, data, f"✅ Lưu thu hoạch lô {lot_id} thành công!")
                
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
                    
                render_team_dataframe("harvest_logs", df_har_team, ["lot_id", "ngay_thu_hoach", "so_luong", "created_at"])

        with t2:
            render_global_data_tab(c_farm)

    # =================================================
    # MODULE 3: XƯỞNG ĐÓNG GÓI
    # =================================================
    elif c_team == "Xưởng Đóng Gói":
        t1, t2 = st.tabs(["📦 Cập nhật BSR", "🌐 Dữ liệu toàn cục"])
        
        with t1:
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
                    if st.button("✅ Cập nhật BSR", key="btn_add_bsr", use_container_width=True, type="primary"):
                        if bsr_val <= 0: st.error("❌ Tỷ lệ BSR phải > 0")
                        else:
                            data = {
                                "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                "ngay_nhap": ngay.isoformat(), "bsr": bsr_val, "tuan": ngay.isocalendar()[1]
                            }
                            confirm_action_dialog("INSERT", "bsr_logs", None, data, f"✅ Ghi nhận BSR lô {lot_id} thành công!")
                
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

        with t2:
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

