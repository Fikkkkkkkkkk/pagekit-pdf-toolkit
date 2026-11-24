"""Upload validation for PDF to Word."""

from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class WordConversionError(ValueError):
    pass


def save_validated_pdf(upload: FileStorage, target: Path) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise WordConversionError("Choose one file with a .pdf extension.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise WordConversionError("This PDF is over the 25 MB file limit.")
            output.write(chunk)
    if not size:
        raise WordConversionError("This PDF is empty. Choose a readable file.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise WordConversionError("This file is not a valid PDF. Choose a readable PDF.")
