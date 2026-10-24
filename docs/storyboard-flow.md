# Luồng kịch bản riêng cho từng sản phẩm

1. **Nguồn**: lấy tên, mô tả và các ảnh tải được. Danh tính sản phẩm dựa trên shop/item Shopee, không phụ thuộc query tracking; link affiliate gốc vẫn giữ trong bài đăng.
2. **Hồ sơ**: AI phân loại sản phẩm, đề xuất khách hàng/nhu cầu, liệt kê thông tin chưa biết và trích nguyên văn dữ kiện. Chương trình kiểm tra trích dẫn có tồn tại trong tên/mô tả; dữ kiện được đánh ID F0, F1… Khách hàng và nhu cầu chỉ là giả thuyết biên tập.
3. **Đạo diễn**: AI đọc hồ sơ và lịch sử, đưa ba góc nội dung có câu mở đầu, bối cảnh, lý do, dữ kiện hỗ trợ, điểm phù hợp và điểm dễ thể hiện. Chương trình loại câu mở đầu gần trùng, chọn góc điểm cao nhất còn lại. Điểm là đánh giá của model, không phải đo lường khách quan.
4. **Biên kịch**: AI viết 3–5 cảnh theo góc đã chọn. Mỗi cảnh có lời đọc, prompt hình ảnh, ảnh tham chiếu, thời lượng dự kiến và ID dữ kiện. Câu mở đầu phải khớp góc chọn, cảnh kết công bố affiliate. Kiểm tra kiểu dữ liệu, độ dài, chỉ số ảnh và ID nguồn trước khi tiếp tục.
5. **Kiểm tra ở lượt gọi riêng**: một lượt gọi AI khác so từng cảnh với hồ sơ, kiểm tra cả lời đọc và chỉ dẫn hình ảnh. Bắt buộc báo đã đọc đủ tất cả cảnh. Nội dung không được chấp thuận sẽ dừng, giữ lý do trong giao diện, chưa gọi giọng đọc hoặc đăng bài.
6. **Lịch sử**: SQLite lưu câu mở đầu, góc, bối cảnh và lời đọc. Trước khi chấp nhận kịch bản, giao dịch khóa ghi kiểm tra lại để hai worker không đồng thời chấp nhận bản trùng. So sánh gần trùng câu mở đầu và lời đọc, có bỏ tên sản phẩm để phát hiện chỉ thay tên. Xem tối đa 200 bản gần nhất ở bước lưu; đây là phát hiện tương đồng văn bản, không bảo đảm mọi ý tưởng đều mới.
7. **Đầu ra**: tạo giọng đọc, đo thời lượng, dựng ảnh và chữ; giữ storyboard JSON để xem/tải. Đăng Facebook chỉ khi đã kết nối và bật tự đăng.

## Ranh giới kiểm tra

Trích dẫn tồn tại trong nguồn không chứng minh nội dung nguồn chính xác. AI kiểm tra có thể bỏ sót suy diễn, và một lượt gọi riêng vẫn có thể dùng cùng model. Cần xem lại nội dung trước khi vận hành đăng tự động, nhất là sản phẩm có tuyên bố sức khỏe.

Không tạo người dẫn hoặc cảnh video từ prompt trong phiên bản này. Chưa so sánh chất lượng kịch bản với model thật vì chưa có khóa AI được cấp. Kiểm thử dùng phản hồi giả lập có chủ đích để kiểm tra luồng, dẫn nguồn, từ chối, lịch sử và tranh chấp giữa worker; không chứng minh chất lượng biên tập của AI thực tế.
