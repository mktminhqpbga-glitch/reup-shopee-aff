# Note chung — Affiliate Studio

Đây là nơi ghi các thay đổi, phản biện, lý do kỹ thuật và bằng chứng kiểm tra của repository. Các lần sửa tiếp theo đọc note trước, rồi bổ sung mục mới; không ghi khóa hay token vào đây.

## 2026-10-24 — Đánh giá và kết nối repository

**Yêu cầu người dùng:** làm trực tiếp trong `mktminhqpbga-glitch/reup-shopee-aff`, đọc note có sẵn, ghi mọi thay đổi/góp ý và phản biện có lý do. Mốc ngày theo Asia/Saigon.

**Phạm vi đã đọc:** `README.md`, `docs/storyboard-flow.md`, `docs/reference-video.md` cùng mã nguồn và kiểm thử hiện có. Trước thay đổi này chưa tìm thấy `NOTES.md` hoặc một note chung khác. Ba tài liệu trên là tài liệu tạo trong các bước trước của cuộc trò chuyện, không phải note độc lập của một tác giả khác.

**Bằng chứng Git lúc bắt đầu:** `origin` đã trỏ repo được yêu cầu; các lần đọc `git ls-remote origin` thành công nhưng không trả nhánh/commit. Local HEAD là nhánh unborn `work`, mã đang là tệp chưa được commit. `git fetch origin` không tìm thấy remote HEAD. Vì vậy không có lịch sử remote hoặc note remote nào để nhận là đã đọc. Không reset hoặc ghi đè lịch sử remote.

### Đánh giá tính khả thi

| Hạng mục | Kết luận | Lý do và điều kiện chứng minh |
| --- | --- | --- |
| Nhận một link và tổ chức tác vụ | Khả thi; đã có kiểm thử cục bộ | Batch, worker pool, tiến trình và hủy đã có mã/kiểm thử |
| Tự lấy mọi sản phẩm Shopee từ link | Chưa đủ bằng chứng để cam kết | Hiện chỉ đọc HTML công khai; có thể gặp JavaScript, đăng nhập/CAPTCHA hoặc giới hạn truy cập. Cần nguồn dữ liệu được cấp quyền để ổn định |
| Kịch bản phù hợp từng sản phẩm | Khả thi về kiến trúc; chất lượng AI thật chưa đo | Có hồ sơ, ba góc kể chuyện, biên kịch và kiểm tra. Cần chạy mẫu sản phẩm thật để đánh giá độ đúng/đa dạng |
| Không bao giờ lặp kịch bản | Không nên cam kết tuyệt đối | So sánh văn bản gần trùng chỉ phát hiện được một phần; ý giống nhau có thể diễn đạt khác |
| Sinh video người cầm sản phẩm như clip tham chiếu | Khả thi có điều kiện; chưa tích hợp | Cần API sinh video, ảnh tham chiếu, kiểm tra độ đúng logo/hình dáng và chi phí; FFmpeg hiện dựng ảnh có giọng đọc |
| Đăng Facebook Page tự động | Có adapter; chưa xác minh dịch vụ thật | Cần token/Page/quyền hợp lệ và kiểm tra sau khi nền tảng xử lý. API nhận video chưa đồng nghĩa đã đăng thành công |
| Hiệu quả kinh doanh | Chưa có dữ liệu | Phải đo chi phí/video, lượt nhấp, đơn được ghi nhận, hoa hồng và hoàn/hủy đơn |

**Kết luận:** có thể phát triển và thử nghiệm dự án. Chưa có cơ sở gọi phiên bản hiện tại là công cụ tự động hoàn toàn đã sẵn sàng vận hành hoặc có lợi nhuận.

### Phản biện các hướng đang có

1. **“AI kiểm tra độc lập”**: một lượt gọi riêng có thể vẫn dùng cùng model/nhà cung cấp, nên lỗi có thể tương quan. Cách diễn đạt chính xác là “kiểm tra ở lượt gọi riêng”. Trích dẫn tồn tại trong trang bán hàng cũng không chứng minh tuyên bố của người bán là đúng. Giữ bước kiểm tra, nhưng không dùng nó để cam kết mọi nội dung đã được xác thực.
2. **“Mỗi sản phẩm một kịch bản riêng”**: cần xét khác biệt góc và câu chuyện, không chỉ đổi tên. Phát hiện được một lỗi cụ thể: bộ chọn góc trước đây so câu mở đầu nguyên văn, trong khi bước ghi lịch sử lại bỏ tên sản phẩm. Hai bước có thể bất đồng và tốn thêm lượt viết/kiểm tra rồi mới bị từ chối.
3. **Đa luồng**: tăng số worker không khắc phục việc nguồn Shopee từ chối truy cập, không tạo thêm quota AI, không chứng minh API trả phí hoạt động. Giữ mặc định hai worker; mở rộng sau khi đo RAM/CPU, giới hạn API và phí.
4. **Tự động đăng ngay**: phù hợp sau khi đã chạy thử và xem đầu ra thật. Hiện để mặc định tắt; khi người dùng đã cấu hình bật, giữ hành vi tự động mà không hỏi lại từng sản phẩm. Không tự retry upload không rõ kết quả vì có thể tạo bài trùng.
5. **Chạy trên loopback**: bind `127.0.0.1` chưa đủ chống DNS rebinding. Host/Origin của một miền ngoài có thể trùng nhau và vượt kiểm tra Origin cũ. Cần xác nhận Host và cổng thực tế trước khi trả dữ liệu hoặc khởi chạy AI trả phí.

### Sửa trực tiếp trong lượt này

- `storyboard.py`: dùng chung chuẩn hóa tên sản phẩm khi lọc hook ở bước đạo diễn và khi ghi lịch sử. Mục đích là loại phương án gần trùng sớm, giảm khả năng tốn lượt AI rồi mới bị từ chối. Không tự gọi lại AI.
- `app.py`: từ chối HTTP Host ngoài `localhost`/`127.0.0.1`, sai cổng, nhiều Host hoặc authority không hợp lệ trên cả GET/POST. Kiểm tra Origin vẫn giữ. Đây là bảo vệ cho app cục bộ, không thay thế đăng nhập khi triển khai công khai.
- `tests/test_storyboard.py`: bổ sung ca thay tên sản phẩm phải bị loại ngay khi chọn góc.
- `tests/test_flow.py`: kiểm tra Host giả mạo/sai cổng; đưa dữ liệu kiểm thử video vào thư mục tạm để không thêm video giả vào lịch sử runtime thực tế.
- `.gitignore`: bổ sung mẫu tệp môi trường và SQLite nhằm giảm khả năng commit nhầm khóa/lịch sử.
- `AGENTS.md`: lưu quy ước đọc và cập nhật note chung theo yêu cầu người dùng.
- `README.md`, `docs/storyboard-flow.md`: liên kết note chung và sửa cách mô tả bước AI kiểm tra.

### Kiểm chứng và điều kiện còn thiếu

- Đã chạy `.venv/bin/python -m unittest discover -s tests -v`: **33 kiểm thử đạt**, không có kiểm thử bỏ qua trong lần này. Có chạy Chromium cho giao diện và FFmpeg cho MP4; phản hồi Shopee/OpenAI/Facebook vẫn giả lập.
- Đã kiểm tra `.env`, `.env.local`, runtime, virtualenv và SQLite đều được Git bỏ qua. Kết quả kiểm thử không chứng minh chất lượng AI thật.
- Repository chưa có remote refs tại thời điểm kiểm tra cuối trước commit; chuẩn bị commit đầu tiên trên `main`, gồm mã app đã làm trong cuộc trò chuyện và bản phản biện/sửa lỗi hiện tại.
- Bằng chứng trước đó: link quạt GOOJODOQ shop `1053077389`, item `25176208160` bị proxy chặn CONNECT 403. Chưa có khóa AI hoặc kết nối Facebook được xác minh. Chưa tạo video thật của sản phẩm này.
- Việc cần làm tiếp theo theo thứ tự: xác minh nguồn sản phẩm thật → chạy kịch bản trên nhiều nhóm sản phẩm → đo phí và chất lượng → chọn/tích hợp dịch vụ sinh cảnh video → kiểm chứng đăng một Page thử nghiệm → đo hiệu quả affiliate. Không đóng gói ở giai đoạn này.

## Mẫu ghi chú cho các lần tiếp theo

- Ngày và mục tiêu.
- Note/quyết định đã đọc; điểm đồng ý hoặc phản biện, kèm lý do.
- Những tệp/hành vi thực sự đã sửa.
- Kiểm thử đã chạy, kết quả đạt/lỗi/bỏ qua và bằng chứng dịch vụ thật nếu có.
- Điều kiện còn thiếu, tác động tới người dùng và bước tiếp theo.
