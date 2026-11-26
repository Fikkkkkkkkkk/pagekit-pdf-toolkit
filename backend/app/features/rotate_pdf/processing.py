"""Read one PDF and rotate its pages without changing their order."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .validation import RotateValidationError, validate_rotations

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)


def rotate_document(path: Path, raw_rotations: str) -> BytesIO:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise RotateValidationError("This PDF is password protected. Choose an unlocked PDF.")
        page_count = len(reader.pages)
        if not page_count:
            raise RotateValidationError("This PDF has no pages to rotate.")
    except RotateValidationError:
        raise
    except PDF_ERRORS as exc:
        raise RotateValidationError("This PDF cannot be read. Replace it and try again.") from exc

    rotations = validate_rotations(raw_rotations, page_count)
    writer = PdfWriter()
    output = BytesIO()
    try:
        for page, angle in zip(reader.pages, rotations):
            if angle:
                page.rotate(angle)
            writer.add_page(page)
        writer.write(output)
    except PDF_ERRORS as exc:
        raise RotateValidationError("A page could not be rotated. Choose another PDF and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
