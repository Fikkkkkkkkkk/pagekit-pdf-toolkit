"""Set a visible crop box on every source page, preserving its content streams."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import RectangleObject

from ...shared.progress import ProgressReporter

from .validation import CropValidationError, validate_crop

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)


def _crop_page(page, area: tuple[float, float, float, float]) -> None:
    left, top, right, bottom = area
    box = page.cropbox
    x0, y0 = float(box.left), float(box.bottom)
    width, height = float(box.width), float(box.height)
    if width <= 0 or height <= 0:
        raise CropValidationError("A page has an invalid visible area and cannot be cropped.")
    rotation = page.rotation % 360
    if rotation == 0:
        bounds = (x0 + left * width, y0 + (1 - bottom) * height, x0 + right * width, y0 + (1 - top) * height)
    elif rotation == 90:
        bounds = (x0 + top * width, y0 + left * height, x0 + bottom * width, y0 + right * height)
    elif rotation == 180:
        bounds = (x0 + (1 - right) * width, y0 + top * height, x0 + (1 - left) * width, y0 + bottom * height)
    elif rotation == 270:
        bounds = (x0 + (1 - bottom) * width, y0 + (1 - right) * height, x0 + (1 - top) * width, y0 + (1 - left) * height)
    else:
        raise CropValidationError("A page has an unsupported rotation. Rotate it to a 90-degree step first.")
    page.cropbox = RectangleObject(bounds)


def crop_document(path: Path, raw_crop: str, progress: ProgressReporter | None = None) -> BytesIO:
    area = validate_crop(raw_crop)
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise CropValidationError("This PDF is password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise CropValidationError("This PDF has no pages to crop.")
    except CropValidationError:
        raise
    except PDF_ERRORS as exc:
        raise CropValidationError("This PDF cannot be read. Replace it and try again.") from exc

    writer = PdfWriter()
    output = BytesIO()
    if progress:
        progress.start(len(reader.pages) + 1, "Cropping pages")
    try:
        for source in reader.pages:
            if progress:
                progress.check()
            page = writer.add_page(source)
            _crop_page(page, area)
            if progress:
                progress.advance("Cropping pages")
        if progress:
            progress.set_phase("Writing cropped PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing cropped PDF")
    except CropValidationError:
        raise
    except PDF_ERRORS as exc:
        raise CropValidationError("A page could not be cropped. Choose another PDF and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
