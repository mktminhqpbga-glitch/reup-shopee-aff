import base64
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import Image
import app


class Flow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.patches = [patch.object(app, 'DATA', Path(cls.temporary.name)), patch.object(app, 'JOBS', {})]
        for change in cls.patches:
            change.start()
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for change in reversed(cls.patches):
            change.stop()
        cls.temporary.cleanup()

    def test_export_and_download(self):
        image = Image.new('RGB', (400, 500), '#79dbbc')
        buf = io.BytesIO()
        image.save(buf, 'PNG')
        body = {'title': 'Sản phẩm thử nghiệm', 'scenes': ['Thông tin đã được kiểm tra.'],
                'affiliate': 'https://s.shopee.vn/example',
                'images': ['data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()]}
        with urlopen(Request(self.base+'/api/render', json.dumps(body).encode(), {'Content-Type':'application/json'})) as response:
            self.assertEqual(response.status, 202)
            job_id = json.load(response)['id']
        deadline = time.monotonic()+90
        while time.monotonic()<deadline:
            with urlopen(self.base+'/api/jobs/'+job_id) as response:
                job = json.load(response)
            if job['status'] in ('done', 'error'):
                break
            time.sleep(.3)
        self.assertEqual(job['status'], 'done', job)
        with urlopen(self.base+job['video']) as response:
            self.assertEqual(response.headers['Content-Type'], 'video/mp4')
            self.assertGreater(len(response.read()), 1000)
        result = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(app.DATA/job_id/'video.mp4')], capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        video = next(s for s in metadata['streams'] if s['codec_type']=='video')
        self.assertEqual((video['width'],video['height']), (720,1280))
        self.assertAlmostEqual(float(metadata['format']['duration']),5,delta=.2)
        self.assertIn(body['affiliate'], job['caption'])

    def test_reject_empty_input(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/api/render', b'{}', {'Content-Type':'application/json'}))
        self.assertEqual(caught.exception.code,400)

    def test_reject_output_traversal(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base+'/output/../app.py')
        self.assertEqual(caught.exception.code,404)

    def test_reject_foreign_host_on_reads_and_writes(self):
        for path, payload in [('/api/jobs', None), ('/api/render', b'{}')]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base+path, payload,
                                {'Host':'attacker.example', 'Origin':'http://attacker.example',
                                 'Content-Type':'application/json'}))
            self.assertEqual(caught.exception.code,403)

    def test_reject_wrong_host_port(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/api/jobs', headers={'Host':'localhost:1'}))
        self.assertEqual(caught.exception.code,403)


if __name__ == '__main__':
    unittest.main()
