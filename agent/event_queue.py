"""Event queue — buffers events until backend registration completes."""

import logging
import threading
from collections import deque

from shared.events import ProjectEventCreate

logger = logging.getLogger(__name__)


class EventQueue:
    """Thread-safe queue that holds events when project/user IDs are missing."""

    MAX_SIZE = 500

    def __init__(self):
        self._queue: deque[ProjectEventCreate] = deque(maxlen=self.MAX_SIZE)
        self._lock = threading.Lock()

    def enqueue(self, event: ProjectEventCreate) -> None:
        with self._lock:
            self._queue.append(event)
            logger.debug("Event queued (%d pending): %s", len(self._queue), event.event_type)

    def flush(self, send_fn) -> int:
        """Send all queued events. Returns count sent."""
        sent = 0
        with self._lock:
            while self._queue:
                event = self._queue.popleft()
                if send_fn(event):
                    sent += 1
                else:
                    self._queue.appendleft(event)
                    break
        if sent:
            logger.info("Flushed %d queued event(s) to backend", sent)
        return sent

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()
# ProjectPulse live tracking test