"""Upload and known-password validation for Unlock PDF."""

from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class UnlockValidationError(ValueError):
    pass


def validate_password(password: str) -> str:
    if not password or not password.strip():
        raise UnlockValidationError("Enter the known password for this PDF.")
    return password


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise UnlockValidationError("Choose one .pdf file to unlock.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise UnlockValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise UnlockValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise UnlockValidationError("This file is not a valid PDF.")
