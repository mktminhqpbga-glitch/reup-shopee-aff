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
- Đã tạo và đẩy commit đầu tiên `fd13800` lên `main`, gồm mã app đã làm trong cuộc trò chuyện và bản phản biện/sửa lỗi hiện tại. Đã đọc lại remote ref để xác minh SHA trùng local; bản cập nhật note xác nhận kết quả được lưu trong commit kế tiếp.
- Đã khởi động lại app với bản sửa: `/api/health` trả thành công cho địa chỉ cục bộ, yêu cầu GET với `Host: attacker.example` trả HTTP 403. Trạng thái AI/Facebook vẫn là chưa cấu hình; không gọi dịch vụ trả phí hoặc đăng bài thật trong lượt này.
- Bằng chứng trước đó: link quạt GOOJODOQ shop `1053077389`, item `25176208160` bị proxy chặn CONNECT 403. Chưa có khóa AI hoặc kết nối Facebook được xác minh. Chưa tạo video thật của sản phẩm này.
- Việc cần làm tiếp theo theo thứ tự: xác minh nguồn sản phẩm thật → chạy kịch bản trên nhiều nhóm sản phẩm → đo phí và chất lượng → chọn/tích hợp dịch vụ sinh cảnh video → kiểm chứng đăng một Page thử nghiệm → đo hiệu quả affiliate. Không đóng gói ở giai đoạn này.

## 2026-10-24 — Bổ sung phản biện về sản phẩm và cách thử nghiệm

**Đã đọc lại:** note chung, quy ước trong `AGENTS.md`, bộ chọn góc/hạn chế chống trùng, API nhận batch và adapter Facebook. Đã fetch `main` trước khi sửa; local và remote không lệch commit.

**Phạm vi lượt này:** ghi đề xuất và tiêu chí kiểm chứng theo câu hỏi của người dùng. Chỉ thay đổi tài liệu; các đề xuất dưới đây chưa được coi là chức năng đã triển khai.

### 1. Một sản phẩm cần nhiều góc để học, không cần chốt một kịch bản duy nhất

- Mục tiêu nên là “kịch bản phù hợp sản phẩm và tạo được kết quả”, thay vì chỉ “mỗi sản phẩm một bản khác nhau”. Tính mới về câu chữ chưa chứng minh người xem muốn bấm link hoặc mua.
- Đề xuất: giữ mỗi bản video có một góc rõ ràng, thử hai góc cho cùng một sản phẩm: ví dụ tình huống sử dụng và soi chi tiết. Chỉ thay một yếu tố chính khi so sánh, ghi thời điểm/tệp/ngữ cảnh đăng để tránh kết luận từ các bài có điều kiện quá khác nhau.
- Chống trùng hiện là lọc tương đồng văn bản; có thể từ chối một câu mở đầu hợp lệ của sản phẩm khác và cũng có thể bỏ sót diễn đạt khác nhưng cùng ý. Cần đo cả từ chối nhầm và bỏ sót trên dữ liệu thật trước khi chỉnh ngưỡng. Không bỏ cơ chế chống sao chép nguyên bản chỉ để tăng tỷ lệ hoàn tất.

### 2. Cần giới hạn chi phí và ghi nhận sử dụng trước khi tăng batch

- Bằng chứng mã hiện tại: mỗi video hoàn tất luồng dùng 4 lượt biên tập AI và 3–5 lượt TTS, tức 7–9 lượt gọi; chưa bao gồm dịch vụ sinh cảnh video. Một lượt 10 video có thể có 70–90 lượt gọi. Đây là đếm lệnh, không phải dự báo số tiền; phí phụ thuộc token, ký tự/âm thanh, model và bảng giá tại thời điểm dùng.
- Đề xuất ưu tiên: hiển thị số video sau khi nhân link × kiểu trước khi gửi, cho phép đặt trần ngân sách/số video và ghi token/âm thanh/chi phí thực tế theo tác vụ. Cần định nghĩa rõ khi nhà cung cấp không trả usage: ghi “chưa biết”, không ghi 0 đồng.
- Worker limit hiện chỉ giới hạn đồng thời, không giới hạn tổng tiền. Chưa triển khai trần tiền hoặc bộ đo chi phí.

### 3. Tự động hóa toàn luồng vẫn nên giữ ảnh sản phẩm gốc

- Các cảnh cần đúng logo, hình dáng, màu và nhãn nên dùng ảnh sản phẩm gốc; AI có thể tạo bối cảnh/cảnh bổ trợ và điều phối biên tập. Đây vẫn là một luồng người dùng chỉ đưa link.
- Khi thêm dịch vụ sinh video, cần kiểm tra từng cảnh với ảnh tham chiếu và loại cảnh sai sản phẩm. Chưa có cơ sở hứa “video nào cũng giữ đúng sản phẩm”, nhất là đồ có chữ nhỏ, bộ phận chuyển động hoặc nhiều biến thể.
- Đề xuất: bắt đầu với một nhà cung cấp, một định dạng dọc và một nhóm hàng dễ kiểm chứng; chưa mở rộng ngay sang mọi ngành hàng hoặc mọi nền tảng.

### 4. Cần dữ liệu truy vết và điều kiện hoàn tất rõ ràng

- Nên lưu phiên bản prompt, model thực tế, thời điểm lấy nguồn, bản chụp dữ liệu nguồn, hash nội dung và mã yêu cầu nhà cung cấp (không lưu token). Khi giá/mô tả hoặc model thay đổi, những dữ liệu này giúp giải thích vì sao hai lần tạo khác nhau. Hiện đã lưu sản phẩm/storyboard, nhưng chưa có bộ thông tin truy vết đầy đủ này.
- Facebook trả ID mới có nghĩa là nhận upload. Bước tiếp theo cần phân biệt “đã nhận”, “đang xử lý”, “đã hiển thị”, “lỗi”; chưa có polling/đối soát sau upload.
- Link affiliate đang được giữ nguyên. Không nên tự thêm hoặc thay tham số tracking khi chưa có quy tắc được nền tảng hỗ trợ; cần đối chiếu đơn/hoa hồng từ dữ liệu affiliate thật, không lấy lượt xem làm thay thế.

### 5. Tận dụng dữ liệu chung khi tạo nhiều phiên bản

- Hiện các tác vụ phiên bản có thể cùng tải lại nguồn/ảnh và lập hồ sơ cho một sản phẩm. Khi nguồn ổn định và đã xác minh, có thể dùng chung snapshot nguồn/ảnh/hồ sơ trong một batch; góc, lời đọc và storyboard vẫn riêng.
- Cache phải dựa trên danh tính sản phẩm, nội dung nguồn và phiên bản model/prompt; có thời hạn, không làm mất link tracking riêng của từng tác vụ. Chưa triển khai cache dùng chung hoặc gộp các yêu cầu đang chạy.

### Ưu tiên thực hiện và cách quyết định tiếp

1. Giải quyết truy cập nguồn thật và khóa dịch vụ; chưa có điều kiện này thì không dùng kiểm thử giả lập để kết luận hiệu quả sản phẩm.
2. Chạy thử 3 sản phẩm, mỗi sản phẩm 2 góc: 6 video. Theo mã hiện tại, dự kiến 42–54 lượt gọi AI/TTS nếu đều chạy đủ các bước, chưa tính sinh cảnh video. Đây là kế hoạch đề xuất, chưa thực hiện và chưa phát sinh phí trong lượt này.
3. Ghi đủ: dữ liệu đúng/sai, số lần bị từ chối nhầm, cảnh lỗi, thời gian, phí thực tế và số video dùng được. Tính phí trên **video dùng được**, gồm cả chi phí của các lần thất bại.
4. Khi đăng thử có đủ dữ liệu, theo dõi lượt xem đủ lâu, lượt nhấp, đơn được ghi nhận và hoa hồng sau hoàn/hủy. Thử 6 video chỉ giúp phát hiện lỗi ban đầu, chưa đủ chứng minh lợi nhuận hoặc góc nào luôn tốt hơn.
5. Đạt điều kiện chất lượng/chi phí đã thống nhất rồi mới tăng worker, batch và nền tảng.

**Kiểm tra lượt này:** chỉ sửa `NOTES.md`, kiểm tra diff/định dạng và đồng bộ Git. Không chạy lại bộ kiểm thử ứng dụng vì không thay mã; không gọi AI trả phí, không sinh video và không đăng bài thật.

## Mẫu ghi chú cho các lần tiếp theo

- Ngày và mục tiêu.
- Note/quyết định đã đọc; điểm đồng ý hoặc phản biện, kèm lý do.
- Những tệp/hành vi thực sự đã sửa.
- Kiểm thử đã chạy, kết quả đạt/lỗi/bỏ qua và bằng chứng dịch vụ thật nếu có.
- Điều kiện còn thiếu, tác động tới người dùng và bước tiếp theo.
