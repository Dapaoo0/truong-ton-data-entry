"""
=======================================================================
  ỨNG DỤNG NHẬP LIỆU QUẢN LÝ TIẾN ĐỘ SINH TRƯỞNG CHUỐI XUẤT KHẨU
  Công ty Trường Tồn  |  Streamlit + Supabase
=======================================================================
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# =====================================================
# CẤU HÌNH BAN ĐẦU
# =====================================================

# Load biến môi trường từ file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Khởi tạo Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Trường Tồn - Quản lý Tiến độ Chuối",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# MẢNG MẬT KHẨU CỨNG (CHỈ ĐỂ TEST)
# =====================================================
FARM_PASSWORDS = {
    "Farm 126": "123",
    "Farm 157": "456",
    "Farm 195": "789",
}

# Danh sách vụ và màu dây
VU_OPTIONS = ["F0", "F1", "F2", "F3", "F4", "F5"]
MAU_DAY_OPTIONS = ["Đỏ", "Xanh lá", "Vàng", "Xanh dương", "Trắng", "Cam"]
GIAI_DOAN_OPTIONS = ["Chích bắp", "Cắt bắp", "Thu hoạch"]

# =====================================================
# STYLE TÙY CHỈNH (CSS)
# =====================================================
st.markdown("""
<style>
    /* Tiêu đề chính */
    .main-title {
        text-align: center;
        color: #2E7D32;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        text-align: center;
        color: #6D6D6D;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    /* Card cho login */
    .login-card {
        max-width: 420px;
        margin: 4rem auto;
        padding: 2.5rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
    }
    /* Badge farm */
    .farm-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        background: #2E7D32;
        color: white;
        font-weight: 600;
        font-size: 0.9rem;
    }
    /* Khu vực bảng */
    .dataframe-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1B5E20;
        margin: 1rem 0 0.5rem 0;
        padding-left: 0.5rem;
        border-left: 4px solid #2E7D32;
    }
    /* Divider */
    .section-divider {
        border: none;
        border-top: 2px solid #E8F5E9;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================
# HÀM TIỆN ÍCH
# =====================================================

def init_session_state():
    """Khởi tạo các giá trị mặc định trong session_state."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "current_farm" not in st.session_state:
        st.session_state["current_farm"] = None


def logout():
    """Đăng xuất: reset session state."""
    st.session_state["logged_in"] = False
    st.session_state["current_farm"] = None


def fetch_base_lots(farm: str) -> pd.DataFrame:
    """Lấy danh sách lô trồng gốc từ Supabase, lọc theo Farm."""
    response = (
        supabase.table("base_lots")
        .select("*")
        .eq("farm", farm)
        .order("created_at", desc=True)
        .execute()
    )
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


def fetch_stage_logs(farm: str) -> pd.DataFrame:
    """Lấy nhật ký tiến độ từ Supabase, lọc theo Farm."""
    response = (
        supabase.table("stage_logs")
        .select("*")
        .eq("farm", farm)
        .order("created_at", desc=True)
        .execute()
    )
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


def get_lot_ids_for_farm(farm: str) -> list:
    """Lấy danh sách lot_id thuộc Farm đang đăng nhập."""
    response = (
        supabase.table("base_lots")
        .select("lot_id")
        .eq("farm", farm)
        .order("lot_id")
        .execute()
    )
    if response.data:
        return [row["lot_id"] for row in response.data]
    return []


def insert_base_lot(data: dict) -> bool:
    """Thêm lô trồng mới vào Supabase. Trả về True nếu thành công."""
    try:
        supabase.table("base_lots").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu lô trồng: {e}")
        return False


def insert_stage_log(data: dict) -> bool:
    """Thêm bản ghi tiến độ mới vào Supabase. Trả về True nếu thành công."""
    try:
        supabase.table("stage_logs").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu tiến độ: {e}")
        return False


# =====================================================
# MÀN HÌNH ĐĂNG NHẬP (LOGIN)
# =====================================================

def render_login():
    """Hiển thị màn hình đăng nhập."""
    
    # Khu vực chứa logo (nếu có)
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
    with col_logo2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
            
    st.markdown('<p class="main-title">🍌 Trường Tồn Banana Tracker</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Hệ thống quản lý tiến độ sinh trưởng chuối xuất khẩu</p>', unsafe_allow_html=True)

    # Card đăng nhập
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 Đăng nhập hệ thống")
        st.divider()

        # Chọn Farm
        selected_farm = st.selectbox(
            "🏗️ Chọn Farm",
            options=list(FARM_PASSWORDS.keys()),
            index=0,
            key="login_farm",
        )

        # Nhập mật khẩu
        password = st.text_input(
            "🔑 Mật khẩu",
            type="password",
            key="login_password",
            placeholder="Nhập mật khẩu Farm...",
        )

        st.markdown("")  # Khoảng trống nhỏ

        # Nút đăng nhập
        if st.button("🚀 Đăng nhập", use_container_width=True, type="primary"):
            if not password:
                st.warning("⚠️ Vui lòng nhập mật khẩu.")
            elif password == FARM_PASSWORDS.get(selected_farm):
                st.session_state["logged_in"] = True
                st.session_state["current_farm"] = selected_farm
                st.success(f"✅ Đăng nhập thành công! Chào mừng đến {selected_farm}.")
                st.rerun()
            else:
                st.error("❌ Mật khẩu không đúng. Vui lòng thử lại.")

        st.divider()
        st.caption("💡 Mỗi Farm có mật khẩu riêng. Liên hệ quản lý nếu quên.")


# =====================================================
# GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP)
# =====================================================

def render_main_app():
    """Hiển thị giao diện chính sau khi đăng nhập thành công."""
    current_farm = st.session_state["current_farm"]

    # ----- SIDEBAR: Thông tin Farm + Đăng xuất -----
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("### 🍌 Trường Tồn")
            
        st.divider()
        st.markdown(f'<span class="farm-badge">{current_farm}</span>', unsafe_allow_html=True)
        st.caption(f"Đăng nhập lúc: {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
        st.divider()

        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            logout()
            st.rerun()

        st.divider()
        
        # Hướng dẫn sử dụng (Collapsible Expander)
        with st.expander("📖 Hướng dẫn sử dụng chi tiết", expanded=False):
            st.markdown("""
            Chào mừng bạn đến với hệ thống Quản lý Tiến độ Sinh trưởng Chuối Xuất khẩu của công ty Trường Tồn.
            Hệ thống gồm 2 bước chính để Đăng ký và Theo dõi một Lô trồng.
            
            ---
            
            **BƯỚC 1: KHỞI TẠO LÔ TRỒNG MỚI**
            *(Làm 1 lần duy nhất ngay khi xuống giống mới)*
            
            1. Bấm vào Tab **"📋 Khởi tạo Lô Trồng"** ở màn hình chính.
            2. Chọn **Vụ** trồng (Ví dụ: F1, F2...).
            3. Nhập tên **Lô** (Ví dụ: A1, B3...). *App sẽ tự ghép thành mã lô như F1-A1.*
            4. Chọn **Ngày trồng** (mặc định là hôm nay).
            5. Nhập **Số lượng trồng** (tổng số lượng cây của lô này).
            6. Bấm nút màu đỏ **"✅ Tạo Lô Trồng Mới"**.
            👉 Sau khi tạo, lô sẽ ngay lập tức được thêm vào **Bảng 1 (Danh sách Lô trồng)** ở dưới cùng.
            
            ---
            
            **BƯỚC 2: CẬP NHẬT TIẾN ĐỘ**
            *(Ghi nhận sinh trưởng theo thời gian thực tế)*
            
            1. Bấm vào Tab **"📈 Cập nhật Tiến độ"** ở màn hình chính.
            2. **Chọn Lô**: Bấm vào danh sách thả xuống, hệ thống sẽ tự liệt kê các Lô mà Farm bạn đã Khởi tạo ở Bước 1.
            3. **Chọn Giai đoạn** cần cập nhật (Chích bắp / Cắt bắp / Thu hoạch).
            4. Chọn **Ngày thực hiện** công việc.
            5. Ghi **Số lượng** cây thực tế đã thực hiện trong ngày hôm đó.
            6. **Trường hợp Đặc Biệt**:
               - Nếu chọn **Chính bắp**: Bắt buộc phải chọn **Màu Dây** (Đỏ, Xanh lá, Vàng...) để đánh dấu lứa chích.
               - Nếu chọn **Thu hoạch**: Bắt buộc phải nhập tỷ lệ **BSR** (Buồng/Sản Rạ) đạt được (Ví dụ: 0.95, 1.1...).
            7. Bấm nút màu đỏ **"✅ Lưu Tiến Độ"**.
            👉 Bản ghi này sẽ được thêm ngay vào **Bảng 2 (Nhật ký cập nhật tiến độ)**.
            
            ---
            
            **LƯU Ý:**
            - 🔒 **Bảo Mật**: Dữ liệu hoàn toàn độc lập. Tài khoản Farm nào chỉ cập nhật và nhìn thấy báo cáo của đúng Farm đó.
            - 💾 **Lưu Trữ**: App kết nối trực tiếp lên Cloud (Supabase). Do đó dữ liệu sẽ không bao giờ mất khi bạn tắt máy ngang.
            - ✏️ **Chỉ Nhập Thêm**: Hiện tại Hệ thống chỉ hỗ trợ **Nhập mới**, không cho tự ý Xóa/Sửa để hạn chế sai sót. Nếu lỡ tay nhập nhầm, hãy ghi chú lại và báo cho Quản lý / IT để điều chỉnh trên hệ thống gốc.
            """)
            
        st.divider()
        st.info("📌 Dữ liệu được lưu trên Supabase Cloud.")

    # ----- TIÊU ĐỀ CHÍNH -----
    st.markdown(f'<p class="main-title">🍌 Quản lý Tiến độ - {current_farm}</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Nhập liệu và theo dõi tiến độ sinh trưởng chuối xuất khẩu</p>', unsafe_allow_html=True)

    # ----- TABS CHÍNH -----
    tab1, tab2 = st.tabs([
        "📋 Khởi tạo Lô Trồng (Base Info)", 
        "📈 Cập nhật Tiến độ (Stage Tracking)"
    ])

    # =====================================================
    # TAB 1: KHỞI TẠO LÔ TRỒNG
    # =====================================================
    with tab1:
        st.markdown("#### 🌱 Đăng ký đợt xuống giống mới")
        st.caption("Nhập đầy đủ thông tin bên dưới để tạo Lô trồng mới.")

        with st.form("form_base_info", clear_on_submit=True):
            col_a, col_b = st.columns(2)

            with col_a:
                vu = st.selectbox("📅 Vụ", options=VU_OPTIONS, index=0)
                ngay_trong = st.date_input("📆 Ngày trồng", value=date.today())

            with col_b:
                lo = st.text_input("🏷️ Lô (VD: A1, B3, C2...)", placeholder="Nhập tên lô...")
                so_luong_trong = st.number_input(
                    "🔢 Số lượng trồng (cây)",
                    min_value=0,
                    value=0,
                    step=100,
                )

            submitted_base = st.form_submit_button(
                "✅ Tạo Lô Trồng Mới",
                use_container_width=True,
                type="primary",
            )

            if submitted_base:
                # --- Validate ---
                if not lo or not lo.strip():
                    st.error("❌ Vui lòng nhập tên Lô.")
                elif so_luong_trong <= 0:
                    st.error("❌ Số lượng trồng phải lớn hơn 0.")
                else:
                    # Tạo ID ghép: VD "F1-A2"
                    lot_id = f"{vu}-{lo.strip()}"

                    # Chuẩn bị dữ liệu để INSERT
                    new_lot = {
                        "farm": current_farm,
                        "lot_id": lot_id,
                        "vu": vu,
                        "lo": lo.strip(),
                        "ngay_trong": ngay_trong.isoformat(),
                        "so_luong": so_luong_trong,
                        "trang_thai": "Đã trồng",
                    }

                    # Lưu vào Supabase
                    if insert_base_lot(new_lot):
                        st.success(f"✅ Tạo thành công Lô **{lot_id}** ({current_farm})")
                        st.balloons()

    # =====================================================
    # TAB 2: CẬP NHẬT TIẾN ĐỘ
    # =====================================================
    with tab2:
        st.markdown("#### 📊 Cập nhật giai đoạn sinh trưởng")
        st.caption("Chọn Lô và ghi nhận tiến độ: Chích bắp → Cắt bắp → Thu hoạch.")

        # Lấy danh sách lô thuộc Farm hiện tại
        available_lots = get_lot_ids_for_farm(current_farm)

        if not available_lots:
            st.warning("⚠️ Chưa có Lô trồng nào được khởi tạo. Vui lòng tạo ở Tab 1 trước.")
        else:
            with st.form("form_stage_tracking", clear_on_submit=True):
                col_c, col_d = st.columns(2)

                with col_c:
                    selected_lot = st.selectbox(
                        "🏷️ Chọn Lô cần cập nhật",
                        options=available_lots,
                    )
                    giai_doan = st.radio(
                        "📌 Giai đoạn",
                        options=GIAI_DOAN_OPTIONS,
                        horizontal=True,
                    )

                with col_d:
                    ngay_thuc_hien = st.date_input(
                        "📆 Ngày thực hiện",
                        value=date.today(),
                    )
                    so_luong_thuc_hien = st.number_input(
                        "🔢 Số lượng thực hiện",
                        min_value=0,
                        value=0,
                        step=100,
                    )

                # --- Trường điều kiện: BSR (chỉ khi Thu hoạch) ---
                bsr_value = None
                if giai_doan == "Thu hoạch":
                    bsr_value = st.number_input(
                        "📐 BSR (Buồng/Sản Rạ)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        format="%.2f",
                        help="Chỉ số BSR - chỉ áp dụng cho giai đoạn Thu hoạch",
                    )

                # --- Trường điều kiện: Màu dây (bắt buộc khi Chích bắp) ---
                mau_day_value = None
                if giai_doan == "Chích bắp":
                    mau_day_value = st.selectbox(
                        "🎨 Màu dây (Bắt buộc)",
                        options=MAU_DAY_OPTIONS,
                    )

                submitted_stage = st.form_submit_button(
                    "✅ Lưu Tiến Độ",
                    use_container_width=True,
                    type="primary",
                )

                if submitted_stage:
                    # --- Validate ---
                    if so_luong_thuc_hien <= 0:
                        st.error("❌ Số lượng thực hiện phải lớn hơn 0.")
                    elif giai_doan == "Chích bắp" and not mau_day_value:
                        st.error("❌ Vui lòng chọn Màu dây cho giai đoạn Chích bắp.")
                    elif giai_doan == "Thu hoạch" and (bsr_value is None or bsr_value <= 0):
                        st.error("❌ Vui lòng nhập BSR cho giai đoạn Thu hoạch.")
                    else:
                        # Chuẩn bị dữ liệu
                        new_log = {
                            "farm": current_farm,
                            "lot_id": selected_lot,
                            "giai_doan": giai_doan,
                            "ngay_thuc_hien": ngay_thuc_hien.isoformat(),
                            "so_luong": so_luong_thuc_hien,
                            "bsr": bsr_value,
                            "mau_day": mau_day_value,
                        }

                        # Lưu vào Supabase
                        if insert_stage_log(new_log):
                            st.success(
                                f"✅ Đã ghi nhận **{giai_doan}** cho Lô **{selected_lot}** "
                                f"({so_luong_thuc_hien} cây - {ngay_thuc_hien.strftime('%d/%m/%Y')})"
                            )

    # =====================================================
    # HIỂN THỊ DỮ LIỆU BẢNG (LỌC THEO FARM)
    # =====================================================
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(f"### 📊 Dữ liệu của {current_farm}")
    st.caption("Chỉ hiển thị dữ liệu thuộc Farm bạn đang đăng nhập.")

    # ----- Bảng 1: Danh sách Lô gốc -----
    st.markdown('<p class="dataframe-header">🌱 Bảng 1: Danh sách Lô trồng đã khởi tạo</p>', unsafe_allow_html=True)
    df_lots = fetch_base_lots(current_farm)

    if df_lots.empty:
        st.info("📭 Chưa có lô trồng nào. Hãy tạo mới ở Tab 1.")
    else:
        # Chọn và đổi tên cột để hiển thị đẹp
        display_lots = df_lots[["lot_id", "vu", "lo", "ngay_trong", "so_luong", "trang_thai", "created_at"]].copy()
        display_lots.columns = ["Mã Lô", "Vụ", "Lô", "Ngày Trồng", "Số Lượng", "Trạng Thái", "Ngày Tạo"]
        st.dataframe(
            display_lots,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Số Lượng": st.column_config.NumberColumn(format="%d 🌱"),
                "Ngày Trồng": st.column_config.DateColumn(format="DD/MM/YYYY"),
            },
        )

    st.markdown("")  # Khoảng cách

    # ----- Bảng 2: Nhật ký tiến độ -----
    st.markdown('<p class="dataframe-header">📈 Bảng 2: Nhật ký cập nhật tiến độ</p>', unsafe_allow_html=True)
    df_logs = fetch_stage_logs(current_farm)

    if df_logs.empty:
        st.info("📭 Chưa có bản ghi tiến độ nào. Hãy cập nhật ở Tab 2.")
    else:
        display_logs = df_logs[["lot_id", "giai_doan", "ngay_thuc_hien", "so_luong", "bsr", "mau_day", "created_at"]].copy()
        display_logs.columns = ["Mã Lô", "Giai Đoạn", "Ngày Thực Hiện", "Số Lượng", "BSR", "Màu Dây", "Ngày Ghi Nhận"]
        st.dataframe(
            display_logs,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Số Lượng": st.column_config.NumberColumn(format="%d 🌿"),
                "Ngày Thực Hiện": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "BSR": st.column_config.NumberColumn(format="%.2f"),
            },
        )


# =====================================================
# MAIN: ĐIỀU KHIỂN LUỒNG APP
# =====================================================

def main():
    """Hàm chính điều khiển toàn bộ ứng dụng."""
    # Khởi tạo session state
    init_session_state()

    # Phân luồng: Login hay Main App
    if not st.session_state["logged_in"]:
        render_login()
    else:
        render_main_app()


# Chạy app
if __name__ == "__main__":
    main()
