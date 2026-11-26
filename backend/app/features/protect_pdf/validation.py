"""Upload and password validation for Protect PDF."""

from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class ProtectValidationError(ValueError):
    pass


def validate_passwords(password: str, confirmation: str) -> str:
    if not password or not password.strip():
        raise ProtectValidationError("Enter a password to open the protected PDF.")
    if password != confirmation:
        raise ProtectValidationError("The passwords do not match. Enter the same password twice.")
    return password


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise ProtectValidationError("Choose one .pdf file to protect.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ProtectValidationError("The PDF is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise ProtectValidationError("The PDF is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise ProtectValidationError("This file is not a valid PDF.")
