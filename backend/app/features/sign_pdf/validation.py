"""Validate PDF, signature image, and page-relative placements."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_SIGNATURE_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class SignValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Placement:
    page: int
    x: float
    y: float
    width: float
    height: float
    angle: float


def _save_file(upload: FileStorage, target: Path, maximum: int, label: str) -> None:
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > maximum:
                raise SignValidationError(f"The {label} is over the {maximum // (1024 * 1024)} MB limit.")
            output.write(chunk)
    if not size:
        raise SignValidationError(f"The {label} is empty. Choose a readable file.")


def save_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise SignValidationError("Choose one .pdf file to sign.")
    _save_file(upload, target, MAX_PDF_BYTES, "PDF")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise SignValidationError("This file is not a valid PDF.")


def save_signature(upload: FileStorage, target: Path) -> None:
    if not upload.filename or Path(upload.filename).suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise SignValidationError("Choose a PNG or JPG signature image.")
    _save_file(upload, target, MAX_SIGNATURE_BYTES, "signature image")
    with target.open("rb") as saved:
        header = saved.read(8)
    if not (header == b"\x89PNG\r\n\x1a\n" or header.startswith(b"\xff\xd8\xff")):
        raise SignValidationError("The signature is not a valid PNG or JPG image.")


def parse_placements(raw: str, page_count: int) -> list[Placement]:
    try:
        values = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise SignValidationError("Signature placements are malformed. Review the pages and try again.") from exc
    if not isinstance(values, list) or not values:
        raise SignValidationError("Add the signature to at least one page.")
    if len(values) > page_count:
        raise SignValidationError("Choose no more than one signature placement per page.")
    placements = []
    used_pages = set()
    for value in values:
        if not isinstance(value, dict):
            raise SignValidationError("A signature placement is malformed. Review the pages and try again.")
        page = value.get("page")
        if type(page) is not int or not 1 <= page <= page_count:
            raise SignValidationError(f"Choose a signature page from 1 to {page_count}.")
        if page in used_pages:
            raise SignValidationError(f"Page {page} has more than one signature placement.")
        used_pages.add(page)
        numbers = []
        for field in ("x", "y", "width", "height", "angle"):
            number = value.get(field, 0 if field == "angle" else None)
            if type(number) not in (int, float) or not math.isfinite(number):
                raise SignValidationError(f"Page {page} has an invalid signature position or size.")
            numbers.append(float(number))
        x, y, width, height, angle = numbers
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1.000001 or y + height > 1.000001:
            raise SignValidationError(f"Page {page} has a signature outside its visible area. Move or resize it and try again.")
        if angle < -180 or angle > 180:
            raise SignValidationError(f"Page {page} has an invalid signature angle. Choose -180 to 180 degrees.")
        placements.append(Placement(page, x, y, width, height, angle))
    return placements


def validate_rotated_bounds(placement: Placement, page_width: float, page_height: float) -> None:
    radians = math.radians(placement.angle)
    cosine, sine = abs(math.cos(radians)), abs(math.sin(radians))
    half_x = (cosine * placement.width * page_width + sine * placement.height * page_height) / 2
    half_y = (sine * placement.width * page_width + cosine * placement.height * page_height) / 2
    center_x = (placement.x + placement.width / 2) * page_width
    center_y = (placement.y + placement.height / 2) * page_height
    if (center_x - half_x < -0.001 or center_x + half_x > page_width + 0.001
            or center_y - half_y < -0.001 or center_y + half_y > page_height + 0.001):
        raise SignValidationError(f"Page {placement.page} has a rotated signature outside its visible area. Move or resize it and try again.")
