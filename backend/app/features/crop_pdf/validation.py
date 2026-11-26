"""Upload and crop-area validation for Crop PDF."""

import json
import math
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class CropValidationError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise CropValidationError("Choose one .pdf file to crop.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise CropValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise CropValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise CropValidationError("This file is not a valid PDF.")


def validate_crop(raw_crop: str) -> tuple[float, float, float, float]:
    try:
        crop = json.loads(raw_crop)
    except (TypeError, ValueError) as exc:
        raise CropValidationError("The crop area is invalid. Select a rectangle and try again.") from exc
    if not isinstance(crop, dict) or set(crop) != {"left", "top", "right", "bottom"}:
        raise CropValidationError("The crop area is invalid. Select a rectangle and try again.")
    values = tuple(crop[key] for key in ("left", "top", "right", "bottom"))
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise CropValidationError("Crop edges must be finite numbers between 0 and 1.")
    left, top, right, bottom = values
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise CropValidationError("Choose a crop area inside the page with a positive width and height.")
    return left, top, right, bottom
