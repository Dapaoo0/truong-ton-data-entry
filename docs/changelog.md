# Changelog

Lịch sử các thay đổi và tính năng mới được triển khai vào dự án.

## [2026-04-06]
## [Version 24.3 - Refactoring & Fix UI] - 2026-04-06

#### Refactor (`app.py`)
- **[Fix UI/Data Formatter]**: Sửa lỗi giao diện hiển thị bảng "Toàn bộ thông tin vụ". Thay đổi `st.dataframe` sang render bằng `st.markdown` với chuỗi `df.to_html()`. Xử lý đồng thời 2 lỗi: 
  1. Header (`Thông tin`, `Cắt bắp`...) bị căn trái (Do Streamlit sử dụng Glide Data Grid không hỗ trợ nhận HTML css text-align từ Styler).
  2. Trường `Diện tích` dù đã ép kiểu String Formatter `f-str` nhưng vẫn bị Streamlit Arrow backend ép ngược lại thành Object numbers (hiển thị 6 chữ số 0 dư).
- **[Logic Code]**: Loại bỏ phương thức `.drop()` của Pandas (tránh các warning khi gọi trên MultiIndex DataFrame) khi truy xuất dữ liệu danh sách `detail_rows`. Chuyển sang thu thập dictionary collection độc lập từng trường theo `{"Vụ" : rows_dict_list}`, tối ưu memory mapping.
- **[Layout Table]**: Áp dụng Styler `set_properties(**{'text-align': 'center'})` và ép f-string formatting `f"{dien_tich:.2f}"` ở phần tử diện tích để chốt cứng display UI. Mặc dù mất ưu thế Sortable by values của `st.dataframe()`, bù lại đem về thẩm mỹ tối ưu cho Dashboard.
