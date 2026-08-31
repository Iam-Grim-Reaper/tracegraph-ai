import logging
from dataclasses import dataclass
from threading import Event, Lock, Thread, current_thread
from time import monotonic

from app.core.observability import log_event


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamWorker:
    request_id: str
    cancelled: Event
    thread: Thread


class StreamWorkerRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._workers: dict[int, StreamWorker] = {}
        self._shutting_down = False

    def start(self) -> None:
        with self._lock:
            if not self._workers:
                self._shutting_down = False

    def register(self, worker: StreamWorker) -> bool:
        with self._lock:
            if self._shutting_down:
                return False
            self._workers[id(worker.thread)] = worker
            active_worker_count = len(self._workers)
        log_event(
            logger,
            logging.INFO,
            "stream_worker_registered",
            operation="stream_worker",
            status="started",
            request_id=worker.request_id,
            active_worker_count=active_worker_count,
        )
        return True

    def unregister(self, thread: Thread) -> None:
        with self._lock:
            worker = self._workers.pop(id(thread), None)
            active_worker_count = len(self._workers)
        if worker is not None:
            log_event(
                logger,
                logging.INFO,
                "stream_worker_finished",
                operation="stream_worker",
                status="complete",
                request_id=worker.request_id,
                active_worker_count=active_worker_count,
            )

    def shutdown(self, timeout_seconds: float) -> tuple[int, int, int]:
        with self._lock:
            self._shutting_down = True
            workers = list(self._workers.values())
        for worker in workers:
            worker.cancelled.set()

        deadline = monotonic() + timeout_seconds
        for worker in workers:
            if worker.thread is current_thread() or not worker.thread.is_alive():
                continue
            remaining = max(0.0, deadline - monotonic())
            if remaining <= 0:
                break
            worker.thread.join(remaining)

        workers_stopped = sum(not worker.thread.is_alive() for worker in workers)
        remaining_worker_count = len(workers) - workers_stopped
        return len(workers), workers_stopped, remaining_worker_count

    def active_workers(self) -> tuple[StreamWorker, ...]:
        with self._lock:
            return tuple(self._workers.values())


stream_workers = StreamWorkerRegistry()
