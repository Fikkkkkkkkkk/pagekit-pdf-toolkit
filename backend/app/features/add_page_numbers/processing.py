"""Overlay sequential page numbers without moving or removing source content."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject

from .validation import PageNumberValidationError, validate_options

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)
FONT_SIZE = 10
MARGIN = 24


def _add_number(writer: PdfWriter, page, value: int, position: str) -> None:
    """Append a Helvetica text stream, mapping visible placement through /Rotate."""
    crop = page.cropbox
    left, bottom = float(crop.left), float(crop.bottom)
    width, height = float(crop.width), float(crop.height)
    rotation = page.rotation % 360
    if rotation not in (0, 90, 180, 270):
        raise PageNumberValidationError("A page has an unsupported rotation. Rotate it to a 90-degree step first.")
    display_width, display_height = (height, width) if rotation in (90, 270) else (width, height)
    label = str(value)
    text_width = len(label) * FONT_SIZE * 0.556  # Standard Helvetica digits are 556 units wide.
    edge = min(MARGIN, display_width / 10, display_height / 10)
    vertical, horizontal = position.split("-")
    x = edge if horizontal == "left" else (display_width - text_width) / 2 if horizontal == "center" else display_width - edge - text_width
    y = display_height - edge - FONT_SIZE if vertical == "top" else edge

    if rotation == 0:
        a, b, c, d, tx, ty = 1, 0, 0, 1, left + x, bottom + y
    elif rotation == 90:
        a, b, c, d, tx, ty = 0, 1, -1, 0, left + width - y, bottom + x
    elif rotation == 180:
        a, b, c, d, tx, ty = -1, 0, 0, -1, left + width - x, bottom + height - y
    else:
        a, b, c, d, tx, ty = 0, -1, 1, 0, left + y, bottom + height - x

    resources = page.get("/Resources")
    if resources is None:
        resources = DictionaryObject()
        page[NameObject("/Resources")] = resources
    else:
        resources = resources.get_object()
    fonts = resources.get("/Font")
    if fonts is None:
        fonts = DictionaryObject()
        resources[NameObject("/Font")] = fonts
    else:
        fonts = fonts.get_object()
    font_name = "/PKPageNumber"
    suffix = 1
    while NameObject(font_name) in fonts:
        font_name = f"/PKPageNumber{suffix}"
        suffix += 1
    fonts[NameObject(font_name)] = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    stream = DecodedStreamObject()
    stream.set_data(
        f"q\nBT\n{font_name} {FONT_SIZE} Tf\n0 g\n{a} {b} {c} {d} {tx:.3f} {ty:.3f} Tm\n({label}) Tj\nET\nQ\n".encode("ascii")
    )
    overlay = writer._add_object(stream)
    original = page.get("/Contents")
    if original is None:
        page[NameObject("/Contents")] = overlay
    else:
        resolved = original.get_object()
        existing = list(resolved) if isinstance(resolved, ArrayObject) else [original]
        page[NameObject("/Contents")] = ArrayObject([*existing, overlay])


def number_document(path: Path, position: str, raw_start: str) -> BytesIO:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise PageNumberValidationError("This PDF is password protected. Choose an unlocked PDF.")
        page_count = len(reader.pages)
        if not page_count:
            raise PageNumberValidationError("This PDF has no pages to number.")
    except PageNumberValidationError:
        raise
    except PDF_ERRORS as exc:
        raise PageNumberValidationError("This PDF cannot be read. Replace it and try again.") from exc

    start = validate_options(position, raw_start, page_count)
    writer = PdfWriter()
    output = BytesIO()
    try:
        for index, source in enumerate(reader.pages):
            page = writer.add_page(source)
            _add_number(writer, page, start + index, position)
        writer.write(output)
    except PageNumberValidationError:
        raise
    except PDF_ERRORS as exc:
        raise PageNumberValidationError("A page could not be numbered. Choose another PDF and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
