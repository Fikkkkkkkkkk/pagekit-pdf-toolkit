"""Short-lived in-process progress for PDF requests."""

import time
from dataclasses import dataclass, field
from secrets import token_urlsafe
from threading import Event, Lock

from flask import Blueprint, jsonify, request

RETENTION_SECONDS = 15 * 60


class ProgressCancelled(Exception):
    """The client cancelled an active PDF request."""


@dataclass
class ProgressReporter:
    created_at: float = field(default_factory=time.time)
    lock: Lock = field(default_factory=Lock)
    cancelled: Event = field(default_factory=Event)
    phase: str = "Waiting for upload"
    completed: int = 0
    total: int = 0

    def check(self) -> None:
        if self.cancelled.is_set() or time.time() - self.created_at >= RETENTION_SECONDS:
            raise ProgressCancelled()

    def start(self, total: int, phase: str) -> None:
        self.check()
        with self.lock:
            self.total = total
            self.completed = 0
            self.phase = phase

    def advance(self, phase: str) -> None:
        self.check()
        with self.lock:
            self.completed += 1
            self.phase = phase

    def update(self, phase: str, completed: int, total: int) -> None:
        self.check()
        with self.lock:
            self.phase = phase
            self.completed = completed
            self.total = total

    def set_phase(self, phase: str) -> None:
        self.check()
        with self.lock:
            self.phase = phase

    def snapshot(self) -> dict:
        with self.lock:
            return {"phase": self.phase, "completed": self.completed, "total": self.total}


_progress: dict[str, ProgressReporter] = {}
_lock = Lock()
progress_blueprint = Blueprint("pdf_progress", __name__)


def cleanup_expired_progress() -> None:
    now = time.time()
    with _lock:
        expired = [key for key, item in _progress.items()
                   if now - item.created_at >= RETENTION_SECONDS]
        for key in expired:
            _progress.pop(key).cancelled.set()


def progress_for_request() -> ProgressReporter | None:
    progress_id = request.headers.get("X-PageKit-Progress-ID")
    if not progress_id:
        return None
    with _lock:
        item = _progress.get(progress_id)
    if item is None:
        raise ProgressCancelled()
    item.check()
    return item


@progress_blueprint.before_app_request
def remove_expired_progress():
    cleanup_expired_progress()


@progress_blueprint.post("/api/progress")
def create_progress():
    progress_id = token_urlsafe(18)
    with _lock:
        _progress[progress_id] = ProgressReporter()
    response = jsonify(id=progress_id)
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response


@progress_blueprint.get("/api/progress/<progress_id>")
def read_progress(progress_id: str):
    with _lock:
        item = _progress.get(progress_id)
    if item is None:
        return jsonify(error="Progress expired. Try again."), 404
    response = jsonify(item.snapshot())
    response.headers["Cache-Control"] = "no-store"
    return response


@progress_blueprint.delete("/api/progress/<progress_id>")
def cancel_progress(progress_id: str):
    with _lock:
        item = _progress.pop(progress_id, None)
    if item is not None:
        item.cancelled.set()
    return "", 204
