"""Image upload and page-option validation."""

from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_FILES = 20
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
EXTENSIONS = {".jpg", ".jpeg", ".png"}


class ImagePdfValidationError(ValueError):
    pass


def validate_options(page_size: str, orientation: str) -> None:
    if page_size not in ("a4", "letter", "fit"):
        raise ImagePdfValidationError("Choose A4, Letter, or Fit to image for the page size.")
    if orientation not in ("portrait", "landscape"):
        raise ImagePdfValidationError("Choose portrait or landscape page orientation.")


def validate_file_count(files: list[FileStorage]) -> None:
    if not files:
        raise ImagePdfValidationError("Choose at least one JPG or PNG image.")
    if len(files) > MAX_FILES:
        raise ImagePdfValidationError(f"Choose no more than {MAX_FILES} images.")


def save_validated_image(upload: FileStorage, target: Path, position: int, total_so_far: int) -> int:
    extension = Path(upload.filename or "").suffix.lower()
    if extension not in EXTENSIONS:
        raise ImagePdfValidationError(f"Image {position} must be a .jpg, .jpeg, or .png file.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ImagePdfValidationError(f"Image {position} is over the 25 MB limit.")
            if total_so_far + size > MAX_TOTAL_BYTES:
                raise ImagePdfValidationError("The selected images exceed the 100 MB total limit.")
            output.write(chunk)
    if not size:
        raise ImagePdfValidationError(f"Image {position} is empty. Choose a readable image.")
    with target.open("rb") as saved:
        header = saved.read(8)
    matches = header.startswith(b"\xff\xd8\xff") if extension in (".jpg", ".jpeg") else header == b"\x89PNG\r\n\x1a\n"
    if not matches:
        raise ImagePdfValidationError(f"Image {position} is not a valid {extension.upper().lstrip('.')} file. Replace it and try again.")
    return size
