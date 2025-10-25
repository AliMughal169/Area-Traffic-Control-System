import threading
from typing import Callable, Optional, List

class TimerManager:
    """Manage up to N timers with safe start/cancel semantics."""
    def __init__(self, n: int):
        self._timers: List[Optional[threading.Timer]] = [None] * n
        self._lock = threading.Lock()

    def start_timer(self, idx: int, seconds: float, fn: Callable, args=()):
        """Start (or restart) a timer at index idx to call fn(*args) after seconds."""
        with self._lock:
            self._cancel_no_lock(idx)
            t = threading.Timer(seconds, fn, args=args)
            self._timers[idx] = t
            t.start()
            return t

    def cancel_timer(self, idx: int):
        """Cancel the timer at index idx if active."""
        with self._lock:
            self._cancel_no_lock(idx)

    def cancel_all(self):
        """Cancel all managed timers."""
        with self._lock:
            for i in range(len(self._timers)):
                self._cancel_no_lock(i)

    def _cancel_no_lock(self, idx: int):
        t = self._timers[idx]
        if t is not None:
            try:
                t.cancel()
            except Exception:
                pass
            self._timers[idx] = None