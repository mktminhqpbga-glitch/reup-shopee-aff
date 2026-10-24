"""One affiliate URL -> public product metadata -> AI narration -> MP4 inputs.

No private Shopee endpoints, browser cookies or CAPTCHA bypasses are used.
"""
import base64
from dataclasses import dataclass
from html.parser import HTMLParser
import io
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PIL import Image, ImageOps


class PipelineError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


PRODUCT_HOSTS = ('shopee.vn', 'shp.ee')
IMAGE_HOSTS = ('susercontent.com', 'shopee.vn')
PRODUCT_PATH = re.compile(r'(?:-i\.(\d+)\.(\d+)|/product/(\d+)/(\d+))(?:/|$)')


def check_url(url, hosts):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        if (parsed.scheme != 'https' or parsed.username or parsed.password
                or parsed.port not in (None, 443)
                or not any(host == domain or host.endswith('.' + domain) for domain in hosts)):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise PipelineError('INVALID_LINK', 'Chỉ nhận link HTTPS thuộc Shopee Việt Nam hoặc shp.ee.') from None
    return url


def validate_affiliate(url):
    if not isinstance(url, str) or not url.strip() or len(url) > 4096:
        raise PipelineError('INVALID_LINK', 'Hãy dán link affiliate Shopee hợp lệ.')
    return check_url(url.strip(), PRODUCT_HOSTS)


class CheckedRedirect(HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass
class Download:
    content: bytes
    url: str
    content_type: str


def fetch_public(url, hosts=PRODUCT_HOSTS, max_bytes=6 * 1024 * 1024):
    check_url(url, hosts)
    opener = build_opener(CheckedRedirect(hosts))
    try:
        with opener.open(Request(url, headers={'User-Agent': 'AffiliateStudio/0.3',
                                               'Accept-Language': 'vi-VN,vi;q=0.9'}), timeout=25) as response:
            check_url(response.url, hosts)
            content = response.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise PipelineError('SOURCE_TOO_LARGE', 'Dữ liệu nguồn vượt giới hạn cho phép.')
            return Download(content, response.url, response.headers.get_content_type())
    except HTTPError as error:
        if error.code in (401, 403, 429):
            raise PipelineError('SOURCE_BLOCKED',
                                'Không đọc được nguồn sản phẩm: bị từ chối truy cập hoặc giới hạn lượt đọc. '
                                'Kiểm tra quyền truy cập mạng và nguồn dữ liệu Shopee; app không vượt CAPTCHA hoặc đăng nhập.') from None
        raise PipelineError('SOURCE_HTTP_ERROR', f'Nguồn sản phẩm trả về HTTP {error.code}. Vui lòng thử lại sau.') from None
    except (URLError, TimeoutError, OSError):
        raise PipelineError('SOURCE_UNREACHABLE',
                            'Không kết nối được Shopee/CDN ảnh. Kiểm tra mạng và danh sách miền cho phép trong cài đặt môi trường.') from None


class ProductHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.documents = []
        self.recording = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key and attrs.get('content'):
                self.meta[key.lower()] = attrs['content']
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json':
            self.recording = True
            self.parts = []

    def handle_data(self, data):
        if self.recording:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.recording:
            try:
                self.documents.append(json.loads(''.join(self.parts)))
            except (ValueError, RecursionError):
                pass
            self.recording = False


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_text(value, limit):
    if not isinstance(value, str):
        return ''
    parser = PlainText()
    parser.feed(value[:20_000])
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()[:limit]


def find_product(document, depth=0):
    if depth > 20:
        return None
    if isinstance(document, list):
        return next((product for node in document if (product := find_product(node, depth+1))), None)
    if isinstance(document, dict):
        kind = document.get('@type', '')
        if kind == 'Product' or isinstance(kind, list) and 'Product' in kind:
            return document
        if '@graph' in document:
            return find_product(document['@graph'], depth+1)
    return None


def parse_product(download):
    path = urlparse(download.url).path
    if not PRODUCT_PATH.search(path):
        raise PipelineError('PRODUCT_NOT_RESOLVED',
                            'Link chưa mở tới một trang sản phẩm Shopee. Link có thể cần đăng nhập, đã hết hạn hoặc chỉ mở được trong app.')
    if download.content_type not in ('text/html', 'application/xhtml+xml'):
        raise PipelineError('SOURCE_FORMAT', 'Nguồn Shopee không trả về trang thông tin sản phẩm.')
    parser = ProductHTML()
    parser.feed(download.content.decode('utf-8', errors='replace'))
    product = next((node for doc in parser.documents if (node := find_product(doc))), {})
    title = clean_text(product.get('name') or parser.meta.get('og:title', ''), 160)
    title = re.sub(r'\s*[|\-]\s*Shopee(?: Việt Nam)?\s*$', '', title, flags=re.I).strip()
    if (not title or title.lower() in ('shopee', 'shopee việt nam')
            or re.search(r'captcha|access denied|đăng nhập|verify.*human', title, re.I)):
        raise PipelineError('PRODUCT_DATA_MISSING',
                            'Trang không cung cấp tên và ảnh sản phẩm công khai (có thể cần JavaScript, đăng nhập hoặc CAPTCHA). '
                            'Cần kết nối nguồn dữ liệu Shopee được cấp quyền; app không tự đoán thông tin.')
    description = clean_text(product.get('description') or parser.meta.get('og:description', ''), 4000)
    raw_images = product.get('image') or parser.meta.get('og:image', '')
    raw_images = raw_images if isinstance(raw_images, list) else [raw_images]
    images = []
    for raw in raw_images:
        raw = raw.get('url', '') if isinstance(raw, dict) else raw
        if not isinstance(raw, str):
            continue
        url = urljoin(download.url, raw)
        try:
            check_url(url, IMAGE_HOSTS)
        except PipelineError:
            continue
        if url not in images:
            images.append(url)
    if not images:
        raise PipelineError('PRODUCT_IMAGES_MISSING', 'Không tìm thấy ảnh sản phẩm công khai từ Shopee. Cần kiểm tra nguồn dữ liệu.')
    return {'title': title, 'description': description, 'image_urls': images[:5], 'source_url': download.url}


def load_product(affiliate, fetch=fetch_public):
    return parse_product(fetch(validate_affiliate(affiliate)))


def download_images(product, fetch=fetch_public):
    images = []
    available_urls = []
    for url in product['image_urls']:
        try:
            result = fetch(url, hosts=IMAGE_HOSTS, max_bytes=8 * 1024 * 1024)
            with Image.open(io.BytesIO(result.content)) as source:
                if source.width * source.height > 25_000_000:
                    continue
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((1600, 1600))
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=90)
                images.append('data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode())
                available_urls.append(url)
        except (PipelineError, OSError, ValueError, Image.DecompressionBombError):
            continue
    if not images:
        raise PipelineError('IMAGE_DOWNLOAD_FAILED', 'Không tải được ảnh sản phẩm hợp lệ. Kiểm tra quyền truy cập CDN ảnh Shopee.')
    product['image_urls'] = available_urls
    return images


def ai_settings():
    return {'configured': bool(os.environ.get('AI_API_KEY', '').strip()),
            'text_model': os.environ.get('AI_TEXT_MODEL', 'gpt-4o-mini'),
            'tts_model': os.environ.get('AI_TTS_MODEL', 'gpt-4o-mini-tts'),
            'voice': os.environ.get('AI_VOICE', 'coral')}


def require_ai():
    if not ai_settings()['configured']:
        raise PipelineError('AI_NOT_CONFIGURED',
                            'Cần kết nối dịch vụ AI một lần: thêm AI_API_KEY trong cài đặt môi trường, rồi khởi động lại app. '
                            'Không nhập khóa vào ô link hoặc gửi khóa trong chat.')


def ai_request(path, body, *, binary=False):
    require_ai()
    request = Request('https://api.openai.com/v1/' + path,
                      data=json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json',
                               'Authorization': 'Bearer ' + os.environ['AI_API_KEY']})
    # Do not follow redirects with an Authorization header.
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with build_opener(NoRedirect()).open(request, timeout=90) as response:
            data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise PipelineError('AI_RESPONSE_TOO_LARGE', 'Phản hồi AI vượt giới hạn cho phép.')
            if binary:
                return data
            return json.loads(data)
    except HTTPError as error:
        messages = {401: 'Khóa AI không hợp lệ hoặc chưa được cấp quyền.',
                    403: 'Dịch vụ AI hoặc chính sách mạng từ chối truy cập.',
                    429: 'Dịch vụ AI hết hạn mức hoặc đang giới hạn lượt gọi.'}
        raise PipelineError('AI_HTTP_ERROR', messages.get(error.code, f'Dịch vụ AI trả về HTTP {error.code}. Kiểm tra model và thử lại.')) from None
    except (URLError, TimeoutError, OSError):
        raise PipelineError('AI_UNREACHABLE', 'Không kết nối được dịch vụ AI. Kiểm tra mạng và quyền truy cập api.openai.com.') from None
    except (ValueError, TypeError):
        raise PipelineError('AI_RESPONSE_INVALID', 'Dịch vụ AI trả về dữ liệu không hợp lệ.') from None


STYLES = {
    'overview': 'Giới thiệu tổng quan, tên và đặc điểm có trong nguồn.',
    'details': 'Tập trung từng chi tiết sản phẩm được ghi trong nguồn; không giả vờ đã dùng.',
    'checklist': 'Danh sách thông tin nên kiểm tra trước khi mua, như biến thể và mô tả; không tự đoán câu trả lời.'
}


def generate_script(product, request=ai_request):
    # Compatibility for callers that only need the spoken lines.
    from storyboard import build_storyboard
    story = build_storyboard(product, request=request)
    return [scene['narration'] for scene in story['scenes']]


def synthesize_speech(scenes, folder, request=ai_request):
    paths = []
    settings = ai_settings()
    for index, scene in enumerate(scenes):
        body = {'model': settings['tts_model'], 'voice': settings['voice'],
                'input': scene, 'response_format': 'mp3'}
        if settings['tts_model'].startswith('gpt-4o-mini-tts'):
            body['instructions'] = 'Đọc tiếng Việt tự nhiên, rõ ràng, thân thiện; không đọc quá nhanh.'
        audio = request('audio/speech', body, binary=True)
        if not isinstance(audio, bytes) or len(audio) < 100:
            raise PipelineError('AI_AUDIO_INVALID', 'Dịch vụ giọng đọc trả về âm thanh không hợp lệ.')
        path = folder / f'voice-{index:02}.mp3'
        path.write_bytes(audio)
        paths.append(path)
    return paths
