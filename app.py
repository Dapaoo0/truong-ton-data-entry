"""
=======================================================================
  ỨNG DỤNG NHẬP LIỆU QUẢN LÝ TIẾN ĐỘ SINH TRƯỞNG CHUỐI XUẤT KHẨU
  Công ty Trường Tồn  |  Streamlit + Supabase (RBAC Version 2.0)
=======================================================================
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
import io
import uuid
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json

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
# QUYỀN TRUY CẬP (RBAC) — ĐỌC TỪ DATABASE
# =====================================================
# Cấu trúc trả về: RBAC_DB[Farm][Team] = Password

@st.cache_data(ttl=300)  # Cache 5 phút
def fetch_rbac_from_db():
    """Đọc bảng user_roles từ Supabase, trả về dict {farm: {team: password}}."""
    try:
        res = supabase.table("user_roles").select("farm, team, password").eq("is_active", True).execute()
        rbac = {}
        for row in res.data:
            farm = row["farm"]
            team = row["team"]
            pw = row["password"]
            if farm not in rbac:
                rbac[farm] = {}
            rbac[farm][team] = pw
        return rbac
    except Exception as e:
        st.error(f"❌ Không thể tải dữ liệu phân quyền: {e}")
        return {}

RBAC_DB = fetch_rbac_from_db()
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
# TIMELINE SINH TRƯỞNG CHUỐI (Constants)
# =====================================================
# F0 (từ ngày trồng): Trồng → +180d Chích → +14d Cắt → +70d Thu hoạch (tổng 264d)
# Fn (từ harvest trước): +90d Chích → +14d Cắt → +70d Thu hoạch (tổng 174d)
# Cây con Fn sinh trưởng 3 tháng dưới gốc mẹ trước khi mẹ thu hoạch
F0_DAYS_TO_CHICH = 180
F0_DAYS_TO_CAT = 194      # 180 + 14
F0_DAYS_TO_THU = 264       # 180 + 14 + 70
FN_CYCLE_DAYS = 174        # 90 + 14 + 70 (từ harvest trước)
FN_DAYS_CHICH_OFFSET = 90  # Từ harvest trước đến chích bắp Fn
FN_DAYS_CAT_OFFSET = 104   # 90 + 14
FN_DAYS_THU_OFFSET = 174   # 90 + 14 + 70
CONVERGENCE_DAYS = 15      # Ngưỡng hội tụ: 2 đợt chênh ≤15d → coi như gộp
MAX_GENERATION = 5         # Tính tối đa F0→F5

# =====================================================
# SẢN LƯỢNG DỰ TOÁN (kg/buồng)
# =====================================================
KG_PER_TREE_F0 = 15        # F0: 15 kg/buồng
KG_PER_TREE_FN = 18        # Fn (F1+): 18 kg/buồng
KG_PER_BOX = 13            # 13 kg/thùng
BOXES_PER_CONTAINER = 1320 # 1320 thùng/container

# =====================================================
# TỈ LỆ HAO HỤT THEO GIAI ĐOẠN (so với số cây trồng gốc)
# =====================================================
# Trồng → Chích bắp: 5% loss | Chích bắp → Thu hoạch: +5% loss | Tổng: 10%
LOSS_RATE_TO_CHICH = 0.05   # 5% hao hụt từ trồng → chích bắp
LOSS_RATE_TO_THU   = 0.10   # 10% tổng hao hụt từ trồng → thu hoạch

def get_estimated_rate(stage: str) -> float:
    """
    Trả về tỉ lệ còn lại (1 - loss) theo giai đoạn.
    - Chích bắp: 0.95 (5% hao hụt)
    - Cắt bắp:  0.95 (cắt bắp chỉ cách chích 14 ngày, chưa chênh đáng kể)
    - Thu hoạch: 0.90 (10% hao hụt tổng cộng)
    """
    if stage in ("chich_bap", "cat_bap"):
        return 1 - LOSS_RATE_TO_CHICH  # 0.95
    elif stage == "thu_hoach":
        return 1 - LOSS_RATE_TO_THU    # 0.90
    return 1.0  # Trồng: không hao hụt

def get_kg_per_tree(vu: str) -> int:
    """Trả về kg/buồng tương ứng theo vụ. F0 = 15kg, Fn = 18kg."""
    return KG_PER_TREE_F0 if vu == "F0" else KG_PER_TREE_FN

# Stage offsets cho thuật toán matching
_STAGE_OFFSETS = {
    "Chích bắp": {"f0": F0_DAYS_TO_CHICH, "fn": FN_DAYS_CHICH_OFFSET},
    "Cắt bắp":   {"f0": F0_DAYS_TO_CAT,   "fn": FN_DAYS_CAT_OFFSET},
    "Thu hoạch":  {"f0": F0_DAYS_TO_THU,   "fn": FN_DAYS_THU_OFFSET},
}


# Map giai đoạn xuất hủy → stage tương ứng để dùng timeline matching
_DESTRUCTION_STAGE_MAP = {
    "Trước chích bắp": "Chích bắp",
    "Trước cắt bắp": "Cắt bắp",
    "Trước thu hoạch": "Thu hoạch",
}

def resolve_base_lot_id(dim_lo_id, action_date, giai_doan):
    """
    Tự động suy luận base_lot_id dựa trên ngày hành động và giai đoạn.
    Tính expected dates cho TẤT CẢ vụ (F0→F5) của mỗi đợt trồng trong lô.
    Chọn đợt có khoảng cách nhỏ nhất (closest match).
    Luôn trả về kết quả — không bao giờ None (trừ khi lô chưa có đợt trồng).
    """
    res = supabase.table("base_lots") \
        .select("id, ngay_trong") \
        .eq("dim_lo_id", dim_lo_id) \
        .eq("is_deleted", False) \
        .execute()
    
    if not res.data:
        return None  # Lô chưa có đợt trồng nào

    action_dt = pd.to_datetime(action_date)
    best_match_id = None
    best_distance = float('inf')

    # Nếu là giai đoạn xuất hủy → map sang stage tương ứng để dùng timeline
    effective_giai_doan = _DESTRUCTION_STAGE_MAP.get(giai_doan, giai_doan)

    for batch in res.data:
        trong_dt = pd.to_datetime(batch["ngay_trong"])

        if effective_giai_doan in _STAGE_OFFSETS:
            offsets = _STAGE_OFFSETS[effective_giai_doan]

            # --- F0 ---
            f0_expected = trong_dt + timedelta(days=offsets["f0"])
            dist = abs((action_dt - f0_expected).days)
            if dist < best_distance:
                best_distance = dist
                best_match_id = batch["id"]

            # --- F1 → F5 ---
            f0_harvest_dt = trong_dt + timedelta(days=F0_DAYS_TO_THU)
            for n in range(1, MAX_GENERATION + 1):
                prev_harvest = f0_harvest_dt + timedelta(days=FN_CYCLE_DAYS * (n - 1))
                fn_expected = prev_harvest + timedelta(days=offsets["fn"])
                dist = abs((action_dt - fn_expected).days)
                if dist < best_distance:
                    best_distance = dist
                    best_match_id = batch["id"]
        else:
            # Giai đoạn không xác định → đợt trồng gần nhất trước ngày hành động
            if trong_dt <= action_dt:
                dist = (action_dt - trong_dt).days
                if dist < best_distance:
                    best_distance = dist
                    best_match_id = batch["id"]

    # Fallback: nếu tất cả đợt trồng đều SAU ngày hành động → chọn đợt sớm nhất
    if best_match_id is None:
        best_match_id = sorted(res.data, key=lambda b: b["ngay_trong"])[0]["id"]

    return best_match_id


# =====================================================
# STYLE TÙY CHỈNH (CSS)
# =====================================================
st.markdown("""
<style>
    /* --- Loại bỏ khoảng trắng mặc định ở đầu trang --- */
    .stMainBlockContainer { padding-top: 1rem !important; }
    header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; padding: 0 !important; }
    .stDeployButton { display: none !important; }

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
    for k in ["queue_stg", "queue_des", "queue_har", "queue_sm", "queue_inv", "queue_bsr", "queue_fus"]:
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
    """Lấy danh sách Tên Lô gốc từ dim_lo (đã chuẩn hóa)."""
    res = supabase.table("dim_lo").select("lo_name, dim_farm!inner(farm_name)") \
        .eq("dim_farm.farm_name", farm).eq("is_active", True).order("lo_name").execute()
    if res.data:
        return list(dict.fromkeys(r["lo_name"] for r in res.data))  # unique, preserve order
    return []

def fetch_table_data(table_name: str, farm: str) -> pd.DataFrame:
    """Hàm chung lấy dữ liệu. Quản trị viên (Admin) sẽ lấy của tất cả các farm."""
    tables_with_lo = [
        "stage_logs", "harvest_logs", "destruction_logs", "bsr_logs", 
        "size_measure_logs", "tree_inventory_logs", "soil_ph_logs", 
        "fusarium_logs", "seasons", "base_lots"
    ]
    
    if table_name in tables_with_lo:
        # Use left join (not !inner) so records with dim_lo_id=NULL still appear
        query = supabase.table(table_name).select("*, dim_lo(lo_name, area_ha, dim_doi(doi_name), dim_farm(farm_name))").eq("is_deleted", False)
        if farm not in ["Admin", "Phòng Kinh doanh"] and farm:
            # For non-admin, we need dim_lo to exist for farm filtering to work
            # But we still show orphan records to avoid silent data loss
            query = supabase.table(table_name).select("*, dim_lo!inner(lo_name, area_ha, dim_doi!inner(doi_name), dim_farm!inner(farm_name))").eq("is_deleted", False)
            query = query.eq("dim_lo.dim_farm.farm_name", farm)
    else:
        query = supabase.table(table_name).select("*")
        if table_name != "user_roles":
            query = query.eq("is_deleted", False)
            if farm not in ["Admin", "Phòng Kinh doanh"] and farm:
                query = query.eq("farm", farm)

    if table_name != "user_roles":
        res = query.order("created_at", desc=True).execute()
    else:
        res = query.execute()

    if not res.data:
        return pd.DataFrame()
        
    df = pd.DataFrame(res.data)
    
    if table_name in tables_with_lo:
        df["farm"] = df["dim_lo"].apply(lambda x: (x.get("dim_farm") or {}).get("farm_name") if isinstance(x, dict) and x else None)
        df["team"] = df["dim_lo"].apply(lambda x: (x.get("dim_doi") or {}).get("doi_name") if isinstance(x, dict) and x else None)
        df["lo"] = df["dim_lo"].apply(lambda x: x.get("lo_name") if isinstance(x, dict) and x else None)
        df["dien_tich"] = df["dim_lo"].apply(lambda x: x.get("area_ha") if isinstance(x, dict) and x else None)
        df["lot_id"] = df["lo"]
            
        # Optional: we can drop dim_lo if needed, but it shouldn't hurt
        # df = df.drop(columns=["dim_lo"])

    return df
@st.cache_data(ttl=60)
def get_dim_lo_id(farm_name: str, lo_name: str):
    if not farm_name or not lo_name: return None
    res = supabase.table("dim_lo").select("lo_id, dim_farm!inner(farm_name)").eq("lo_name", lo_name).eq("dim_farm.farm_name", farm_name).limit(1).execute()
    return res.data[0]["lo_id"] if res.data else None

def get_or_create_dim_lo(farm_name: str, lo_name: str, team_name: str = None):
    """Tìm dim_lo_id. Nếu lô chưa tồn tại → tự động tạo mới trong dim_lo."""
    existing = get_dim_lo_id(farm_name, lo_name)
    if existing:
        return existing
    
    # Lô chưa có → tạo mới
    # 1. Tìm farm_id
    farm_res = supabase.table("dim_farm").select("farm_id").eq("farm_name", farm_name).limit(1).execute()
    if not farm_res.data:
        st.error(f"❌ Không tìm thấy Farm '{farm_name}' trong hệ thống.")
        return None
    farm_id = farm_res.data[0]["farm_id"]
    
    # 2. Tìm doi_id (team)
    doi_id = None
    if team_name:
        doi_res = supabase.table("dim_doi").select("doi_id").eq("farm_id", farm_id).eq("doi_name", team_name).limit(1).execute()
        if doi_res.data:
            doi_id = doi_res.data[0]["doi_id"]
    
    # 3. Insert vào dim_lo
    new_lo = {
        "farm_id": farm_id,
        "lo_code": lo_name,
        "lo_name": lo_name,
        "lo_type": "Lô thực",
        "is_active": True
    }
    if doi_id:
        new_lo["doi_id"] = doi_id
    
    try:
        res = supabase.table("dim_lo").insert(new_lo).execute()
        if res.data:
            new_id = res.data[0]["lo_id"]
            # Clear cache so subsequent calls see the new lot
            get_dim_lo_id.clear()
            return new_id
    except Exception as e:
        st.error(f"❌ Lỗi khi tạo Lô mới trong danh mục: {e}")
    return None

def insert_to_db(table_name: str, data: dict) -> bool:
    try:
        tables_with_lo = [
            "stage_logs", "harvest_logs", "destruction_logs", "bsr_logs", 
            "size_measure_logs", "tree_inventory_logs", "soil_ph_logs", 
            "fusarium_logs", "seasons", "base_lots"
        ]
        if table_name in tables_with_lo:
            dim_id = None
            if "dim_lo_id" not in data:
                if "lot_id" in data and "farm" in data:
                    dim_id = get_dim_lo_id(data["farm"], data["lot_id"])
                elif "lo" in data and "farm" in data:
                    dim_id = get_dim_lo_id(data["farm"], data["lo"])
                if dim_id:
                    data["dim_lo_id"] = dim_id
            
            # Remove denormalized fields so insert to Supabase doesn't fail
            for col in ["farm", "team", "lot_id", "lo"]:
                data.pop(col, None)
            
            # GUARD: Block insert if dim_lo_id is still missing
            if not data.get("dim_lo_id"):
                st.error("❌ Lỗi hệ thống: Không tìm thấy Lô trong danh mục (dim_lo_id = null). Vui lòng kiểm tra tên Lô.")
                return False
            
            # Auto-resolve base_lot_id cho stage/harvest/destruction logs
            auto_resolve_tables = ["stage_logs", "harvest_logs", "destruction_logs"]
            if table_name in auto_resolve_tables and not data.get("base_lot_id"):
                date_col_map = {"stage_logs": "ngay_thuc_hien", "harvest_logs": "ngay_thu_hoach", "destruction_logs": "ngay_xuat_huy"}
                giai_doan_map = {"stage_logs": data.get("giai_doan", ""), "harvest_logs": "Thu hoạch", "destruction_logs": data.get("giai_doan", "")}
                action_date = data.get(date_col_map.get(table_name, ""))
                giai_doan = giai_doan_map.get(table_name, "")
                if action_date and data.get("dim_lo_id"):
                    resolved_id = resolve_base_lot_id(data["dim_lo_id"], action_date, giai_doan)
                    if resolved_id:
                        data["base_lot_id"] = resolved_id

        supabase.table(table_name).insert(data).execute()
        return True
    except Exception as e:
        if 'duplicate key value violates unique constraint' in str(e):
            if table_name == "base_lots":
                dim_lo_id = data.get("dim_lo_id")
                check_res = supabase.table("base_lots").select("is_deleted").eq("dim_lo_id", dim_lo_id).execute()
                if check_res.data and check_res.data[0].get("is_deleted") is True:
                    data["is_deleted"] = False
                    supabase.table("base_lots").update(data).eq("dim_lo_id", dim_lo_id).execute()
                    return True
            st.error(f"❌ Mã Lô đã tồn tại trong hệ thống. Vui lòng kiểm tra lại!")
        else:
            st.error(f"❌ Lỗi khi lưu vào {table_name}: {e}")
        return False

def get_available_capacity_for_lot(farm_name, lot_id_str, log_type, giai_doan=None, exclude_id=None):
    dim_id = get_dim_lo_id(farm_name, lot_id_str)
    if not dim_id: return 0, 0
    
    res_lot = supabase.table("base_lots").select("so_luong, so_luong_con_lai").eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
    if not res_lot.data: return 0, 0
    total_planted = sum(int(row.get("so_luong_con_lai")) if row.get("so_luong_con_lai") is not None else int(row.get("so_luong", 0)) for row in res_lot.data)

    max_allowed = total_planted

    if log_type == "stage" and giai_doan == "Cắt bắp":
        res_cb = supabase.table("stage_logs").select("so_luong").eq("dim_lo_id", dim_id).eq("giai_doan", "Chích bắp").eq("is_deleted", False).execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cb.data)
    elif log_type == "harvest":
        res_cut = supabase.table("stage_logs").select("so_luong").eq("dim_lo_id", dim_id).eq("giai_doan", "Cắt bắp").eq("is_deleted", False).execute()
        max_allowed = sum(int(r["so_luong"]) for r in res_cut.data)

    total_used = 0
    if log_type == "stage":
        res = supabase.table("stage_logs").select("id, so_luong").eq("dim_lo_id", dim_id).eq("giai_doan", giai_doan).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "harvest":
        res = supabase.table("harvest_logs").select("id, so_luong").eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
    elif log_type == "destruction":
        res = supabase.table("destruction_logs").select("id, so_luong").eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        total_used = sum(int(r["so_luong"]) for r in res.data if r["id"] != exclude_id)
        
    return max_allowed, total_used


def allocate_fifo_quantity(farm_name, lo_name, new_sl, log_type, target_date, action_type, giai_doan=None):
    dim_id = get_dim_lo_id(farm_name, lo_name)
    if not dim_id:
        return False, f"❌ Lỗi: Không tìm thấy lô {lo_name} hoặc đã bị xóa.", []
        
    is_time_valid, msg_time = validate_timeline_logic(farm_name, lo_name, target_date, action_type)
    if not is_time_valid:
        return False, msg_time, []
            
    max_allowed, total_used = get_available_capacity_for_lot(farm_name, lo_name, log_type, giai_doan)
    remain = max_allowed - total_used
    
    if remain >= int(new_sl):
        return True, "", [{"dim_lo_id": dim_id, "so_luong": int(new_sl), "lot_id": lo_name}]
    else:
        return False, f"❌ Yêu cầu {new_sl} nhưng tổng số lượng cho phép của nhánh '{lo_name}' chỉ còn {remain}.", []


def check_quantity_limit(farm_name, lot_id_str, new_sl, log_type, giai_doan=None, exclude_id=None):
    max_allowed, total_used = get_available_capacity_for_lot(farm_name, lot_id_str, log_type, giai_doan, exclude_id)
    unit = "buồng" if log_type == "harvest" else "cây"

    if log_type == "destruction":
        if int(new_sl) > (max_allowed - total_used):
            return False, f"❌ Mã lứa này chỉ còn {max_allowed - total_used} cây sống, không thể xuất hủy {new_sl} cây."
        return True, ""

    if total_used + int(new_sl) > max_allowed:
        remain = max_allowed - total_used
        return False, f"❌ Bạn đã nhập {new_sl} {unit}, nhưng lứa này chỉ có {remain} {unit} cho phép."
    return True, ""

def validate_timeline_logic(farm_name, lot_id_str, target_date, action_type):
    dim_id = get_dim_lo_id(farm_name, lot_id_str)
    if not dim_id: return False, "Lỗi không tìm thấy lô."
    
    target_dt = pd.to_datetime(target_date).tz_localize(None)
    
    if action_type == "Chích bắp":
        res = supabase.table("base_lots").select("ngay_trong").eq("dim_lo_id", dim_id).eq("is_deleted", False).execute()
        if res.data and any(r.get("ngay_trong") for r in res.data):
            valid_dates = [pd.to_datetime(r["ngay_trong"]).tz_localize(None) for r in res.data if r.get("ngay_trong")]
            if valid_dates:
                earliest_trong = min(valid_dates)
                if target_dt < earliest_trong:
                    return False, f"❌ Ngày Chích bắp ({target_dt.date()}) không thể trước Ngày Trồng ({earliest_trong.date()})."
                
    elif action_type == "Cắt bắp":
        res = supabase.table("stage_logs").select("ngay_thuc_hien").eq("dim_lo_id", dim_id).eq("giai_doan", "Chích bắp").eq("is_deleted", False).execute()
        if res.data:
            earliest_cb = min([pd.to_datetime(r["ngay_thuc_hien"]).tz_localize(None) for r in res.data])
            if target_dt < earliest_cb:
                return False, f"❌ Ngày Cắt bắp ({target_dt.date()}) không thể trước Ngày Chích bắp sớm nhất ({earliest_cb.date()})."
        else:
            return False, "❌ Lô này chưa được ghi nhận Chích bắp, không thể Cắt bắp!"
            
    elif action_type == "Thu hoạch":
        res = supabase.table("stage_logs").select("ngay_thuc_hien").eq("dim_lo_id", dim_id).eq("giai_doan", "Cắt bắp").eq("is_deleted", False).execute()
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
            if giai_doan != "Chích bắp":
                mau_day = st.text_input("🎨 Màu dây", value=def_mau, key="dlg_mau_stg", placeholder="VD: Đỏ, Xanh lá...")
            else:
                mau_day = ""
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay_th = st.date_input("📆 Ngày thực hiện", value=def_ngay, key="dlg_dt_stg")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay_th.isocalendar()[1]), disabled=True, key=f"dlg_w_stg_{ngay_th}")
            sl = st.number_input("🔢 Số lượng cây", min_value=0, step=100, value=def_sl, key="dlg_sl_stg")
        
        if st.button("✅ Cập nhật", key="btn_edit_stg", use_container_width=True, type="primary"):
            if sl <= 0: st.error("❌ Cần nhập số lượng.")
            elif giai_doan != "Chích bắp" and not mau_day.strip(): st.error("❌ Phải nhập màu dây định danh lứa đối với Cắt bắp.")
            else:
                mau_day_clean = mau_day.strip().capitalize() if mau_day.strip() else None
                is_valid, msg = check_quantity_limit(editing_row["farm"], lot_id, sl, "stage", giai_doan=giai_doan, exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    resolved_blid = resolve_base_lot_id(editing_row["dim_lo_id"], ngay_th.isoformat(), giai_doan)
                    data = {
                        "giai_doan": giai_doan, 
                        "ngay_thuc_hien": ngay_th.isoformat(), "so_luong": sl, "mau_day": mau_day_clean,
                        "tuan": ngay_th.isocalendar()[1],
                        "base_lot_id": resolved_blid
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
                is_valid, msg = check_quantity_limit(editing_row["farm"], lot_id, sl, "destruction", exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    resolved_blid = resolve_base_lot_id(editing_row["dim_lo_id"], ngay.isoformat(), gxh)
                    data = {"ngay_xuat_huy": ngay.isoformat(), "giai_doan": gxh, "ly_do": ly_do.strip(), "so_luong": sl, "tuan": ngay.isocalendar()[1], "mau_day": mau_day_clean, "base_lot_id": resolved_blid}
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
                is_valid, msg = check_quantity_limit(editing_row["farm"], lot_id, sl, "harvest", exclude_id=editing_row["id"])
                if not is_valid: st.error(msg)
                else:
                    resolved_blid = resolve_base_lot_id(editing_row["dim_lo_id"], ngay.isoformat(), "Thu hoạch")
                    data = {
                        "mau_day": mau_day_clean, 
                        "ngay_thu_hoach": ngay.isoformat(), "so_luong": sl, 
                        "hinh_thuc_thu_hoach": hinh_thuc_thu_hoach, "tuan": ngay.isocalendar()[1],
                        "base_lot_id": resolved_blid
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
                data = {"ngay_nhap": ngay.isoformat(), "bsr": bsr_val, "tuan": ngay.isocalendar()[1]}
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
                    "mau_day": mau_day_clean, "lan_do": lan_do,
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
                data = {"ngay_kiem_ke": ngay.isoformat(), "so_luong_cay_thuc_te": sl, "tuan": ngay.isocalendar()[1]}
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
                data = {"ngay_do": ngay.isoformat(), "ph_value": val, "tuan": ngay.isocalendar()[1]}
                supabase.table("soil_ph_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Lưu kết quả pH lô {lot_id} thành công!"
                st.rerun()

@dialog_decorator("✏️ Chỉnh sửa Kiểm tra Fusarium")
def edit_fusarium_log_dialog(editing_row, available_lots):
    def_lot = available_lots.index(editing_row["lot_id"]) if editing_row["lot_id"] in available_lots else 0
    def_ngay = pd.to_datetime(editing_row["ngay_kiem_tra"]).date()
    def_sl = int(editing_row["so_cay_fusarium"])
    
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("🏷️ Lứa (Mã hệ thống)", value=editing_row["lot_id"], disabled=True, key="dlg_fus_lot")
            lot_id = editing_row["lot_id"]
        with col_b:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                ngay = st.date_input("📆 Ngày kiểm tra", value=def_ngay, key="dlg_fus_ngay")
            with col_b2:
                st.text_input("📍 Tuần", value=str(ngay.isocalendar()[1]), disabled=True, key=f"dlg_w_fus_{ngay}")
            sl = st.number_input("🔢 Số cây bị Fusarium", min_value=0, step=1, value=def_sl, key="dlg_fus_sl")

        if st.button("✅ Cập nhật", key="btn_edit_fus", use_container_width=True, type="primary"):
            if sl < 0: st.error("❌ Cần nhập số cây lớn hơn hoặc bằng 0.")
            else:
                data = {"ngay_kiem_tra": ngay.isoformat(), "so_cay_fusarium": sl, "tuan": ngay.isocalendar()[1]}
                supabase.table("fusarium_logs").update(data).eq("id", editing_row["id"]).execute()
                st.session_state["toast"] = f"✅ Chi tiết Fusarium lô {lot_id} đã được lưu thành công!"
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
                correct_pass = RBAC_DB.get(selected_farm, {}).get(selected_team, "")
                if password.strip() == str(correct_pass).strip():
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

def generate_chich_bap_excel(df_lots, df_stg) -> bytes:
    """Tạo file Excel báo cáo Chích bắp theo ngày, chia sheet theo năm.
    Mỗi sheet = 1 năm. Cột = từng ngày nhóm theo tuần, Hàng = Lô (đợt trồng)."""
    import re as _re_chich

    # ── Styles ──
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    week_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    subtotal_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    grand_total_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # ── Filter chích bắp ──
    df_chich = df_stg[df_stg["giai_doan"] == "Chích bắp"].copy() if not df_stg.empty and "giai_doan" in df_stg.columns else pd.DataFrame()

    # Chỉ lấy đợt trồng mới
    if not df_lots.empty and "loai_trong" in df_lots.columns:
        valid_blids = set(df_lots[df_lots["loai_trong"] == "Trồng mới"]["id"].dropna().astype(int).tolist())
        if not df_chich.empty and "base_lot_id" in df_chich.columns:
            df_chich = df_chich[df_chich["base_lot_id"].isin(valid_blids)]

    # Loại bỏ records trước ngày trồng
    if not df_chich.empty and not df_lots.empty and "ngay_trong" in df_lots.columns:
        planting_date_map = {}
        for _, lr in df_lots.iterrows():
            if pd.notna(lr.get("id")) and pd.notna(lr.get("ngay_trong")):
                planting_date_map[int(lr["id"])] = pd.to_datetime(lr["ngay_trong"])
        def _is_after_planting(row):
            blid = row.get("base_lot_id")
            if pd.isna(blid): return True
            plant_dt = planting_date_map.get(int(blid))
            if plant_dt is None: return True
            return pd.to_datetime(row["ngay_thuc_hien"]) >= plant_dt
        df_chich = df_chich[df_chich.apply(_is_after_planting, axis=1)]

    wb = Workbook()

    if df_chich.empty:
        ws = wb.active
        ws.title = "Báo cáo Chích bắp"
        ws.cell(row=1, column=1, value="Chưa có dữ liệu Chích bắp.")
        output = io.BytesIO(); wb.save(output); output.seek(0)
        return output.getvalue()

    # Parse dates & year
    df_chich["ngay_thuc_hien"] = pd.to_datetime(df_chich["ngay_thuc_hien"])
    df_chich["tuan"] = df_chich["tuan"].fillna(
        df_chich["ngay_thuc_hien"].dt.isocalendar().week
    ).astype(int)
    df_chich["_year"] = df_chich["ngay_thuc_hien"].dt.year

    # ── Build lot display names ──
    lot_batch_keys = []
    if not df_lots.empty and "id" in df_lots.columns:
        lot_groups = df_lots.groupby("lo")
        for lo_name, grp in lot_groups:
            if len(grp) > 1:
                sorted_grp = grp.sort_values("ngay_trong") if "ngay_trong" in grp.columns else grp
                for i, (_, b_row) in enumerate(sorted_grp.iterrows(), 1):
                    lot_batch_keys.append((lo_name, b_row["id"], f"{lo_name} (đợt {i})"))
            else:
                for _, b_row in grp.iterrows():
                    lot_batch_keys.append((lo_name, b_row["id"], lo_name))
    active_blids = set(df_chich["base_lot_id"].dropna().astype(int).unique())
    lot_batch_keys = [x for x in lot_batch_keys if x[1] in active_blids]
    mapped_blids = {x[1] for x in lot_batch_keys}
    for blid in active_blids - mapped_blids:
        lo_name = df_chich[df_chich["base_lot_id"] == blid]["lo"].iloc[0] if "lo" in df_chich.columns else f"Lot_{blid}"
        lot_batch_keys.append((lo_name, blid, lo_name))

    def _nat_sort(item):
        name = item[2]
        m_batch = _re_chich.match(r"^(.+?)\s*\(đợt\s*(\d+)\)$", name)
        base_name, batch_num = (m_batch.group(1), int(m_batch.group(2))) if m_batch else (name, 0)
        m_num = _re_chich.match(r"^(\d+)(.*)", base_name)
        return (int(m_num.group(1)), m_num.group(2), batch_num) if m_num else (9999, base_name, batch_num)
    lot_batch_keys.sort(key=_nat_sort)

    # ── Build one sheet per year ──
    years = sorted(df_chich["_year"].unique())
    wb.remove(wb.active)  # remove default empty sheet

    for year in years:
        ws = wb.create_sheet(title=str(year))
        df_yr = df_chich[df_chich["_year"] == year]

        weeks = sorted(df_yr["tuan"].unique())
        week_dates = {}
        for wk in weeks:
            week_dates[wk] = sorted(df_yr[df_yr["tuan"] == wk]["ngay_thuc_hien"].dt.date.unique())

        # Lọc lot_batch_keys chỉ giữ lô có data năm này
        yr_blids = set(df_yr["base_lot_id"].dropna().astype(int).unique())
        yr_lots = [x for x in lot_batch_keys if x[1] in yr_blids]

        # === HEADER ===
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)
        c_lo = ws.cell(row=1, column=1, value="Lô")
        c_lo.font = Font(bold=True, size=11); c_lo.fill = header_fill
        c_lo.alignment = center_align; c_lo.border = thin_border
        ws.cell(row=2, column=1).border = thin_border

        col = 2
        week_col_map = {}
        for wk in weeks:
            dates = week_dates[wk]
            start_col = col
            end_col = col + len(dates)  # dates + subtotal
            ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
            c_wk = ws.cell(row=1, column=start_col, value=f"Tuần {wk}")
            c_wk.font = Font(bold=True, size=11); c_wk.fill = week_fill
            c_wk.alignment = center_align; c_wk.border = thin_border

            date_cols = {}
            for d in dates:
                c_d = ws.cell(row=2, column=col, value=d.strftime("%d/%m"))
                c_d.font = Font(size=9); c_d.fill = header_fill
                c_d.alignment = center_align; c_d.border = thin_border
                date_cols[d] = col; col += 1

            c_sub = ws.cell(row=2, column=col, value="Σ tuần")
            c_sub.font = Font(bold=True, size=9); c_sub.fill = subtotal_fill
            c_sub.alignment = center_align; c_sub.border = thin_border
            week_col_map[wk] = {"date_cols": date_cols, "subtotal_col": col}
            col += 1

        # Lũy kế column
        c_gt = ws.cell(row=1, column=col, value="Lũy kế")
        c_gt.font = Font(bold=True, size=11); c_gt.fill = grand_total_fill
        c_gt.alignment = center_align; c_gt.border = thin_border
        c_gt2 = ws.cell(row=2, column=col, value="Tổng")
        c_gt2.font = Font(bold=True, size=9); c_gt2.fill = grand_total_fill
        c_gt2.alignment = center_align; c_gt2.border = thin_border
        grand_total_col = col; total_col_end = col

        for r in range(1, 3):
            for ci in range(1, total_col_end + 1):
                ws.cell(row=r, column=ci).border = thin_border

        # === DATA ROWS ===
        data_start_row = 3
        for li, (_, blid, display_name) in enumerate(yr_lots):
            row_idx = data_start_row + li
            c = ws.cell(row=row_idx, column=1, value=display_name)
            c.font = Font(bold=True); c.border = thin_border; c.alignment = center_align
            lot_total = 0
            for wk in weeks:
                wm = week_col_map[wk]; week_sum = 0
                for d, d_col in wm["date_cols"].items():
                    mask = (df_yr["base_lot_id"] == blid) & (df_yr["ngay_thuc_hien"].dt.date == d)
                    val = int(df_yr[mask]["so_luong"].sum())
                    cell = ws.cell(row=row_idx, column=d_col, value=val if val > 0 else "")
                    cell.border = thin_border; cell.alignment = center_align
                    week_sum += val
                c_ws = ws.cell(row=row_idx, column=wm["subtotal_col"], value=week_sum if week_sum > 0 else "")
                c_ws.font = Font(bold=True); c_ws.fill = PatternFill(start_color="FFFDE7", end_color="FFFDE7", fill_type="solid")
                c_ws.border = thin_border; c_ws.alignment = center_align
                lot_total += week_sum
            c_gt_val = ws.cell(row=row_idx, column=grand_total_col, value=lot_total if lot_total > 0 else "")
            c_gt_val.font = Font(bold=True); c_gt_val.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
            c_gt_val.border = thin_border; c_gt_val.alignment = center_align

        # === TOTAL ROW ===
        total_row = data_start_row + len(yr_lots)
        c = ws.cell(row=total_row, column=1, value="TỔNG")
        c.font = Font(bold=True, size=11); c.fill = grand_total_fill
        c.border = thin_border; c.alignment = center_align
        for ci in range(2, total_col_end + 1):
            col_sum = sum(int(ws.cell(row=r, column=ci).value) for r in range(data_start_row, total_row) if isinstance(ws.cell(row=r, column=ci).value, (int, float)))
            c_tot = ws.cell(row=total_row, column=ci, value=col_sum if col_sum > 0 else "")
            c_tot.font = Font(bold=True); c_tot.fill = grand_total_fill
            c_tot.border = thin_border; c_tot.alignment = center_align

        ws.column_dimensions[get_column_letter(1)].width = 16
        for ci in range(2, total_col_end + 1):
            ws.column_dimensions[get_column_letter(ci)].width = 9
        ws.freeze_panes = "B3"

    output = io.BytesIO(); wb.save(output); output.seek(0)
    return output.getvalue()


def generate_cut_bap_excel(df_lots, df_stg, df_des) -> bytes:
    """Tạo file Excel báo cáo Cắt bắp theo tuần, chia sheet theo năm.
    Mỗi sheet = 1 năm. Mỗi tuần = 2 cột: CẮT BẮP + XUẤT HỦY."""
    # Styles
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    cut_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    des_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    total_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    COLOR_MAP = {
        "đỏ": "FFB3B3", "cam": "FFD9B3", "vàng": "FFFFB3",
        "xanh lá": "B3FFB3", "xanh dương": "B3D9FF", "tím": "D9B3FF",
        "đen": "D9D9D9", "trắng": "F5F5F5", "hồng": "FFB3D9", "nâu": "D9C4B3",
    }
    def get_mau_day_fill(mau_day_name):
        base = mau_day_name.split("-")[0].strip().lower() if mau_day_name else ""
        hex_color = COLOR_MAP.get(base)
        return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid") if hex_color else None

    # Get lots
    lot_names = sorted(df_lots["lo"].unique().tolist()) if not df_lots.empty else []
    lot_id_map = {}
    if not df_lots.empty:
        for _, row in df_lots.iterrows():
            lo = row["lo"]
            if lo not in lot_id_map: lot_id_map[lo] = []
            lot_id_map[lo].append(row["lot_id"])

    # Filter data
    df_cut = df_stg[df_stg["giai_doan"] == "Cắt bắp"].copy() if not df_stg.empty and "giai_doan" in df_stg.columns else pd.DataFrame()

    wb = Workbook()

    # Determine years from ngay_thuc_hien
    all_years = set()
    if not df_cut.empty and "ngay_thuc_hien" in df_cut.columns:
        df_cut["ngay_thuc_hien"] = pd.to_datetime(df_cut["ngay_thuc_hien"])
        df_cut["_year"] = df_cut["ngay_thuc_hien"].dt.year
        all_years.update(df_cut["_year"].dropna().unique())
    if not df_des.empty and "ngay_thuc_hien" in df_des.columns:
        df_des = df_des.copy()
        df_des["ngay_thuc_hien"] = pd.to_datetime(df_des["ngay_thuc_hien"])
        df_des["_year"] = df_des["ngay_thuc_hien"].dt.year
        all_years.update(df_des["_year"].dropna().unique())

    if not all_years:
        ws = wb.active; ws.title = "Báo cáo Cắt bắp"
        ws.cell(row=1, column=1, value="Chưa có dữ liệu Cắt bắp.")
        output = io.BytesIO(); wb.save(output); output.seek(0)
        return output.getvalue()

    years = sorted(all_years)
    wb.remove(wb.active)

    for year in years:
        ws = wb.create_sheet(title=str(int(year)))
        df_cut_yr = df_cut[df_cut["_year"] == year] if not df_cut.empty and "_year" in df_cut.columns else pd.DataFrame()
        df_des_yr = df_des[df_des["_year"] == year] if not df_des.empty and "_year" in df_des.columns else pd.DataFrame()

        # Week-color map for this year
        week_color = {}
        if not df_cut_yr.empty and "tuan" in df_cut_yr.columns and "mau_day" in df_cut_yr.columns:
            for tuan_val in df_cut_yr["tuan"].dropna().unique():
                wn = int(tuan_val)
                colors = df_cut_yr[df_cut_yr["tuan"] == tuan_val]["mau_day"].dropna().unique()
                week_color[wn] = str(colors[0]) if len(colors) > 0 else ""
        if not df_des_yr.empty and "tuan" in df_des_yr.columns:
            for tuan_val in df_des_yr["tuan"].dropna().unique():
                wn = int(tuan_val)
                if wn not in week_color:
                    colors = df_des_yr[df_des_yr["tuan"] == tuan_val]["mau_day"].dropna().unique() if "mau_day" in df_des_yr.columns else []
                    week_color[wn] = str(colors[0]) if len(colors) > 0 else ""

        weeks = sorted(week_color.keys())
        if not weeks:
            ws.cell(row=1, column=1, value=f"Chưa có dữ liệu Cắt bắp năm {int(year)}.")
            continue

        # === HEADER ===
        ws.cell(row=1, column=1, value="Lô").font = Font(bold=True, size=10)
        ws.cell(row=1, column=1).fill = header_fill
        ws.cell(row=1, column=1).border = thin_border
        ws.cell(row=1, column=1).alignment = center_align
        ws.merge_cells(start_row=1, start_column=1, end_row=3, end_column=1)

        col_offset = 2
        week_col_map = {}
        for week in weeks:
            cut_col, des_col = col_offset, col_offset + 1
            week_col_map[week] = {"cut_col": cut_col, "des_col": des_col}
            color_name = week_color.get(week, "")
            color_fill_cell = get_mau_day_fill(color_name)

            ws.merge_cells(start_row=1, start_column=cut_col, end_row=1, end_column=des_col)
            c = ws.cell(row=1, column=cut_col, value=f"Tuần {week}")
            c.font = Font(bold=True, size=11); c.fill = header_fill
            c.alignment = center_align; c.border = thin_border

            c1 = ws.cell(row=2, column=cut_col, value="CẮT BẮP")
            c1.font = Font(bold=True, color="006100"); c1.fill = cut_fill
            c1.alignment = center_align; c1.border = thin_border
            c2 = ws.cell(row=2, column=des_col, value="XUẤT HỦY")
            c2.font = Font(bold=True, color="9C0006"); c2.fill = des_fill
            c2.alignment = center_align; c2.border = thin_border

            c3 = ws.cell(row=3, column=cut_col, value=color_name)
            c3.font = Font(bold=True, size=9); c3.fill = color_fill_cell if color_fill_cell else cut_fill
            c3.alignment = center_align; c3.border = thin_border
            c4 = ws.cell(row=3, column=des_col, value=color_name)
            c4.font = Font(bold=True, size=9); c4.fill = color_fill_cell if color_fill_cell else des_fill
            c4.alignment = center_align; c4.border = thin_border
            col_offset += 2

        for r in range(1, 4):
            for ci in range(1, col_offset):
                ws.cell(row=r, column=ci).border = thin_border

        # === DATA ===
        data_start_row = 4
        for li, lo_name in enumerate(lot_names):
            row_idx = data_start_row + li
            c = ws.cell(row=row_idx, column=1, value=lo_name)
            c.font = Font(bold=True); c.border = thin_border; c.alignment = center_align
            valid_ids = lot_id_map.get(lo_name, [])
            for week in weeks:
                wm = week_col_map[week]
                val_cut = int(df_cut_yr[df_cut_yr["lot_id"].isin(valid_ids) & (df_cut_yr["tuan"] == week)]["so_luong"].sum()) if not df_cut_yr.empty else 0
                cell = ws.cell(row=row_idx, column=wm["cut_col"], value=val_cut if val_cut > 0 else "")
                cell.border = thin_border; cell.alignment = center_align
                val_des = int(df_des_yr[df_des_yr["lot_id"].isin(valid_ids) & (df_des_yr["tuan"] == week)]["so_luong"].sum()) if not df_des_yr.empty else 0
                cell = ws.cell(row=row_idx, column=wm["des_col"], value=val_des if val_des > 0 else "")
                cell.border = thin_border; cell.alignment = center_align

        # === TOTAL ===
        total_row = data_start_row + len(lot_names)
        c = ws.cell(row=total_row, column=1, value="Tổng")
        c.font = Font(bold=True, size=11); c.fill = total_fill
        c.border = thin_border; c.alignment = center_align
        for week in weeks:
            wm = week_col_map[week]
            for col_idx in [wm["cut_col"], wm["des_col"]]:
                total = sum(int(ws.cell(row=r, column=col_idx).value) for r in range(data_start_row, total_row) if isinstance(ws.cell(row=r, column=col_idx).value, (int, float)))
                c = ws.cell(row=total_row, column=col_idx, value=total if total > 0 else "")
                c.font = Font(bold=True); c.fill = total_fill
                c.border = thin_border; c.alignment = center_align

        ws.column_dimensions[get_column_letter(1)].width = 8
        for ci in range(2, col_offset):
            ws.column_dimensions[get_column_letter(ci)].width = 12

    output = io.BytesIO(); wb.save(output); output.seek(0)
    return output.getvalue()

def generate_planting_excel(df_lots, df_seasons):
    """Tạo file Excel báo cáo Trồng mới, chia sheet theo năm."""
    wb = Workbook()
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    headers = ["Ngày trồng", "Lô", "Số lượng cây", "Loại trồng"]

    if df_lots.empty:
        ws = wb.active; ws.title = "Báo cáo Trồng mới"
        ws.cell(row=1, column=1, value="Chưa có dữ liệu Trồng mới.")
        output = io.BytesIO(); wb.save(output); output.seek(0)
        return output.getvalue()

    df_plot = df_lots[['ngay_trong', 'farm', 'lo', 'so_luong', 'lot_id']].copy()
    df_plot.dropna(subset=['ngay_trong'], inplace=True)
    df_plot['ngay_trong'] = pd.to_datetime(df_plot['ngay_trong'])
    df_plot.sort_values(by='ngay_trong', inplace=True)

    # Map loai_trong
    if not df_seasons.empty and 'loai_trong' in df_seasons.columns and 'lo' in df_seasons.columns:
        seasons_map = df_seasons.drop_duplicates(subset=['farm', 'lo'])[['farm', 'lo', 'loai_trong']]
        df_plot = pd.merge(df_plot, seasons_map, on=['farm', 'lo'], how='left')
    else:
        df_plot['loai_trong'] = None
    df_plot['loai_trong'] = df_plot['loai_trong'].fillna('Trồng mới')
    df_plot['_year'] = df_plot['ngay_trong'].dt.year

    years = sorted(df_plot['_year'].unique())
    wb.remove(wb.active)

    for year in years:
        ws = wb.create_sheet(title=str(int(year)))
        # Header row
        for col_num, header_title in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header_title)
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        df_yr = df_plot[df_plot['_year'] == year]
        for r_idx, row in df_yr.iterrows():
            ngay_str = row['ngay_trong'].strftime('%d/%m/%Y')
            loai = row.get('loai_trong', 'Trồng mới') or 'Trồng mới'
            ws.append([ngay_str, row['lo'], row['so_luong'], loai])
            current_row = ws.max_row
            for col_idx in range(1, 5):
                ws.cell(row=current_row, column=col_idx).border = thin_border

        # Auto column widths
        for col in ws.columns:
            max_length = 0
            column = [cell for cell in col]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length: max_length = len(cell.value)
                except: pass
            ws.column_dimensions[get_column_letter(column[0].column)].width = max_length + 2

    output = io.BytesIO(); wb.save(output); output.seek(0)
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

    # ─── Phân loại Trồng mới vs Trồng dặm ───
    # loai_trong nằm trực tiếp trong base_lots (sau migration add_loai_trong_to_base_lots)
    # Trồng dặm KHÔNG phải đợt trồng độc lập → tách riêng khỏi forecast & bảng chi tiết
    if not df_lots_all.empty and 'loai_trong' not in df_lots_all.columns:
        df_lots_all['loai_trong'] = 'Trồng mới'  # fallback nếu cột chưa có
    
    df_lots_trong_moi = df_lots_all[df_lots_all['loai_trong'] == 'Trồng mới'] if not df_lots_all.empty else pd.DataFrame()
    df_lots_trong_dam = df_lots_all[df_lots_all['loai_trong'] == 'Trồng dặm'] if not df_lots_all.empty else pd.DataFrame()

    # Nút Xuất Báo cáo Excel 
    import base64
    st.markdown("""
    <style>
    .custom-dl-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        border-radius: 0.5rem;
        line-height: 1.6;
        width: 100%;
        min-height: 64px;
        text-align: center;
        text-decoration: none !important;
        transition: opacity 0.2s ease, filter 0.2s ease;
        box-sizing: border-box;
    }
    .custom-dl-btn:hover {
        opacity: 0.85;
        filter: brightness(0.95);
    }
    .btn-excel { background-color: #e3f2fd; color: #1565c0 !important; border: 1px solid #90caf9; }
    .btn-chich { background-color: #fff8e1; color: #f57f17 !important; border: 1px solid #ffe082; }
    .btn-cat   { background-color: #ffebee; color: #c62828 !important; border: 1px solid #ef9a9a; }
    .btn-trong { background-color: #e8f5e9; color: #2e7d32 !important; border: 1px solid #a5d6a7; }
    </style>
    """, unsafe_allow_html=True)
    
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([2, 1, 1, 1, 1])
    
    with col_t2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_lots_all.to_excel(writer, sheet_name='Base Lots (Lô trồng)', index=False)
            df_stg_all.to_excel(writer, sheet_name='Stage Logs (Tiến độ)', index=False)
            df_des_all.to_excel(writer, sheet_name='Destruction Logs', index=False)
            df_har_all.to_excel(writer, sheet_name='Harvest Logs (Thu Hoạch)', index=False)
            df_bsr_all.to_excel(writer, sheet_name='BSR Logs (Tỷ lệ)', index=False)
        b64 = base64.b64encode(output.getvalue()).decode()
        fn = f"Bao_cao_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx"
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fn}" class="custom-dl-btn btn-excel">Xuất Báo Cáo Excel</a>'
        st.markdown(href, unsafe_allow_html=True)

    with col_t3:
        chich_excel = generate_chich_bap_excel(df_lots_all, df_stg_all)
        b64 = base64.b64encode(chich_excel).decode()
        fn = f"Bao_cao_chich_bap_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx"
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fn}" class="custom-dl-btn btn-chich">Báo cáo Chích bắp</a>'
        st.markdown(href, unsafe_allow_html=True)

    with col_t4:
        cut_excel = generate_cut_bap_excel(df_lots_all, df_stg_all, df_des_all)
        b64 = base64.b64encode(cut_excel).decode()
        fn = f"Bao_cao_cat_bap_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx"
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fn}" class="custom-dl-btn btn-cat">Báo cáo Cắt bắp</a>'
        st.markdown(href, unsafe_allow_html=True)

    with col_t5:
        plant_excel = generate_planting_excel(df_lots_all, df_seasons)
        b64 = base64.b64encode(plant_excel).decode()
        fn = f"Bao_cao_trong_moi_{c_farm}_{date.today().strftime('%Y%m%d')}.xlsx"
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fn}" class="custom-dl-btn btn-trong">Báo cáo Trồng mới</a>'
        st.markdown(href, unsafe_allow_html=True)

    st.divider()

    # Filter helpers
    farms_all = ["Tất cả"] + list(df_lots_all["farm"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    teams_all = ["Tất cả"] + list(df_lots_all["team"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    lots_all = ["Tất cả"] + list(df_lots_all["lo"].dropna().unique()) if not df_lots_all.empty else ["Tất cả"]
    seasons_all = ["Tất cả"] + list(df_seasons["vu"].dropna().unique()) if not df_seasons.empty else ["Tất cả"]

    def get_dynamic_lot_options(df_lots, df_seasons, f_farm, f_team, f_vu):
        df_filtered = df_lots.copy()
        if not df_filtered.empty:
            if f_farm != "Tất cả" and "farm" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["farm"] == f_farm]
            if f_team != "Tất cả" and "team" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["team"] == f_team]
            if f_vu != "Tất cả" and not df_seasons.empty:
                valid_lots = df_seasons[df_seasons["vu"] == f_vu]["lo"].tolist()
                # we don't have lot_id in df_seasons directly linked sometimes, so match by lot ID
                # Actually, df_seasons has 'lo' or 'lot_id', but in app.py we saw: `valid_lots = df_seasons[df_seasons["vu"] == f_vu]["lo"].tolist()`. Let's match df_lots_all's 'lo' with that. 
                # Oh wait, earlier the code did: df_filtered["lot_id"].isin(valid_lots_season) but valid_lots_season was a list of "lo". Wait, that might be a bug in the old code. base_lots 'lo' should match seasons 'lo'.
                if "lo" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["lo"].isin(valid_lots)]
        return ["Tất cả"] + list(df_filtered["lo"].dropna().unique()) if not df_filtered.empty else ["Tất cả"]

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

    def show_season_info(f_vu, f_lot):
        """Hiển thị thông tin khoảng thời gian vụ khi chọn cả Vụ và Lô cụ thể."""
        if f_vu == "Tất cả" or f_lot == "Tất cả" or df_seasons.empty:
            return
        matched = df_seasons[(df_seasons["vu"] == f_vu) & (df_seasons["lo"] == f_lot)]
        if matched.empty:
            return
        row = matched.iloc[0]
        start = pd.to_datetime(row.get("ngay_bat_dau"))
        end_actual = row.get("ngay_ket_thuc_thuc_te")
        end_planned = row.get("ngay_ket_thuc_du_kien")
        end = pd.to_datetime(end_actual) if pd.notna(end_actual) else pd.to_datetime(end_planned) if pd.notna(end_planned) else None
        loai = row.get("loai_trong", "")
        
        start_str = start.strftime("%d/%m/%Y") if pd.notna(start) else "—"
        if end:
            end_label = "Kết thúc" if pd.notna(end_actual) else "Dự kiến KT"
            end_str = end.strftime("%d/%m/%Y")
        else:
            end_label, end_str = "Kết thúc", "Chưa xác định"
        
        loai_str = f" · Loại: **{loai}**" if loai else ""
        st.info(f"📅 Vụ **{f_vu}** — Lô **{f_lot}**{loai_str} · Bắt đầu: **{start_str}** · {end_label}: **{end_str}**", icon="ℹ️")

    def render_chart_filters(prefix: str, include_date: bool = False, use_dynamic_lots: bool = True):
        """
        Render bộ lọc chuẩn (Farm, Vụ, Đội, Lô, [Date]) và trả về giá trị filter.
        Args:
            prefix: tiền tố key duy nhất cho session_state (vd: "dt", "ek", "lc")
            include_date: hiển thị ô chọn khoảng thời gian
            use_dynamic_lots: True = lọc lô theo farm/team/vụ, False = hiện tất cả lô
        Returns: (farm, vu, team, lot, date_or_None)
        """
        if c_farm in ["Admin", "Phòng Kinh doanh"]:
            cols = st.columns([1, 1, 1, 1, 1.5] if include_date else [1, 1, 1, 1])
            col_idx = 0
            with cols[col_idx]:
                f_farm = st.selectbox("Lọc theo Farm", options=farms_all, key=f"{prefix}_farm")
            col_idx += 1
        else:
            f_farm = c_farm
            cols = st.columns([1, 1, 1, 1.5] if include_date else [1, 1, 1])
            col_idx = 0

        with cols[col_idx]:
            f_vu = st.selectbox("Lọc theo Vụ", options=seasons_all, key=f"{prefix}_vu")
        col_idx += 1
        with cols[col_idx]:
            f_team = st.selectbox("Lọc theo Đội", options=teams_all, key=f"{prefix}_team")
        col_idx += 1
        with cols[col_idx]:
            if use_dynamic_lots:
                lot_opts = get_dynamic_lot_options(df_lots_all, df_seasons, f_farm, f_team, f_vu)
            else:
                lot_opts = lots_all
            f_lot = st.selectbox("Lọc theo Lô", options=lot_opts, key=f"{prefix}_lot")

        f_date = None
        if include_date:
            col_idx += 1
            with cols[col_idx]:
                f_date = st.date_input("Khoảng thời gian", value=(), key=f"{prefix}_date")

        return f_farm, f_vu, f_team, f_lot, f_date

    def get_filtered_dfs(farm, vu, team, lot, date_range, data_dict):
        """Show season info và apply bộ lọc chuẩn. Trả về dict filtered DataFrames."""
        show_season_info(vu, lot)
        return apply_filters_local(farm, vu, team, lot, date_range, data_dict)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════
    # 🗺️ BẢN ĐỒ TƯƠNG TÁC FARM 157
    # ═══════════════════════════════════════════════════════════════════
    POLYGON_JSON_PATH = os.path.join(os.path.dirname(__file__), "farm_157_polygons.json")
    if os.path.exists(POLYGON_JSON_PATH) and c_farm in ["Farm 157", "Admin", "Phòng Kinh doanh"]:
        st.markdown("#### 🗺️ Bản đồ Farm 157")
        st.caption("Di chuột vào từng lô để xem thông tin chi tiết. Màu sắc thể hiện giai đoạn hiện tại.")

        with open(POLYGON_JSON_PATH, "r", encoding="utf-8") as f:
            polygon_data = json.load(f)

        # ── Build lot info từ DB data (per-batch tracking) ──
        lot_info_map = {}  # lo_name → {info dict with batches}

        def _get_batch_stage(lo_name, base_lot_id, vu="F0", season_start=None):
            """Xác định giai đoạn của 1 đợt trồng cụ thể dựa trên logs.
            Áp dụng Harvest Growth Buffer (§1.2.1): F1+ chỉ tính harvest nếu >= season_start + 18 tuần.
            """
            so_chich, so_cat, so_thu = 0, 0, 0
            if not df_stg_all.empty and "lo" in df_stg_all.columns and "base_lot_id" in df_stg_all.columns:
                stg = df_stg_all[(df_stg_all["lo"] == lo_name) & (df_stg_all["base_lot_id"] == base_lot_id)]
                if not stg.empty:
                    c = stg[stg["giai_doan"] == "Chích bắp"]
                    k = stg[stg["giai_doan"] == "Cắt bắp"]
                    so_chich = int(c["so_luong"].sum()) if not c.empty else 0
                    so_cat = int(k["so_luong"].sum()) if not k.empty else 0
            if not df_har_all.empty and "lo" in df_har_all.columns and "base_lot_id" in df_har_all.columns:
                har = df_har_all[(df_har_all["lo"] == lo_name) & (df_har_all["base_lot_id"] == base_lot_id)]
                # Harvest Growth Buffer: F1+ chỉ tính harvest >= season_start + 18 tuần
                if vu != "F0" and season_start is not None:
                    harvest_min_date = season_start + timedelta(weeks=18)
                    if "ngay_thu_hoach" in har.columns and not har.empty:
                        har_dates = pd.to_datetime(har["ngay_thu_hoach"], errors="coerce")
                        har = har[har_dates >= pd.Timestamp(harvest_min_date)]
                so_thu = int(har["so_luong"].sum()) if not har.empty else 0
            gd = "Đang sinh trưởng"
            if so_thu > 0: gd = "Thu hoạch"
            elif so_cat > 0: gd = "Cắt bắp"
            elif so_chich > 0: gd = "Chích bắp"
            return gd, so_chich, so_cat, so_thu

        if not df_seasons.empty and not df_lots_trong_moi.empty:
            for lo_name in df_lots_trong_moi["lo"].dropna().unique():
                lo_lots = df_lots_trong_moi[df_lots_trong_moi["lo"] == lo_name]
                dien_tich = lo_lots["dien_tich"].iloc[0] if "dien_tich" in lo_lots.columns and not lo_lots["dien_tich"].isna().all() else None
                lo_seasons = df_seasons[
                    (df_seasons["lo"] == lo_name) & (df_seasons["loai_trong"] != "Trồng dặm")
                ].sort_values("ngay_bat_dau", ascending=False)
                if lo_seasons.empty:
                    continue

                # Build per-batch info
                batches = []
                for _, s_row in lo_seasons.iterrows():
                    vu = s_row.get("vu", "?")
                    ngay_bd_raw = s_row.get("ngay_bat_dau")
                    ngay_bd = str(ngay_bd_raw)[:10] if ngay_bd_raw is not None else ""
                    blid = s_row.get("base_lot_id")
                    # Parse season_start cho Harvest Growth Buffer
                    season_start = None
                    if ngay_bd_raw is not None:
                        try:
                            season_start = pd.Timestamp(ngay_bd_raw).date() if not isinstance(ngay_bd_raw, date) else ngay_bd_raw
                        except Exception:
                            pass
                    # Số cây của đợt trồng này
                    if blid and not df_lots_trong_moi.empty and "id" in df_lots_trong_moi.columns:
                        batch_lot = df_lots_trong_moi[df_lots_trong_moi["id"] == blid]
                        so_cay = int(batch_lot["so_luong"].sum()) if not batch_lot.empty else 0
                    else:
                        so_cay = 0
                    gd, chich, cat, thu = _get_batch_stage(lo_name, blid, vu=vu, season_start=season_start) if blid else ("Đang sinh trưởng", 0, 0, 0)
                    batches.append({"vu": vu, "ngay_bd": ngay_bd, "so_cay": so_cay, "gd": gd, "chich": chich, "cat": cat, "thu": thu})

                # Dominant batch = nhiều cây nhất → quyết định màu polygon
                dominant = max(batches, key=lambda b: b["so_cay"]) if batches else batches[0]
                lot_info_map[lo_name] = {
                    "dominant_gd": dominant["gd"],
                    "dien_tich": float(dien_tich) if dien_tich else None,
                    "total_cay": sum(b["so_cay"] for b in batches),
                    "batches": batches,
                }

        # ── Màu theo giai đoạn ──
        stage_colors = {
            "Đang sinh trưởng": "#00b894",
            "Chích bắp": "#fdcb6e",
            "Cắt bắp": "#e17055",
            "Thu hoạch": "#0984e3",
        }
        stage_colors_json = json.dumps(stage_colors, ensure_ascii=False)
        default_color = "#636e72"

        # ── Label placement: geometric centroid + fallback ──
        def _point_in_polygon(px, py, pts):
            """Ray casting algorithm."""
            n = len(pts)
            inside = False
            j = n - 1
            for i in range(n):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                    inside = not inside
                j = i
            return inside

        def _geometric_centroid(pts):
            """Shoelace-based area centroid — trọng tâm diện tích chính xác."""
            n = len(pts)
            if n < 3:
                return sum(p[0] for p in pts)/n, sum(p[1] for p in pts)/n
            signed_area = 0
            cx = cy = 0
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                cross = x0 * y1 - x1 * y0
                signed_area += cross
                cx += (x0 + x1) * cross
                cy += (y0 + y1) * cross
            area6 = 3 * signed_area  # 6A = 3 * 2A
            if abs(area6) < 1e-6:
                return sum(p[0] for p in pts)/n, sum(p[1] for p in pts)/n
            return cx / area6, cy / area6

        def _dist_to_edge(px, py, pts):
            """Min distance from point to polygon edges."""
            min_d = float('inf')
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0:
                    d = ((px - x1)**2 + (py - y1)**2) ** 0.5
                else:
                    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)))
                    d = ((px - (x1 + t*dx))**2 + (py - (y1 + t*dy))**2) ** 0.5
                min_d = min(min_d, d)
            return min_d

        def _pole_of_inaccessibility(pts):
            """Fallback: tìm điểm xa biên nhất (cho polygon lõm nặng)."""
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            best_x = (min_x + max_x) / 2
            best_y = (min_y + max_y) / 2
            best_d = -1
            step_x = (max_x - min_x) / 10
            step_y = (max_y - min_y) / 10
            for _ in range(5):
                for ix in range(11):
                    for iy in range(11):
                        cx = min_x + ix * step_x
                        cy = min_y + iy * step_y
                        if _point_in_polygon(cx, cy, pts):
                            d = _dist_to_edge(cx, cy, pts)
                            if d > best_d:
                                best_d = d
                                best_x = cx
                                best_y = cy
                min_x = best_x - step_x
                max_x = best_x + step_x
                min_y = best_y - step_y
                max_y = best_y + step_y
                step_x /= 5
                step_y /= 5
            return best_x, best_y

        def _best_label_pos(pts):
            """Hybrid: geometric centroid nếu nằm trong polygon, else pole of inaccessibility."""
            cx, cy = _geometric_centroid(pts)
            if _point_in_polygon(cx, cy, pts):
                return cx, cy
            return _pole_of_inaccessibility(pts)

        # ── Build SVG polygons ──
        img_w = polygon_data.get("image_width", 4000)
        img_h = polygon_data.get("image_height", 2250)

        svg_polygons = ""
        for lot in polygon_data.get("lots", []):
            name = lot["name"]
            points_str = " ".join(f'{p["x"]},{p["y"]}' for p in lot["points"])
            info = lot_info_map.get(name, {})
            giai_doan = info.get("dominant_gd", "Chưa có dữ liệu")
            fill = stage_colors.get(giai_doan, default_color)
            dt = info.get("dien_tich")
            dt_str = f'{dt:.2f} ha' if dt else "—"
            total_cay = info.get("total_cay", 0)
            # Encode batches as JSON string for JS tooltip
            batches_json = json.dumps(info.get("batches", []), ensure_ascii=False).replace('"', '&quot;')

            # Hybrid label placement: geometric centroid → fallback pole of inaccessibility
            poly_pts = [(p["x"], p["y"]) for p in lot["points"]]
            cx, cy = _best_label_pos(poly_pts)

            svg_polygons += f'''
            <polygon class="lot-poly" points="{points_str}" fill="{fill}"
                data-name="{name}" data-dt="{dt_str}" data-total="{total_cay}"
                data-gd="{giai_doan}" data-batches="{batches_json}" />
            <text x="{cx:.0f}" y="{cy:.0f}" class="lot-label">{name}</text>
            '''

        # ── Legend items ──
        legend_html = ""
        for stage, color in stage_colors.items():
            legend_html += f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{stage}</span>'
        legend_html += f'<span class="legend-item"><span class="legend-dot" style="background:{default_color}"></span>Chưa có dữ liệu</span>'

        html_content = f'''
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ background: transparent; }}
            .farm-map-container {{
                position: relative;
                width: 100%;
                background: #1a1a2e;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid #2d3460;
            }}
            .farm-map-container svg {{
                display: block;
                width: 100%;
                height: auto;
            }}
            .lot-poly {{
                fill-opacity: 0.45;
                stroke: rgba(255,255,255,0.5);
                stroke-width: 3;
                cursor: pointer;
                transition: fill-opacity 0.2s, stroke-width 0.2s;
            }}
            .lot-poly:hover {{
                fill-opacity: 0.75;
                stroke: #fff;
                stroke-width: 5;
            }}
            .lot-poly.pinned {{
                fill-opacity: 0.85;
                stroke: #6366f1;
                stroke-width: 6;
            }}
            .lot-label {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 47px;
                font-weight: 700;
                fill: #fff;
                text-anchor: middle;
                dominant-baseline: central;
                pointer-events: none;
                text-shadow: 0 2px 6px rgba(0,0,0,0.7);
            }}
            .map-tooltip {{
                position: absolute;
                display: none;
                background: rgba(15, 23, 42, 0.96);
                color: #e2e8f0;
                border: 1px solid rgba(99,102,241,0.4);
                border-radius: 10px;
                padding: 14px 18px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                line-height: 1.65;
                pointer-events: none;
                z-index: 1000;
                min-width: 240px;
                max-width: 320px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.45);
                backdrop-filter: blur(8px);
            }}
            .map-tooltip.pinned {{
                pointer-events: auto;
                max-height: 480px;
                overflow-y: auto;
                border-color: rgba(99,102,241,0.8);
                box-shadow: 0 8px 32px rgba(99,102,241,0.25), 0 8px 32px rgba(0,0,0,0.45);
            }}
            .map-tooltip.pinned::-webkit-scrollbar {{ width: 4px; }}
            .map-tooltip.pinned::-webkit-scrollbar-thumb {{ background: #4a5568; border-radius: 4px; }}
            .map-tooltip .tt-title {{
                font-size: 16px;
                font-weight: 700;
                color: #fff;
                margin-bottom: 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid rgba(255,255,255,0.15);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .map-tooltip .tt-pin {{
                font-size: 12px;
                opacity: 0.6;
            }}
            .map-tooltip .tt-row {{
                display: flex;
                justify-content: space-between;
                gap: 16px;
            }}
            .map-tooltip .tt-label {{ color: #94a3b8; }}
            .map-tooltip .tt-value {{ font-weight: 600; color: #fff; }}
            .map-tooltip .tt-stage {{
                display: inline-block;
                padding: 2px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            .map-tooltip .tt-hint {{
                font-size: 11px;
                color: #64748b;
                margin-top: 8px;
                text-align: center;
                border-top: 1px solid rgba(255,255,255,0.08);
                padding-top: 6px;
            }}
            .legend-bar {{
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 16px;
                padding: 10px 16px;
                background: #16213e;
                border-top: 1px solid #2d3460;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 6px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
                color: #94a3b8;
            }}
            .legend-dot {{
                width: 12px; height: 12px;
                border-radius: 3px;
                flex-shrink: 0;
            }}
        </style>

        <div class="farm-map-container" id="farmMapContainer">
            <svg viewBox="0 0 {img_w} {img_h}" xmlns="http://www.w3.org/2000/svg">
                <rect width="{img_w}" height="{img_h}" fill="#1a1a2e"/>
                {svg_polygons}
            </svg>
            <div class="map-tooltip" id="mapTooltip"></div>
            <div class="legend-bar">{legend_html}</div>
        </div>

        <script>
        (function() {{
            const container = document.getElementById('farmMapContainer');
            const tooltip = document.getElementById('mapTooltip');
            const polys = container.querySelectorAll('.lot-poly');
            const stageColors = {stage_colors_json};
            stageColors["Chưa có dữ liệu"] = "#636e72";

            let pinned = false;
            let pinnedPoly = null;

            function buildHTML(d, showPin) {{
                let batches = [];
                try {{ batches = JSON.parse(d.batches || '[]'); }} catch(e) {{}}

                let pinIcon = showPin ? '<span class="tt-pin">📌 Đã ghim</span>' : '<span class="tt-pin"></span>';
                let html = '<div class="tt-title"><span>Lô ' + d.name + '</span>' + pinIcon + '</div>';
                html += '<div class="tt-row"><span class="tt-label">Diện tích</span><span class="tt-value">' + d.dt + '</span></div>';
                html += '<div class="tt-row"><span class="tt-label">Tổng số cây</span><span class="tt-value">' + parseInt(d.total||0).toLocaleString() + '</span></div>';

                if (batches.length > 0) {{
                    html += '<div style="border-top:1px solid rgba(255,255,255,0.1);margin:8px 0"></div>';
                    for (var i = 0; i < batches.length; i++) {{
                        var b = batches[i];
                        var sc = stageColors[b.gd] || "#636e72";
                        html += '<div style="margin-bottom:' + (i < batches.length-1 ? '8' : '0') + 'px;padding:6px 8px;background:rgba(255,255,255,0.04);border-radius:6px;border-left:3px solid ' + sc + '">';
                        html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px"><span style="font-weight:700;color:#fff">' + b.vu + '</span><span class="tt-stage" style="background:' + sc + ';color:#fff">' + b.gd + '</span></div>';
                        html += '<div class="tt-row"><span class="tt-label">Bắt đầu</span><span class="tt-value">' + b.ngay_bd + '</span></div>';
                        html += '<div class="tt-row"><span class="tt-label">Số cây</span><span class="tt-value">' + b.so_cay.toLocaleString() + '</span></div>';
                        html += '<div class="tt-row"><span class="tt-label">Chích bắp</span><span class="tt-value">' + b.chich.toLocaleString() + '</span></div>';
                        html += '<div class="tt-row"><span class="tt-label">Cắt bắp</span><span class="tt-value">' + b.cat.toLocaleString() + '</span></div>';
                        html += '<div class="tt-row"><span class="tt-label">Thu hoạch</span><span class="tt-value">' + b.thu.toLocaleString() + '</span></div>';
                        html += '</div>';
                    }}
                }} else {{
                    html += '<div style="color:#94a3b8;margin-top:6px">Chưa có dữ liệu</div>';
                }}

                if (!showPin) {{
                    html += '<div class="tt-hint">💡 Click để ghim tooltip</div>';
                }} else {{
                    html += '<div class="tt-hint">Click lô khác hoặc vùng trống để bỏ ghim</div>';
                }}
                return html;
            }}

            function unpin() {{
                pinned = false;
                if (pinnedPoly) {{
                    pinnedPoly.classList.remove('pinned');
                    pinnedPoly = null;
                }}
                tooltip.classList.remove('pinned');
                tooltip.style.display = 'none';
            }}

            polys.forEach(poly => {{
                poly.addEventListener('mouseenter', function(e) {{
                    if (pinned) return;
                    tooltip.innerHTML = buildHTML(this.dataset, false);
                    tooltip.style.display = 'block';
                }});

                poly.addEventListener('mousemove', function(e) {{
                    if (pinned) return;
                    const rect = container.getBoundingClientRect();
                    let x = e.clientX - rect.left + 16;
                    let y = e.clientY - rect.top + 16;
                    if (x + 300 > rect.width) x = e.clientX - rect.left - 310;
                    if (y + 200 > rect.height) y = Math.max(10, e.clientY - rect.top - 200);
                    tooltip.style.left = x + 'px';
                    tooltip.style.top = y + 'px';
                }});

                poly.addEventListener('mouseleave', function() {{
                    if (pinned) return;
                    tooltip.style.display = 'none';
                }});

                poly.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    if (pinned && pinnedPoly === this) {{
                        unpin();
                        return;
                    }}
                    if (pinnedPoly) pinnedPoly.classList.remove('pinned');

                    pinned = true;
                    pinnedPoly = this;
                    this.classList.add('pinned');
                    tooltip.innerHTML = buildHTML(this.dataset, true);
                    tooltip.classList.add('pinned');
                    tooltip.style.display = 'block';
                    tooltip.scrollTop = 0;

                    const rect = container.getBoundingClientRect();
                    let x = e.clientX - rect.left + 16;
                    let y = e.clientY - rect.top + 16;
                    if (x + 300 > rect.width) x = e.clientX - rect.left - 310;
                    var maxY = rect.height - 490;
                    if (y > maxY) y = Math.max(10, maxY);
                    tooltip.style.left = x + 'px';
                    tooltip.style.top = y + 'px';
                }});
            }});

            container.addEventListener('click', function(e) {{
                if (e.target.closest('.lot-poly') || e.target.closest('.map-tooltip')) return;
                if (pinned) unpin();
            }});

            tooltip.addEventListener('click', function(e) {{
                e.stopPropagation();
            }});
        }})();
        </script>
        '''

        import streamlit.components.v1 as components
        components.html(html_content, height=700, scrolling=False)

    st.divider()

    # --- BẢNG CHI TIẾT THÔNG TIN CÁC LÔ ---
    # KG dự toán: sử dụng get_kg_per_tree(vu) — F0=15, Fn=18
    st.markdown("#### 📋 Bảng chi tiết thông tin các lô (Theo Vụ)")
    st.caption("Xem thông tin chi tiết từng lô phân loại theo vụ (Season). Các cột dữ liệu dự toán và thực tế được tính toán trong phạm vi khoảng thời gian của mục tiêu.")
    st.caption(f"📉 Hao hụt: Trồng → Chích bắp **{LOSS_RATE_TO_CHICH*100:.0f}%** · Chích bắp → Thu hoạch **{LOSS_RATE_TO_CHICH*100:.0f}%** · Tổng **{LOSS_RATE_TO_THU*100:.0f}%** · Sản lượng: **F0 = {KG_PER_TREE_F0} kg/buồng**, **Fn = {KG_PER_TREE_FN} kg/buồng**")

    dt_farm, dt_vu, dt_team, dt_lot, _ = render_chart_filters("dt")

    df_dt_seasons = df_seasons.copy()
    if not df_dt_seasons.empty:
        # Loại trồng dặm khỏi bảng chi tiết (trồng dặm hiện ở bảng riêng bên dưới)
        if 'loai_trong' in df_dt_seasons.columns:
            df_dt_seasons = df_dt_seasons[df_dt_seasons['loai_trong'] != 'Trồng dặm']
        if dt_farm != "Tất cả" and "farm" in df_dt_seasons.columns:
            df_dt_seasons = df_dt_seasons[df_dt_seasons["farm"] == dt_farm]
        if dt_vu != "Tất cả" and "vu" in df_dt_seasons.columns:
            df_dt_seasons = df_dt_seasons[df_dt_seasons["vu"] == dt_vu]
        if dt_team != "Tất cả" and "team" in df_dt_seasons.columns:
            df_dt_seasons = df_dt_seasons[df_dt_seasons["team"] == dt_team]
        if dt_lot != "Tất cả" and "lo" in df_dt_seasons.columns:
            df_dt_seasons = df_dt_seasons[df_dt_seasons["lo"] == dt_lot]
        
        # ── Merge diện tích trồng thực tế từ base_lots ──
        # dien_tich_trong (per-batch) thay thế area_ha (per-lot max)
        if not df_lots_trong_moi.empty and "id" in df_lots_trong_moi.columns and "dien_tich_trong" in df_lots_trong_moi.columns:
            _dt_map = df_lots_trong_moi.set_index("id")["dien_tich_trong"].to_dict()
            df_dt_seasons["dien_tich_trong"] = df_dt_seasons["base_lot_id"].map(_dt_map)

    if not df_dt_seasons.empty:
        detail_rows_by_vu = {}
        
        # ─── Xây dựng label "đợt X" cho các lô có nhiều đợt trồng (chỉ trồng mới) ───
        batch_label_map = {}  # {base_lot_id: "Tên lô (đợt N)" hoặc "Tên lô"}
        if not df_lots_trong_moi.empty and "id" in df_lots_trong_moi.columns and "lo" in df_lots_trong_moi.columns:
            lot_groups = df_lots_trong_moi.groupby("lo")
            for lo_name_grp, grp_df in lot_groups:
                if len(grp_df) > 1:
                    # Nhiều đợt → sort theo ngày trồng, đánh số
                    sorted_grp = grp_df.sort_values("ngay_trong") if "ngay_trong" in grp_df.columns else grp_df
                    for i, (_, b_row) in enumerate(sorted_grp.iterrows(), 1):
                        batch_label_map[b_row["id"]] = f"{lo_name_grp} (đợt {i})"
                else:
                    # Chỉ 1 đợt → giữ nguyên tên lô
                    for _, b_row in grp_df.iterrows():
                        batch_label_map[b_row["id"]] = lo_name_grp

        # ─── Dedup: bỏ season trùng (vu, base_lot_id) ───
        # Sort: ưu tiên season đã kết thúc (có ngay_ket_thuc_thuc_te), rồi ngay_bat_dau mới nhất
        df_dt_seasons = df_dt_seasons.copy()
        df_dt_seasons["_has_end"] = df_dt_seasons["ngay_ket_thuc_thuc_te"].notna().astype(int)
        df_dt_seasons = df_dt_seasons.sort_values(["_has_end", "ngay_bat_dau"], ascending=[False, False])
        seen_vu_blid = set()
        
        # ─── Build next_season_start + kiểm tra vụ kế có sản xuất chưa ───
        _next_season_map = {}  # (base_lot_id, vu) → ngày bắt đầu vụ kế tiếp (hoặc None)
        _next_vu_producing = set()  # set of (base_lot_id, vu) đã có chích bắp
        
        # Pre-build: (base_lot_id, vu) nào đã có chích bắp?
        if not df_stg_all.empty and "base_lot_id" in df_stg_all.columns:
            stg_chich = df_stg_all[df_stg_all["giai_doan"] == "Chích bắp"]
            if not stg_chich.empty:
                # Cần xác định chích bắp thuộc vụ nào → dùng season date range
                for _, s_row in df_dt_seasons[df_dt_seasons["base_lot_id"].notna()].iterrows():
                    s_blid = int(s_row["base_lot_id"])
                    s_vu = s_row["vu"]
                    s_start = pd.to_datetime(s_row["ngay_bat_dau"])
                    chich_for_blid = stg_chich[stg_chich["base_lot_id"] == s_blid]
                    if not chich_for_blid.empty:
                        chich_in_range = chich_for_blid[
                            pd.to_datetime(chich_for_blid["ngay_thuc_hien"]).dt.date >= s_start.date()
                        ]
                        if not chich_in_range.empty:
                            _next_vu_producing.add((s_blid, s_vu))
        
        if "base_lot_id" in df_dt_seasons.columns:
            for blid, blid_grp in df_dt_seasons[df_dt_seasons["base_lot_id"].notna()].groupby("base_lot_id"):
                sorted_seasons = blid_grp.sort_values("ngay_bat_dau").drop_duplicates("vu")
                vu_list = sorted_seasons[["vu", "ngay_bat_dau"]].values.tolist()
                for i, (vu_val, start_dt) in enumerate(vu_list):
                    if i + 1 < len(vu_list):
                        next_vu = vu_list[i + 1][0]
                        next_blid = int(blid)
                        # Chỉ set upper bound nếu vụ KẾ TIẾP đã có chích bắp
                        if (next_blid, next_vu) in _next_vu_producing:
                            _next_season_map[(int(blid), vu_val)] = pd.to_datetime(vu_list[i + 1][1])
                        else:
                            _next_season_map[(int(blid), vu_val)] = None
                    else:
                        _next_season_map[(int(blid), vu_val)] = None

        for idx, row in df_dt_seasons.iterrows():
            f_vu = row.get("vu")
            lo_name = row.get("lo")
            lot_id = row.get("lot_id") or row.get("dim_lo_id")
            season_blid = row.get("base_lot_id")
            dien_tich_trong = row.get("dien_tich_trong")
            dien_tich_fallback = row.get("dien_tich", 0)
            # Ưu tiên diện tích trồng thực tế (per-batch), fallback diện tích lô tối đa (per-lot)
            dien_tich = float(dien_tich_trong) if pd.notna(dien_tich_trong) else (float(dien_tich_fallback) if pd.notna(dien_tich_fallback) else 0.0)

            # Skip duplicate (vu, base_lot_id) - giữ dòng đầu tiên
            if pd.notna(season_blid):
                dedup_key = (f_vu, int(season_blid))
                if dedup_key in seen_vu_blid:
                    continue
                seen_vu_blid.add(dedup_key)

            start = pd.to_datetime(row.get("ngay_bat_dau"))
            end_actual = row.get("ngay_ket_thuc_thuc_te")
            end_planned = row.get("ngay_ket_thuc_du_kien")
            end = pd.to_datetime(end_actual) if pd.notna(end_actual) else pd.to_datetime(end_planned) if pd.notna(end_planned) else None

            start_str = start.strftime("%d/%m/%Y") if pd.notna(start) else "—"
            if pd.notna(end):
                end_str = end.strftime("%d/%m/%Y")
            else:
                end_str = "Hiện tại"
            thoi_gian_vu = f"{start_str} - {end_str}"

            # ─── Lọc dữ liệu theo base_lot_id (chính xác theo đợt trồng) ───
            has_blid_col = (not df_stg_all.empty and "base_lot_id" in df_stg_all.columns) or \
                           (not df_har_all.empty and "base_lot_id" in df_har_all.columns)
            
            if pd.notna(season_blid) and has_blid_col:
                # ✅ NEW: Filter chính xác theo đợt trồng
                sub_lots = df_lots_all[df_lots_all["id"] == season_blid] if "id" in df_lots_all.columns else pd.DataFrame()
                sub_stg = df_stg_all[df_stg_all["base_lot_id"] == season_blid] if not df_stg_all.empty else pd.DataFrame()
                sub_har = df_har_all[df_har_all["base_lot_id"] == season_blid] if not df_har_all.empty else pd.DataFrame()
                sub_des = df_des_all[df_des_all["base_lot_id"] == season_blid] if not df_des_all.empty else pd.DataFrame()
            else:
                # ⚠️ FALLBACK: Lô chưa có base_lot_id → dùng lot_id
                sub_lots = df_lots_all[df_lots_all["lot_id"] == lot_id] if not df_lots_all.empty else pd.DataFrame()
                sub_stg = df_stg_all[df_stg_all["lot_id"] == lot_id] if not df_stg_all.empty else pd.DataFrame()
                sub_har = df_har_all[df_har_all["lot_id"] == lot_id] if not df_har_all.empty else pd.DataFrame()
                sub_des = df_des_all[df_des_all["lot_id"] == lot_id] if not df_des_all.empty else pd.DataFrame()

            # ─── Filter date range cho stage/harvest/destruction ───
            # (Cả khi đã filter base_lot_id, vì cùng đợt trồng có nhiều vụ F0/F1/F2...)
            # ⚠️ KHÔNG filter sub_lots: "Cây đã trồng" là thuộc tính đợt trồng,
            # không thay đổi theo vụ (F0=F1=F2=... = số cây gốc).
            if pd.notna(start):
                if not sub_stg.empty and "ngay_thuc_hien" in sub_stg.columns:
                    sub_stg = sub_stg[pd.to_datetime(sub_stg["ngay_thuc_hien"]).dt.date >= start.date()]
                if not sub_har.empty and "ngay_thu_hoach" in sub_har.columns:
                    sub_har = sub_har[pd.to_datetime(sub_har["ngay_thu_hoach"]).dt.date >= start.date()]
                if not sub_des.empty and "ngay_xuat_huy" in sub_des.columns:
                    sub_des = sub_des[pd.to_datetime(sub_des["ngay_xuat_huy"]).dt.date >= start.date()]
            if pd.notna(end):
                if not sub_stg.empty and "ngay_thuc_hien" in sub_stg.columns:
                    sub_stg = sub_stg[pd.to_datetime(sub_stg["ngay_thuc_hien"]).dt.date <= end.date()]
                if not sub_des.empty and "ngay_xuat_huy" in sub_des.columns:
                    sub_des = sub_des[pd.to_datetime(sub_des["ngay_xuat_huy"]).dt.date <= end.date()]
            
            # ─── Harvest upper bound: dùng start vụ KẾ TIẾP (nếu vụ kế đã sản xuất) ───
            # Thu hoạch có thể kéo dài sau end date hành chính,
            # nhưng chỉ giới hạn khi vụ kế tiếp ĐÃ có chích bắp (đang sản xuất).
            # Nếu vụ kế chưa sản xuất → harvest vẫn thuộc vụ hiện tại.
            if pd.notna(season_blid):
                next_start = _next_season_map.get((int(season_blid), f_vu))
                if next_start is not None and not sub_har.empty and "ngay_thu_hoach" in sub_har.columns:
                    # F0: upper bound = next_season_start + growth buffer
                    # (Thu hoạch F0 có thể kéo dài sau ngày bắt đầu hành chính F1)
                    harvest_upper = next_start + pd.Timedelta(weeks=18)
                    sub_har = sub_har[pd.to_datetime(sub_har["ngay_thu_hoach"]).dt.date < harvest_upper.date()]
            elif pd.notna(end):
                # Fallback: dùng season end date cho harvest nếu không có next_season_map
                if not sub_har.empty and "ngay_thu_hoach" in sub_har.columns:
                    sub_har = sub_har[pd.to_datetime(sub_har["ngay_thu_hoach"]).dt.date <= end.date()]

            so_luong_trong = int(sub_lots["so_luong"].sum()) if not sub_lots.empty else 0
            so_chich_bap = int(sub_stg[sub_stg["giai_doan"] == "Chích bắp"]["so_luong"].sum()) if not sub_stg.empty else 0
            so_cat_bap = int(sub_stg[sub_stg["giai_doan"] == "Cắt bắp"]["so_luong"].sum()) if not sub_stg.empty else 0
            so_thu_hoach = int(sub_har["so_luong"].sum()) if not sub_har.empty else 0
            
            # ─── Safety: thu hoạch chưa thể xảy ra nếu chưa đủ thời gian sinh trưởng ───
            # Vụ Fn (n>=1): cây cần ít nhất ~18 tuần từ khi bắt đầu vụ mới đến khi thu hoạch.
            # Nếu harvest_date < season_start + 18 tuần → đó là harvest F(n-1) bị overlap, loại bỏ.
            HARVEST_MIN_GROWTH_WEEKS = 18
            if f_vu != "F0" and pd.notna(start):
                harvest_earliest = start + pd.Timedelta(weeks=HARVEST_MIN_GROWTH_WEEKS)
                if not sub_har.empty and "ngay_thu_hoach" in sub_har.columns:
                    sub_har = sub_har[pd.to_datetime(sub_har["ngay_thu_hoach"]).dt.date >= harvest_earliest.date()]
                so_thu_hoach = int(sub_har["so_luong"].sum()) if not sub_har.empty else 0
            
            # Fallback: nếu F1+ mà chưa có chích bắp → chắc chắn chưa thu hoạch
            if f_vu != "F0" and so_chich_bap == 0:
                so_thu_hoach = 0

            # Tên lô: gắn "(đợt X)" nếu lô có nhiều đợt trồng
            display_lo = batch_label_map.get(season_blid, lo_name) if pd.notna(season_blid) else lo_name

            if f_vu not in detail_rows_by_vu:
                detail_rows_by_vu[f_vu] = []

            dt_chich_est = int(round(so_luong_trong * get_estimated_rate("chich_bap")))
            dt_cat_est   = int(round(so_luong_trong * get_estimated_rate("cat_bap")))
            dt_thu_est   = int(round(so_luong_trong * get_estimated_rate("thu_hoach")))

            detail_rows_by_vu[f_vu].append({
                ("Thông tin", "Thời gian vụ"): thoi_gian_vu,
                ("Thông tin", "Tên lô"): display_lo,
                ("Thông tin", "DT trồng (ha)"): f"{dien_tich:.2f}",
                ("Thông tin", "Cây đã trồng"): so_luong_trong,
                ("Chích bắp", "Dự toán"): dt_chich_est,
                ("Chích bắp", "Thực tế"): so_chich_bap,
                ("Cắt bắp", "Dự toán"): dt_cat_est,
                ("Cắt bắp", "Thực tế"): so_cat_bap,
                ("Thu hoạch", "Dự toán"): dt_thu_est,
                ("Thu hoạch", "Thực tế"): so_thu_hoach,
                ("Tổng khối lượng (kg)", "Dự toán"): dt_thu_est * get_kg_per_tree(f_vu),
                ("Tổng khối lượng (kg)", "Thực tế"): so_thu_hoach * get_kg_per_tree(f_vu)
            })
            
        # ─── Sort bảng theo tên lô tự nhiên (3B < 4A < 12A) rồi đợt trồng ───
        import re
        def _lo_sort_key(row_dict):
            name = row_dict.get(("Thông tin", "Tên lô"), "")
            # Tách: "3B (đợt 2)" → base="3B", batch=2
            m_batch = re.match(r"^(.+?)\s*\(đợt\s*(\d+)\)$", name)
            if m_batch:
                base_name, batch_num = m_batch.group(1), int(m_batch.group(2))
            else:
                base_name, batch_num = name, 0
            # Natural sort: "3B" → (3, "B"), "12A" → (12, "A")
            m_num = re.match(r"^(\d+)(.*)", base_name)
            if m_num:
                return (int(m_num.group(1)), m_num.group(2), batch_num)
            return (9999, base_name, batch_num)

        for vu_key in detail_rows_by_vu:
            detail_rows_by_vu[vu_key].sort(key=_lo_sort_key)

        with st.expander("📋 Xem toàn bộ thông tin", expanded=True):
            if detail_rows_by_vu:
                # Đẩy CSS override thẳng vào markdown để đảm bảo mọi table được xuất từ to_html() đều căn giữa tuyệt đối
                st.markdown("""
                    <style>
                    .centered-table-wrapper table th, .centered-table-wrapper table td {
                        text-align: center !important;
                    }
                    .centered-table-wrapper table {
                        width: 100%;
                    }
                    </style>
                """, unsafe_allow_html=True)

                for vu_val, rows in detail_rows_by_vu.items():
                    st.markdown(f"##### 🌿 Vụ {vu_val}")
                    df_detail = pd.DataFrame(rows)
                    if not isinstance(df_detail.columns, pd.MultiIndex):
                        df_detail.columns = pd.MultiIndex.from_tuples(df_detail.columns)
                    
                    # Tính tổng các cột trước khi format chuỗi
                    # Diện tích trồng (per-batch): mỗi đợt có diện tích riêng → sum trực tiếp
                    _area_col = df_detail[("Thông tin", "DT trồng (ha)")].astype(float)
                    total_dien_tich = _area_col.sum()
                    total_row = {
                        ("Thông tin", "Thời gian vụ"): "",
                        ("Thông tin", "Tên lô"): "<b>TỔNG</b>",
                        ("Thông tin", "DT trồng (ha)"): f"<b>{total_dien_tich:.2f}</b>",
                        ("Thông tin", "Cây đã trồng"): f"<b>{df_detail[('Thông tin', 'Cây đã trồng')].sum():,}</b>",
                        ("Chích bắp", "Dự toán"): f"<b>{df_detail[('Chích bắp', 'Dự toán')].sum():,}</b>",
                        ("Chích bắp", "Thực tế"): f"<b>{df_detail[('Chích bắp', 'Thực tế')].sum():,}</b>",
                        ("Cắt bắp", "Dự toán"): f"<b>{df_detail[('Cắt bắp', 'Dự toán')].sum():,}</b>",
                        ("Cắt bắp", "Thực tế"): f"<b>{df_detail[('Cắt bắp', 'Thực tế')].sum():,}</b>",
                        ("Thu hoạch", "Dự toán"): f"<b>{df_detail[('Thu hoạch', 'Dự toán')].sum():,}</b>",
                        ("Thu hoạch", "Thực tế"): f"<b>{df_detail[('Thu hoạch', 'Thực tế')].sum():,}</b>",
                        ("Tổng khối lượng (kg)", "Dự toán"): f"<b>{df_detail[('Tổng khối lượng (kg)', 'Dự toán')].sum():,}</b>",
                        ("Tổng khối lượng (kg)", "Thực tế"): f"<b>{df_detail[('Tổng khối lượng (kg)', 'Thực tế')].sum():,}</b>"
                    }
                    
                    # Format số nguyên có dấu phẩy cho các dòng dữ liệu
                    for c in df_detail.columns:
                        if df_detail[c].dtype.kind in 'iuf' and c[1] != "Diện tích (ha)":
                            df_detail[c] = df_detail[c].apply(lambda x: f"{int(x):,}")
                            
                    # Thêm dòng tổng vào DataFrame
                    df_detail = pd.concat([df_detail, pd.DataFrame([total_row])], ignore_index=True)
                    
                    # Căn giữa MultiIndex Header và các ô
                    styled_df = df_detail.style.set_properties(**{'text-align': 'center'})
                    styled_df = styled_df.set_table_styles([
                        {"selector": "th", "props": [("text-align", "center")]},
                        {"selector": "th.col_heading", "props": [("text-align", "center")]},
                        {"selector": "td", "props": [("text-align", "center")]}
                    ])
                    # Xoá index mặc định bằng Pandas Styler
                    styled_df = styled_df.hide(axis="index")
                    
                    # Render bằng HTML thuần để xử lý triệt để bug của Streamlit Arrow
                    # (Arrow tự convert string format thành chuỗi dư 0 & làm mất CSS center header)
                    table_html = styled_df.to_html(escape=False)
                    st.markdown(f'<div class="centered-table-wrapper" style="overflow-x: auto; margin-bottom: 2rem;">{table_html}</div>', unsafe_allow_html=True)
            else:
                st.info("Chưa có cấu hình Vụ/Lô nào để hiển thị bảng chi tiết.")
    else:
        st.info("Chưa có cấu hình Vụ/Lô nào để hiển thị bảng chi tiết.")
    # ─── Bảng Lịch sử Trồng dặm ───
    if not df_lots_trong_dam.empty:
        import re as _re_dam
        # Filter theo farm hiện tại (dt_farm) nếu có
        df_dam_display = df_lots_trong_dam.copy()
        if dt_farm != "Tất cả" and "farm" in df_dam_display.columns:
            df_dam_display = df_dam_display[df_dam_display["farm"] == dt_farm]
        
        if not df_dam_display.empty:
            with st.expander(f"📋 Lịch sử Trồng dặm ({len(df_dam_display)} đợt · {df_dam_display['so_luong'].sum():,} cây)", expanded=False):
                # Sort tự nhiên theo lô, rồi theo ngày
                def _nat_sort_dam(name):
                    m = _re_dam.match(r"^(\d+)(.*)", str(name))
                    return (int(m.group(1)), m.group(2)) if m else (9999, str(name))
                
                df_dam_tbl = df_dam_display[["lo", "farm", "ngay_trong", "so_luong"]].copy()
                df_dam_tbl["ngay_trong"] = pd.to_datetime(df_dam_tbl["ngay_trong"]).dt.strftime("%d/%m/%Y")
                df_dam_tbl["_sort"] = df_dam_tbl["lo"].apply(_nat_sort_dam)
                df_dam_tbl = df_dam_tbl.sort_values(["_sort", "ngay_trong"]).drop(columns=["_sort"])
                df_dam_tbl.columns = ["Lô", "Farm", "Ngày trồng dặm", "Số cây"]
                
                # Tổng dặm theo lô
                summary_dam = df_dam_display.groupby("lo")["so_luong"].agg(["sum", "count"]).reset_index()
                summary_dam.columns = ["Lô", "Tổng cây dặm", "Số đợt"]
                
                col_dam1, col_dam2 = st.columns([2, 1])
                with col_dam1:
                    st.caption("Chi tiết từng đợt trồng dặm")
                    styled_dam = df_dam_tbl.style.set_properties(**{'text-align': 'center', 'font-size': '0.85rem'})
                    styled_dam = styled_dam.set_table_styles([
                        {"selector": "th", "props": [("text-align", "center"), ("font-size", "0.85rem")]},
                    ]).hide(axis="index")
                    st.markdown(f'<div style="overflow-x:auto;">{styled_dam.to_html(escape=False)}</div>', unsafe_allow_html=True)
                with col_dam2:
                    st.caption("Tổng hợp theo lô")
                    styled_sum = summary_dam.style.set_properties(**{'text-align': 'center', 'font-size': '0.85rem'})
                    styled_sum = styled_sum.set_table_styles([
                        {"selector": "th", "props": [("text-align", "center"), ("font-size", "0.85rem")]},
                    ]).hide(axis="index")
                    st.markdown(f'<div style="overflow-x:auto;">{styled_sum.to_html(escape=False)}</div>', unsafe_allow_html=True)

    st.divider()

    # --- LỊCH THU HOẠCH DỰ KIẾN (Normal Distribution Model) ---
    st.markdown("#### 📅 Lịch Thu hoạch Dự kiến")
    st.caption(f"Hao hụt từ Trồng → Thu hoạch: **{LOSS_RATE_TO_THU*100:.0f}%/vụ** · Sản lượng: **F0 = {KG_PER_TREE_F0} kg/buồng**, **Fn = {KG_PER_TREE_FN} kg/buồng**")

    if not df_lots_trong_moi.empty and "ngay_trong" in df_lots_trong_moi.columns and "lo" in df_lots_trong_moi.columns:
        from scipy.stats import norm as scipy_norm
        import numpy as np
        import re as _re
        
        LOSS_RATE = LOSS_RATE_TO_THU  # Sử dụng constant trung tâm
        FORECAST_GENERATIONS = 4  # F0, F1, F2, F3
        # Mặc định khoảng thời gian (ngày) — có thể tùy chỉnh bởi user
        DEFAULT_DAYS_BOI = 14   # 14 ngày thu bói
        DEFAULT_DAYS_RO  = 26   # 26 ngày thu rộ
        DEFAULT_DAYS_VET = 14   # 14 ngày thu vét
        
        # ─── Tùy chỉnh tỷ lệ phân phối thu hoạch ───
        with st.expander("⚙️ Tùy chỉnh tỷ lệ phân phối thu hoạch", expanded=False):
            st.caption("Mặc định: Thu bói 10% · Thu rộ 80% · Thu vét 10%. Thay đổi tỷ lệ để xem kịch bản khác. Tổng phải = 100%.")
            col_boi, col_ro, col_vet = st.columns(3)
            with col_boi:
                pct_boi = st.number_input("Thu bói (%)", min_value=0, max_value=100, 
                                           value=10, step=1, key="pct_thu_boi")
            with col_ro:
                pct_ro = st.number_input("Thu rộ (%)", min_value=0, max_value=100, 
                                          value=80, step=1, key="pct_thu_ro")
            with col_vet:
                pct_vet = st.number_input("Thu vét (%)", min_value=0, max_value=100, 
                                           value=10, step=1, key="pct_thu_vet")
            
            total_pct = pct_boi + pct_ro + pct_vet
            if total_pct != 100:
                st.warning(f"⚠️ Tổng tỷ lệ = {total_pct}%, cần = 100%. Đang dùng mặc định 10/80/10.")
                pct_boi, pct_ro, pct_vet = 10, 80, 10

            st.divider()
            st.caption(f"Mặc định: Thu bói {DEFAULT_DAYS_BOI} ngày · Thu rộ {DEFAULT_DAYS_RO} ngày · Thu vét {DEFAULT_DAYS_VET} ngày (tổng {DEFAULT_DAYS_BOI + DEFAULT_DAYS_RO + DEFAULT_DAYS_VET} ngày). Thay đổi để điều chỉnh cửa sổ thu hoạch.")
            col_d_boi, col_d_ro, col_d_vet = st.columns(3)
            with col_d_boi:
                days_boi = st.number_input("Thu bói (ngày)", min_value=1, max_value=60, 
                                            value=DEFAULT_DAYS_BOI, step=1, key="days_thu_boi")
            with col_d_ro:
                days_ro = st.number_input("Thu rộ (ngày)", min_value=1, max_value=120, 
                                           value=DEFAULT_DAYS_RO, step=1, key="days_thu_ro")
            with col_d_vet:
                days_vet = st.number_input("Thu vét (ngày)", min_value=1, max_value=60, 
                                            value=DEFAULT_DAYS_VET, step=1, key="days_thu_vet")
            
            total_days = days_boi + days_ro + days_vet
            st.caption(f"📐 Tổng cửa sổ: **{total_days} ngày** (Thu bói {days_boi} + Thu rộ {days_ro} + Thu vét {days_vet})")
        
        # Tính lại DAYS_RO_HALF, WINDOW_HALF từ input user
        DAYS_RO_HALF  = days_ro // 2   # Nửa cửa sổ thu rộ (VD: 26 → 13)
        DAYS_BOI_VET  = max(days_boi, days_vet)  # Lấy max để window cân đối
        WINDOW_HALF   = DAYS_RO_HALF + days_boi  # Tổng nửa window = nửa rộ + bói
        # Đảm bảo window đủ chứa cả vét: nếu vét > bói thì mở rộng phía sau
        WINDOW_HALF_RIGHT = DAYS_RO_HALF + days_vet
        
        # σ tính từ: P(|X| ≤ DAYS_RO_HALF) = 0.80 → σ = DAYS_RO_HALF / Φ⁻¹(0.90)
        SIGMA = DAYS_RO_HALF / scipy_norm.ppf(0.90) if DAYS_RO_HALF > 0 else 10.14
        
        # Tính trọng số PDF cho cửa sổ thu hoạch (bất đối xứng nếu bói ≠ vét)
        day_offsets = np.arange(-WINDOW_HALF, WINDOW_HALF_RIGHT + 1)  # [-bói-rộ/2 .. +vét+rộ/2]
        pdf_weights = scipy_norm.pdf(day_offsets, loc=0, scale=SIGMA)
        pdf_weights /= pdf_weights.sum()  # Normalize tổng = 1.0
        
        # Xác định loại thu cho mỗi offset
        def _classify_phase(offset):
            if offset < -DAYS_RO_HALF:
                return "Thu bói"
            elif offset <= DAYS_RO_HALF:
                return "Thu rộ"
            else:
                return "Thu vét"
        
        day_phases = [_classify_phase(d) for d in day_offsets]
        
        # ─── Rescale PDF weights theo tỷ lệ custom ───
        # Giữ nguyên shape Normal Distribution trong mỗi phase,
        # nhưng scale tổng trọng số mỗi phase khớp với % user nhập.
        phase_arr = np.array(day_phases)
        mask_boi = phase_arr == "Thu bói"
        mask_ro  = phase_arr == "Thu rộ"
        mask_vet = phase_arr == "Thu vét"
        
        raw_sum_boi = pdf_weights[mask_boi].sum()
        raw_sum_ro  = pdf_weights[mask_ro].sum()
        raw_sum_vet = pdf_weights[mask_vet].sum()
        
        target_boi = pct_boi / 100.0
        target_ro  = pct_ro / 100.0
        target_vet = pct_vet / 100.0
        
        # Scale mỗi phase: giữ shape tương đối bên trong, thay tổng
        if raw_sum_boi > 0:
            pdf_weights[mask_boi] *= (target_boi / raw_sum_boi)
        if raw_sum_ro > 0:
            pdf_weights[mask_ro]  *= (target_ro / raw_sum_ro)
        if raw_sum_vet > 0:
            pdf_weights[mask_vet] *= (target_vet / raw_sum_vet)
        
        # Đảm bảo tổng = 1.0 (phòng floating point)
        pdf_weights /= pdf_weights.sum()
        
        # ─── Pre-compute: xuất hủy & cắt bắp & thu hoạch per (base_lot_id) ───
        # Destruction: group by base_lot_id (trừ trực tiếp) và dim_lo_id (phân bổ tỉ lệ)
        des_by_base_lot = {}  # {base_lot_id: total_destroyed}
        des_by_lo_only = {}   # {dim_lo_id: total_destroyed} — chỉ records thiếu base_lot_id
        if not df_des_all.empty:
            for _, d_row in df_des_all.iterrows():
                blid = d_row.get("base_lot_id")
                dlid = d_row.get("dim_lo_id")
                qty = int(d_row.get("so_luong", 0)) if pd.notna(d_row.get("so_luong")) else 0
                if pd.notna(blid):
                    des_by_base_lot[blid] = des_by_base_lot.get(blid, 0) + qty
                elif pd.notna(dlid):
                    des_by_lo_only[dlid] = des_by_lo_only.get(dlid, 0) + qty
        
        # Pre-compute tổng cây trồng mới theo dim_lo_id (cho phân bổ tỉ lệ)
        lot_trees_by_lo = {}  # {dim_lo_id: total_trees_trong_moi}
        if not df_lots_trong_moi.empty:
            for _, lr in df_lots_trong_moi.iterrows():
                dlid = lr.get("dim_lo_id")
                qty = int(lr.get("so_luong", 0)) if pd.notna(lr.get("so_luong")) else 0
                if pd.notna(dlid):
                    lot_trees_by_lo[dlid] = lot_trees_by_lo.get(dlid, 0) + qty
        
        # Cắt bắp: giữ raw records (base_lot_id, ngày, qty) để match theo generation
        cat_bap_records = []  # [(base_lot_id, ngay, so_luong), ...]
        if not df_stg_all.empty:
            df_cat = df_stg_all[df_stg_all["giai_doan"] == "Cắt bắp"]
            if not df_cat.empty:
                for _, s_row in df_cat.iterrows():
                    blid = s_row.get("base_lot_id")
                    ngay = pd.to_datetime(s_row.get("ngay_thuc_hien"), errors="coerce")
                    qty = int(s_row.get("so_luong", 0)) if pd.notna(s_row.get("so_luong")) else 0
                    if pd.notna(blid) and pd.notna(ngay):
                        cat_bap_records.append((blid, ngay, qty))
        
        # Chích bắp: giữ raw records (base_lot_id, ngày, qty) để match theo generation
        chich_bap_records = []  # [(base_lot_id, ngay, so_luong), ...]
        if not df_stg_all.empty:
            df_chich = df_stg_all[df_stg_all["giai_doan"] == "Chích bắp"]
            if not df_chich.empty:
                for _, s_row in df_chich.iterrows():
                    blid = s_row.get("base_lot_id")
                    ngay = pd.to_datetime(s_row.get("ngay_thuc_hien"), errors="coerce")
                    qty = int(s_row.get("so_luong", 0)) if pd.notna(s_row.get("so_luong")) else 0
                    if pd.notna(blid) and pd.notna(ngay):
                        chich_bap_records.append((blid, ngay, qty))
        
        # Thu hoạch thực tế: giữ raw records để match theo generation
        harvest_records = []  # [(base_lot_id, ngay, so_luong), ...]
        if not df_har_all.empty:
            for _, h_row in df_har_all.iterrows():
                blid = h_row.get("base_lot_id")
                ngay = pd.to_datetime(h_row.get("ngay_thu_hoach"), errors="coerce")
                qty = int(h_row.get("so_luong", 0)) if pd.notna(h_row.get("so_luong")) else 0
                if pd.notna(blid) and pd.notna(ngay):
                    harvest_records.append((blid, ngay, qty))
        
        # ─── Tạo daily harvest data (3 mốc) ───
        daily_rows = []
        lot_gen_midpoints = {}  # {(base_lot_id, gen_index): midpoint_date}
        for _, lot_row in df_lots_trong_moi.iterrows():
            ngay_trong_raw = lot_row.get("ngay_trong")
            lo_name = lot_row.get("lo", "")
            so_luong = int(lot_row.get("so_luong", 0)) if pd.notna(lot_row.get("so_luong")) else 0
            farm_name = lot_row.get("farm", "")
            base_lot_id = lot_row.get("id")
            dim_lo_id = lot_row.get("dim_lo_id")
            
            if pd.isna(ngay_trong_raw) or so_luong == 0:
                continue
            
            ngay_trong = pd.to_datetime(ngay_trong_raw)
            
            # ── Mốc ①: Dự báo từ Trồng (trừ xuất hủy thực tế) ──
            # Xuất hủy trực tiếp (có base_lot_id)
            direct_des = des_by_base_lot.get(base_lot_id, 0)
            # Xuất hủy phân bổ tỉ lệ (chỉ dim_lo_id, không có base_lot_id)
            proportional_des = 0
            if pd.notna(dim_lo_id) and dim_lo_id in des_by_lo_only:
                total_lo_trees = lot_trees_by_lo.get(dim_lo_id, so_luong)
                if total_lo_trees > 0:
                    lot_ratio = so_luong / total_lo_trees
                    proportional_des = int(round(des_by_lo_only[dim_lo_id] * lot_ratio))
            total_des = direct_des + proportional_des
            so_luong_sau_huy = max(so_luong - total_des, 0)
            so_thu_after_loss = so_luong_sau_huy * (1 - LOSS_RATE)  # Trừ hao hụt ước tính
            
            # ── Pre-compute midpoints cho tất cả generations ──
            all_midpoints = []
            mp = ngay_trong + timedelta(days=F0_DAYS_TO_THU)
            for g in range(FORECAST_GENERATIONS):
                all_midpoints.append(mp)
                mp = mp + timedelta(days=FN_CYCLE_DAYS)
            
            # ── Match cắt bắp records vào generation gần nhất (closest midpoint) ──
            cat_bap_by_gen = {}  # {gen_index: total_qty}
            for blid, ngay, qty in cat_bap_records:
                if blid != base_lot_id:
                    continue
                closest_gen = min(range(len(all_midpoints)),
                                  key=lambda g: abs((all_midpoints[g] - ngay).days))
                cat_bap_by_gen[closest_gen] = cat_bap_by_gen.get(closest_gen, 0) + qty
            
            # ── Match chích bắp records vào generation gần nhất (closest midpoint) ──
            chich_bap_by_gen = {}  # {gen_index: total_qty}
            for blid, ngay, qty in chich_bap_records:
                if blid != base_lot_id:
                    continue
                closest_gen = min(range(len(all_midpoints)),
                                  key=lambda g: abs((all_midpoints[g] - ngay).days))
                chich_bap_by_gen[closest_gen] = chich_bap_by_gen.get(closest_gen, 0) + qty
            
            harvest_midpoint = ngay_trong + timedelta(days=F0_DAYS_TO_THU)
            for gen in range(FORECAST_GENERATIONS):
                vu_label = f"F{gen}"
                lot_gen_midpoints[(base_lot_id, gen)] = harvest_midpoint
                
                # ── Mốc ② (Chích bắp) & Mốc ③ (Cắt bắp) cho ĐÚNG generation này ──
                so_chich_bap_gen = chich_bap_by_gen.get(gen, None)  # None = chưa chích bắp cho vụ này
                so_cat_bap_gen = cat_bap_by_gen.get(gen, None)  # None = chưa cắt bắp cho vụ này
                
                # Window boundaries (hỗ trợ bất đối xứng: bói ≠ vét)
                win_start = harvest_midpoint - timedelta(days=WINDOW_HALF)
                thu_boi_start = win_start
                thu_boi_end   = harvest_midpoint - timedelta(days=DAYS_RO_HALF + 1)
                thu_ro_start  = harvest_midpoint - timedelta(days=DAYS_RO_HALF)
                thu_ro_end    = harvest_midpoint + timedelta(days=DAYS_RO_HALF)
                thu_vet_start = harvest_midpoint + timedelta(days=DAYS_RO_HALF + 1)
                thu_vet_end   = harvest_midpoint + timedelta(days=WINDOW_HALF_RIGHT)
                
                # Tạo row cho mỗi ngày
                for idx, (offset, weight, phase) in enumerate(zip(day_offsets, pdf_weights, day_phases)):
                    actual_date = harvest_midpoint + timedelta(days=int(offset))
                    daily_qty = so_thu_after_loss * weight
                    
                    # Mốc ②: chích bắp × (1 - 5% hao hụt chích→thu) × weight
                    daily_qty_chich = (so_chich_bap_gen * (1 - LOSS_RATE_TO_CHICH) * weight) if so_chich_bap_gen is not None else None
                    
                    # Mốc ③: cắt bắp × (1 - 5% hao hụt cắt→thu) × weight
                    daily_qty_cat = (so_cat_bap_gen * (1 - LOSS_RATE_TO_CHICH) * weight) if so_cat_bap_gen is not None else None
                    
                    # Window label cho phase này
                    if phase == "Thu bói":
                        wlabel = f"{thu_boi_start.strftime('%d/%m')} – {thu_boi_end.strftime('%d/%m/%Y')}"
                    elif phase == "Thu rộ":
                        wlabel = f"{thu_ro_start.strftime('%d/%m')} – {thu_ro_end.strftime('%d/%m/%Y')}"
                    else:
                        wlabel = f"{thu_vet_start.strftime('%d/%m')} – {thu_vet_end.strftime('%d/%m/%Y')}"
                    
                    daily_rows.append({
                        "farm": farm_name,
                        "lo": lo_name,
                        "base_lot_id": base_lot_id,
                        "vu": vu_label,
                        "loai_thu": phase,
                        "ngay": actual_date,
                        "thang": actual_date.strftime("%m/%Y"),
                        "year": actual_date.year,
                        "so_luong_trong": so_luong,
                        "so_xuat_huy": total_des,
                        "daily_qty": daily_qty,
                        "daily_qty_chich": daily_qty_chich,
                        "daily_qty_cat": daily_qty_cat,

                        "window_label": wlabel,
                    })
                
                harvest_midpoint = harvest_midpoint + timedelta(days=FN_CYCLE_DAYS)
        
        if daily_rows:
            df_daily = pd.DataFrame(daily_rows)
            
            # Gom theo tháng + lô + vụ + loại thu (từ daily → monthly) — 3 mốc
            agg_dict = {
                "so_thu_hoach_dk": ("daily_qty", "sum"),
            }
            df_harvest = df_daily.groupby(
                ["farm", "lo", "base_lot_id", "vu", "loai_thu", "thang", "year", 
                 "so_luong_trong", "so_xuat_huy", "window_label"],
                as_index=False
            ).agg(**agg_dict)
            
            # Mốc ②: Chích bắp (sum daily_qty_chich nếu có)
            if "daily_qty_chich" in df_daily.columns:
                chich_agg = df_daily.groupby(
                    ["base_lot_id", "vu", "loai_thu", "thang"],
                    as_index=False
                ).agg(so_thu_chich_bap=("daily_qty_chich", lambda x: x.sum() if x.notna().all() else None))
                df_harvest = df_harvest.merge(chich_agg, on=["base_lot_id", "vu", "loai_thu", "thang"], how="left")
            else:
                df_harvest["so_thu_chich_bap"] = None
            
            # Mốc ③: Cắt bắp (sum daily_qty_cat nếu có)
            if "daily_qty_cat" in df_daily.columns:
                cat_agg = df_daily.groupby(
                    ["base_lot_id", "vu", "loai_thu", "thang"],
                    as_index=False
                ).agg(so_thu_cat_bap=("daily_qty_cat", lambda x: x.sum() if x.notna().all() else None))
                df_harvest = df_harvest.merge(cat_agg, on=["base_lot_id", "vu", "loai_thu", "thang"], how="left")
            else:
                df_harvest["so_thu_cat_bap"] = None
            
            # Largest Remainder Method: làm tròn mà đảm bảo tổng mỗi (lô, vụ) chính xác
            # Áp dụng cho Mốc ① (so_thu_hoach_dk)
            for (lo_k, bid_k, vu_k), grp_idx in df_harvest.groupby(["lo", "base_lot_id", "vu"]).groups.items():
                vals = df_harvest.loc[grp_idx, "so_thu_hoach_dk"].values.astype(float)
                target_total = int(round(vals.sum()))
                floors = np.floor(vals).astype(int)
                remainders = vals - floors
                deficit = target_total - floors.sum()
                if deficit > 0:
                    top_idx = np.argsort(-remainders)[:deficit]
                    floors[top_idx] += 1
                df_harvest.loc[grp_idx, "so_thu_hoach_dk"] = floors
                
                # Áp dụng cho Mốc ② (so_thu_chich_bap) nếu có data
                chich_vals = df_harvest.loc[grp_idx, "so_thu_chich_bap"]
                if chich_vals.notna().all():
                    chv = chich_vals.values.astype(float)
                    ch_total = int(round(chv.sum()))
                    ch_floors = np.floor(chv).astype(int)
                    ch_rem = chv - ch_floors
                    ch_deficit = ch_total - ch_floors.sum()
                    if ch_deficit > 0:
                        ch_top = np.argsort(-ch_rem)[:ch_deficit]
                        ch_floors[ch_top] += 1
                    df_harvest.loc[grp_idx, "so_thu_chich_bap"] = ch_floors
                
                # Áp dụng cho Mốc ③ (so_thu_cat_bap) nếu có data
                cat_vals = df_harvest.loc[grp_idx, "so_thu_cat_bap"]
                if cat_vals.notna().all():
                    cv = cat_vals.values.astype(float)
                    ct_total = int(round(cv.sum()))
                    ct_floors = np.floor(cv).astype(int)
                    ct_rem = cv - ct_floors
                    ct_deficit = ct_total - ct_floors.sum()
                    if ct_deficit > 0:
                        ct_top = np.argsort(-ct_rem)[:ct_deficit]
                        ct_floors[ct_top] += 1
                    df_harvest.loc[grp_idx, "so_thu_cat_bap"] = ct_floors
            
            df_harvest["so_thu_hoach_dk"] = df_harvest["so_thu_hoach_dk"].astype(int)
            # so_thu_chich_bap: keep as int or None
            df_harvest["so_thu_chich_bap"] = df_harvest["so_thu_chich_bap"].apply(
                lambda x: int(x) if pd.notna(x) else None)
            # so_thu_cat_bap: keep as int or None
            df_harvest["so_thu_cat_bap"] = df_harvest["so_thu_cat_bap"].apply(
                lambda x: int(x) if pd.notna(x) else None)
            # ── Mốc ④: Thu hoạch thực tế — match từng record theo (gen, phase, tháng) ──
            # harvest_logs có từng ngày riêng lẻ, cần xác định mỗi record
            # thuộc generation nào + phase nào (Thu bói/rộ/vét) + tháng nào.
            actual_harvest_rows = []
            for blid, ngay, qty in harvest_records:
                # Tìm tất cả midpoints của lot này
                lot_mps = [(g, mp) for (lid, g), mp in lot_gen_midpoints.items() if lid == blid]
                if not lot_mps:
                    continue
                # Match vào generation gần nhất
                closest_gen, closest_mp = min(lot_mps, key=lambda x: abs((x[1] - ngay).days))
                # Xác định phase dựa trên khoảng cách đến midpoint
                days_from_mp = (ngay - closest_mp).days
                if days_from_mp < -(DAYS_RO_HALF):
                    phase = "Thu bói"
                elif days_from_mp <= DAYS_RO_HALF:
                    phase = "Thu rộ"
                else:
                    phase = "Thu vét"
                actual_harvest_rows.append({
                    "base_lot_id": blid,
                    "vu": f"F{closest_gen}",
                    "loai_thu": phase,
                    "thang": ngay.strftime("%m/%Y"),
                    "so_thu_thuc_te": qty
                })
            if actual_harvest_rows:
                df_actual = pd.DataFrame(actual_harvest_rows)
                df_actual = df_actual.groupby(
                    ["base_lot_id", "vu", "loai_thu", "thang"], as_index=False
                ).agg(so_thu_thuc_te=("so_thu_thuc_te", "sum"))
                df_actual["so_thu_thuc_te"] = df_actual["so_thu_thuc_te"].astype(int)
                df_harvest = df_harvest.merge(
                    df_actual, on=["base_lot_id", "vu", "loai_thu", "thang"], how="left")
            else:
                df_harvest["so_thu_thuc_te"] = None
            df_harvest.rename(columns={"thang": "thang_thu_hoach"}, inplace=True)
            
            # ─── Bộ lọc: Farm + Năm + Tháng ───
            year_options = sorted(df_harvest["year"].unique())
            current_year = date.today().year
            default_year_idx = year_options.index(current_year) + 1 if current_year in year_options else 0

            if c_farm in ["Admin", "Phòng Kinh doanh"]:
                hcf0, hcf1, hcf2 = st.columns([1, 1, 1])
                with hcf0:
                    hv_farm = st.selectbox("Lọc theo Farm", options=farms_all, key="hv_farm_sched")
                with hcf1:
                    hv_year = st.selectbox("Lọc theo Năm",
                                          options=["Tất cả"] + [str(y) for y in year_options],
                                          index=default_year_idx, key="hv_year_sched")
                with hcf2:
                    _df_tmp = df_harvest.copy()
                    if hv_year != "Tất cả":
                        _df_tmp = _df_tmp[_df_tmp["year"] == int(hv_year)]
                    all_months = sorted(_df_tmp["thang_thu_hoach"].unique(),
                                       key=lambda x: pd.to_datetime(x, format="%m/%Y"))
                    hv_month = st.selectbox("Lọc theo tháng thu hoạch",
                                          options=["Tất cả"] + list(all_months), key="hv_month_sched")
            else:
                hv_farm = c_farm
                hcf1, hcf2 = st.columns([1, 1])
                with hcf1:
                    hv_year = st.selectbox("Lọc theo Năm",
                                          options=["Tất cả"] + [str(y) for y in year_options],
                                          index=default_year_idx, key="hv_year_sched")
                with hcf2:
                    _df_tmp = df_harvest.copy()
                    if hv_year != "Tất cả":
                        _df_tmp = _df_tmp[_df_tmp["year"] == int(hv_year)]
                    all_months = sorted(_df_tmp["thang_thu_hoach"].unique(),
                                       key=lambda x: pd.to_datetime(x, format="%m/%Y"))
                    hv_month = st.selectbox("Lọc theo tháng thu hoạch",
                                           options=["Tất cả"] + list(all_months), key="hv_month_sched")
            
            df_hv = df_harvest.copy()
            if hv_farm != "Tất cả":
                df_hv = df_hv[df_hv["farm"] == hv_farm]
            if hv_year != "Tất cả":
                df_hv = df_hv[df_hv["year"] == int(hv_year)]
            if hv_month != "Tất cả":
                df_hv = df_hv[df_hv["thang_thu_hoach"] == hv_month]
            
            if not df_hv.empty:
                # ─── @st.dialog: chi tiết breakdown theo tháng ───
                @st.dialog("📊 Chi tiết thu hoạch", width="large")
                def _show_harvest_detail(month_key, df_src):
                    df_month = df_src[df_src["thang_thu_hoach"] == month_key].copy()
                    
                    def _nat_key_pop(name):
                        _m = _re.match(r"^(\d+)(.*)", str(name))
                        return (int(_m.group(1)), _m.group(2)) if _m else (9999, str(name))
                    
                    df_month["_sort"] = df_month["lo"].apply(_nat_key_pop)
                    df_month = df_month.sort_values(["_sort", "vu", "loai_thu"]).drop(columns=["_sort"])
                    
                    # Header — Mốc ①
                    total_buong = df_month["so_thu_hoach_dk"].sum()
                    df_month["_kg"] = df_month.apply(lambda r: r["so_thu_hoach_dk"] * get_kg_per_tree(r["vu"]), axis=1)
                    total_kg = df_month["_kg"].sum()
                    so_thung = int(total_kg // KG_PER_BOX)
                    so_container = so_thung / BOXES_PER_CONTAINER
                    st.markdown(f"### Tháng {month_key}")
                    
                    # 4 mốc summary
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric("① Từ Trồng", f"{total_buong:,} buồng", f"≈ {total_kg:,.0f} kg")
                    with col_m2:
                        chich_total = df_month["so_thu_chich_bap"].sum() if df_month["so_thu_chich_bap"].notna().any() else None
                        if chich_total is not None:
                            chich_kg = df_month.apply(lambda r: r["so_thu_chich_bap"] * get_kg_per_tree(r["vu"]) if pd.notna(r.get("so_thu_chich_bap")) else 0, axis=1).sum()
                            st.metric("② Chích bắp", f"{int(chich_total):,} buồng", f"≈ {chich_kg:,.0f} kg")
                        else:
                            st.metric("② Chích bắp", "Chưa có TT", "")
                    with col_m3:
                        cat_total = df_month["so_thu_cat_bap"].sum() if df_month["so_thu_cat_bap"].notna().any() else None
                        if cat_total is not None:
                            cat_kg = df_month.apply(lambda r: r["so_thu_cat_bap"] * get_kg_per_tree(r["vu"]) if pd.notna(r.get("so_thu_cat_bap")) else 0, axis=1).sum()
                            st.metric("③ Từ Cắt bắp", f"{int(cat_total):,} buồng", f"≈ {cat_kg:,.0f} kg")
                        else:
                            st.metric("③ Từ Cắt bắp", "Chưa có TT", "")
                    with col_m4:
                        # Thực tế: distinct per (base_lot_id, vu)
                        tt_df = df_month.drop_duplicates(subset=["base_lot_id", "vu"])
                        tt_total = tt_df["so_thu_thuc_te"].sum() if tt_df["so_thu_thuc_te"].notna().any() else None
                        if tt_total is not None:
                            st.metric("④ Thực tế", f"{int(tt_total):,} buồng", "")
                        else:
                            st.metric("④ Thực tế", "Chưa có TT", "")
                    
                    st.markdown(f"📦 **~{so_thung:,} thùng** (13 kg/thùng) · 🚛 **~{so_container:,.1f} container** (1320 thùng/cont)")
                    
                    # Tổng hợp theo loại thu
                    summary_by_type = df_month.groupby("loai_thu")["so_thu_hoach_dk"].sum()
                    type_parts = []
                    for lt in ["Thu bói", "Thu rộ", "Thu vét"]:
                        if lt in summary_by_type.index:
                            type_parts.append(f"**{lt}**: {summary_by_type[lt]:,}")
                    st.markdown(" · ".join(type_parts))
                    st.markdown("---")
                    
                    # Bảng chi tiết — 4 mốc
                    df_pop = df_month[["lo", "vu", "loai_thu", "so_thu_hoach_dk", "so_thu_chich_bap", "so_thu_cat_bap", "so_thu_thuc_te", "window_label"]].copy()
                    df_pop["so_thu_chich_bap"] = df_pop["so_thu_chich_bap"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_pop["so_thu_cat_bap"] = df_pop["so_thu_cat_bap"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_pop["so_thu_thuc_te"] = df_pop["so_thu_thuc_te"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_pop.columns = ["Lô", "Vụ", "Loại thu", "① Từ Trồng", "② Chích bắp", "③ Cắt bắp", "④ Thực tế", "Khoảng TG"]
                    
                    styled_pop = df_pop.style.set_properties(**{'text-align': 'center', 'font-size': '0.85rem'})
                    styled_pop = styled_pop.set_table_styles([
                        {"selector": "th", "props": [("text-align", "center"), ("font-size", "0.85rem")]},
                        {"selector": "td", "props": [("text-align", "center")]}
                    ]).hide(axis="index")
                    st.markdown(f'<div style="overflow-x:auto;">{styled_pop.to_html(escape=False)}</div>',
                               unsafe_allow_html=True)
                
                # ─── CSS: style button thành card (scoped qua container key) ───
                st.markdown("""
                <style>
                .st-key-harvest-cards button {
                    background: linear-gradient(135deg, #b7e4c7 0%, #95d5b2 100%) !important;
                    color: #1b4332 !important;
                    border: 1px solid #74c69d !important;
                    border-radius: 12px !important;
                    padding: 1.2rem 0.5rem !important;
                    width: 100%;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    cursor: pointer;
                    transition: transform 0.15s, box-shadow 0.15s;
                    min-height: 180px;
                }
                .st-key-harvest-cards button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
                    background: linear-gradient(135deg, #95d5b2 0%, #74c69d 100%) !important;
                    color: #1b4332 !important;
                    border: 1px solid #52b788 !important;
                }
                .st-key-harvest-cards button:active {
                    transform: translateY(0px);
                }
                .st-key-harvest-cards button p {
                    color: #1b4332 !important;
                    margin: 0;
                    font-size: 0.85rem;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # ─── Metric cards (buttons) trong container scoped ───
                # Tính kg theo từng dòng trước khi gộp (vì mỗi vụ có kg/buồng khác nhau)
                df_hv["_kg_est"] = df_hv.apply(lambda r: r["so_thu_hoach_dk"] * get_kg_per_tree(r["vu"]), axis=1)
                df_hv["_kg_chich"] = df_hv.apply(
                    lambda r: r["so_thu_chich_bap"] * get_kg_per_tree(r["vu"]) if pd.notna(r.get("so_thu_chich_bap")) else None, axis=1)
                df_hv["_kg_cat"] = df_hv.apply(
                    lambda r: r["so_thu_cat_bap"] * get_kg_per_tree(r["vu"]) if pd.notna(r.get("so_thu_cat_bap")) else None, axis=1)
                monthly_summary = df_hv.groupby("thang_thu_hoach").agg(
                    tong_cay=("so_thu_hoach_dk", "sum"),
                    kg_est=("_kg_est", "sum"),
                    so_lo=("lo", "nunique")
                ).reset_index()
                
                # Mốc ②: tổng chích bắp theo tháng
                chich_month = df_hv.groupby("thang_thu_hoach").agg(
                    tong_chich=("so_thu_chich_bap", lambda x: int(x.sum()) if x.notna().any() else None),
                    kg_chich=("_kg_chich", lambda x: x.sum() if x.notna().any() else None)
                ).reset_index()
                monthly_summary = monthly_summary.merge(chich_month, on="thang_thu_hoach", how="left")
                
                # Mốc ③: tổng cắt bắp theo tháng (None nếu chưa có data nào)
                cat_month = df_hv.groupby("thang_thu_hoach").agg(
                    tong_cat=("so_thu_cat_bap", lambda x: int(x.sum()) if x.notna().any() else None),
                    kg_cat=("_kg_cat", lambda x: x.sum() if x.notna().any() else None)
                ).reset_index()
                monthly_summary = monthly_summary.merge(cat_month, on="thang_thu_hoach", how="left")
                
                # Mốc ④: tổng thực tế theo tháng — dùng unique lot-level values
                # so_thu_thuc_te là per-lot, cần distinct trước khi sum
                actual_by_month = df_hv.drop_duplicates(subset=["base_lot_id", "vu", "thang_thu_hoach"]).groupby("thang_thu_hoach").agg(
                    tong_thuc_te=("so_thu_thuc_te", lambda x: int(x.sum()) if x.notna().any() else None)
                ).reset_index()
                monthly_summary = monthly_summary.merge(actual_by_month, on="thang_thu_hoach", how="left")
                
                monthly_summary = monthly_summary.sort_values("thang_thu_hoach",
                    key=lambda x: pd.to_datetime(x, format="%m/%Y"))
                
                month_list = monthly_summary.to_dict("records")
                with st.container(key="harvest-cards"):
                    for i in range(0, len(month_list), 4):
                        cols = st.columns(min(4, len(month_list) - i))
                        for j, col in enumerate(cols):
                            if i + j < len(month_list):
                                m = month_list[i + j]
                                kg_est = m["kg_est"]
                                month_key = m["thang_thu_hoach"]
                                
                                with col:
                                    so_thung_card = int(kg_est // KG_PER_BOX)
                                    so_cont_card = so_thung_card / BOXES_PER_CONTAINER
                                    
                                    # Mốc ① — Từ Trồng
                                    line1 = f"① Trồng: **{m['tong_cay']:,}** buồng ≈ {kg_est:,.0f} kg"
                                    
                                    # Mốc ② — Từ Chích bắp
                                    tong_chich = m.get("tong_chich")
                                    if pd.notna(tong_chich) and tong_chich is not None:
                                        kg_chich_val = m.get("kg_chich", 0) or 0
                                        line2 = f"② Chích: **{int(tong_chich):,}** buồng ≈ {kg_chich_val:,.0f} kg"
                                    else:
                                        line2 = "② Chích: _Chưa có TT_"
                                    
                                    # Mốc ③ — Từ Cắt bắp
                                    tong_cat = m.get("tong_cat")
                                    if pd.notna(tong_cat) and tong_cat is not None:
                                        kg_cat_val = m.get("kg_cat", 0) or 0
                                        line3 = f"③ Cắt: **{int(tong_cat):,}** buồng ≈ {kg_cat_val:,.0f} kg"
                                    else:
                                        line3 = "③ Cắt: _Chưa có TT_"
                                    
                                    # Mốc ④ — Thực tế
                                    tong_tt = m.get("tong_thuc_te")
                                    if pd.notna(tong_tt) and tong_tt is not None:
                                        kg_tt = int(tong_tt) * KG_PER_TREE_F0  # approx
                                        line4 = f"④ TT: **{int(tong_tt):,}** buồng ≈ {kg_tt:,} kg"
                                    else:
                                        line4 = "④ TT: _Chưa có TT_"
                                    
                                    btn_label = f"📅 Tháng {month_key}\n\n{line1}\n\n{line2}\n\n{line3}\n\n{line4}\n\n🚛 ~{so_cont_card:,.1f} cont · {m['so_lo']} lô"
                                    if st.button(btn_label, key=f"hv_card_{month_key}",
                                               use_container_width=True):
                                        _show_harvest_detail(month_key, df_hv)
                
                # ─── Bảng tổng hợp (expander) ───
                with st.expander("📋 Bảng tổng hợp lịch thu hoạch", expanded=False):
                    def _nat_key(name):
                        m = _re.match(r"^(\d+)(.*)", str(name))
                        return (int(m.group(1)), m.group(2)) if m else (9999, str(name))
                    
                    df_display = df_hv[["lo", "vu", "loai_thu", "thang_thu_hoach",
                                        "so_luong_trong", "so_xuat_huy", "so_thu_hoach_dk",
                                        "so_thu_chich_bap", "so_thu_cat_bap", "so_thu_thuc_te", "window_label"]].copy()
                    df_display["so_thu_chich_bap"] = df_display["so_thu_chich_bap"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_display["so_thu_cat_bap"] = df_display["so_thu_cat_bap"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_display["so_thu_thuc_te"] = df_display["so_thu_thuc_te"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                    df_display["_sort"] = df_display["lo"].apply(lambda x: _nat_key(x))
                    df_display = df_display.sort_values(["_sort", "vu", "loai_thu"]).drop(columns=["_sort"])
                    df_display.columns = ["Lô", "Vụ", "Loại thu", "Tháng TH",
                                         "Trồng", "Xuất hủy", "① Từ Trồng",
                                         "② Chích bắp", "③ Cắt bắp", "④ Thực tế", "Khoảng TG"]
                    
                    styled = df_display.style.set_properties(**{'text-align': 'center'})
                    styled = styled.set_table_styles([
                        {"selector": "th", "props": [("text-align", "center")]},
                        {"selector": "td", "props": [("text-align", "center")]}
                    ]).hide(axis="index")
                    
                    st.markdown(f'<div class="centered-table-wrapper" style="overflow-x: auto;">'
                               f'{styled.to_html(escape=False)}</div>', unsafe_allow_html=True)
            else:
                st.info("Không có dữ liệu thu hoạch phù hợp với bộ lọc.")
    else:
        st.info("Chưa có dữ liệu lô trồng để tính lịch thu hoạch.")

    st.divider()

    # --- DỰ TOÁN SẢN LƯỢNG THU HOẠCH (KG) ---
    st.markdown("#### ⚖️ Dự toán Sản lượng Thu hoạch (Kg)")
    st.caption(f"Ước tính sản lượng dựa trên số cây ở giai đoạn gần nhất × **{KG_PER_TREE_F0} kg/cây (F0)** hoặc **{KG_PER_TREE_FN} kg/cây (Fn)**.")

    ek_farm, ek_vu, ek_team, ek_lot, _ = render_chart_filters("ek")
    filtered_ek_dfs = get_filtered_dfs(ek_farm, ek_vu, ek_team, ek_lot, None, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })

    ek_lots_df = filtered_ek_dfs["lots"]
    ek_stg_df = filtered_ek_dfs["stg"]
    ek_har_df = filtered_ek_dfs["har"]
    ek_des_df = filtered_ek_dfs["des"]

    total_cay_da_trong = int(ek_lots_df["so_luong"].sum()) if not ek_lots_df.empty else 0
    total_du_toan_thu = int(round(total_cay_da_trong * get_estimated_rate("thu_hoach")))
    total_da_thu = int(ek_har_df["so_luong"].sum()) if not ek_har_df.empty else 0
    total_xuat_huy = int(ek_des_df["so_luong"].sum()) if not ek_des_df.empty else 0
    total_con_lai = max(total_du_toan_thu - total_da_thu - total_xuat_huy, 0)

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🌱 Dự toán thu hoạch", f"{total_du_toan_thu:,} buồng",
                  delta=f"Trồng: {total_cay_da_trong:,} · Hao hụt: {LOSS_RATE_TO_THU*100:.0f}%")
    with m2:
        _kg_rate = get_kg_per_tree(ek_vu if ek_vu != "Tất cả" else "Fn")
        st.metric("✅ Đã thu hoạch", f"{total_da_thu:,} buồng", delta=f"{total_da_thu * _kg_rate:,.0f} kg")
    with m3:
        st.metric("🗑️ Xuất hủy", f"{total_xuat_huy:,} cây")
    with m4:
        st.metric("📦 Kg dự toán còn lại", f"{total_con_lai * _kg_rate:,.0f} kg")

    st.divider()

    # --- BIỂU ĐỒ SO SÁNH TIẾN ĐỘ: DỰ TOÁN vs THỰC TẾ ---
    # Chart: sử dụng get_kg_per_tree(vu) — F0=15, Fn=18

    st.markdown("#### 📈 So sánh Tiến độ Sinh trưởng: Dự toán vs Thực tế")
    st.caption("Mỗi đường line đại diện cho 1 Lô. Các điểm đánh dấu màu thể hiện giai đoạn sinh trưởng. Hover để xem chi tiết.")

    lc_farm, lc_vu, lc_team, lc_lot, lc_date = render_chart_filters("lc", include_date=True)
    filtered_lc_dfs = get_filtered_dfs(lc_farm, lc_vu, lc_team, lc_lot, lc_date, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })

    lc_lots_df = filtered_lc_dfs["lots"]
    lc_stg_df = filtered_lc_dfs["stg"]
    lc_har_df = filtered_lc_dfs["har"]
    lc_des_df = filtered_lc_dfs["des"]

    STAGE_COLORS = {
        "Trồng": "#4CAF50",
        "Chích bắp": "#FFC107",
        "Cắt bắp": "#FF9800",
        "Thu hoạch": "#2196F3",
        "Xuất hủy": "#F44336",
    }

    if not lc_lots_df.empty:
        # ==============================
        # CHART 1: DỰ TOÁN (LÝ TƯỞNG)
        # ==============================
        st.markdown("##### 🎯 Dự toán (Lý tưởng)")
        ideal_events = []
        # Sort theo ngày trồng trước khi đánh số đợt (đợt 1 = trồng sớm nhất)
        lc_lots_df = lc_lots_df.sort_values(["lo", "ngay_trong"]).reset_index(drop=True)
        _batch_counts = lc_lots_df.groupby("lo").cumcount() + 1
        _batch_totals = lc_lots_df.groupby("lo")["lo"].transform("count")
        for idx, (_, lot_row) in enumerate(lc_lots_df.iterrows()):
            batch_id = lot_row["id"]  # PK base_lots – unique per batch
            lo_name = lot_row["lo"]
            batch_num = _batch_counts.iloc[idx]
            batch_total = _batch_totals.iloc[idx]
            label = f"{lo_name} (đợt {batch_num})" if batch_total > 1 else lo_name
            sl = int(lot_row["so_luong"])
            _dt_trong = lot_row.get("dien_tich_trong")
            dt = float(_dt_trong) if pd.notna(_dt_trong) else (float(lot_row.get("dien_tich", 0)) if pd.notna(lot_row.get("dien_tich")) else 0)
            d_trong = pd.to_datetime(lot_row["ngay_trong"])
            d_chich = d_trong + timedelta(days=180)
            d_cat = d_chich + timedelta(days=14)
            d_thu = d_cat + timedelta(days=70)

            ideal_events.append({"batch_id": batch_id, "lo": label, "date": d_trong, "so_luong": sl, "giai_doan": "Trồng",
                "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Trồng<br>Ngày: {d_trong.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})
            ideal_events.append({"batch_id": batch_id, "lo": label, "date": d_chich, "so_luong": sl, "giai_doan": "Chích bắp",
                "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Chích bắp<br>Ngày: {d_chich.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})
            ideal_events.append({"batch_id": batch_id, "lo": label, "date": d_cat, "so_luong": sl, "giai_doan": "Cắt bắp",
                "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Cắt bắp<br>Ngày: {d_cat.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})
            ideal_events.append({"batch_id": batch_id, "lo": label, "date": d_thu, "so_luong": sl, "giai_doan": "Thu hoạch",
                "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Thu hoạch<br>Ngày: {d_thu.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây<br><b>Sản lượng dự toán: {sl * KG_PER_TREE_F0:,.0f} kg</b>"})

        df_ideal = pd.DataFrame(ideal_events)
        fig_ideal = go.Figure()

        # Đường nối mờ cho mỗi đợt trồng
        for bid in df_ideal["batch_id"].unique():
            lot_data = df_ideal[df_ideal["batch_id"] == bid].sort_values("date")
            fig_ideal.add_trace(go.Scatter(
                x=lot_data["date"], y=lot_data["so_luong"],
                mode="lines", line=dict(color="rgba(150,150,150,0.4)", width=1.5, dash="dot"),
                showlegend=False, hoverinfo="skip",
                name=lot_data["lo"].iloc[0]
            ))

        # Marker màu theo giai đoạn
        for stage in ["Trồng", "Chích bắp", "Cắt bắp", "Thu hoạch"]:
            stage_data = df_ideal[df_ideal["giai_doan"] == stage]
            if not stage_data.empty:
                fig_ideal.add_trace(go.Scatter(
                    x=stage_data["date"], y=stage_data["so_luong"],
                    mode="markers",
                    marker=dict(size=10, color=STAGE_COLORS[stage], line=dict(width=1, color="white")),
                    name=stage, text=stage_data["hover"],
                    hovertemplate="%{text}<extra></extra>"
                ))

        # Lưu phạm vi thời gian của chart Dự toán
        _ideal_dates = df_ideal["date"]

        fig_ideal.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)", "title": "Số cây"},
            xaxis={"title": "Thời gian"},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400, margin=dict(t=60)
        )
        # Chưa render chart Dự toán, đợi tính shared range với Thực tế

        # ==============================
        # CHART 2: THỰC TẾ
        # ==============================
        actual_events = []
        # Dùng lại lc_lots_df đã sort ở trên
        _batch_counts2 = lc_lots_df.groupby("lo").cumcount() + 1
        _batch_totals2 = lc_lots_df.groupby("lo")["lo"].transform("count")
        for idx, (_, lot_row) in enumerate(lc_lots_df.iterrows()):
            batch_id = lot_row["id"]  # PK base_lots
            lot_id = lot_row["lot_id"]  # lot name for matching stage/harvest
            lo_name = lot_row["lo"]
            batch_num = _batch_counts2.iloc[idx]
            batch_total = _batch_totals2.iloc[idx]
            label = f"{lo_name} (đợt {batch_num})" if batch_total > 1 else lo_name
            sl_trong = int(lot_row["so_luong"])
            _dt_trong = lot_row.get("dien_tich_trong")
            dt = float(_dt_trong) if pd.notna(_dt_trong) else (float(lot_row.get("dien_tich", 0)) if pd.notna(lot_row.get("dien_tich")) else 0)
            ngay_trong = pd.to_datetime(lot_row["ngay_trong"])

            # Sự kiện Trồng
            actual_events.append({"batch_id": batch_id, "lo": label, "date": ngay_trong,
                "so_luong": sl_trong, "giai_doan": "Trồng",
                "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Trồng<br>Ngày: {ngay_trong.strftime('%d/%m/%Y')}<br>Số lượng: {sl_trong:,} cây"})

            # Sự kiện Chích bắp
            if not lc_stg_df.empty:
                cb_data = lc_stg_df[(lc_stg_df["lot_id"] == lot_id) & (lc_stg_df["giai_doan"] == "Chích bắp")]
                if not cb_data.empty:
                    for _, row in cb_data.groupby("ngay_thuc_hien")["so_luong"].sum().reset_index().iterrows():
                        d = pd.to_datetime(row["ngay_thuc_hien"])
                        sl = int(row["so_luong"])
                        actual_events.append({"batch_id": batch_id, "lo": label, "date": d,
                            "so_luong": sl, "giai_doan": "Chích bắp",
                            "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Chích bắp<br>Ngày: {d.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})

            # Sự kiện Cắt bắp
            if not lc_stg_df.empty:
                cat_data = lc_stg_df[(lc_stg_df["lot_id"] == lot_id) & (lc_stg_df["giai_doan"] == "Cắt bắp")]
                if not cat_data.empty:
                    for _, row in cat_data.groupby("ngay_thuc_hien")["so_luong"].sum().reset_index().iterrows():
                        d = pd.to_datetime(row["ngay_thuc_hien"])
                        sl = int(row["so_luong"])
                        actual_events.append({"batch_id": batch_id, "lo": label, "date": d,
                            "so_luong": sl, "giai_doan": "Cắt bắp",
                            "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Cắt bắp<br>Ngày: {d.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})

            # Sự kiện Thu hoạch
            if not lc_har_df.empty:
                har_data = lc_har_df[lc_har_df["lot_id"] == lot_id]
                if not har_data.empty:
                    for _, row in har_data.groupby("ngay_thu_hoach")["so_luong"].sum().reset_index().iterrows():
                        d = pd.to_datetime(row["ngay_thu_hoach"])
                        sl = int(row["so_luong"])
                        _vu_for_kg = lc_vu if lc_vu != "Tất cả" else "Fn"
                        actual_events.append({"batch_id": batch_id, "lo": label, "date": d,
                            "so_luong": sl, "giai_doan": "Thu hoạch",
                            "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>Giai đoạn: Thu hoạch<br>Ngày: {d.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} buồng<br><b>Sản lượng dự toán: {sl * get_kg_per_tree(_vu_for_kg):,.0f} kg</b>"})

            # Sự kiện Xuất hủy (điểm rời, không nối line)
            if not lc_des_df.empty:
                des_data = lc_des_df[lc_des_df["lot_id"] == lot_id]
                if not des_data.empty:
                    for _, row in des_data.groupby("ngay_xuat_huy")["so_luong"].sum().reset_index().iterrows():
                        d = pd.to_datetime(row["ngay_xuat_huy"])
                        sl = int(row["so_luong"])
                        actual_events.append({"batch_id": batch_id, "lo": label, "date": d,
                            "so_luong": sl, "giai_doan": "Xuất hủy",
                            "hover": f"<b>Lô {label}</b><br>Diện tích: {dt:.2f} ha<br>🗑️ Xuất hủy<br>Ngày: {d.strftime('%d/%m/%Y')}<br>Số lượng: {sl:,} cây"})

        fig_actual = go.Figure()
        if actual_events:
            df_actual = pd.DataFrame(actual_events)

            # Đường nối mờ cho mỗi Lô (chỉ nối các giai đoạn chính, BỎ QUA Xuất hủy)
            for bid in df_actual["batch_id"].unique():
                lot_data = df_actual[(df_actual["batch_id"] == bid) & (df_actual["giai_doan"] != "Xuất hủy")].sort_values("date")
                if len(lot_data) > 1:
                    fig_actual.add_trace(go.Scatter(
                        x=lot_data["date"], y=lot_data["so_luong"],
                        mode="lines", line=dict(color="rgba(150,150,150,0.4)", width=1.5, dash="dot"),
                        showlegend=False, hoverinfo="skip",
                        name=lot_data["lo"].iloc[0]
                    ))

            # Marker màu theo giai đoạn
            for stage, color in STAGE_COLORS.items():
                stage_data = df_actual[df_actual["giai_doan"] == stage]
                if not stage_data.empty:
                    marker_symbol = "x" if stage == "Xuất hủy" else "circle"
                    marker_size = 12 if stage == "Xuất hủy" else 10
                    fig_actual.add_trace(go.Scatter(
                        x=stage_data["date"], y=stage_data["so_luong"],
                        mode="markers",
                        marker=dict(size=marker_size, color=color, symbol=marker_symbol, line=dict(width=1, color="white")),
                        name=stage, text=stage_data["hover"],
                        hovertemplate="%{text}<extra></extra>"
                    ))

        fig_actual.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)", "title": "Số cây"},
            xaxis={"title": "Thời gian"},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400, margin=dict(t=60)
        )

        # Đồng bộ khung thời gian 2 chart
        all_dates = list(_ideal_dates)
        if actual_events:
            all_dates += list(df_actual["date"])
        if all_dates:
            x_min = pd.to_datetime(min(all_dates)) - timedelta(days=14)
            x_max = pd.to_datetime(max(all_dates)) + timedelta(days=14)
            shared_range = [x_min, x_max]
            fig_ideal.update_layout(xaxis_range=shared_range)
            fig_actual.update_layout(xaxis_range=shared_range)

        st.plotly_chart(fig_ideal, use_container_width=True)
        st.markdown("##### 📊 Thực tế")
        st.plotly_chart(fig_actual, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu Lô trồng để hiển thị biểu đồ tiến độ.")

    st.divider()

    # --- BIỂU ĐỒ PHỄU TIẾN ĐỘ THEO LÔ ---
    st.markdown("#### 📊 Biểu đồ Phễu Tiến độ theo Lô (Pipeline Funnel)")
    st.caption("So sánh tương quan Mức độ Hao hụt và Năng suất từ lúc Xuống giống đến khi Thu hoạch.")
    
    # 1. Pipeline Chart Filters
    pf_farm, pf_vu, pf_team, pf_lot, pf_date = render_chart_filters("pf", include_date=True)
    filtered_pipe_dfs = get_filtered_dfs(pf_farm, pf_vu, pf_team, pf_lot, pf_date, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })
    
    pipe_lots_df = filtered_pipe_dfs["lots"]
    pipe_stg_df = filtered_pipe_dfs["stg"]
    pipe_har_df = filtered_pipe_dfs["har"]
    pipe_des_df = filtered_pipe_dfs["des"]

    # Gom dữ liệu để vẽ grouped/stacked bar chart
    if not pipe_lots_df.empty:
        pipe_lots_merged = pipe_lots_df

        lots = pipe_lots_merged["lo"].unique()
        pipeline_data = []
        for l in lots:
            valid_ids = pipe_lots_merged[pipe_lots_merged["lo"] == l]["lot_id"].tolist()
            
            # 1. Trồng mới và Trồng dặm
            l_lots = pipe_lots_merged[pipe_lots_merged["lo"] == l]
            sl_trong_moi = l_lots[l_lots["loai_trong"] == "Trồng mới"]["so_luong"].sum()
            sl_trong_dam = l_lots[l_lots["loai_trong"] == "Trồng dặm"]["so_luong"].sum()
            # Ưu tiên dien_tich_trong (per-batch), fallback dien_tich (per-lot max)
            if "dien_tich_trong" in l_lots.columns and l_lots["dien_tich_trong"].notna().any():
                dt = l_lots["dien_tich_trong"].sum()
            else:
                dt = l_lots["dien_tich"].max()
                if pd.isna(dt): dt = 0
            
            pipeline_data.append({"Lô": l, "Giai đoạn": "1a. Trồng mới", "Số lượng": sl_trong_moi, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            pipeline_data.append({"Lô": l, "Giai đoạn": "1b. Trồng dặm", "Số lượng": sl_trong_dam, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            
            # 2. Chích bắp
            if not pipe_stg_df.empty:
                sl_cb = pipe_stg_df[(pipe_stg_df["lot_id"].isin(valid_ids)) & (pipe_stg_df["giai_doan"] == "Chích bắp")]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "2. Chích bắp", "Số lượng": sl_cb, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "2. Chích bắp", "Số lượng": 0, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            
            # 3. Cắt bắp
            if not pipe_stg_df.empty:
                sl_cut = pipe_stg_df[(pipe_stg_df["lot_id"].isin(valid_ids)) & (pipe_stg_df["giai_doan"] == "Cắt bắp")]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "3. Cắt bắp", "Số lượng": sl_cut, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "3. Cắt bắp", "Số lượng": 0, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            
            # 4. Thu hoạch (Buồng ~ Cây)
            if not pipe_har_df.empty:
                sl_har = pipe_har_df[pipe_har_df["lot_id"].isin(valid_ids)]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "4. Thu hoạch", "Số lượng": sl_har, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "4. Thu hoạch", "Số lượng": 0, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
                
            # 5. Xuất hủy
            if not pipe_des_df.empty:
                sl_des = pipe_des_df[pipe_des_df["lot_id"].isin(valid_ids)]["so_luong"].sum()
                pipeline_data.append({"Lô": l, "Giai đoạn": "5. Xuất hủy", "Số lượng": sl_des, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            else: pipeline_data.append({"Lô": l, "Giai đoạn": "5. Xuất hủy", "Số lượng": 0, "hover": f"<b>Lô {l}</b><br>Diện tích: {dt:.2f} ha"})
            
        df_pipeline = pd.DataFrame(pipeline_data)
        
        # Build hybrid chart: Trồng mới + Trồng dặm stacked, rest clustered
        lots_list = list(df_pipeline["Lô"].unique())
        
        fig_pipe = go.Figure()
        
        # --- Stacked pair: Trồng mới + Trồng dặm (same offsetgroup) ---
        df_tm = df_pipeline[df_pipeline["Giai đoạn"] == "1a. Trồng mới"]
        fig_pipe.add_trace(go.Bar(
            name="1a. Trồng mới", x=df_tm["Lô"], y=df_tm["Số lượng"],
            marker_color="#4CAF50", offsetgroup="trong",
            customdata=df_tm["hover"], hovertemplate="%{customdata}<br>Giai đoạn: 1a. Trồng mới<br>Số lượng: %{y:,}<extra></extra>"
        ))
        df_td = df_pipeline[df_pipeline["Giai đoạn"] == "1b. Trồng dặm"]
        fig_pipe.add_trace(go.Bar(
            name="1b. Trồng dặm", x=df_td["Lô"], y=df_td["Số lượng"],
            marker_color="#8BC34A", offsetgroup="trong", base=df_tm["Số lượng"].values,
            customdata=df_td["hover"], hovertemplate="%{customdata}<br>Giai đoạn: 1b. Trồng dặm<br>Số lượng: %{y:,}<extra></extra>"
        ))
        
        # --- Clustered bars: each gets its own offsetgroup ---
        cluster_stages = [
            ("2. Chích bắp", "#FFC107"),
            ("3. Cắt bắp", "#FF9800"),
            ("4. Thu hoạch", "#2196F3"),
            ("5. Xuất hủy", "#F44336"),
        ]
        for stage_name, color in cluster_stages:
            df_s = df_pipeline[df_pipeline["Giai đoạn"] == stage_name]
            fig_pipe.add_trace(go.Bar(
                name=stage_name, x=df_s["Lô"], y=df_s["Số lượng"],
                marker_color=color, offsetgroup=stage_name,
                customdata=df_s["hover"], hovertemplate=f"%{{customdata}}<br>Giai đoạn: {stage_name}<br>Số lượng: %{{y:,}}<extra></extra>"
            ))
        
        fig_pipe.update_layout(
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis={"showgrid": True, "gridcolor": "rgba(0,0,0,0.1)", "title": "Số lượng cây / buồng"},
            xaxis={"title": "Danh sách Lô"},
            legend_title_text="Tiến trình"
        )
        st.plotly_chart(fig_pipe, use_container_width=True)
    else:
        st.info("Chưa có danh sách lô để hiển thị biểu đồ Phễu.")

    st.divider()
    st.divider()
    st.markdown("##### 📉 Tiến trình Tổng hợp theo Thời gian")
    st.caption("Biểu đồ gộp thể hiện biến động các công đoạn dọc theo trục ngày. Có thể filter để làm nổi bật.")

    # 2. Multi-line Chart Filters
    mlf_farm, mlf_vu, mlf_team, mlf_lot, mlf_date = render_chart_filters("mlf", include_date=True)
    filtered_ml_dfs = get_filtered_dfs(mlf_farm, mlf_vu, mlf_team, mlf_lot, mlf_date, {
        "lots": df_lots_all, "stg": df_stg_all, "des": df_des_all, "har": df_har_all
    })

    ml_lots_df = filtered_ml_dfs["lots"]
    ml_stg_df = filtered_ml_dfs["stg"]
    ml_har_df = filtered_ml_dfs["har"]
    ml_des_df = filtered_ml_dfs["des"]

    plot_dfs = []
    
    # 1. Trồng mới / Trồng dặm
    if not ml_lots_df.empty and "ngay_trong" in ml_lots_df.columns:
        ml_lots_merged = ml_lots_df
        
        cols_to_keep = ["ngay_trong", "so_luong", "loai_trong"]
        if "lot_id" in ml_lots_merged.columns: cols_to_keep.append("lot_id")
        
        # Missing 'loai_trong' maps to "Trồng mới"
        ml_lots_merged["loai_trong"] = ml_lots_merged["loai_trong"].fillna("Trồng mới")
        
        # Trồng mới
        df_new = ml_lots_merged[ml_lots_merged["loai_trong"] == "Trồng mới"].copy()
        if not df_new.empty:
            df_new.rename(columns={"ngay_trong": "Date"}, inplace=True)
            df_new["Giai đoạn"] = "1a. Trồng mới"
            plot_dfs.append(df_new)
            
        # Trồng dặm
        df_old = ml_lots_merged[ml_lots_merged["loai_trong"] == "Trồng dặm"].copy()
        if not df_old.empty:
            df_old.rename(columns={"ngay_trong": "Date"}, inplace=True)
            df_old["Giai đoạn"] = "1b. Trồng dặm"
            plot_dfs.append(df_old)

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
        # Lấy tên lô và diện tích từ lot_id nếu có (join base_lots)
        lot_name_map = {}
        lot_dt_map = {}
        if not ml_lots_df.empty and "lot_id" in ml_lots_df.columns:
            if "lo" in ml_lots_df.columns:
                lot_name_map = ml_lots_df.set_index("lot_id")["lo"].to_dict()
            if "dien_tich_trong" in ml_lots_df.columns:
                lot_dt_map = ml_lots_df.set_index("lot_id")["dien_tich_trong"].fillna(ml_lots_df.set_index("lot_id")["dien_tich"]).to_dict()
            elif "dien_tich" in ml_lots_df.columns:
                lot_dt_map = ml_lots_df.set_index("lot_id")["dien_tich"].to_dict()
        
        if "lot_id" in df_combined.columns:
            df_combined["Tên Lô"] = df_combined["lot_id"].map(lot_name_map).fillna(df_combined.get("lot_id", ""))
            df_combined["Diện tích"] = df_combined["lot_id"].map(lot_dt_map).fillna(0)
            df_breakdown = (
                df_combined.groupby(["Date", "Giai đoạn", "Tên Lô", "Diện tích"], as_index=False)["so_luong"]
                .sum()
                .sort_values("so_luong", ascending=False)
            )
            def make_breakdown(grp):
                lines = []
                for _, r in grp.iterrows():
                    dt = r['Diện tích']
                    dt_str = f" ({dt:.2f} ha)" if pd.notna(dt) and dt != 0 else ""
                    lines.append(f"&nbsp;&nbsp;• Lô {r['Tên Lô']}{dt_str}: {int(r['so_luong']):,}")
                return "<br>".join(lines)
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
            "1a. Trồng mới": "#4CAF50",    # Green
            "1b. Trồng dặm": "#8BC34A",    # Light Green
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
    ti_farm, ti_vu, ti_team, ti_lot, ti_date = render_chart_filters("ti", include_date=True, use_dynamic_lots=False)
    filtered_ti_dfs = get_filtered_dfs(ti_farm, ti_vu, ti_team, ti_lot, ti_date, {"inv": df_tree_inv_all})
    ti_inv_df = filtered_ti_dfs["inv"]
    
    if not ti_inv_df.empty and "ngay_kiem_ke" in ti_inv_df.columns:
        df_inv = ti_inv_df.copy()
        
        # Ánh xạ lot_id sang lo và dien_tich
        if not df_lots_all.empty:
            mapped_dict_lo = df_lots_all.set_index("lot_id")["lo"].to_dict()
            if "dien_tich_trong" in df_lots_all.columns:
                mapped_dict_dt = df_lots_all.set_index("lot_id")["dien_tich_trong"].fillna(df_lots_all.set_index("lot_id")["dien_tich"]).to_dict()
            else:
                mapped_dict_dt = df_lots_all.set_index("lot_id")["dien_tich"].to_dict()
        else:
            mapped_dict_lo, mapped_dict_dt = {}, {}
            
        df_inv["Tên Lô"] = df_inv["lot_id"].map(lambda x: mapped_dict_lo.get(x, x))
        df_inv["Diện tích"] = df_inv["lot_id"].map(lambda x: mapped_dict_dt.get(x, 0))
        
        df_inv["Ngày"] = pd.to_datetime(df_inv["ngay_kiem_ke"])
        df_inv_grouped = df_inv.groupby(["Ngày", "Tên Lô", "Diện tích"], as_index=False)["so_luong_cay_thuc_te"].sum()
        df_inv_grouped.sort_values(by="Ngày", inplace=True)
        # Tạo chuỗi hover tuỳ chỉnh
        df_inv_grouped["hover"] = df_inv_grouped.apply(lambda r: f"<b>Lô {r['Tên Lô']}</b><br>Diện tích: {r['Diện tích']:.2f} ha<br>Ngày: {r['Ngày'].strftime('%d/%m/%Y')}<br>Số lượng: {int(r['so_luong_cay_thuc_te']):,} cây", axis=1)

        fig_inv = px.line(
            df_inv_grouped, x="Ngày", y="so_luong_cay_thuc_te", color="Tên Lô", 
            markers=True, line_shape="linear",
            custom_data=["hover"],
            labels={"Ngày": "Ngày Kiểm Kê", "so_luong_cay_thuc_te": "Số lượng cây", "Tên Lô": "Lô"},
        )
        fig_inv.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
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


    # --- HEADER ---
    if "toast" in st.session_state:
        st.success(st.session_state.pop("toast"))
        


    # =================================================
    # MODULE ADMIN
    # =================================================
    if c_farm == "Admin" and c_team == "Quản trị viên":
        tab_opts = ["🌐 Dữ liệu toàn cục", "👑 Quản trị Mùa Vụ"]
        active_tab = st.segmented_control("Chức năng", tab_opts, label_visibility="collapsed", key="tab_admin_menu", default=tab_opts[0])
        if active_tab is None: active_tab = tab_opts[0]
        
        if active_tab == tab_opts[1]:
            st.info("👋 Chào mừng Quản trị viên. Tại đây bạn có thể quản lý lịch sử Vụ cho từng lô.")
            
            res = supabase.table("seasons").select("*, dim_lo!inner(lo_name, dim_farm!inner(farm_name))").eq("is_deleted", False).order("created_at", desc=True).execute()
            df_seasons = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            
            if df_seasons.empty:
                st.warning("Hiện tại hệ thống chưa có dữ liệu Vụ (Seasons). Vui lòng tạo lô ở Nông trường trước!")
                return
            
            # Flatten dim_lo join
            df_seasons["farm"] = df_seasons["dim_lo"].apply(lambda x: x.get("dim_farm", {}).get("farm_name") if isinstance(x, dict) else None)
            df_seasons["lo"] = df_seasons["dim_lo"].apply(lambda x: x.get("lo_name") if isinstance(x, dict) else None)
                
            f_farm = st.selectbox("Lọc Farm", options=["Tất cả"] + list(df_seasons["farm"].dropna().unique()))
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
                        cur_start = row.get("ngay_bat_dau")
                        def_start_date = pd.to_datetime(cur_start).date() if cur_start else date.today()
                        start_date = st.date_input("📆 Ngày bắt đầu", value=def_start_date)
                        
                        cur_end = row.get("ngay_ket_thuc_thuc_te")
                        def_end_date = pd.to_datetime(cur_end).date() if cur_end else date.today()
                        end_date = st.date_input("📆 Ngày kết thúc (Thực tế)", value=def_end_date)
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
                                "ngay_bat_dau": start_date.isoformat(),
                                "ngay_ket_thuc_thuc_te": end_date.isoformat()
                            }).eq("id", row["id"]).execute()
                            
                            if auto_next and not cur_end:
                                new_season = {
                                    "dim_lo_id": row["dim_lo_id"],
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
    # MODULE KINH DOANH
    # =================================================
    if c_farm == "Phòng Kinh doanh" and c_team == "Kinh doanh":
        render_global_data_tab("Phòng Kinh doanh")
        return

    # =================================================
    # MODULE 4: QUẢN LÝ FARM
    # =================================================
    if c_team == "Quản lý farm":
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
            tab_opts = ["🌐 Dữ liệu toàn cục", "🌱 Khởi tạo Lô trồng", "📈 Cập nhật Tiến độ", "📏 Đo Size", "🗑️ Cập nhật Xuất hủy", "🌳 Kiểm kê cây", "🧪 Đo pH Đất", "🦠 Kiểm tra Fusarium"]
            
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
                        # Auto-create lô trong dim_lo nếu chưa tồn tại
                        dim_lo_id = get_or_create_dim_lo(c_farm, ten_lo_goc, c_team)
                        if not dim_lo_id:
                            st.error(f"❌ Không thể khởi tạo Lô '{ten_lo_goc}'. Vui lòng thử lại hoặc liên hệ quản trị viên.")
                        else:
                            data_base = {
                                "dim_lo_id": dim_lo_id,
                                "ngay_trong": ngay_trong.isoformat(), "so_luong": so_luong,
                                "so_luong_con_lai": so_luong,
                                "tuan": ngay_trong.isocalendar()[1],
                                "loai_trong": loai_trong
                            }
                            data_season = {
                                "dim_lo_id": dim_lo_id, "vu": "F0",
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
                                _dim_id = get_dim_lo_id(c_farm, lot_id)
                                if _dim_id:
                                    res_lan1 = supabase.table("size_measure_logs") \
                                        .select("id").eq("dim_lo_id", _dim_id).eq("mau_day", mau_day_clean).eq("lan_do", 1).eq("is_deleted", False).execute()
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
                        if insert_to_db("size_measure_logs", data):
                            success_count += 1
                        else:
                            st.error(f"❌ Lỗi ghi lô {item['Lô']}")
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
                        if insert_to_db("tree_inventory_logs", data):
                            success_count += 1
                        else:
                            st.error(f"❌ Lỗi ghi lô {item['Lô']}")
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
                            is_time_valid, msg_time = validate_timeline_logic(c_farm, lot_id, ngay_th, giai_doan)
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
                        valid, msg = check_quantity_limit(c_farm, l_id, req_sl, "stage", giai_doan=g_doan)
                        if not valid:
                            st.error(f"❌ Lỗi tổng số lượng ở Lô {l_id} - {g_doan}: {msg}")
                            return
                    success_count = 0
                    for item in queue:
                        is_valid, msg, allocations = allocate_fifo_quantity(c_farm, item["Lô"], item["Số lượng"], "stage", item["Ngày"], item["Giai đoạn"], item["Giai đoạn"])
                        if is_valid:
                            for alloc in allocations:
                                data = {"farm": c_farm, "team": c_team, "giai_doan": item["Giai đoạn"], "ngay_thuc_hien": item["Ngày"], "mau_day": item["Màu dây"], "tuan": item["Tuần"], "lot_id": alloc["lot_id"], "so_luong": alloc["so_luong"]}
                                if not insert_to_db("stage_logs", data):
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}")
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
                        valid, msg = check_quantity_limit(c_farm, l_id, req_sl, "destruction")
                        if not valid:
                            st.error(f"❌ Lỗi tổng số lượng ở Lô {l_id}: {msg}")
                            return
                    success_count = 0
                    for item in queue:
                        is_valid, msg, allocations = allocate_fifo_quantity(c_farm, item["Lô"], item["Số lượng"], "destruction", item["Ngày"], "Xuất hủy")
                        if is_valid:
                            for alloc in allocations:
                                data = {"farm": c_farm, "team": c_team, "ngay_xuat_huy": item["Ngày"], "giai_doan": item["Giai đoạn"], "mau_day": item.get("Màu dây", "") or None, "ly_do": item["Lý do"], "tuan": item["Tuần"], "lot_id": alloc["lot_id"], "so_luong": alloc["so_luong"]}
                                if not insert_to_db("destruction_logs", data):
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}")
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

        # TAB 8: KIỂM TRA FUSARIUM
        elif active_tab == "🦠 Kiểm tra Fusarium":
            st.markdown("#### Ghi nhận số lượng cây bị bệnh Fusarium")
            available_lots = get_lots_by_farm(c_farm)
            if not available_lots:
                st.warning("⚠️ Chưa có Lô trồng nào. Hãy tạo ở Tab 1.")
            else:
                df_fus = fetch_table_data("fusarium_logs", c_farm)
                df_fus_team = df_fus[df_fus["team"] == c_team] if not df_fus.empty else pd.DataFrame()
                editing_row, is_within_48h = get_editing_row("fusarium_logs", df_fus_team)
                is_editing = editing_row is not None
                
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        lot_id = st.selectbox("🏷️ Chọn Lô kiểm tra", options=available_lots, key="add_fus_lot")
                    with col_b:
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            ngay_kiem_tra = st.date_input("📆 Ngày kiểm tra", value=date.today(), key="add_fus_ngay")
                        with col_b2:
                            st.text_input("📍 Tuần", value=str(ngay_kiem_tra.isocalendar()[1]), disabled=True, key=f"main_w_fus_{ngay_kiem_tra}")
                        so_cay = st.number_input("🔢 Số lượng cây bị Fusarium", min_value=0, step=1, key="add_fus_cay")
                        
                    st.markdown("")
                    if st.button("➕ Thêm vào Danh sách", key="btn_add_fus", use_container_width=True, type="secondary"):
                        if so_cay < 0: st.error("❌ Số lượng cây phải >= 0.")
                        else:
                            st.session_state["queue_fus"].append({
                                "Lô": lot_id, "Ngày": ngay_kiem_tra.isoformat(), "Số cây": so_cay, "Tuần": ngay_kiem_tra.isocalendar()[1]
                            })
                            st.rerun()

                def process_fus_queue():
                    queue = st.session_state["queue_fus"]
                    success_count = 0
                    for item in queue:
                        data = {
                            "farm": c_farm, "team": c_team, "lot_id": item["Lô"],
                            "ngay_kiem_tra": item["Ngày"], "so_cay_fusarium": item["Số cây"], "tuan": item["Tuần"]
                        }
                        try:
                            supabase.table("fusarium_logs").insert(data).execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Lỗi ghi Lô {item['Lô']}: {e}")
                            return
                            
                    st.session_state["queue_fus"] = []
                    st.cache_data.clear()
                    st.session_state["toast"] = f"✅ Ghi nhận {success_count} kết quả kiểm tra Fusarium thành công!"
                    st.rerun()

                render_queue_ui("queue_fus", ["Lô", "Số cây", "Ngày", "Tuần"], process_fus_queue)
                
                st.markdown("---")
                col_t, col_e, col_d = st.columns([5, 1.5, 1.5])
                with col_t:
                    st.markdown('<p class="dataframe-header" style="margin-top:0.5rem;">Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)</p>', unsafe_allow_html=True)
                
                if is_editing and is_within_48h:
                    with col_e:
                        if st.button("✏️ Chỉnh sửa", key="edit_fus_nt", use_container_width=True):
                            edit_fusarium_log_dialog(editing_row, available_lots)
                    with col_d:
                        if st.button("🗑️ Xóa", key="del_fus_nt", use_container_width=True):
                            confirm_action_dialog("DELETE", "fusarium_logs", editing_row["id"], None, "✅ Đã xóa bản ghi kiểm tra Fusarium!")
                elif is_editing and not is_within_48h:
                    with col_e: st.caption("🔒 Quá 48h")
                    with col_d: st.empty()
                else:
                    with col_e: st.empty()
                    with col_d: st.empty()
                    
                render_team_dataframe("fusarium_logs", df_fus_team, ["lot_id", "ngay_kiem_tra", "so_cay_fusarium", "tuan"])

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
                            _dim_id_har = get_dim_lo_id(c_farm, lot_id)
                            if _dim_id_har:
                                res_sm = supabase.table("size_measure_logs").select("id") \
                                    .eq("dim_lo_id", _dim_id_har).eq("mau_day", mau_day_clean).eq("lan_do", 1).eq("is_deleted", False).execute()
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
                        valid, msg = check_quantity_limit(c_farm, l_id, req_sl, "harvest")
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
                                if not insert_to_db("harvest_logs", data):
                                    st.error(f"❌ Lỗi ghi phân rã {alloc['lot_id']}")
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
                        if insert_to_db("bsr_logs", data):
                            success_count += 1
                        else:
                            st.error(f"❌ Lỗi ghi lô {item['Lô']}")
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

