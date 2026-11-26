"""Add a text watermark to each PDF page without changing the source file."""

import math
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject

from ...shared.progress import ProgressReporter
from .validation import WatermarkOptions, WatermarkValidationError

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)
FONT_NAMES = {
    "helvetica": ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"),
    "times": ("Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic"),
    "courier": ("Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique"),
}
WIDTH_FACTORS = {"helvetica": 0.52, "times": 0.49, "courier": 0.60}


def _pdf_literal(text: str) -> bytes:
    """Use octal escapes so PDF syntax and WinAnsi bytes remain unambiguous."""
    return b"(" + b"".join(f"\\{value:03o}".encode("ascii") for value in text.encode("cp1252")) + b")"


def _resource_dictionary(page, name: str) -> DictionaryObject:
    resources = page.get("/Resources")
    if resources is None:
        resources = DictionaryObject()
        page[NameObject("/Resources")] = resources
    else:
        resources = resources.get_object()
    child = resources.get(name)
    if child is None:
        child = DictionaryObject()
        resources[NameObject(name)] = child
    return child.get_object()


def _unique_name(resources: DictionaryObject, base: str) -> NameObject:
    name = NameObject(base)
    suffix = 1
    while name in resources:
        name = NameObject(f"{base}{suffix}")
        suffix += 1
    return name


def _add_watermark(writer: PdfWriter, page, options: WatermarkOptions) -> None:
    crop = page.cropbox
    left, bottom = float(crop.left), float(crop.bottom)
    width, height = float(crop.width), float(crop.height)
    page_rotation = page.rotation % 360
    if page_rotation not in (0, 90, 180, 270):
        raise WatermarkValidationError("A page has an unsupported rotation. Rotate it to a 90-degree step first.")
    display_width, display_height = (height, width) if page_rotation in (90, 270) else (width, height)
    if options.mosaic:
        placements = [(display_width * x, display_height * y, "center")
                      for y in (0.12, 0.37, 0.62, 0.87) for x in (0.16, 0.5, 0.84)]
    else:
        vertical, horizontal = options.position.split("-")
        placements = [(display_width * {"left": 0.16, "center": 0.5, "right": 0.84}[horizontal],
                       display_height * {"bottom": 0.16, "middle": 0.5, "top": 0.84}[vertical], horizontal)]
    width_factor = WIDTH_FACTORS[options.font_family]
    available_width = display_width * (0.27 if options.mosaic else 0.82)
    font_size = min(float(options.font_size), available_width / max(len(options.text) * width_factor, 1))
    estimated_width = len(options.text) * font_size * width_factor

    display_matrix = {
        0: (1, 0, 0, 1, left, bottom),
        90: (0, 1, -1, 0, left + width, bottom),
        180: (-1, 0, 0, -1, left + width, bottom + height),
        270: (0, -1, 1, 0, left, bottom + height),
    }[page_rotation]
    radians = math.radians(options.rotation)
    cosine, sine = math.cos(radians), math.sin(radians)
    font_resources = _resource_dictionary(page, "/Font")
    font_name = _unique_name(font_resources, "/PKWatermark")
    variant = int(options.bold) + 2 * int(options.italic)
    font_resources[font_name] = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/" + FONT_NAMES[options.font_family][variant]),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    states = _resource_dictionary(page, "/ExtGState")
    state_name = _unique_name(states, "/PKWatermarkAlpha")
    alpha = FloatObject(options.opacity / 100)
    states[state_name] = DictionaryObject({NameObject("/Type"): NameObject("/ExtGState"), NameObject("/ca"): alpha, NameObject("/CA"): alpha})
    red, green, blue = options.color
    a, b, c, d, tx, ty = display_matrix
    parts = [(f"q\n{state_name} gs\n{a} {b} {c} {d} {tx:.3f} {ty:.3f} cm\n"
              f"{red:.4f} {green:.4f} {blue:.4f} rg\n").encode("ascii")]
    for x, y, alignment in placements:
        offset_x = {"left": 0, "center": -estimated_width / 2, "right": -estimated_width}[alignment]
        baseline = -font_size * 0.35
        parts.append((f"q\n{cosine:.6f} {sine:.6f} {-sine:.6f} {cosine:.6f} {x:.3f} {y:.3f} cm\n"
                      f"BT\n{font_name} {font_size:.3f} Tf\n"
                      f"{offset_x:.3f} {baseline:.3f} Td\n").encode("ascii"))
        parts.append(_pdf_literal(options.text) + b" Tj\nET\n")
        if options.underline:
            underline_y = baseline - font_size * 0.1
            parts.append((f"{red:.4f} {green:.4f} {blue:.4f} RG\n"
                          f"{max(0.5, font_size * 0.05):.3f} w\n"
                          f"{offset_x:.3f} {underline_y:.3f} m\n"
                          f"{offset_x + estimated_width:.3f} {underline_y:.3f} l\nS\n").encode("ascii"))
        parts.append(b"Q\n")
    parts.append(b"Q\n")
    stream = DecodedStreamObject()
    stream.set_data(b"".join(parts))
    overlay = writer._add_object(stream)
    original = page.get("/Contents")
    if original is None:
        page[NameObject("/Contents")] = overlay
    else:
        resolved = original.get_object()
        existing = list(resolved) if isinstance(resolved, ArrayObject) else [original]
        page[NameObject("/Contents")] = ArrayObject([*existing, overlay] if options.layer == "over" else [overlay, *existing])


def watermark_document(path: Path, options: WatermarkOptions, progress: ProgressReporter | None = None) -> BytesIO:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise WatermarkValidationError("This PDF is password protected. Choose an unlocked PDF.")
        page_count = len(reader.pages)
        if not page_count:
            raise WatermarkValidationError("This PDF has no pages to watermark.")
    except WatermarkValidationError:
        raise
    except PDF_ERRORS as exc:
        raise WatermarkValidationError("This PDF cannot be read. Replace it and try again.") from exc

    writer = None
    output = BytesIO()
    if progress:
        progress.start(page_count + 2, "Copying document")
    try:
        writer = PdfWriter(clone_from=reader)
        if progress:
            progress.advance("Copying document")
        for page in writer.pages:
            if progress:
                progress.check()
            _add_watermark(writer, page, options)
            if progress:
                progress.advance("Adding watermarks")
        if progress:
            progress.set_phase("Writing watermarked PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing watermarked PDF")
    except WatermarkValidationError:
        raise
    except PDF_ERRORS as exc:
        raise WatermarkValidationError("The watermark could not be added. Choose another PDF and try again.") from exc
    finally:
        if writer is not None:
            writer.close()
    output.seek(0)
    return output
