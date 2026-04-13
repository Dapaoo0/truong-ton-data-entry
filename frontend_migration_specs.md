# ĐẶC TẢ GIAO DIỆN FRONT-END (REACT / NEXT.JS) DÀNH CHO GOOGLE STITCH
**Dự án:** Hệ thống Quản lý Sinh trưởng Chuối Xuất Khẩu (Trường Tồn)
**Mục tiêu:** Cung cấp prompt và mô tả giao diện cực kỳ chi tiết, độc lập hoàn toàn với backend, để Google Stitch có thể tạo ra các component React/Next.js sử dụng Tailwind CSS.

---

## 1. DESIGN SYSTEM & THÀNH PHẦN CHUNG (UI TOKENS)

**Colors (Tailwind):**
- **Primary:** `bg-green-700` (text: `text-white`), Hex: `#2E7D32`. Dùng cho nút chính, border chính, badge logo.
- **Secondary:** `bg-gray-200` (text: `text-gray-800`). Dùng cho nút phụ.
- **Warning/Accent:** `bg-orange-500` (text: `text-white`), Hex: `#FF9800`. Dùng cho badge team, cảnh báo.
- **Background:** `bg-gray-50` cho nền trang, `bg-white` cho form/card nội dung.

**Biểu đồ / Trạng thái (Chart Colors):**
- Trồng mới: `#4CAF50` (Green)
- Trồng dặm: `#8BC34A` (Light Green)
- Chích bắp: `#FFC107` (Amber)
- Cắt bắp: `#FF9800` (Orange)
- Thu hoạch: `#2196F3` (Blue)
- Xuất hủy: `#F44336` (Red)

**Typography:**
- Font: Inter.
- Tiêu đề chính (Page Title): `text-2xl font-bold text-green-800`.
- Phụ đề (Caption): `text-sm text-gray-500`.

**Layout chung (App Shell):**
Tất cả các trang sau đăng nhập đều sử dụng một **Layout Component** bao gồm:
1. **Sidebar (Cột trái - 250px, cố định):**
   - Logo hoặc Text "🍌 Trường Tồn".
   - Badge hiển thị Farm: `🏭 Farm 195` (Nền xanh lá bo tròn tròn `rounded-full px-3 py-1 text-sm font-semibold`).
   - Badge hiển thị Team: `👥 NT1` (Nền cam bo tròn `rounded-full px-3 py-1 text-sm font-semibold`).
   - Thông tin thời gian đăng nhập (text nhỏ màu xám).
   - Nút Đăng xuất (`w-full` nằm dưới cùng).
2. **Main Content (Nội dung chính - Không gian còn lại):**
   - **Header:** Chứa tiêu đề trang đang xem (ví dụ: "Hệ thống Đội Nông trường 1 - Farm 195"). Đi kèm là hệ thống Toast Notification (hiển thị góc trên phải khi có sự kiện thành công).
   - **Tabs Navigation:** Thanh ngang điều hướng (React Tabs / Next.js Links) để chuyển qua lại giữa các màn hình nhập liệu. Nút tab đang active có gạch chân hoặc màu nền khác biệt.

---

## 2. TRANG ĐĂNG NHẬP (LOGIN PAGE)

**Bố cục (Layout):**
- Full màn hình (`h-screen`), background trắng.
- Ở giữa màn hình là một Card đăng nhập (`max-w-md w-full p-8 shadow-lg rounded-xl border border-gray-100`).

**Thành phần bên trong Card:**
- Ảnh Logo công ty (căn giữa, width khoảng 150px).
- Dòng chữ: "🍌 Trường Tồn Banana Tracker" (`text-xl font-bold text-center text-green-700`).
- Tiêu đề phụ: "🔐 Đăng nhập hệ thống" (`text-lg text-center mt-2`).
- Đường kẻ ngang `<hr className="my-4" />`.
- **Form UI:**
  - Dropdown 1: "🏗️ Chọn Farm" (Placeholder: Vui lòng chọn Farm...).
  - Dropdown 2: "👥 Chọn Đội / Vai trò" (Placeholder: Vui lòng chọn Đội / Vai trò...). Ghi chú UI: Dropdown này sẽ render các options khác nhau dạng động (mô phỏng select liên kết).
  - Input: "🔑 Mật khẩu" (Type: `password`).
  - Nút bấm: "🚀 Đăng nhập" (`w-full bg-green-700 text-white rounded-md py-2 mt-4 hover:bg-green-800 transition`).
- Footer của Card: Text nhỏ màu xám "💡 Vui lòng chọn đúng vai trò của mình để thao tác đúng nghiệp vụ."

---

## 3. CẤU TRÚC GIAO DIỆN NHẬP LIỆU (FORM PAGES)

Tất cả các màn hình nhập liệu (Tabs) đều tuân theo một khuôn mẫu (Template) UI thống nhất gồm 2 phần chính: **Vùng Form Nhập** ở trên và **Bảng Dữ Liệu Tạm (Queue)** cùng **Bảng Dữ liệu Đã Lưu** ở dưới.

### Phần 1: Form Nhập Liệu (Card Container)
- Khung: `border border-gray-200 rounded-lg p-4 bg-white shadow-sm`.
- Layout: Grid 2 cột (`grid-cols-1 md:grid-cols-2 gap-4`).
- **Các field thường gặp:**
  - `Select` chọn Lô trồng (VD: A1, B2).
  - `Date Picker` chọn Ngày.
  - Vị trí kế bên Date Picker luôn là 1 `Input` bị disable hiển thị "Tuần" (Week number) - UI tự động fill.
  - `Input type="number"` nhập số lượng.
  - Nút bấm: "➕ Thêm vào Danh sách" (`w-full bg-gray-200 text-gray-800 py-2 rounded-md hover:bg-gray-300 mt-4`).

### Phần 2: UI Danh sách chờ duyệt (Queue Data Grid)
- Tiêu đề: "📋 Danh sách chờ duyệt" (`text-lg font-semibold mt-6 mb-2`).
- Component Bảng (Table): Render một mảng state dạng list.
  - Có cột Checkbox ở đâu để chọn dòng (Row selection).
  - Các cột dữ liệu: Lô, Giai đoạn, Ngày, Số lượng...
- Khu vực Nút bấm hành động (dưới bảng Queue):
  - Cột 1 (trái): Nút "🚀 Lưu toàn bộ lên Hệ thống" (`w-full bg-green-600 text-white`).
  - Cột 2 (phải): Nút "🗑️ Xóa dòng đã chọn" hoặc "🗑️ Xóa toàn bộ danh sách" (`w-full bg-red-100 text-red-600`).

### Phần 3: UI Dữ liệu Đã Lưu (History Data Grid)
- Tiêu đề: "Dữ liệu của đội bạn (Click 1 dòng để sửa/xóa)".
- Component Bảng: Table chuẩn, row có hiệu ứng hover cursor-pointer.
- Nút bấm (nâng cao, chỉ hiện khi click 1 row): Sẽ hiện cụm nút vát cạnh "✏️ Chỉnh sửa" (Mở modal) và "🗑️ Xóa" (Mở modal confirm). UI thể hiện icon 🔒 "Quá 48h" nếu dòng đó bị khóa.

---

## 4. CHI TIẾT CÁC MÀN HÌNH CHỨC NĂNG (TABS) ĐỂ GOOGLE STITCH TẠO COMPONENT

Bạn có thể yêu cầu Google Stitch tạo từng màn hình rời rạc dựa trên các layout sau:

### 4.1. Màn hình Khởi Tạo Lô Trồng
- **Form:**
  - Input text: "🏷️ Tên Lô"
  - Select: "🌱 Loại trồng" (Trồng mới / Trồng dặm).
  - DatePicker: "📆 Ngày trồng".
  - Input (disabled): "📍 Tuần".
  - Input (number): "🔢 Số lượng trồng".
- **Action:** Nút "✅ Tạo Lô Trồng" (Lưu thẳng, không dùng Queue).

### 4.2. Màn hình Cập Nhật Tiến Độ
- **Form:**
  - Select: "🏷️ Chọn Lô".
  - Radio Group (Row layout): "📌 Giai đoạn" (Chích bắp / Cắt bắp).
  - Input text: "🎨 Màu dây" (Hiển thị khi chọn Cắt bắp).
  - DatePicker: "📆 Ngày thực hiện".
  - Input (number): "🔢 Số lượng cây".

### 4.3. Màn hình Đo Size
- **Form:**
  - Select: Lô.
  - Input: Màu dây.
  - Radio Group: "Lần đo" (1 hoặc 2).
  - DatePicker: Ngày đo.
  - Input text: "📏 Hàng kiểm tra".
  - Input (number float): "📏 Size (Cal)".
  - Input (number): "🔢 Số lượng buồng mẫu".

### 4.4. Màn hình Cập nhật Xuất Hủy
- **Form:**
  - Select: Lô.
  - Select: "⏱️ Giai đoạn xuất hủy" (Trước chích bắp, Trước cắt bắp, Trước thu hoạch).
  - Pill component hoặc Radio ngang: "📝 Nhóm lý do" (Bệnh, Đổ Ngã, Khác).
  - TextArea: "📝 Chi tiết lý do" (Chỉ render diện tích nhập chữ nếu chọn Khác).
  - DatePicker: Ngày.
  - Input (number): Số lượng.

### 4.5. Màn hình Đo pH Đất (Dynamic Form Component)
- **Đặc biệt (UI dùng Form Array/Repeater):**
  - Vùng Fixed: Select Lô, DatePicker Ngày đo.
  - Vùng Dynamic List: Render n dòng. Mỗi dòng có Label "Lần đo X" và Input số (0.0 -> 14.0).
  - Nút "➕ Thêm lần đo" (Nằm dưới danh sách, style chữ xanh/icon cộng, không viền).
  - Nút "🚀 Lưu kết quả" (Nút to phía dưới cùng).

### 4.6. Màn hình Thu Hoạch (Của đội thu hoạch)
- **Form:**
  - Select: Lô.
  - Input: Màu dây.
  - Select: "🚜 Hình thức thu hoạch" (Bằng xe cày / Bằng ròng rọc).
  - DatePicker: Ngày thu hoạch.
  - Input (number): Số lượng buồng thu hoạch.

### 4.7. Màn hình Cập nhật BSR (Xưởng Đóng Gói)
- **Form:**
  - Select: Lô.
  - DatePicker: Ngày đóng gói.
  - Input (number float, step 0.1): "📐 Nhập tỷ lệ BSR".

---

## 5. MÀN HÌNH DASHBOARD TOÀN CỤC (GLOBAL DATA DASHBOARD)

Đây là trang có UI phức tạp nhất, nặng về biểu đồ, dùng Recharts, Chart.js hoặc thư viện biểu đồ của React.

**Thanh công cụ Export (Top):**
- Layout Flex or Grid (3 nút).
- Nút 1: "📥 Xuất Báo Cáo Excel" (Style secondary outline).
- Nút 2: "✂️ Báo cáo Cắt bắp".
- Nút 3: "🌱 Báo cáo Trồng mới".

**Bộ lọc phân tích (Global Filters):**
- Vùng nền `bg-white shadow-sm rounded-lg p-4 mb-6`.
- Bố cục 4 dropdowns ngang + 1 Date Range Picker:
  1. Select: Lọc Farm.
  2. Select: Lọc Vụ.
  3. Select: Lọc Đội.
  4. Select: Lọc Lô.
  5. DateRangePicker: Chọn từ ngày - đến ngày.

**Khu vực Biểu đồ:**

1. **Biểu Đồ Phễu Tiến Độ (Bar Chart)**
   - UI Card ôm gọn biểu đồ.
   - Trục X: Label tên Lô (Ví dụ: Lô A1, Lô B2).
   - Trục Y: Cột giá trị số lượng.
   - Kiểu cột: "Trồng mới" và "Trồng dặm" đè lên nhau (Stacked). Các trạng thái khác (Chích bắp, Cắt bắp, Thu hoạch, Xuất hủy) nằm cạnh nhau (Grouped).
   - Truyền màu sắc đúng với Design System.

2. **Tiến trình Tổng hợp theo thời gian (Multi-Line Chart)**
   - Biểu đồ đường, có điểm (dots) tại các vị trí dữ liệu.
   - Trục X: Thời gian (Ngày).
   - Trục Y: Khối lượng tổng.
   - Tính năng Tương tác (UI): Có các checkbox gạt (Toggle/Legend) ở phía trên để ẩn/hiện từng đường dây. Khi rê chuột (Hover), một Tooltip chung hiển thị chi tiết (VD: Ngày đó Lô A có x cây, Lô B có y cây).

3. **Biểu đồ Số lượng cây thực tế (Multi-Line Chart)**
   - Trục X: Ngày.
   - Trục Y: Số lượng cây.
   - Mỗi Lô đất được vẽ thành 1 đường riêng biệt để theo dõi xu hướng (sụt giảm).

---

## 6. MÀN HÌNH ADMIN QUẢN TRỊ MÙA VỤ

**Bố cục:**
- Một Data Grid (Table) to giữa màn hình liệt kê (`Lô`, `Vụ`, `Loại trồng`, `Ngày BĐ`, `Ngày KT`).
- Khi user click vào 1 dòng trong Table, render một panel ngay bên rưới (Hoặc Modal/Drawer).
- **Form panel Chốt Vụ:**
  - Tiêu đề UI: "🛠️ Chốt vụ: [Farm] - [Lô]".
  - 2 DatePicker liền kề: Ngày bắt đầu và Ngày kết thúc.
  - Phía dưới là 1 dòng Checkbox: "🚀 Cho phép tự động tạo vụ nối tiếp: F[N+1]" (Tick mặc định).
  - Nút to "💾 Lưu thay đổi & Chốt vụ".

---
*Ghi chú cho Google Stitch: Khi sử dụng file này làm mô tả, hãy focus vào việc build cấu trúc UI dạng Component Driven (React/Next.js). Thiết lập các State rỗng tương ứng để UI hoạt động (VD: gõ vào form > bấm nút > log ra console hoặc hiện UI Queue) thay vì kết nối API thật.*
