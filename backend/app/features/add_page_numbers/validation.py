"""Upload and numbering-option validation."""

import re
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
POSITIONS = frozenset({"top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"})
MAX_NUMBER = 999999


class PageNumberValidationError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise PageNumberValidationError("Choose one .pdf file to number.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise PageNumberValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise PageNumberValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise PageNumberValidationError("This file is not a valid PDF.")


def validate_options(position: str, raw_start: str, page_count: int) -> int:
    if position not in POSITIONS:
        raise PageNumberValidationError("Choose a valid page-number position.")
    if not re.fullmatch(r"[0-9]+", raw_start or "") or len(raw_start) > 6:
        raise PageNumberValidationError("Starting number must be a positive whole number.")
    start = int(raw_start)
    if start < 1 or start + page_count - 1 > MAX_NUMBER:
        raise PageNumberValidationError(f"Choose a starting number from 1 to {MAX_NUMBER - page_count + 1} for this PDF.")
    return start
