"""Upload and level validation for Compress PDF."""

from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
LEVELS = frozenset({"gentle", "balanced", "strong"})


class CompressValidationError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise CompressValidationError("Choose one .pdf file to compress.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise CompressValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise CompressValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise CompressValidationError("This file is not a valid PDF.")


def validate_level(level: str) -> str:
    if level not in LEVELS:
        raise CompressValidationError("Choose Gentle, Balanced, or Strong compression.")
    return level
