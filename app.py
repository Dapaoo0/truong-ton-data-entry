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
DESTRUCTION_STAGE_OPTIONS = ["Trước chích bắp", "Trước cắt bắp"]


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

@dialog_decorator("⚠️ Xác nhận lưu dữ liệu")
def confirm_save_dialog(table_name, data_dict, success_msg):
    st.warning("Vui lòng kiểm tra kỹ dữ liệu trước khi lưu")
    st.json(data_dict)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Tôi đã kiểm tra kỹ", use_container_width=True):
            if insert_to_db(table_name, data_dict):
                st.session_state["toast"] = success_msg
                st.rerun()
    with col2:
        if st.button("❌ Quay lại", use_container_width=True):
            st.rerun()

def render_editable_dataframe(table_name, df, disabled_cols, display_cols):
    if df.empty:
        st.info("Chưa có bản ghi nào.")
        return

    df["created_at_dt"] = pd.to_datetime(df["created_at"], utc=True)
    now = pd.Timestamp.utcnow()
    mask_48h = df["created_at_dt"] > (now - pd.Timedelta(hours=48))
    
    df_editable = df[mask_48h].copy().drop(columns=["created_at_dt"]).reset_index(drop=True)
    df_readonly = df[~mask_48h].copy().drop(columns=["created_at_dt"]).reset_index(drop=True)
    
    if not df_editable.empty:
        st.markdown("**✏️ Dữ liệu có thể chỉnh sửa / xóa (Trong vòng 48h):**")
        editor_key = f"editor_{table_name}"
        
        with st.form(f"form_edit_{table_name}"):
            st.caption("Sửa trực tiếp vào bảng hoặc chọn hàng và bấm biểu tượng thùng rác để xóa.")
            edited_df = st.data_editor(
                df_editable,
                use_container_width=True,
                num_rows="dynamic",
                disabled=disabled_cols,
                column_order=display_cols,
                key=editor_key
            )
            
            if st.form_submit_button("Lưu thay đổi", type="primary"):
                changes = st.session_state[editor_key]
                has_changes = False
                
                # Deletions
                for row_idx in changes.get("deleted_rows", []):
                    rec_id = df_editable.iloc[row_idx]["id"]
                    supabase.table(table_name).delete().eq("id", int(rec_id)).execute()
                    has_changes = True
                    
                # Edits
                for row_idx, edits in changes.get("edited_rows", {}).items():
                    rec_id = df_editable.iloc[row_idx]["id"]
                    clean_edits = {}
                    for k, v in edits.items():
                        if pd.isna(v): clean_edits[k] = None
                        elif hasattr(v, "item"): clean_edits[k] = v.item()
                        else: clean_edits[k] = v
                    supabase.table(table_name).update(clean_edits).eq("id", int(rec_id)).execute()
                    has_changes = True

                if has_changes:
                    st.session_state["toast"] = "✅ Đã lưu thay đổi thành công!"
                st.rerun()
                
    if not df_readonly.empty:
        st.markdown("**🔒 Dữ liệu cũ (Chỉ xem):**")
        st.dataframe(df_readonly[display_cols], use_container_width=True)


# =====================================================
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
        t1, t2, t3 = st.tabs(["🌱 Khởi tạo Lô trồng", "📈 Cập nhật Tiến độ", "🗑️ Cập nhật Xuất hủy"])

        # TAB 1: KHỞI TẠO LÔ
        with t1:
            st.markdown("#### Đăng ký đợt xuống giống mới")
            with st.form("form_nt_base", clear_on_submit=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    vu = st.selectbox("📅 Vụ", options=VU_OPTIONS)
                    lo = st.text_input("🏷️ Tên Lô (VD: A1, B3...)", placeholder="Nhập tên lô...")
                    loai_trong = st.selectbox("🌱 Loại trồng", options=LOAI_TRONG_OPTIONS)
                with col_b:
                    ngay_trong = st.date_input("📆 Ngày trồng", value=date.today())
                    so_luong = st.number_input("🔢 Số lượng trồng (cây)", min_value=0, step=100)

                if st.form_submit_button("✅ Tạo Lô Trồng", use_container_width=True, type="primary"):
                    if not lo.strip(): st.error("❌ Nhập tên lô.")
                    elif so_luong <= 0: st.error("❌ Cần nhập số lượng.")
                    else:
                        # Auto-generate lot_id: F1-A1-M (Mới) hoặc F1-A1-D (Dặm)
                        suffix = "M" if loai_trong == "Trồng mới" else "D"
                        lot_id = f"{vu}-{lo.strip()}-{suffix}"
                        
                        data = {
                            "farm": c_farm, "team": c_team, "vu": vu, "lo": lo.strip(),
                            "loai_trong": loai_trong, "lot_id": lot_id.upper(),
                            "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong
                        }
                        confirm_save_dialog("base_lots", data, f"✅ Tạo Lô: {lot_id.upper()} thành công!")

            st.markdown('<p class="dataframe-header">Dữ liệu hiện tại: Các Lô trồng</p>', unsafe_allow_html=True)
            df_lots = fetch_table_data("base_lots", c_farm)
            render_editable_dataframe("base_lots", df_lots, ["id", "created_at", "team", "farm", "lot_id", "vu", "lo"], ["lot_id", "loai_trong", "ngay_trong", "so_luong", "team", "created_at"])

        # TAB 2: CẬP NHẬT TIẾN ĐỘ NT
        with t2:
            st.markdown("#### Ghi nhận: Chích bắp / Cắt bắp")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào. Hãy tạo ở Tab 1.")
            else:
                with st.form("form_nt_stage", clear_on_submit=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots)
                        giai_doan = st.radio("📌 Giai đoạn", options=STAGE_NT_OPTIONS, horizontal=True)
                        mau_day = st.selectbox("🎨 Màu dây", options=[""] + MAU_DAY_OPTIONS)
                    with col_b:
                        ngay_th = st.date_input("📆 Ngày thực hiện", value=date.today())
                        sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100)

                    if st.form_submit_button("✅ Cập nhật Tiến độ", use_container_width=True, type="primary"):
                        if sl <= 0: st.error("❌ Nhập số lượng > 0.")
                        elif not mau_day: st.error("❌ Phải chọn màu dây định danh lứa.")
                        else:
                            data = {
                                "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                "giai_doan": giai_doan, "ngay_thuc_hien": ngay_th.isoformat(),
                                "so_luong": sl, "mau_day": mau_day
                            }
                            confirm_save_dialog("stage_logs", data, f"✅ Lưu tiến độ {giai_doan} lô {lot_id} thành công!")

                st.markdown('<p class="dataframe-header">Dữ liệu hiện tại: Tiến độ Nông trường</p>', unsafe_allow_html=True)
                df_stg = fetch_table_data("stage_logs", c_farm)
                render_editable_dataframe("stage_logs", df_stg, ["id", "created_at", "team", "farm", "lot_id", "giai_doan"], ["lot_id", "giai_doan", "ngay_thuc_hien", "so_luong", "mau_day", "team"])

        # TAB 3: XUẤT HỦY
        with t3:
            st.markdown("#### Ghi nhận số lượng cây chết / hư hỏng")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào.")
            else:
                with st.form("form_nt_destroy", clear_on_submit=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô", options=available_lots, key="destry_lot")
                        giai_doan_xuat_huy = st.selectbox("⏱️ Giai đoạn xuất hủy", options=DESTRUCTION_STAGE_OPTIONS)
                        ly_do = st.text_area("📝 Lý do (Gió, bệnh...)", height=100)
                    with col_b:
                        ngay = st.date_input("📆 Ngày xuất hủy", value=date.today(), key="destroy_d")
                        sl = st.number_input("🔢 Số lượng cây xuất hủy", min_value=0, step=10)

                    if st.form_submit_button("🗑️ Ghi nhận Xuất hủy", use_container_width=True, type="primary"):
                        if sl <= 0: st.error("❌ Nhập số lượng xuất hủy > 0.")
                        elif not ly_do.strip(): st.error("❌ Cần ghi rõ lý do.")
                        else:
                            data = {
                                "farm": c_farm, "team": c_team, "lot_id": lot_id,
                                "ngay_xuat_huy": ngay.isoformat(), "giai_doan": giai_doan_xuat_huy,
                                "ly_do": ly_do.strip(), "so_luong": sl
                            }
                            confirm_save_dialog("destruction_logs", data, f"✅ Lưu xuất hủy lô {lot_id} thành công!")

                st.markdown('<p class="dataframe-header">Dữ liệu hiện tại: Số lượng Xuất hủy</p>', unsafe_allow_html=True)
                df_des = fetch_table_data("destruction_logs", c_farm)
                render_editable_dataframe("destruction_logs", df_des, ["id", "created_at", "team", "farm", "lot_id"], ["lot_id", "ngay_xuat_huy", "giai_doan", "so_luong", "ly_do", "team"])


    # =================================================
    # MODULE 2: ĐỘI THU HOẠCH
    # =================================================
    elif c_team == "Đội Thu Hoạch":
        st.markdown("#### Ghi nhận Sản lượng Thu hoạch hàng ngày")
        available_lots = get_lots_by_farm(c_farm)
        if not available_lots:
            st.warning("⚠️ Chưa có Lô trồng nào trên hệ thống.")
        else:
            with st.form("form_harvest", clear_on_submit=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    lot_id = st.selectbox("🏷️ Chọn Lô thu hoạch", options=available_lots)
                    ngay = st.date_input("📆 Ngày thu hoạch", value=date.today())
                with col_b:
                    sl = st.number_input("🍌 Số lượng buồng thu hoạch", min_value=0, step=50)

                st.markdown("")
                if st.form_submit_button("✅ Cập nhật Thu hoạch", use_container_width=True, type="primary"):
                    if sl <= 0: st.error("❌ Số lượng buồng phải > 0")
                    else:
                        data = {"farm": c_farm, "team": c_team, "lot_id": lot_id, "ngay_thu_hoach": ngay.isoformat(), "so_luong": sl}
                        confirm_save_dialog("harvest_logs", data, f"✅ Lưu lịch sử thu hoạch lô {lot_id} thành công!")
            
            st.markdown('<p class="dataframe-header">Dữ liệu hiện tại: Nhập liệu Thu hoạch</p>', unsafe_allow_html=True)
            df_har = fetch_table_data("harvest_logs", c_farm)
            render_editable_dataframe("harvest_logs", df_har, ["id", "created_at", "team", "farm", "lot_id"], ["lot_id", "ngay_thu_hoach", "so_luong", "created_at"])


    # =================================================
    # MODULE 3: XƯỞNG ĐÓNG GÓI
    # =================================================
    elif c_team == "Xưởng Đóng Gói":
        st.markdown("#### Ghi nhận Tỷ lệ BSR thành phẩm")
        available_lots = get_lots_by_farm(c_farm)
        if not available_lots:
            st.warning("⚠️ Chưa có Lô trồng nào trên hệ thống.")
        else:
            with st.form("form_bsr", clear_on_submit=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    lot_id = st.selectbox("🏷️ Chọn Lô đóng gói", options=available_lots)
                    ngay = st.date_input("📆 Ngày đóng gói", value=date.today())
                with col_b:
                    bsr_val = st.number_input("📐 Nhập tỷ lệ BSR (Buồng / Sản Rạ)", min_value=0.0, value=0.0, step=0.1, format="%.2f")

                st.markdown("")
                if st.form_submit_button("✅ Cập nhật BSR", use_container_width=True, type="primary"):
                    if bsr_val <= 0: st.error("❌ Tỷ lệ BSR phải > 0")
                    else:
                        data = {"farm": c_farm, "team": c_team, "lot_id": lot_id, "ngay_nhap": ngay.isoformat(), "bsr": bsr_val}
                        confirm_save_dialog("bsr_logs", data, f"✅ Ghi nhận BSR lô {lot_id} thành công!")
            
            st.markdown('<p class="dataframe-header">Dữ liệu hiện tại: Nhập liệu BSR</p>', unsafe_allow_html=True)
            df_bsr = fetch_table_data("bsr_logs", c_farm)
            render_editable_dataframe("bsr_logs", df_bsr, ["id", "created_at", "team", "farm", "lot_id"], ["lot_id", "ngay_nhap", "bsr", "created_at"])


    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🌐 Bảng dữ liệu Toàn cục Farm")
    st.caption("Cho phép tra cứu chéo Lô trồng và Tiến độ sinh trưởng từ các Đội khác.")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown('<p class="dataframe-header">🌱 Lô Trồng</p>', unsafe_allow_html=True)
        df_lots_all = fetch_table_data("base_lots", c_farm)
        if not df_lots_all.empty:
             st.dataframe(df_lots_all[["lot_id", "loai_trong", "ngay_trong", "so_luong", "team"]], use_container_width=True, hide_index=True)
        else:
             st.info("Chưa có dữ liệu.")
             
    with col_t2:
        st.markdown('<p class="dataframe-header">📈 Sinh Trưởng</p>', unsafe_allow_html=True)
        df_stg_all = fetch_table_data("stage_logs", c_farm)
        if not df_stg_all.empty:
             st.dataframe(df_stg_all[["lot_id", "giai_doan", "ngay_thuc_hien", "so_luong", "mau_day", "team"]], use_container_width=True, hide_index=True)
        else:
             st.info("Chưa có dữ liệu.")


# =====================================================
# MAIN ROUTING
# =====================================================
if __name__ == "__main__":
    init_session_state()
    if not st.session_state["logged_in"]:
        render_login()
    else:
        render_main_app()

