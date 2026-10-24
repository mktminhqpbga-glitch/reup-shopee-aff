"""Optional Facebook Page video publishing, enabled by explicit saved configuration."""
import json
import os
import re
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from automation import PipelineError


def settings():
    page = os.environ.get('FB_PAGE_ID', '').strip()
    return {'configured': bool(re.fullmatch(r'\d+', page) and os.environ.get('FB_PAGE_ACCESS_TOKEN', '').strip()),
            'auto_publish': os.environ.get('FB_AUTO_PUBLISH', '').lower() == 'true'}


def publish_video(video, title, caption):
    if not settings()['configured']:
        raise PipelineError('FACEBOOK_NOT_CONFIGURED',
                            'Chưa kết nối Facebook Page. Thêm FB_PAGE_ID và FB_PAGE_ACCESS_TOKEN trong cài đặt.')
    version = os.environ.get('FB_GRAPH_VERSION', 'v23.0')
    if not re.fullmatch(r'v\d+\.\d+', version):
        raise PipelineError('FACEBOOK_VERSION_INVALID', 'Phiên bản Facebook Graph API không hợp lệ.')
    if video.stat().st_size > 128 * 1024 * 1024:
        raise PipelineError('FACEBOOK_VIDEO_TOO_LARGE', 'Video vượt giới hạn tải lên 128 MB của app. Video vẫn có thể tải về.')
    boundary = 'affiliate-' + uuid.uuid4().hex
    chunks = []
    for field, text in [('title', title), ('description', caption), ('published', 'true')]:
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{text}\r\n').encode())
    chunks.extend([(f'--{boundary}\r\nContent-Disposition: form-data; name="source"; filename="video.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode(),
                   video.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
    request = Request(f"https://graph-video.facebook.com/{version}/{os.environ['FB_PAGE_ID'].strip()}/videos",
                      data=b''.join(chunks), headers={
                          'Authorization': 'Bearer ' + os.environ['FB_PAGE_ACCESS_TOKEN'],
                          'Content-Type': f'multipart/form-data; boundary={boundary}'})
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with build_opener(NoRedirect()).open(request, timeout=120) as response:
            result = json.loads(response.read(1024 * 1024))
        video_id = str(result.get('id', ''))
        if not re.fullmatch(r'\d+', video_id):
            raise ValueError()
        return {'status': 'submitted', 'video_id': video_id,
                'url': 'https://www.facebook.com/watch/?v=' + video_id,
                'message': 'Facebook đã nhận video; nền tảng có thể cần thêm thời gian xử lý.'}
    except HTTPError as error:
        raise PipelineError('FACEBOOK_HTTP_ERROR',
                            f'Facebook trả về HTTP {error.code}. Kiểm tra token Page, quyền đăng video và phiên bản API. '
                            'Không tự thử đăng lại để tránh bài trùng.') from None
    except (URLError, TimeoutError, OSError):
        raise PipelineError('FACEBOOK_UPLOAD_UNCERTAIN',
                            'Kết nối Facebook gián đoạn. Chưa xác định nền tảng đã nhận video hay chưa; '
                            'kiểm tra Page trước khi tạo lại để tránh bài trùng.') from None
    except (ValueError, TypeError, AttributeError):
        raise PipelineError('FACEBOOK_RESPONSE_INVALID',
                            'Facebook chưa trả về mã video hợp lệ. Kiểm tra Page trước khi thử đăng lại.') from None
