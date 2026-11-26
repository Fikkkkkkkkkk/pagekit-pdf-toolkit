"""Short-lived, cancellable Compress PDF jobs and measured work progress."""

import time
from dataclasses import dataclass, field
from io import BytesIO
from threading import Event, Lock, Thread
from uuid import uuid4

from .processing import compress_document
from .storage import RETENTION_SECONDS
from .validation import CompressValidationError


class CompressionCancelled(Exception):
    pass


@dataclass
class CompressionJob:
    id: str
    created_at: float = field(default_factory=time.time)
    lock: Lock = field(default_factory=Lock)
    cancelled: Event = field(default_factory=Event)
    state: str = "created"
    phase: str = "Waiting for upload"
    completed: int = 0
    total: int = 0
    error: str | None = None
    result: BytesIO | None = None

    def check_cancel(self) -> None:
        if self.cancelled.is_set() or time.time() - self.created_at >= RETENTION_SECONDS:
            raise CompressionCancelled()

    def progress(self, phase: str, completed: int, total: int) -> None:
        self.check_cancel()
        with self.lock:
            self.phase = phase
            self.completed = completed
            self.total = total

    def finish(self, result: BytesIO) -> None:
        with self.lock:
            self.check_cancel()
            self.result = result
            self.completed = self.total
            self.phase = "Ready to download"
            self.state = "ready"

    def snapshot(self) -> dict:
        with self.lock:
            return {"state": self.state, "phase": self.phase,
                    "completed": self.completed, "total": self.total,
                    "error": self.error}


_jobs: dict[str, CompressionJob] = {}
_jobs_lock = Lock()


def cleanup_expired_jobs() -> None:
    now = time.time()
    with _jobs_lock:
        expired = [key for key, job in _jobs.items()
                   if now - job.created_at >= RETENTION_SECONDS]
        for key in expired:
            job = _jobs.pop(key)
            job.cancelled.set()
            with job.lock:
                job.result = None


def create_job() -> CompressionJob:
    cleanup_expired_jobs()
    job = CompressionJob(id=uuid4().hex)
    with _jobs_lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> CompressionJob | None:
    cleanup_expired_jobs()
    with _jobs_lock:
        return _jobs.get(job_id)


def delete_job(job_id: str) -> None:
    with _jobs_lock:
        job = _jobs.pop(job_id, None)
    if job is not None:
        job.cancelled.set()
        with job.lock:
            job.result = None


def start_job(job: CompressionJob, source: bytes, level: str) -> None:
    def run() -> None:
        source_stream = BytesIO(source)
        try:
            result = compress_document(source_stream, level, job.progress, job.check_cancel)
            job.finish(result)
        except CompressionCancelled:
            with job.lock:
                job.state = "cancelled"
                job.phase = "Cancelled"
        except CompressValidationError as exc:
            with job.lock:
                job.state = "error"
                job.error = str(exc)
        except Exception:
            with job.lock:
                job.state = "error"
                job.error = "The PDF could not be compressed. Choose another file and try again."
        finally:
            source_stream.close()

    with job.lock:
        job.state = "processing"
        job.phase = "Preparing PDF"
    Thread(target=run, name=f"compress-pdf-{job.id[:8]}", daemon=True).start()
