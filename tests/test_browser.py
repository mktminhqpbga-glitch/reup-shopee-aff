"""Browser test with external services replaced by fixtures; no real posts or AI charges."""
from functools import partial
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image
import app
import automation as auto
from story_fixtures import story_response
from test_automation import LINK, PRODUCT, PHOTO, HTML, TITLE

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipUnless(sync_playwright and shutil.which('chromium'), 'Optional Playwright/Chromium unavailable')
class BrowserFlow(unittest.TestCase):
    def test_one_link_ui_on_desktop_and_mobile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root/'fixture.mp3'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i',
                            'sine=frequency=440:duration=1',str(audio)],check=True)
            voice = audio.read_bytes()
            image = io.BytesIO()
            Image.new('RGB',(600,600),'#80c6bd').save(image,'PNG')
            def fetch(url, **kwargs):
                return auto.Download(HTML,PRODUCT,'text/html') if url==LINK else auto.Download(image.getvalue(),PHOTO,'image/png')
            def ai(path, body, **kwargs):
                if path=='audio/speech': return voice
                return story_response(body)
            load, images, script, speech = auto.load_product, auto.download_images, app.build_storyboard, auto.synthesize_speech
            with patch.object(app,'DATA',root), patch.object(app,'JOBS',{}), \
                 patch.dict(os.environ,{'AI_API_KEY':'test-not-a-real-key','FB_AUTO_PUBLISH':'false'}), \
                 patch.object(auto,'load_product',partial(load,fetch=fetch)), \
                 patch.object(auto,'download_images',partial(images,fetch=fetch)), \
                 patch.object(app,'build_storyboard',partial(script,request=ai)), \
                 patch.object(auto,'synthesize_speech',partial(speech,request=ai)):
                server = app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
                threading.Thread(target=server.serve_forever,daemon=True).start()
                try:
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(executable_path=shutil.which('chromium'),
                                                              headless=True,args=['--no-sandbox'])
                        try:
                            page = browser.new_page(viewport={'width':1440,'height':1000})
                            errors=[]
                            page.on('pageerror',lambda error:errors.append(str(error)))
                            page.goto(f'http://127.0.0.1:{server.server_port}')
                            page.wait_for_function("!document.getElementById('create').disabled")
                            self.assertEqual(page.locator('input').count(),1)
                            page.locator('#affiliate').fill(LINK)
                            page.locator('#create').click()
                            page.locator('#result').wait_for(state='visible',timeout=60000)
                            self.assertEqual(page.locator('#productTitle').inner_text(),TITLE)
                            self.assertIn(LINK,page.locator('#caption').input_value())
                            self.assertEqual(page.locator('#storyPanel .scene-card').count(),3)
                            self.assertEqual(page.locator('#storyBadge').inner_text(),'AI đã duyệt')
                            self.assertIn('Đồ dùng mang theo',page.locator('#storyPanel').inner_text())
                            page.wait_for_function("document.getElementById('video').readyState >= 1")
                            self.assertEqual(page.locator('#video').evaluate('(v)=>v.videoWidth'),720)
                            self.assertFalse(page.locator('#create').is_disabled())
                            self.assertEqual(errors,[])
                            page.screenshot(path='/tmp/affiliate-studio-desktop.png',full_page=True)
                            page.set_viewport_size({'width':390,'height':844})
                            self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
                            page.screenshot(path='/tmp/affiliate-studio-mobile.png',full_page=True)
                            # A refresh restores the result through its history entry.
                            page.reload()
                            page.locator('#history button').first.click()
                            page.locator('#result').wait_for(state='visible')
                            self.assertEqual(page.locator('#productTitle').inner_text(),TITLE)
                            with patch.dict(os.environ,{'AI_API_KEY':''}):
                                page.reload()
                                page.locator('#setup').wait_for(state='visible')
                                self.assertTrue(page.locator('#create').is_disabled())
                                self.assertIn('AI_API_KEY',page.locator('#setup').inner_text())
                        finally:
                            browser.close()
                finally:
                    server.shutdown()
                    server.server_close()
