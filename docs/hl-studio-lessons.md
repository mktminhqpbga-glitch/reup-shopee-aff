# Bài học tích hợp từ HL Studio — chỉ ý tưởng, không sao chép

> Nguồn: phân tích tĩnh file `_ban-ban.rar` (749,4 MB, HL Studio, app Windows
> làm video sản phẩm + phim hoạt hình bằng AI) ngày 2026-10-24.
> Tài liệu này chỉ ghi **ý tưởng, kiến trúc và luồng sản phẩm** học được.
> Không sao chép code, model, giọng đọc, tài nguyên, thương hiệu hay cơ chế
> bản quyền của HL Studio vào repo này. Không phân tích, không trích, không
> tìm cách vượt qua trial / chữ mờ / khóa theo máy của app đó.

## 1. Kiến trúc đáng học: vỏ desktop mỏng + server local

- HL Studio: vỏ .NET WebView2 chỉ mở cửa sổ, tự chạy `server.py` bằng Python
  trên loopback với cổng ngẫu nhiên, đóng cửa sổ là tắt server.
- Affiliate Studio hiện tại đã là server Python chạy local, giao diện web.
  Vì vậy hướng tích hợp không phải viết lại app, mà là **bọc app hiện tại
  thành dạng dùng được trong 1 lần bấm**, theo thứ tự:
  1. Script khởi động duy nhất: kiểm tra Python, kiểm tra FFmpeg, chọn cổng
     trống, mở trình duyệt/cửa sổ, tắt server khi đóng app.
  2. Chỉ sau khi bước 1 chạy ổn trên máy người dùng thật mới tính tới vỏ
     desktop riêng (WebView2 hoặc tương đương). Vỏ desktop là công việc lớn,
     Windows-only, không làm trong lượt tích hợp tài liệu này.

## 2. Luồng sản phẩm: một luồng, không nhiều tool rời

- HL Studio: ảnh sản phẩm → thông tin → AI viết kịch bản → giọng đọc →
  dựng bằng FFmpeg → xuất. Xung quanh luồng chính chỉ gắn đúng thứ người
  bán cần: lưu project, thương hiệu mặc định, caption, xoay 360°, hộp 3D,
  nhạc nền, phim hoạt hình, video bảng trắng.
- Đối chiếu với Affiliate Studio (theo mã hiện tại, chưa kiểm chứng lại
  toàn bộ giao diện):
  - Đã có dạng tương tự: link → hồ sơ/kịch bản → giọng đọc → video dọc,
    cùng các API project, brand-default, caption, spin trong `app.py`.
  - Vì vậy không cần thêm tính năng mới chỉ vì HL có. Việc cần làm là
    **làm cho luồng hiện tại chạy trơn từ đầu tới cuối trên 1 sản phẩm thật**,
    trước khi thêm tính năng mới — đúng 3 cửa đã ghi trong `NOTES.md`:
    lấy được nguồn thật, video thật được duyệt, bài đăng thử hiển thị.

## 3. Giọng đọc: offline giảm chi phí dài hạn, tăng dung lượng

- HL Studio bundle giọng Việt chạy offline bên cạnh giọng online.
  Lợi: không trả phí API cho mỗi video, không sợ mất mạng giữa chừng.
  Hại: file 749 MB, phần lớn là model, FFmpeg và thư viện Windows.
- Áp dụng có chọn lọc cho repo này:
  - Không bundle model nặng vào repo. Repo giữ code nhẹ; model (nếu có)
    là tải riêng, có phiên bản, có kiểm chứng.
  - Ưu tiên trước: đo chi phí thực tế mỗi video (đã ghi trong note trước),
    rồi mới quyết có đáng đổi sang giọng offline hay không.
  - Lưu ý riêng cho thị trường của người dùng: giọng Việt offline không
    tự động giải quyết giọng Khmer/Thái. Không hứa giọng offline đa ngôn ngữ
    khi chưa có model và kiểm chứng nghe thử.

## 4. Cài đặt 1 lần là chạy: giảm ma sát cho người không rành kỹ thuật

- HL Studio: một file cài đặt làm hết — tạo Python riêng cho app, cài
  FFmpeg, cài giọng, tạo shortcut Desktop.
- Tích hợp vào repo này ở mức tài liệu trước, code sau:
  - `README.md` phải có đúng 1 đường chạy chính, từng bước, không để người
    dùng phải đoán cổng, đường dẫn hay lệnh.
  - `.env.example` đã có (chỉ tên biến, không khóa) là một phần của việc này.
  - Script cài đặt tự động cho Windows là công việc riêng, cần test trên
    máy thật, không viết vội trong lượt này.

## 5. Mô hình chi phí: tách tiền app khỏi tiền AI

- HL Studio: tiền app (trial + khóa theo máy) tách khỏi tiền AI
  (người dùng tự dán key của mình). Nhà phát triển không gánh phí AI
  cho mỗi video người dùng tạo.
- Repo này đã theo hướng tương tự: key AI/Facebook qua biến môi trường,
  không lưu trong code. Giữ nguyên nguyên tắc đó. Không đưa key mẫu,
  key thật hay cơ chế khóa máy vào repo.

## 6. Những điểm không học theo

- Bundle tất cả: trùng FFmpeg, trùng thư mục build, kèm cả thư mục `obj/`
  lúc build — nặng và khó bảo trì.
- Phụ thuộc chéo: tìm Python của một app khác khi không thấy Python của
  mình — dễ gãy khi app kia bị xóa.
- Module chỉ có `.pyc`, không có source — sau này chính tác giả sửa cũng khó.
- Windows-only: wheel, exe, WebView2 đều cho Windows, không có đường
  sang hệ điều hành khác.
- Bật sẵn DevTools, tự cho phép micro trong vỏ app — tiện cho dev,
  nhưng không phải mặc định nên mang sang bản cho người dùng cuối
  mà không rà soát lại quyền.

## 7. Danh sách tích hợp — trạng thái

| Bài học | Trạng thái trong repo này |
| --- | --- |
| Tài liệu bài học này (`docs/hl-studio-lessons.md`) | Đã thêm trong lượt này |
| Ghi vào `NOTES.md` + liên kết từ `README.md` | Đã thêm trong lượt này |
| Luồng link → kịch bản → giọng → video → đăng (đã có) | Giữ nguyên, ưu tiên chạy thật 1 sản phẩm trước |
| Project / brand / caption / spin (đã có API trong `app.py`) | Không thêm mới vì lý do HL có; kiểm chứng giao diện sau |
| Script khởi động 1 lần + vỏ desktop | Chưa làm — cần test máy thật, làm riêng |
| Giọng offline bundle sẵn | Chưa làm — đo chi phí trước, không bundle model nặng vào repo |
| Cơ chế trial / khóa máy kiểu HL | Không làm — repo này là tool của chủ repo, không bán app |

## 8. Ranh giới

- Học ý tưởng và kiến trúc là được. Sao chép code, model, giọng, ảnh,
  thương hiệu, hoặc bẻ khóa bản quyền là không được.
- Mọi tính năng mới sau tài liệu này vẫn phải qua 3 cửa trong `NOTES.md`
  và phải có kiểm thử / kiểm chứng thật, không chỉ vì “HL có tính năng đó”.
