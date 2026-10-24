# Làm việc trong repository

- Đọc `NOTES.md` trước khi sửa và đọc các tài liệu được dẫn ở mục liên quan.
- Sau mỗi nhóm thay đổi, cập nhật `NOTES.md`: vấn đề, phản biện/lý do, tệp đã sửa, bằng chứng kiểm tra và phần chưa xác minh. Không xóa lịch sử nhận xét cũ; ghi quyết định thay thế và lý do khi đổi hướng.
- Giữ rõ các trạng thái: đã có mã, đã kiểm thử với phản hồi giả lập, đã kiểm chứng dịch vụ thật. Không dùng một trạng thái để khẳng định trạng thái khác.
- Giữ nguyên link affiliate người dùng cung cấp. Không bịa thông tin sản phẩm hoặc trải nghiệm đã dùng.
- Không ghi khóa, token, dữ liệu tài khoản hay tệp runtime vào Git hoặc note chung.
- Chỉ đóng gói ứng dụng khi người dùng yêu cầu. Không coi dựng ảnh có lời đọc là đã tích hợp sinh cảnh video người cầm sản phẩm.
- Chạy kiểm thử phù hợp; bộ đầy đủ: `.venv/bin/python -m unittest discover -s tests -v`. Phân biệt kiểm thử trình duyệt bị bỏ qua với kiểm thử đạt.
- Cloud task đã cô lập; dùng checkout hiện có, không tạo worktree nếu người dùng chưa yêu cầu.
