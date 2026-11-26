"""Upload and requested-angle validation for Rotate PDF."""

import json
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class RotateValidationError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise RotateValidationError("Choose one .pdf file to rotate.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise RotateValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise RotateValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise RotateValidationError("This file is not a valid PDF.")


def validate_rotations(raw_rotations: str, page_count: int) -> list[int]:
    try:
        rotations = json.loads(raw_rotations)
    except (TypeError, ValueError) as exc:
        raise RotateValidationError("The page rotations are invalid. Reload the PDF and try again.") from exc
    if not isinstance(rotations, list) or len(rotations) != page_count:
        raise RotateValidationError(f"Provide one rotation for each of the {page_count} pages.")
    if any(type(angle) is not int or angle not in (0, 90, 180, 270) for angle in rotations):
        raise RotateValidationError("Each page rotation must be 0, 90, 180, or 270 degrees clockwise.")
    return rotations
