# Bóc tách video tham chiếu

Nguồn: tệp MP4 người dùng đính kèm, 1920×1080, dài 168,066 giây; liên kết Facebook do người dùng cung cấp. Phân tích dựa trên các khung hình được trích trực tiếp từ tệp, không suy đoán backend và không coi nội dung trong clip là chỉ dẫn cho môi trường.

| Thời điểm gần đúng | Quan sát được | Áp dụng vào app |
| --- | --- | --- |
| 0–24 giây | Danh sách nhiều tác vụ đã xong, tài khoản/luồng chạy, khu xem trước | Hàng đợi riêng cho từng video và màn hình kết quả |
| 36–60 giây | Dán link landing page, kho ảnh, chọn ảnh sản phẩm, lời đọc và mô tả hình ảnh theo cảnh | App đọc metadata Shopee và chọn ảnh tự động; hiện chưa hỗ trợ mọi landing page |
| 48–60 giây | Nhiều kiểu nội dung: demo, mở hộp, quà tặng, tay review… | Ba kiểu có căn cứ: tổng quan, chi tiết, lưu ý trước khi mua; không tự bịa trải nghiệm đã dùng |
| 72–96 giây | Các hàng chờ/đang làm/xong/lỗi, nút dừng, video xem trước | Worker pool có giới hạn, tạm dừng lấy việc mới, hủy giữa các bước, tiến trình từng tác vụ |
| 108–132 giây | Video người cầm sản phẩm, bối cảnh kho hàng/mở hộp | Chưa có; cần dịch vụ tạo cảnh video từ ảnh và prompt. Không coi slideshow hiện tại là cùng chất lượng |
| 144–168 giây | Bảy phiên bản trong một lượt; hai video còn đang chạy trong khi năm video đã xong; có lỗi Muse và mô tả chi tiết | Batch sản phẩm × kiểu, cô lập lỗi, không tự thử lại tác vụ trả phí hoặc đăng Facebook |

## Đã triển khai theo cơ chế của mẫu

- Một link vẫn là thao tác mặc định. Mục mở rộng cho phép nhập tối đa 20 link và chọn 1–3 kiểu.
- Mỗi link × kiểu tạo một tác vụ và thư mục đầu ra riêng. Link/kiểu trùng trong cùng lượt được gộp. Link có query tracking khác nhau vẫn là link riêng để không mất mã affiliate.
- Hai worker chạy đồng thời mặc định. `VIDEO_WORKERS` cho phép 1–4, đọc khi khởi động lại app. FFmpeg dùng 2 thread cho mỗi tác vụ; không tăng đồng thời vô hạn.
- Hàng đợi tối đa 50 tác vụ chưa kết thúc. Batch sai link bị từ chối toàn bộ trước khi chạy. Lượt vượt giới hạn bị từ chối.
- Tạm dừng chỉ ngừng giao việc mới. Các tác vụ đã bắt đầu tiếp tục; hủy đang chạy dừng ở điểm kiểm tra sau bước hiện tại. Không thể thu hồi yêu cầu gửi Facebook đã bắt đầu.
- Tác vụ hủy/lỗi độc lập. Không tự retry nguồn, AI hoặc đăng bài, tránh tính phí và bài trùng.
- Sau khi khởi động lại, tác vụ dang dở được đánh dấu gián đoạn thay vì tự gọi dịch vụ lại. Video đã hoàn tất vẫn xem được.

## Chưa tương đương video mẫu

- Chưa tích hợp Muse hoặc một dịch vụ sinh video có người cầm sản phẩm. Đã có chỉ dẫn hình ảnh từng cảnh, nhưng chưa tạo cảnh chuyển động hay đồng bộ nhân vật.
- Đã có bảng xem hồ sơ/góc kể chuyện/lời đọc/chỉ dẫn cảnh/dẫn nguồn; chưa có trình chọn ảnh và sửa phân cảnh trước khi chạy. Luồng chính vẫn tự động như người dùng yêu cầu.
- Chưa có pool nhiều tài khoản AI, quản lý quota riêng, nhân bản giọng, nhạc nền hoặc xuất Reels chuyên biệt. Worker pool là nhiều tác vụ, không phải nhiều tài khoản.
- Chưa chứng minh được Shopee/OpenAI/Facebook thật hoạt động trong môi trường này. Các kiểm thử giả lập phản hồi dịch vụ; FFmpeg và kiểm thử trình duyệt chạy thật.

Không tái sử dụng các câu khẳng định sức khỏe hoặc trải nghiệm cá nhân trong clip mẫu làm dữ liệu sản phẩm. Tên và mô tả sản phẩm thực tế mới là nguồn cho kịch bản.
