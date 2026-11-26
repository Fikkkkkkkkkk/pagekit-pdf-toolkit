"""Validate browser-rendered JPG pages before ZIP packaging."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

MAX_PAGE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class PdfToJpgValidationError(ValueError):
    pass


def read_jpg_page(upload: FileStorage, position: int, total_so_far: int) -> bytes:
    data = BytesIO()
    size = 0
    while chunk := upload.stream.read(CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_PAGE_BYTES:
            raise PdfToJpgValidationError(f"Page {position} is over the 25 MB image limit. Try a lower quality.")
        if total_so_far + size > MAX_TOTAL_BYTES:
            raise PdfToJpgValidationError("The converted images exceed the 100 MB total limit. Try a lower quality.")
        data.write(chunk)
    content = data.getvalue()
    if not content.startswith(b"\xff\xd8\xff"):
        raise PdfToJpgValidationError(f"Page {position} is not a valid JPG image. Try converting again.")
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != "JPEG":
                raise PdfToJpgValidationError(f"Page {position} is not a valid JPG image. Try converting again.")
            image.verify()
    except PdfToJpgValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise PdfToJpgValidationError(f"Page {position} could not be read as a JPG. Try converting again.") from exc
    return content
