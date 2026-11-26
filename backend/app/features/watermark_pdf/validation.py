"""Validate one PDF and text-watermark options."""

import re
from dataclasses import dataclass
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
POSITIONS = frozenset(f"{vertical}-{horizontal}" for vertical in ("top", "middle", "bottom") for horizontal in ("left", "center", "right"))
FONT_FAMILIES = frozenset({"helvetica", "times", "courier"})


class WatermarkValidationError(ValueError):
    pass


@dataclass(frozen=True)
class WatermarkOptions:
    text: str
    position: str
    rotation: int
    color: tuple[float, float, float]
    opacity: int
    font_family: str
    font_size: int
    bold: bool
    italic: bool
    underline: bool
    mosaic: bool
    layer: str


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise WatermarkValidationError("Choose one .pdf file to watermark.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise WatermarkValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise WatermarkValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise WatermarkValidationError("This file is not a valid PDF.")


def _boolean(value: str, label: str) -> bool:
    if value not in ("true", "false"):
        raise WatermarkValidationError(f"Choose a valid {label} setting.")
    return value == "true"


def validate_options(text: str, position: str, rotation: str, color: str, opacity: str,
                     font_family: str = "helvetica", font_size: str = "36", bold: str = "false",
                     italic: str = "false", underline: str = "false", mosaic: str = "false",
                     layer: str = "over") -> WatermarkOptions:
    if not text or not text.strip():
        raise WatermarkValidationError("Enter text for the watermark.")
    if len(text) > 80 or "\n" in text or "\r" in text or any(ord(char) < 32 for char in text):
        raise WatermarkValidationError("Use a single line of watermark text, up to 80 characters.")
    try:
        text.encode("cp1252")
    except UnicodeEncodeError as exc:
        raise WatermarkValidationError("This watermark font supports Western European characters only. Remove unsupported symbols and try again.") from exc
    if position not in POSITIONS:
        raise WatermarkValidationError("Choose a valid watermark position.")
    if not re.fullmatch(r"-?(?:0|[1-9][0-9]*)", rotation or "") or not -180 <= int(rotation) <= 180:
        raise WatermarkValidationError("Choose a rotation from -180 to 180 degrees.")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color or ""):
        raise WatermarkValidationError("Choose a valid six-digit watermark color.")
    if not re.fullmatch(r"[0-9]+", opacity or "") or not 1 <= int(opacity) <= 100:
        raise WatermarkValidationError("Choose an opacity from 1% to 100%.")
    if font_family not in FONT_FAMILIES:
        raise WatermarkValidationError("Choose Helvetica, Times, or Courier for the watermark font.")
    if not re.fullmatch(r"[0-9]+", font_size or "") or not 8 <= int(font_size) <= 72:
        raise WatermarkValidationError("Choose a font size from 8 to 72 points.")
    if layer not in ("over", "behind"):
        raise WatermarkValidationError("Choose whether the watermark appears over or behind page content.")
    rgb = tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
    return WatermarkOptions(text, position, int(rotation), rgb, int(opacity), font_family,
                            int(font_size), _boolean(bold, "bold"), _boolean(italic, "italic"),
                            _boolean(underline, "underline"), _boolean(mosaic, "mosaic"), layer)
