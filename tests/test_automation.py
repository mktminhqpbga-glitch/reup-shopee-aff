import base64
from functools import partial
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image
import app
import automation as auto
from story_fixtures import story_response

LINK = 'https://s.shopee.vn/test-affiliate'
PRODUCT = 'https://shopee.vn/Binh-giu-nhiet-i.123.456'
PHOTO = 'https://down-vn.img.susercontent.com/file/example'
TITLE = 'Bình giữ nhiệt 500 ml'
HTML = ('<html><script type="application/ld+json">' + json.dumps({
    '@context': 'https://schema.org', '@graph': [{'@type': 'Product', 'name': TITLE,
    'description': 'Dung tích 500 ml. Nắp có quai xách.', 'image': [PHOTO]}]
}) + '</script></html>').encode()


class SourceTests(unittest.TestCase):
    def test_supported_links_and_rejected_hosts(self):
        for link in [LINK, PRODUCT, 'https://vn.shp.ee/test']:
            self.assertEqual(auto.validate_affiliate(link), link)
        for link in ['http://shopee.vn/product/1/2', 'https://shopee.vn.evil.test/x',
                     'https://127.0.0.1/x', 'https://shopee.vn@evil.test/',
                     'https://shopee.vn:444/', 'https://user:password@shopee.vn/', None]:
            with self.subTest(link=link), self.assertRaises(auto.PipelineError):
                auto.validate_affiliate(link)

    def test_redirect_cannot_escape_shopee(self):
        handler = auto.CheckedRedirect(auto.PRODUCT_HOSTS)
        with self.assertRaises(auto.PipelineError):
            handler.redirect_request(Request(LINK), None, 302, '', {}, 'https://169.254.169.254/')

    def test_json_ld_and_metadata_fallback(self):
        product = auto.parse_product(auto.Download(HTML, PRODUCT, 'text/html'))
        self.assertEqual(product['title'], TITLE)
        self.assertEqual(product['image_urls'], [PHOTO])
        html = f'<meta property="og:title" content="{TITLE} | Shopee"><meta property="og:image" content="{PHOTO}">'
        self.assertEqual(auto.parse_product(auto.Download(html.encode(), PRODUCT, 'text/html'))['title'], TITLE)

    def test_blocked_or_missing_product_does_not_fabricate_data(self):
        for html, url in [(b'<title>CAPTCHA</title>', PRODUCT), (HTML, 'https://shopee.vn/login'),
                          (b'<meta property="og:title" content="Shopee">', PRODUCT)]:
            with self.subTest(url=url), self.assertRaises(auto.PipelineError):
                auto.parse_product(auto.Download(html, url, 'text/html'))

    def test_invalid_ai_script_is_not_used(self):
        with self.assertRaises(auto.PipelineError):
            auto.generate_script({'title': TITLE, 'description': ''},
                                 request=lambda *a, **k: {'choices': [{'message': {'content': '{"scenes": []}'}}]})


class AutomaticFlow(unittest.TestCase):
    """Real HTTP + metadata parser + AI response adapter + FFmpeg.

    External Shopee/OpenAI responses are fixtures. Audio is a test tone, not AI speech.
    """
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.patches = [patch.object(app, 'DATA', cls.root), patch.object(app, 'JOBS', {})]
        for p in cls.patches:
            p.start()
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        audio_file = cls.root / 'fixture.mp3'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=1', str(audio_file)], check=True)
        cls.audio = audio_file.read_bytes()
        buf = io.BytesIO()
        Image.new('RGB', (600, 600), '#7ce5c6').save(buf, 'PNG')
        cls.photo = buf.getvalue()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for p in reversed(cls.patches):
            p.stop()
        cls.temporary.cleanup()

    def post(self, body, **headers):
        return urlopen(Request(self.base+'/api/auto', json.dumps(body).encode(),
                               {'Content-Type': 'application/json', **headers}))

    def wait(self, job_id):
        deadline = time.monotonic()+90
        while time.monotonic()<deadline:
            with urlopen(self.base+'/api/jobs/'+job_id) as response:
                state = json.load(response)
            if state['status'] in ('done', 'error'):
                return state
            time.sleep(.2)
        self.fail('Job did not complete')

    def test_one_link_to_voiced_mp4_and_persisted_result(self):
        def fetch(url, **kwargs):
            if url == LINK:
                return auto.Download(HTML, PRODUCT, 'text/html')
            self.assertEqual(url, PHOTO)
            return auto.Download(self.photo, PHOTO, 'image/png')

        calls = []
        def ai(path, body, **kwargs):
            calls.append((path, body))
            if path == 'audio/speech':
                return self.audio
            return story_response(body)

        original_load, original_images = auto.load_product, auto.download_images
        original_script, original_speech = app.build_storyboard, auto.synthesize_speech
        with patch.dict(os.environ, {'AI_API_KEY': 'test-placeholder-not-a-real-key', 'FB_AUTO_PUBLISH': 'true'}), \
             patch.object(app.publishing, 'publish_video', return_value={
                 'status': 'submitted', 'video_id': '12345', 'url': 'https://www.facebook.com/watch/?v=12345',
                 'message': 'Fixture: Facebook accepted upload.'}) as publish, \
             patch.object(auto, 'load_product', partial(original_load, fetch=fetch)), \
             patch.object(auto, 'download_images', partial(original_images, fetch=fetch)), \
             patch.object(app, 'build_storyboard', partial(original_script, request=ai)), \
             patch.object(auto, 'synthesize_speech', partial(original_speech, request=ai)):
            with self.post({'affiliate': LINK}) as response:
                self.assertEqual(response.status, 202)
                job_id = json.load(response)['id']
            state = self.wait(job_id)
        self.assertEqual(state['status'], 'done', state)
        publish.assert_called_once()
        self.assertEqual(state['facebook']['status'], 'submitted')
        self.assertTrue(state['has_voice'])
        self.assertEqual(state['product']['title'], TITLE)
        self.assertIn(LINK, state['caption'])
        with urlopen(self.base+f'/output/{job_id}/storyboard.json') as response:
            exported = json.load(response)
        self.assertTrue(exported['review']['approved'])
        self.assertEqual(len(exported['scenes']), 3)
        self.assertEqual([path for path, body in calls], ['chat/completions']*4 + ['audio/speech']*3)
        output = self.root/job_id/'video.mp4'
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)], capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        video = next(s for s in metadata['streams'] if s['codec_type']=='video')
        self.assertEqual((video['width'],video['height']), (720,1280))
        self.assertTrue(any(s['codec_type']=='audio' for s in metadata['streams']))
        self.assertAlmostEqual(float(metadata['format']['duration']), state['duration'], delta=.3)
        volume = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(output), '-af', 'volumedetect', '-vn', '-f', 'null', '-'],capture_output=True,text=True,check=True)
        self.assertNotIn('max_volume: -inf', volume.stderr)
        with urlopen(Request(self.base+state['video'], headers={'Range':'bytes=0-99'})) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(len(response.read()),100)
        with urlopen(Request(self.base+state['video'], headers={'Range':'bytes=-128'})) as response:
            self.assertEqual(response.status,206)
            self.assertEqual(len(response.read()),128)
        self.assertEqual(json.loads((self.root/job_id/'job.json').read_text())['status'], 'done')
        with urlopen(self.base+'/api/jobs') as response:
            self.assertTrue(any(j['id']==job_id for j in json.load(response)['jobs']))

    def test_missing_ai_is_explicit_and_does_not_start_job(self):
        with patch.dict(os.environ, {'AI_API_KEY': ''}), self.assertRaises(HTTPError) as caught:
            self.post({'affiliate': LINK})
        self.assertEqual(caught.exception.code,409)
        self.assertEqual(json.load(caught.exception)['code'], 'AI_NOT_CONFIGURED')

    def test_external_failure_does_not_generate_fake_video(self):
        failure = auto.PipelineError('SOURCE_BLOCKED', 'Nguồn Shopee từ chối truy cập.')
        with patch.dict(os.environ, {'AI_API_KEY': 'test-placeholder-not-a-real-key'}), \
             patch.object(auto, 'load_product', side_effect=failure), \
             patch.object(app, 'build_storyboard') as generate:
            with self.post({'affiliate': LINK}) as response:
                job_id = json.load(response)['id']
            state = self.wait(job_id)
            generate.assert_not_called()
        self.assertEqual(state['status'],'error')
        self.assertEqual(state['code'],'SOURCE_BLOCKED')
        self.assertNotIn('video',state)

    def test_cross_origin_cannot_trigger_ai(self):
        with self.assertRaises(HTTPError) as caught:
            self.post({'affiliate': LINK}, Origin='https://other.example')
        self.assertEqual(caught.exception.code,403)

    def test_interrupted_upload_is_not_automatically_repeated(self):
        job_id = 'a'*32
        folder = self.root/job_id
        folder.mkdir(exist_ok=True)
        (folder/'video.mp4').write_bytes(b'fixture')
        app.save_job(job_id, status='running', stage='publishing', video=f'/output/{job_id}/video.mp4')
        with patch.object(app.publishing, 'publish_video') as publish:
            app.restore_jobs()
        publish.assert_not_called()
        self.assertEqual(app.JOBS[job_id]['status'], 'done')
        self.assertEqual(app.JOBS[job_id]['facebook']['code'], 'FACEBOOK_UPLOAD_UNCERTAIN')

    def test_health_never_returns_key(self):
        secret = 'test-placeholder-not-a-real-key'
        with patch.dict(os.environ, {'AI_API_KEY': secret}), urlopen(self.base+'/api/health') as response:
            text = response.read().decode()
        self.assertNotIn(secret,text)
        self.assertTrue(json.loads(text)['ai']['configured'])


if __name__ == '__main__':
    unittest.main()
