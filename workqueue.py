"""A bounded worker pool; pausing only stops dispatch of new jobs."""
from collections import deque
import logging
import threading


class WorkQueue:
    def __init__(self, workers=2, capacity=50):
        self.workers = workers
        self.capacity = capacity
        self.condition = threading.Condition()
        self.pending = deque()
        self.active = 0
        self.paused = False
        self.started = False

    def submit(self, tasks):
        with self.condition:
            if len(tasks) + len(self.pending) > self.capacity:
                raise ValueError('Hàng đợi đầy, vui lòng chờ các tác vụ trước hoàn tất.')
            self.pending.extend(tasks)
            if not self.started:
                self.started = True
                for number in range(self.workers):
                    threading.Thread(target=self.run, name=f'video-worker-{number+1}', daemon=True).start()
            self.condition.notify_all()

    def run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.pending and not self.paused)
                _, callback, args = self.pending.popleft()
                self.active += 1
            try:
                callback(*args)
            except Exception:
                logging.getLogger(__name__).error('Worker callback failed', exc_info=False)
            finally:
                with self.condition:
                    self.active -= 1
                    self.condition.notify_all()

    def cancel_pending(self, job):
        with self.condition:
            self.pending = deque(task for task in self.pending if task[0] != job)

    def set_paused(self, paused):
        with self.condition:
            self.paused = paused
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            return {'workers': self.workers, 'paused': self.paused,
                    'waiting': len(self.pending), 'active': self.active, 'capacity': self.capacity}
