"""Private temporary storage for image-to-PDF requests."""

import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator

RETENTION_SECONDS = 15 * 60
TEMP_ROOT = Path(__file__).resolve().parents[3] / "tmp" / "jpg_to_pdf"
_active_requests: set[Path] = set()
_active_lock = Lock()


def cleanup_stale_requests(now: float | None = None) -> None:
    if not TEMP_ROOT.exists():
        return
    current_time = time.time() if now is None else now
    for entry in TEMP_ROOT.iterdir():
        if not entry.is_dir() or entry.is_symlink():
            continue
        try:
            with _active_lock:
                active = entry in _active_requests
            if not active and current_time - entry.stat().st_mtime >= RETENTION_SECONDS:
                shutil.rmtree(entry)
        except FileNotFoundError:
            continue


@contextmanager
def request_directory() -> Iterator[Path]:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="request-", dir=TEMP_ROOT) as path:
        request_path = Path(path)
        with _active_lock:
            _active_requests.add(request_path)
        try:
            yield request_path
        finally:
            with _active_lock:
                _active_requests.discard(request_path)
