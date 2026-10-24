import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
from workqueue import WorkQueue


class WorkerTests(unittest.TestCase):
    def test_parallel_limit_pause_and_pending_cancellation(self):
        queue = WorkQueue(2)
        queue.set_paused(True)
        started = threading.Event()
        two = threading.Event()
        release = threading.Event()
        complete = threading.Event()
        lock = threading.Lock()
        counts = {'running':0, 'peak':0, 'done':0}
        cancelled = threading.Event()
        def task():
            with lock:
                counts['running'] += 1
                counts['peak'] = max(counts['peak'], counts['running'])
                started.set()
                if counts['running']==2: two.set()
            release.wait(5)
            with lock:
                counts['running'] -= 1
                counts['done'] += 1
                if counts['done']==2: complete.set()
        queue.submit([('1',task,()),('2',task,()),('3',cancelled.set,())])
        try:
            self.assertFalse(started.wait(.05))
            queue.cancel_pending('3')
            queue.set_paused(False)
            self.assertTrue(two.wait(3), 'Two jobs must run concurrently, not serially')
            self.assertEqual(queue.snapshot()['active'],2)
        finally:
            release.set()
        self.assertTrue(complete.wait(3))
        self.assertEqual(counts['peak'],2)
        self.assertFalse(cancelled.is_set())

    def test_worker_survives_failed_task(self):
        queue = WorkQueue(1)
        done = threading.Event()
        def failure(): raise ValueError('fixture')
        queue.submit([('failed',failure,()),('next',done.set,())])
        self.assertTrue(done.wait(3))


class BatchAPITests(unittest.TestCase):
    def test_batch_deduplication_variants_and_cancel_before_run(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app,'DATA',Path(tmp)), \
             patch.object(app,'JOBS',{}), patch.object(app,'QUEUE',WorkQueue(2)), \
             patch.dict(os.environ,{'AI_API_KEY':'test-not-a-real-key'}), \
             patch.object(app,'process_job') as process:
            app.QUEUE.set_paused(True)
            server = app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            base=f'http://127.0.0.1:{server.server_port}'
            def post(path,data):
                return urlopen(Request(base+path,json.dumps(data).encode(),{'Content-Type':'application/json'}))
            try:
                links=['https://s.shopee.vn/one','https://s.shopee.vn/two','https://s.shopee.vn/one']
                with post('/api/batch',{'links':links,'styles':['overview','details','overview']}) as r:
                    result=json.load(r)
                self.assertEqual(result['count'],4)
                self.assertEqual(len(set(result['ids'])),4)
                self.assertEqual({state['style'] for state in app.JOBS.values()},{'overview','details'})
                self.assertEqual(app.QUEUE.snapshot()['waiting'],4)
                process.assert_not_called()
                with post('/api/jobs/'+result['id']+'/cancel',{}) as r:
                    self.assertEqual(json.load(r)['status'],'cancelled')
                self.assertEqual(app.QUEUE.snapshot()['waiting'],3)
                # Validate the entire batch before accepting any jobs.
                with self.assertRaises(HTTPError) as error:
                    post('/api/batch',{'links':[links[0],'https://localhost/'],'styles':['overview']})
                self.assertEqual(error.exception.code,400)
                self.assertEqual(len(app.JOBS),4)
                # Remove fixtures without dispatching calls in later tests.
                for job in result['ids']: app.QUEUE.cancel_pending(job)
                with post('/api/queue/resume',{}) as r:
                    self.assertFalse(json.load(r)['paused'])
            finally:
                server.shutdown()
                server.server_close()
