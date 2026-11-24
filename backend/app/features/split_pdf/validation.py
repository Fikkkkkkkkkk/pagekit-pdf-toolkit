"""Input and range validation for Split PDF."""

import re
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_RANGES = 100
CHUNK_SIZE = 1024 * 1024
RANGE_PATTERN = re.compile(r"([0-9]+)(?:-([0-9]+))?")


class SplitValidationError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage | None, target: Path) -> None:
    if upload is None or not upload.filename:
        raise SplitValidationError("Choose one PDF file to split.")
    if not upload.filename.lower().endswith(".pdf"):
        raise SplitValidationError("Choose a file with a .pdf extension.")

    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise SplitValidationError("The PDF is over the 25 MB file limit.")
            output.write(chunk)

    if not size:
        raise SplitValidationError("The PDF is empty. Choose a readable file.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise SplitValidationError("This file is not a valid PDF. Choose a readable PDF.")


def parse_ranges(text: str, page_count: int) -> list[tuple[int, int]]:
    if not text.strip():
        raise SplitValidationError("Enter at least one page range, such as 1-3, 5, 8-10.")
    parts = text.split(",")
    if len(parts) > MAX_RANGES:
        raise SplitValidationError(f"Enter no more than {MAX_RANGES} page ranges.")

    ranges: list[tuple[int, int]] = []
    for position, part in enumerate(parts, start=1):
        match = RANGE_PATTERN.fullmatch(part.strip())
        if not match:
            raise SplitValidationError(f"Range {position} is malformed. Use page numbers such as 1-3 or 5, separated by commas.")
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        if start < 1 or end < start:
            raise SplitValidationError(f"Range {position} must start at page 1 or later and end on or after its start page.")
        if end > page_count:
            raise SplitValidationError(f"Range {position} goes beyond this PDF’s {page_count} pages.")
        if any(start <= previous_end and end >= previous_start for previous_start, previous_end in ranges):
            raise SplitValidationError(f"Range {position} overlaps another range. Choose each page only once.")
        ranges.append((start, end))
    return ranges
