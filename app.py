import base64
import io
import json
import logging
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps
import automation
import publishing
from workqueue import WorkQueue
from storyboard import StoryMemory, build_storyboard
from automation import PipelineError

ROOT = Path(__file__).resolve().parent
DATA = ROOT / '.runtime'
DATA.mkdir(exist_ok=True)
JOBS = {}
LOCK = threading.Lock()
SUBMIT_LOCK = threading.Lock()
try:
    WORKERS = max(1, min(4, int(os.environ.get('VIDEO_WORKERS', '2'))))
except ValueError:
    WORKERS = 2
QUEUE = WorkQueue(WORKERS)
TERMINAL = ('done', 'error', 'cancelled')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
LOG = logging.getLogger(__name__)


def save_job(job, **values):
    with LOCK:
        state = {**JOBS.get(job, {}), **values, 'id': job}
        folder = DATA / job
        folder.mkdir(exist_ok=True)
        temporary = folder / 'job.tmp'
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        temporary.replace(folder / 'job.json')
        JOBS[job] = state


def restore_jobs():
    for file in DATA.glob('*/job.json'):
        try:
            job = file.parent.name
            if len(job) != 32 or any(c not in '0123456789abcdef' for c in job):
                continue
            state = json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(state, dict):
                continue
            JOBS[job] = state
            if state.get('status') not in TERMINAL:
                if state.get('stage') == 'publishing' and (DATA/job/'video.mp4').is_file():
                    save_job(job, status='done', stage='done', progress=100, facebook={
                        'status': 'error', 'code': 'FACEBOOK_UPLOAD_UNCERTAIN',
                        'message': 'App đã dừng khi đang gửi Facebook. Video vẫn tải được; kiểm tra Page trước khi đăng lại để tránh trùng.'})
                else:
                    save_job(job, status='error', code='INTERRUPTED',
                             error='App đã khởi động lại khi đang xử lý. Bấm tạo lại nếu muốn tiếp tục; app không tự gọi AI tính phí lại.')
        except (OSError, ValueError):
            LOG.warning('Could not restore job metadata: %s', file.parent.name)


def validate(body):
    if not isinstance(body, dict):
        raise ValueError('Dữ liệu không hợp lệ.')
    title = body.get('title', '')
    scenes = body.get('scenes', [])
    images = body.get('images', [])
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError('Tên sản phẩm phải có từ 1 đến 160 ký tự.')
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 6:
        raise ValueError('Cần từ 1 đến 6 cảnh.')
    if any(not isinstance(s, str) or not s.strip() or len(s) > 250 for s in scenes):
        raise ValueError('Mỗi cảnh cần nội dung, tối đa 250 ký tự.')
    if not isinstance(images, list) or not 1 <= len(images) <= 6:
        raise ValueError('Cần từ 1 đến 6 ảnh sản phẩm.')
    for field in ('url', 'affiliate'):
        value = body.get(field, '')
        if not isinstance(value, str) or (value and (urlparse(value).scheme != 'https' or not urlparse(value).hostname)):
            raise ValueError('Link phải là địa chỉ HTTPS hợp lệ.')
    return title.strip(), scenes, images


def wrap(draw, text, font, width):
    lines, current = [], ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if draw.textlength(candidate, font=font) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


def run_media(command):
    try:
        return subprocess.run(command, check=True, capture_output=True, timeout=240)
    except (subprocess.SubprocessError, OSError):
        raise PipelineError('MEDIA_FAILED', 'Không xử lý được hình ảnh/âm thanh. Kiểm tra FFmpeg, font và dung lượng ổ đĩa.') from None


def audio_duration(path):
    result = run_media(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)])
    try:
        duration = float(result.stdout)
        if not math.isfinite(duration) or not .2 <= duration <= 40:
            raise ValueError()
        return duration + .4
    except ValueError:
        raise PipelineError('AUDIO_DURATION_INVALID', 'Giọng đọc có thời lượng không hợp lệ (mỗi cảnh tối đa 40 giây).') from None


def render(job, body, audio_paths=None):
    folder = DATA / job
    folder.mkdir(exist_ok=True)
    title, scenes, images = validate(body)
    decoded = []
    for raw in images:
        try:
            if not isinstance(raw, str) or ',' not in raw:
                raise ValueError()
            content = base64.b64decode(raw.split(',', 1)[1], validate=True)
            if len(content) > 8 * 1024 * 1024:
                raise ValueError()
            with Image.open(io.BytesIO(content)) as source:
                if source.width * source.height > 25_000_000:
                    raise ValueError()
                decoded.append(ImageOps.exif_transpose(source).convert('RGB'))
        except (ValueError, OSError, Image.DecompressionBombError):
            raise PipelineError('IMAGE_INVALID', 'Ảnh sản phẩm không hợp lệ hoặc vượt giới hạn kích thước.') from None
    durations = [audio_duration(path) for path in audio_paths] if audio_paths else [5.0] * len(scenes)
    if sum(durations) > 180:
        raise PipelineError('VIDEO_TOO_LONG', 'Video vượt giới hạn 3 phút.')
    if len(durations) != len(scenes):
        raise PipelineError('AUDIO_MISMATCH', 'Số cảnh và số đoạn giọng đọc không khớp.')
    for index, scene in enumerate(scenes):
        checkpoint(job)
        canvas = Image.new('RGB', (720, 1280), '#101827')
        photo = ImageOps.contain(decoded[index % len(decoded)], (656, 680))
        canvas.paste(photo, ((720-photo.width)//2, 185+(680-photo.height)//2))
        draw = ImageDraw.Draw(canvas)
        small = ImageFont.truetype(FONT, 22)
        heading = ImageFont.truetype(FONT, 29)
        subtitle = ImageFont.truetype(FONT, 29)
        draw.text((32, 30), 'AFFILIATE STUDIO  /  GIỚI THIỆU SẢN PHẨM', font=small, fill='#78e5c5')
        for n, line in enumerate(wrap(draw, title, heading, 656)[:3]):
            draw.text((32, 80+n*34), line, font=heading, fill='white')
        for n, line in enumerate(wrap(draw, scene, subtitle, 640)[:8]):
            draw.text((40, 885+n*36), line, font=subtitle, fill='white')
        draw.text((32, 1220), f'Có liên kết tiếp thị • {index+1}/{len(scenes)}', font=small, fill='#aab7ca')
        canvas.save(folder / f'{index:02}.png')
        if index == 0:
            canvas.save(folder / 'poster.jpg', quality=90)
        command = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                   '-loop', '1', '-framerate', '24', '-i', str(folder / f'{index:02}.png')]
        command += ['-i', str(audio_paths[index])] if audio_paths else ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
        command += ['-t', str(durations[index]), '-vf', 'fade=t=in:st=0:d=0.25',
                    '-af', 'apad', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(folder / f'scene-{index:02}.mp4')]
        run_media(command)
        save_job(job, progress=75 + int((index+1)/len(scenes)*20))
    (folder / 'segments.txt').write_text(''.join(f"file 'scene-{i:02}.mp4'\n" for i in range(len(scenes))))
    run_media(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
               '-f', 'concat', '-safe', '1', '-i', str(folder / 'segments.txt'),
               '-c', 'copy', '-movflags', '+faststart', str(folder / 'video.mp4')])
    caption = (f"{title}\n\n" + '\n'.join(scenes)
               + '\n\nNội dung giới thiệu được tạo bằng AI từ thông tin sản phẩm, chưa phải trải nghiệm sử dụng thực tế.'
               + '\nCó liên kết tiếp thị; tôi có thể nhận hoa hồng khi bạn mua hàng.\n' + body.get('affiliate', ''))
    if not audio_paths:
        caption = caption.replace('Nội dung giới thiệu được tạo bằng AI từ thông tin sản phẩm', 'Nội dung giới thiệu từ thông tin sản phẩm')
    (folder / 'caption.txt').write_text(caption, encoding='utf-8')
    return {'video': f'/output/{job}/video.mp4', 'poster': f'/output/{job}/poster.jpg', 'caption': caption,
            'duration': round(sum(durations), 1), 'has_voice': bool(audio_paths),
            'scene_durations': [round(d, 2) for d in durations]}


def checkpoint(job):
    if JOBS.get(job, {}).get('cancel_requested') or JOBS.get(job, {}).get('status') == 'cancelled':
        raise PipelineError('CANCELLED', 'Đã hủy. Lệnh gọi dịch vụ đang thực hiện có thể đã phát sinh phí.')


def process_job(job, body, automatic=False):
    try:
        with SUBMIT_LOCK:
            checkpoint(job)
            save_job(job, status='running', stage='product' if automatic else 'rendering')
        if automatic:
            automation.require_ai()
            affiliate = automation.validate_affiliate(body['affiliate'])
            checkpoint(job)
            save_job(job, status='running', stage='product', progress=8)
            product = automation.load_product(affiliate)
            checkpoint(job)
            product['style'] = body.get('style', 'overview')
            save_job(job, product=product, stage='images', progress=20)
            images = automation.download_images(product)
            checkpoint(job)
            memory = StoryMemory(DATA / 'story-history.sqlite3')
            def on_phase(phase, story):
                temporary = DATA / job / 'storyboard.tmp'
                temporary.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(DATA / job / 'storyboard.json')
                save_job(job, story=story, stage=phase,
                         progress={'profile': 30, 'director': 36, 'writer': 43, 'audit': 50}[phase])
            story = build_storyboard(product, history=memory.history(product),
                                     on_phase=on_phase, checkpoint=lambda: checkpoint(job))
            checkpoint(job)
            memory.remember(job, product, story)
            scenes = [scene['narration'] for scene in story['scenes']]
            # Select the downloaded reference for each scene. Missing source images use
            # the first available image; motion prompts remain available for a future provider.
            images = [images[scene['image_index']] if scene['image_index'] < len(images) else images[0]
                      for scene in story['scenes']]
            save_job(job, story=story, scenes=scenes, stage='voice', progress=55)
            audio_paths = automation.synthesize_speech(scenes, DATA / job)
            checkpoint(job)
            body = {'title': product['title'], 'scenes': scenes, 'images': images,
                    'url': product['source_url'], 'affiliate': affiliate}
        else:
            audio_paths = None
        save_job(job, status='running', stage='rendering', progress=75)
        result = render(job, body, audio_paths)
        checkpoint(job)
        facebook = {'status': 'not_requested', 'message': 'Tự đăng Facebook chưa được bật trong cài đặt.'}
        if automatic and publishing.settings()['auto_publish']:
            with SUBMIT_LOCK:
                checkpoint(job)
                save_job(job, stage='publishing', progress=97, **result)
            try:
                facebook = publishing.publish_video(DATA/job/'video.mp4', body['title'], result['caption'])
            except PipelineError as error:
                facebook = {'status': 'error', 'code': error.code, 'message': str(error)}
        save_job(job, status='done', stage='done', progress=100, facebook=facebook, **result)
    except Exception as error:
        if not isinstance(error, (PipelineError, ValueError)):
            LOG.error('Job %s failed (%s)', job, type(error).__name__)
        save_job(job, status='cancelled' if getattr(error, 'code', '') == 'CANCELLED' else 'error', code=getattr(error, 'code', 'JOB_FAILED'),
                 error=str(error) if isinstance(error, ValueError) else 'Xử lý thất bại. Kiểm tra cấu hình và thử lại.')


class Handler(BaseHTTPRequestHandler):
    def local_request(self):
        # A loopback bind alone does not prevent a web page using DNS rebinding.
        # Require the actual local authority before exposing data or starting paid jobs.
        try:
            authority = urlparse('http://' + self.headers.get('Host', ''))
            allowed = (authority.hostname in ('localhost', '127.0.0.1')
                       and (authority.port or 80) == self.server.server_port
                       and not authority.username and not authority.password
                       and not authority.path and not authority.query and not authority.fragment
                       and len(self.headers.get_all('Host', [])) == 1)
        except ValueError:
            allowed = False
        if not allowed:
            self.reply(403, {'error': 'App chỉ nhận yêu cầu từ địa chỉ máy cục bộ hợp lệ.'})
            return False
        return True

    def reply(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if not self.local_request():
            return
        if self.path not in ('/api/render', '/api/auto', '/api/batch', '/api/queue/pause', '/api/queue/resume') and not (self.path.startswith('/api/jobs/') and self.path.endswith('/cancel')):
            return self.reply(404, {'error': 'Không tìm thấy.'})
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.reply(403, {'error': 'Nguồn yêu cầu không được phép.'})
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, {'error': 'Yêu cầu phải dùng JSON.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            automatic = self.path in ('/api/auto', '/api/batch')
            limit = 16 * 1024 if automatic else 65 * 1024 * 1024
            if not 0 < length <= limit:
                return self.reply(413, {'error': 'Dữ liệu vượt giới hạn cho phép.'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError()
            if self.path in ('/api/queue/pause', '/api/queue/resume'):
                QUEUE.set_paused(self.path.endswith('/pause'))
                return self.reply(200, QUEUE.snapshot())
            if self.path.endswith('/cancel'):
                job = self.path.split('/')[3]
                with SUBMIT_LOCK:
                    state = JOBS.get(job)
                    if not state:
                        return self.reply(404, {'error': 'Không tìm thấy tác vụ.'})
                    if state['status'] in TERMINAL:
                        return self.reply(409, {'error': 'Tác vụ đã kết thúc.'})
                    if state.get('stage') == 'publishing':
                        return self.reply(409, {'error': 'Đang gửi Facebook, không thể thu hồi yêu cầu. Hãy kiểm tra Page.'})
                    pending = state['status'] == 'queued'
                    save_job(job, cancel_requested=True, **({'status': 'cancelled', 'error': 'Đã hủy trước khi xử lý.'} if pending else {}))
                    QUEUE.cancel_pending(job)
                return self.reply(200, JOBS[job])
            if automatic:
                links = body.get('links') if self.path == '/api/batch' else [body.get('affiliate')]
                styles = body.get('styles', ['overview'])
                if not isinstance(links, list) or not 1 <= len(links) <= 20:
                    raise ValueError()
                if not isinstance(styles, list) or not styles or any(style not in automation.STYLES for style in styles):
                    raise ValueError()
                links = list(dict.fromkeys(automation.validate_affiliate(link) for link in links))
                styles = list(dict.fromkeys(styles))
                bodies = [{'affiliate': link, 'style': style} for link in links for style in styles]
                automation.require_ai()
            else:
                validate(body)
                bodies = [body]
            with SUBMIT_LOCK:
                if len(bodies) + sum(v.get('status') not in TERMINAL for v in JOBS.values()) > QUEUE.capacity:
                    return self.reply(429, {'error': 'Hàng đợi tối đa 50 tác vụ. Giảm số link/phiên bản hoặc chờ lượt trước.'})
                batch = uuid.uuid4().hex
                tasks, ids = [], []
                for entry in bodies:
                    job = uuid.uuid4().hex
                    save_job(job, status='queued', stage='queued', progress=0,
                             affiliate=entry.get('affiliate', ''), automatic=automatic,
                             batch=batch, style=entry.get('style', 'overview'))
                    tasks.append((job, process_job, (job, entry, automatic)))
                    ids.append(job)
                QUEUE.submit(tasks)
            self.reply(202, {'id': ids[0], 'ids': ids, 'batch': batch, 'count': len(ids)})
        except PipelineError as error:
            self.reply(409 if error.code == 'AI_NOT_CONFIGURED' else 400, {'error': str(error), 'code': error.code})
        except (ValueError, TypeError, AttributeError):
            self.reply(400, {'error': 'Thông tin chưa hợp lệ. Kiểm tra dữ liệu đã nhập.'})

    def do_GET(self):
        if not self.local_request():
            return
        path = urlparse(self.path).path
        if path == '/api/queue':
            return self.reply(200, QUEUE.snapshot())
        if path == '/api/jobs':
            with LOCK:
                jobs = list(JOBS.values())[-100:][::-1]
            return self.reply(200, {'jobs': jobs})
        if path.startswith('/api/jobs/'):
            job = JOBS.get(path.rsplit('/', 1)[1])
            return self.reply(200 if job else 404, job or {'error': 'Không tìm thấy tác vụ.'})
        if path == '/api/health':
            return self.reply(200, {'ok': bool(shutil.which('ffmpeg') and shutil.which('ffprobe') and Path(FONT).is_file()),
                                    'ai': automation.ai_settings(), 'publishing': publishing.settings()})
        if path.startswith('/output/'):
            parts = path.split('/')
            if len(parts) != 4 or len(parts[2]) != 32 or any(c not in '0123456789abcdef' for c in parts[2]) or parts[3] not in ('video.mp4', 'poster.jpg', 'storyboard.json'):
                return self.reply(404, {'error': 'Không tìm thấy.'})
            state = JOBS.get(parts[2], {})
            if state.get('status') != 'done' and not (parts[3] == 'storyboard.json' and state.get('story')):
                return self.reply(404, {'error': 'Video chưa hoàn tất.'})
            file = DATA / parts[2] / parts[3]
            mime = {'video.mp4': 'video/mp4', 'poster.jpg': 'image/jpeg', 'storyboard.json': 'application/json; charset=utf-8'}[parts[3]]
        elif path == '/':
            file = ROOT / 'static' / 'index.html'
            mime = 'text/html; charset=utf-8'
        else:
            return self.reply(404, {'error': 'Không tìm thấy.'})
        if not file.is_file():
            return self.reply(404, {'error': 'Chưa có tệp.'})
        size = file.stat().st_size
        start, end = 0, size-1
        partial = self.headers.get('Range')
        if partial and mime == 'video/mp4':
            try:
                unit, value = partial.split('=', 1)
                left, right = value.split('-', 1)
                if unit != 'bytes' or ',' in value:
                    raise ValueError()
                if left:
                    start = int(left)
                    end = min(int(right), size-1) if right else size-1
                else:
                    suffix = int(right)
                    if suffix <= 0:
                        raise ValueError()
                    start = max(0, size-suffix)
                if not 0 <= start <= end < size:
                    raise ValueError()
            except ValueError:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
        else:
            partial = None
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end-start+1))
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with file.open('rb') as stream:
                stream.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


restore_jobs()

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8000'))), Handler).serve_forever()
