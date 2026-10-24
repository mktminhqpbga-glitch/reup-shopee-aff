# Affiliate Studio — Một link, một video

Đọc [note chung của repo](NOTES.md) để xem thay đổi, phản biện, đánh giá khả thi và bằng chứng kiểm thử. Người sửa mã đọc [AGENTS.md](AGENTS.md) trước khi làm.

App web tiếng Việt nhận **một link affiliate Shopee**, tự đọc dữ liệu công khai, tải ảnh, viết kịch bản AI, tạo giọng đọc và dựng MP4 dọc. Có thể tự gửi video lên Facebook Page sau khi cấu hình kết nối một lần. Chưa đóng gói desktop.

## Sử dụng

1. Dán link affiliate Shopee Việt Nam (`shopee.vn`, `s.shopee.vn`, `shp.ee`, `vn.shp.ee`).
2. Bấm **Tự động tạo video**. Không nhập tên, mô tả, kịch bản hoặc tải ảnh thủ công.
3. App mở link, đọc tên/mô tả/ảnh công khai, tải ảnh, gọi OpenAI lập hồ sơ, chọn góc kể chuyện, viết 3–5 cảnh và kiểm tra ở lượt gọi riêng; sau đó tạo lời đọc tiếng Việt và ghép video.
4. Nếu đã kết nối Page và bật tự đăng, app gửi MP4 và nội dung bài đăng lên Facebook; nếu chưa bật, kết quả vẫn tải xuống được.
5. Xem video, tải MP4, sao chép nội dung hoặc mở kết quả đã lưu trong danh sách gần đây.

Link gốc được giữ nguyên trong bài đăng. App không tự tạo link affiliate, không xác minh hoa hồng và không đổi link sản phẩm thường thành link affiliate. Không tự dùng lại link sản phẩm đã mở thay cho link tracking ban đầu.

## Kết nối một lần

Cấu hình trong **cài đặt môi trường**, không nhập khóa vào ô link hoặc đưa khóa vào mã nguồn. App không đọc tệp `.env`; các giá trị phải được đưa vào biến môi trường của tiến trình. Sau khi lưu cấu hình cần khởi động lại app để nhận biến mới. Không in giá trị khóa khi kiểm tra.

| Biến | Công dụng | Mặc định |
| --- | --- | --- |
| `AI_API_KEY` | Khóa OpenAI, cần cho kịch bản và giọng đọc | Chưa có |
| `AI_TEXT_MODEL` | Model cho Chat Completions có JSON mode | `gpt-4o-mini` |
| `AI_TTS_MODEL` | Model Text to Speech | `gpt-4o-mini-tts` |
| `AI_VOICE` | Giọng đọc được model hỗ trợ | `coral` |
| `FB_PAGE_ID` | ID Facebook Page, chỉ gồm chữ số | Chưa có |
| `FB_PAGE_ACCESS_TOKEN` | Page access token được cấp quyền đăng video | Chưa có |
| `FB_AUTO_PUBLISH` | Đặt `true` để tự đăng mỗi video tạo từ link | `false` |
| `FB_GRAPH_VERSION` | Phiên bản Graph API còn được hỗ trợ | `v23.0` |
| `PORT` | Cổng máy chủ | `8000` |

Tự đăng dùng Page Video API (`POST /{page-id}/videos`), không phải luồng Facebook Reels hay trang cá nhân. Cần Meta app/Page token hợp lệ và các quyền theo yêu cầu của Meta (thường gồm `pages_manage_posts`, `pages_read_engagement`, cùng quyền liệt kê Page nếu dùng OAuth). Bản này chưa có giao diện OAuth, gia hạn token hoặc kiểm tra trạng thái xử lý video trên Facebook. Kết quả `submitted` nghĩa là Facebook trả về ID video, chưa chứng minh video đã xử lý xong hoặc đã hiển thị công khai.

Khi `FB_AUTO_PUBLISH=true`, app tự gửi video sau khi dựng xong, không hỏi lại từng sản phẩm. Chưa có tài khoản thì để tắt. Không tự thử tải lên lần nữa nếu Facebook trả lỗi hoặc kết nối gián đoạn, tránh bài trùng. Video đã dựng vẫn tải được khi đăng lỗi. Nếu app dừng lúc đang gửi Facebook, cần kiểm tra Page trước khi tạo lại.

Các miền cần truy cập:

- `shopee.vn`, `*.shopee.vn`, `shp.ee`, `*.shp.ee`: mở link và trang sản phẩm.
- `*.susercontent.com`: ảnh Shopee; ảnh từ miền khác bị từ chối.
- `api.openai.com`: tên/mô tả được gửi để viết kịch bản, lời đọc được gửi để tạo âm thanh.
- `graph-video.facebook.com`: gửi MP4 và nội dung nếu đã bật tự đăng.

Mỗi lần tạo gọi API có thể phát sinh phí. Không tự chạy lại các tác vụ đang dở sau khi khởi động lại.

## Chạy môi trường phát triển

Yêu cầu Python 3.12+, FFmpeg/ffprobe có libx264, font DejaVu Sans (Linux).

```bash
cd /workspace/reup-shopee-aff
python -m venv .venv --system-site-packages
.venv/bin/python -m pip install --cache-dir /tmp/affiliate-pip-cache -r requirements.txt
.venv/bin/python app.py
```

Máy chủ chỉ lắng nghe loopback. Dừng bằng Ctrl+C. Mỗi cloud task đã cô lập; dùng checkout sẵn có, không cần tạo worktree. Không triển khai công khai bản này: chưa có đăng nhập và hạn ngạch lưu trữ.

## Cách xử lý dữ liệu và giới hạn

- Chỉ đọc HTML công khai theo redirect hợp lệ, JSON-LD Product hoặc Open Graph; không dùng API Shopee nội bộ, cookie đăng nhập hay vượt CAPTCHA. Khi trang cần JavaScript, chặn đọc hoặc thiếu metadata, app dừng và báo nguyên nhân. Muốn hỗ trợ các trường hợp đó cần tích hợp thêm nguồn dữ liệu Shopee được cấp quyền.
- Link và mọi redirect phải thuộc miền Shopee cho phép; ảnh chỉ lấy từ CDN cho phép. Không tải URL tùy ý, địa chỉ nội bộ hoặc chuyển tiếp khóa API sang miền khác. TLS verification được giữ nguyên.
- Video 720×1280, 24 fps, ảnh tĩnh chuyển cảnh nhẹ, chữ tiếng Việt và giọng AI. Thời lượng từng cảnh theo âm thanh thật, tối đa 3 phút/video. Chưa có tách nền hoặc video sinh bằng AI.
- Kịch bản chỉ được yêu cầu sử dụng tên/mô tả nguồn, không tạo trải nghiệm đã dùng, giá, khuyến mãi hoặc lời cam kết không có căn cứ. Tuy nhiên nội dung AI vẫn cần kiểm tra, nhất là trước khi bật đăng tự động.
- Ảnh cảnh, giọng đọc, MP4, ảnh bìa, kịch bản, link và trạng thái lưu tại `.runtime/<id>/`. Khóa không được lưu vào đó. Danh sách hiển thị tối đa 100 tác vụ gần đây; tác vụ hoàn tất có thể mở lại sau khi khởi động lại.
- Mặc định 2 tác vụ xử lý đồng thời, `VIDEO_WORKERS` cho phép 1–4 sau khi khởi động lại, tối đa 50 tác vụ chờ/chạy. Mục “Chạy hàng loạt / nhiều phiên bản” cho phép 20 link × 1–3 kiểu (tổng lượt không vượt sức chứa còn lại). Tạm dừng chỉ dừng nhận việc mới; tác vụ đang chạy hủy sau bước hiện tại. Chưa có tự dọn dữ liệu; xóa thư mục tác vụ không còn dùng khi app đã dừng để giải phóng dung lượng.
- Giao diện chính chỉ có một ô link. API `/api/render` thủ công được giữ để tương thích và kiểm thử; không xuất hiện trong UI.
- Chưa hỗ trợ tự đăng TikTok, YouTube hoặc Instagram.

## Kiểm thử

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Các kiểm thử dùng HTTP server, parser và FFmpeg thật; xác nhận MP4 9:16, thời lượng theo âm thanh, đường tiếng không im lặng, tải theo byte range, lưu trạng thái, phản hồi lỗi nguồn, thiếu AI và không tự đăng trùng sau gián đoạn.

**Phản hồi Shopee, OpenAI và Facebook trong kiểm thử được giả lập. Âm thanh fixture là tiếng tone, không phải giọng AI thật. Kiểm thử không chứng minh kết nối các dịch vụ thật.** Kiểm thử trình duyệt dùng Playwright và `/usr/bin/chromium` nếu có; nếu thiếu sẽ được ghi nhận là skipped. Không cần Playwright để chạy app.

## Kết quả kiểm tra thực tế của môi trường này

Đã thử link người dùng cung cấp, shop `1053077389`, sản phẩm `25176208160` (quạt GOOJODOQ). Cấu trúc URL được nhận diện đúng nhưng proxy mạng từ chối kết nối tới Shopee với CONNECT 403. Chưa có khóa AI hoặc thông tin Facebook được cấp trong tiến trình, vì vậy **chưa xác minh được luồng dịch vụ thật và chưa tạo video thật của sản phẩm này**.

Đã lưu yêu cầu mạng và tên biến vào cấu hình nháp. Lưu/publish cấu hình không đồng nghĩa đã kiểm tra lại kết nối thành công. Sau khi người dùng cấp quyền mạng và khóa trong cài đặt, cần chạy lại bằng link thật, xem/nghe video và kiểm chứng bài đăng Facebook trước khi coi môi trường sẵn sàng cho luồng tự động đầy đủ.

## Tham chiếu cơ chế đa luồng

Xem [bóc tách video người dùng gửi](docs/reference-video.md) để phân biệt tính năng quan sát được, phần đã làm và phần sinh video người cầm sản phẩm chưa tích hợp.

## Kịch bản riêng theo sản phẩm

Xem [luồng biên tập AI](docs/storyboard-flow.md). Giao diện máy tính gồm ba cột: nhập link và hàng đợi, hồ sơ/kịch bản từng cảnh, video/bài đăng. Trên điện thoại các phần xếp dọc.

Mỗi video dùng 4 lượt gọi AI cho hồ sơ, đạo diễn, biên kịch và kiểm tra; sau đó 3–5 lượt tạo âm thanh. Kịch bản không hợp lệ hoặc quá giống lịch sử bị dừng trước giọng đọc, không tự gọi lại tính phí. Lịch sử chống trùng lưu trong `.runtime/story-history.sqlite3`, tách khỏi các thư mục tác vụ. Xóa thư mục video không xóa lịch sử này. Kịch bản đã qua kiểm tra được ghi vào lịch sử trước khi tạo giọng đọc, kể cả khi một bước phía sau thất bại.

Tải `storyboard.json` trong giao diện để lấy hồ sơ, ba góc đã cân nhắc, góc được chọn, từng cảnh có nguồn/ảnh tham chiếu, thời lượng dự kiến và kết quả kiểm tra. Thời gian thực tế từng cảnh hiển thị sau khi dựng, đo theo âm thanh. Chỉ dẫn hình ảnh đang phục vụ bước tích hợp sinh cảnh video sau này; FFmpeg hiện dựng ảnh tham chiếu với lời đọc, không tự diễn giải prompt thành cảnh người cầm sản phẩm.
