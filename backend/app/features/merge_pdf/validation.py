"""Upload rules for the Merge PDF feature."""

from pathlib import Path
from werkzeug.datastructures import FileStorage

MAX_FILES = 20
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class MergeValidationError(ValueError):
    pass


def validate_file_count(files: list[FileStorage]) -> None:
    if len(files) < 2:
        raise MergeValidationError("Choose at least two PDF files to merge.")
    if len(files) > MAX_FILES:
        raise MergeValidationError(f"Choose no more than {MAX_FILES} PDF files.")


def save_validated_file(upload: FileStorage, target: Path, position: int, total_so_far: int) -> int:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise MergeValidationError(f"File {position} must have a .pdf extension.")

    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise MergeValidationError(f"File {position} is over the 25 MB limit.")
            if total_so_far + size > MAX_TOTAL_BYTES:
                raise MergeValidationError("The selected files exceed the 100 MB total limit.")
            output.write(chunk)

    if not size:
        raise MergeValidationError(f"File {position} is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise MergeValidationError(f"File {position} is not a valid PDF.")
    return size
