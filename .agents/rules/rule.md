---
trigger: always_on
---

Trước khi bắt đầu thực hiện bất cứ tác vụ nào, **bắt buộc** phải đọc hai nguồn sau:

1. **Thư mục `skills/`**: Đọc kĩ từng skill để xem xét và ứng dụng tối đa các skill phù hợp cho tác vụ đang làm, không được bỏ sót hay chỉ dùng một cấu hình duy nhất. Đảm bảo tuân thủ đúng các quy trình và quy tắc phát triển (development standards) của dự án.

2. **Thư mục `docs/`**: Đọc các file documentation hiện có để nắm bối cảnh, schema, và logic hiện tại trước khi thay đổi code hay database. Cụ thể:
   - `business_logic.md`: **Quy tắc nghiệp vụ** — hao hụt, forecast, phân loại trồng, RBAC. ĐỌC ĐẦU TIÊN.
   - `schema.md`: Cấu trúc DB, ý nghĩa các trường, ghi chú nghiệp vụ.
   - `codebase_summary.md`: Luồng dữ liệu, ý nghĩa các hàm, kiến trúc tổng quan.
   - `findings.md`: Các phát hiện, lưu ý kỹ thuật, bài học kinh nghiệm đã ghi nhận.
   - `changelog.md`: Lịch sử thay đổi gần đây để tránh xung đột hoặc lặp lại.
   - `command.md`: Các yêu cầu đã thực hiện (tránh hiểu sai ngữ cảnh).
   - `tech_stack.md`: Công nghệ đang dùng.

Luôn phải đảm bảo duy trì và cập nhật các file markdown (md) sau đây trong thư mục `docs/`:
- `business_logic.md`: Tổng hợp tất cả quy tắc nghiệp vụ (hao hụt, forecast, phân loại trồng, RBAC, ETL).
- `changelog.md`: Lưu lại những thay đổi đã thực hiện.
- `tech_stack.md`: Lưu danh sách những công cụ, framework và công nghệ đang dùng (VD: Streamlit, Node.js, v.v.).
- `findings.md`: Ghi chép lại những khám phá, lưu ý, và bài học kinh nghiệm phát hiện được trong quá trình làm việc.
- `command.md`: Lưu lại tóm tắt những yêu cầu/chỉ thị mà người dùng đã yêu cầu thực hiện.
- `schema.md`: Lưu trữ tất cả thông tin về cấu trúc dữ liệu, các trường (fields) DB và ý nghĩa của chúng.
- `codebase_summary.md`: Lưu lại ý nghĩa của các hàm, mục đích sử dụng và luồng hoạt động chính trong codebase.

Quy tắc sử dụng MCP (Model Context Protocol):
- Khi thực hiện các thao tác với GitHub, ưu tiên sử dụng **GitHub MCP**.
- Khi thực hiện các thao tác liên quan đến database, ưu tiên sử dụng **Supabase MCP**.
- Khi tham khảo/sử dụng các hàm, cú pháp API, framework, luôn bắt buộc dùng **Context7 MCP** để đảm bảo code được viết dựa trên documentation mới nhất.
- Khi thực hiện các thao tác liên quan đến thiết kế UI/prototype với Stitch, sử dụng **Stitch MCP**.

Quy tắc Nhập liệu Database (Data Entry Rules):
- Khi INSERT hoặc UPDATE dữ liệu vào bảng `stage_logs` (chích bắp, cắt bắp, hoặc bất kỳ giai đoạn nào), **bắt buộc ghi theo từng ngày** (`ngay_thuc_hien` = ngày cụ thể, `so_luong` = số lượng của ngày đó). **KHÔNG ĐƯỢC** gộp nhiều ngày thành 1 record tổng tuần.
- Ví dụ đúng: 30/3=29, 1/4=29, 3/4=41 → 3 records riêng biệt.
- Ví dụ sai: 30/3=184 (gộp cả tuần vào 1 record).
- Nếu nguồn dữ liệu (Excel, báo cáo) có chi tiết theo ngày, phải tách ra từng ngày khi nhập vào DB.
- Trường `tuan` chỉ dùng để phân nhóm/lọc, KHÔNG dùng để gộp dữ liệu.

Quy tắc Báo cáo (Task Report):
- Mỗi khi hoàn thành và kết thúc một tác vụ bàn giao cho người dùng, luôn luôn đóng lại bằng một đoạn thông báo ngắn gọn ghi rõ những **Skills** và **MCPs** nào đã được sử dụng.
