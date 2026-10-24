import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import publishing
from automation import PipelineError


class FacebookTests(unittest.TestCase):
    def test_default_is_not_to_publish(self):
        with patch.dict(os.environ, {'FB_AUTO_PUBLISH':'', 'FB_PAGE_ACCESS_TOKEN':'', 'FB_PAGE_ID':''}):
            self.assertEqual(publishing.settings(), {'configured':False, 'auto_publish':False})

    def test_upload_request_and_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args): return json.dumps({'id':'67890'}).encode()

        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'FB_PAGE_ID':'12345', 'FB_PAGE_ACCESS_TOKEN':'test-not-a-real-token', 'FB_GRAPH_VERSION':'v23.0'}), \
             patch.object(publishing, 'build_opener') as opener:
            opener.return_value.open.return_value = Response()
            video = Path(tmp)/'video.mp4'
            video.write_bytes(b'test-video-payload')
            result = publishing.publish_video(video, 'Sản phẩm', 'Có liên kết tiếp thị')
            self.assertEqual(result['status'], 'submitted')
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://graph-video.facebook.com/v23.0/12345/videos')
            self.assertIn(b'test-video-payload', request.data)
            self.assertNotIn(b'test-not-a-real-token', request.data)
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-not-a-real-token')

    def test_failure_message_does_not_leak_response_or_token(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'FB_PAGE_ID':'12345', 'FB_PAGE_ACCESS_TOKEN':'test-not-a-real-token'}), \
             patch.object(publishing, 'build_opener') as opener:
            video = Path(tmp)/'video.mp4'
            video.write_bytes(b'fixture')
            opener.return_value.open.side_effect = HTTPError('https://graph-video.facebook.com/',403,'secret response',{},None)
            with self.assertRaises(PipelineError) as caught:
                publishing.publish_video(video, 'Title', 'Caption')
            self.assertNotIn('test-not-a-real-token', str(caught.exception))
            self.assertNotIn('secret response', str(caught.exception))
            self.assertEqual(opener.return_value.open.call_count,1)
