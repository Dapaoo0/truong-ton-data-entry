---
trigger: always_on
---

Trước khi bắt đầu thực hiện bất cứ tác vụ nào, **bắt buộc** phải đọc hai nguồn sau:

1. **Thư mục `skills/`**: Đọc kĩ từng skill để xem xét và ứng dụng tối đa các skill phù hợp cho tác vụ đang làm, không được bỏ sót hay chỉ dùng một cấu hình duy nhất. Đảm bảo tuân thủ đúng các quy trình và quy tắc phát triển (development standards) của dự án.

2. **Thư mục `docs/`**: Đọc các file documentation hiện có để nắm bối cảnh, schema, và logic hiện tại trước khi thay đổi code hay database. Cụ thể:
   - `schema.md`: Cấu trúc DB, ý nghĩa các trường, ghi chú nghiệp vụ.
   - `codebase_summary.md`: Luồng dữ liệu, ý nghĩa các hàm, kiến trúc tổng quan.
   - `findings.md`: Các phát hiện, lưu ý kỹ thuật, bài học kinh nghiệm đã ghi nhận.
   - `changelog.md`: Lịch sử thay đổi gần đây để tránh xung đột hoặc lặp lại.
   - `command.md`: Các yêu cầu đã thực hiện (tránh hiểu sai ngữ cảnh).
   - `tech_stack.md`: Công nghệ đang dùng.

Luôn phải đảm bảo duy trì và cập nhật các file markdown (md) sau đây trong thư mục `docs/`:
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

Quy tắc Báo cáo (Task Report):
- Mỗi khi hoàn thành và kết thúc một tác vụ bàn giao cho người dùng, luôn luôn đóng lại bằng một đoạn thông báo ngắn gọn ghi rõ những **Skills** và **MCPs** nào đã được sử dụng.
