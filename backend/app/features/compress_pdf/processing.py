"""Compress PDF streams and eligible images without discarding document structure."""

from io import BytesIO
from math import hypot
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import ContentStream

from .validation import CompressValidationError, validate_level

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)
# Target effective resolution at the image's largest displayed size, then JPEG quality.
IMAGE_SETTINGS = {"balanced": (185, 75), "strong": (120, 55)}
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _multiply(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j,
            a*k+c*l+e, b*k+d*l+f)


def _display_sizes(writer: PdfWriter) -> dict[int, tuple[float, float]]:
    """Find the largest width/height in inches at which each image is drawn."""
    sizes: dict[int, tuple[float, float]] = {}

    def visit(stream, resources, ctm, user_unit, ancestors):
        if stream is None or resources is None:
            return
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        xobjects = resources.get("/XObject", {})
        if hasattr(xobjects, "get_object"):
            xobjects = xobjects.get_object()
        stack = []
        for operands, operator in ContentStream(stream, writer).operations:
            if operator == b"q":
                stack.append(ctm)
            elif operator == b"Q":
                if stack:
                    ctm = stack.pop()
            elif operator == b"cm" and len(operands) == 6:
                ctm = _multiply(tuple(float(value) for value in operands), ctm)
            elif operator == b"Do" and operands:
                reference = xobjects.get(operands[0])
                if reference is None:
                    continue
                xobject = reference.get_object()
                if xobject.get("/Subtype") == "/Image" and hasattr(reference, "idnum"):
                    width = hypot(ctm[0], ctm[1]) * user_unit / 72
                    height = hypot(ctm[2], ctm[3]) * user_unit / 72
                    if width > 0 and height > 0:
                        old_width, old_height = sizes.get(reference.idnum, (0, 0))
                        sizes[reference.idnum] = (max(old_width, width), max(old_height, height))
                elif xobject.get("/Subtype") == "/Form" and hasattr(reference, "idnum"):
                    if reference.idnum in ancestors:
                        continue
                    matrix = xobject.get("/Matrix", IDENTITY)
                    form_ctm = _multiply(tuple(float(value) for value in matrix), ctm)
                    visit(xobject, xobject.get("/Resources", resources), form_ctm,
                          user_unit, ancestors | {reference.idnum})

    for page in writer.pages:
        resources = page.get("/Resources")
        if resources is not None:
            resources = resources.get_object()
        visit(page.get_contents(), resources, IDENTITY,
              float(page.get("/UserUnit", 1)), set())
    return sizes


def _compress_images(writer: PdfWriter, level: str, on_image: Callable[[], None] | None = None) -> None:
    target_dpi, quality = IMAGE_SETTINGS[level]
    sizes = _display_sizes(writer)
    seen: set[int] = set()
    for page in writer.pages:
        for embedded in page.images:
            reference = embedded.indirect_reference
            if reference is None or reference.idnum in seen:
                continue  # Inline images cannot be replaced; shared images only need one pass.
            seen.add(reference.idnum)
            try:
                _compress_image(writer, embedded, reference, sizes, target_dpi, quality)
            finally:
                if on_image is not None:
                    on_image()


def _compress_image(writer, embedded, reference, sizes, target_dpi, quality):
    display_size = sizes.get(reference.idnum)
    if display_size is None:
        return  # Unknown placement: retain the source image at full fidelity.
    original = reference.get_object()
    if original.get("/SMask") is not None or original.get("/Mask") is not None:
        return  # Keep transparency and masked images unchanged.
    try:
        image = embedded.image
        if image is None or image.mode not in ("RGB", "L"):
            return
        scale = min(1, target_dpi * display_size[0] / image.width,
                    target_dpi * display_size[1] / image.height)
        if scale < 1:
            image = image.resize(tuple(max(1, round(dimension * scale))
                                       for dimension in image.size), Image.Resampling.LANCZOS)
        embedded.replace(image, quality=quality)
        replacement = reference.get_object()
        if len(replacement._data) >= len(original._data):
            # ImageFile.replace swaps the writer object. Restore the exact source
            # stream when its encoded replacement does not save any bytes.
            writer._objects[reference.idnum - 1] = original
    except (UnidentifiedImageError, OSError, ValueError, TypeError):
        if reference.get_object() is not original:
            writer._objects[reference.idnum - 1] = original
        return  # Unsupported images stay intact; other pages still compress.


def compress_document(
    path: Path | BytesIO,
    raw_level: str,
    on_progress: Callable[[str, int, int], None] | None = None,
    check_cancel: Callable[[], None] | None = None,
) -> BytesIO:
    level = validate_level(raw_level)
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise CompressValidationError("This PDF is password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise CompressValidationError("This PDF has no pages to compress.")
    except CompressValidationError:
        raise
    except PDF_ERRORS as exc:
        raise CompressValidationError("This PDF cannot be read. Replace it and try again.") from exc

    writer = None
    output = BytesIO()
    try:
        # Clone the document root as well as pages so outlines, AcroForm, names,
        # metadata, and page labels are not lost by constructing a page-only PDF.
        writer = PdfWriter(clone_from=reader)
        completed = 0
        total = 0
        if on_progress is not None:
            image_count = 0
            if level in IMAGE_SETTINGS:
                image_ids = {image.indirect_reference.idnum for page in writer.pages
                             for image in page.images if image.indirect_reference is not None}
                image_count = len(image_ids)
            total = len(writer.pages) + image_count + 2
            on_progress("Compressing pages", completed, total)
        for page in writer.pages:
            if check_cancel is not None:
                check_cancel()
            page.compress_content_streams(level=9)
            if on_progress is not None:
                completed += 1
                on_progress("Compressing pages", completed, total)
        if level in IMAGE_SETTINGS:
            if on_progress is not None:
                on_progress("Inspecting images", completed, total)

            def image_done():
                nonlocal completed
                if check_cancel is not None:
                    check_cancel()
                completed += 1
                on_progress("Compressing images", completed, total)

            _compress_images(writer, level, image_done if on_progress is not None else None)
        if check_cancel is not None:
            check_cancel()
        if on_progress is not None:
            on_progress("Optimizing PDF objects", completed, total)
        writer.compress_identical_objects()
        if on_progress is not None:
            completed += 1
            on_progress("Writing output PDF", completed, total)
        if check_cancel is not None:
            check_cancel()
        writer.write(output)
        if check_cancel is not None:
            check_cancel()
    except PDF_ERRORS as exc:
        raise CompressValidationError("This PDF could not be compressed. Choose another file and try again.") from exc
    finally:
        if writer is not None:
            writer.close()
    output.seek(0)
    return output
