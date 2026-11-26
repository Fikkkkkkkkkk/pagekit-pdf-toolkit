"""Place a transparent visual signature on selected PDF pages."""

import math
import zlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from ...shared.progress import ProgressReporter
from .validation import Placement, SignValidationError, validate_rotated_bounds

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)


def _image_stream(writer: PdfWriter, data: bytes, width: int, height: int, grayscale: bool):
    stream = DecodedStreamObject()
    stream.set_data(zlib.compress(data))
    stream.update({
        NameObject('/Type'): NameObject('/XObject'),
        NameObject('/Subtype'): NameObject('/Image'),
        NameObject('/Width'): NumberObject(width),
        NameObject('/Height'): NumberObject(height),
        NameObject('/ColorSpace'): NameObject('/DeviceGray' if grayscale else '/DeviceRGB'),
        NameObject('/BitsPerComponent'): NumberObject(8),
        NameObject('/Filter'): NameObject('/FlateDecode'),
    })
    return writer._add_object(stream)


def _signature_object(writer: PdfWriter, path: Path):
    try:
        with Image.open(path) as source:
            source.load()
            if source.width * source.height > 12_000_000:
                raise SignValidationError('The signature image is too large. Choose an image below 12 megapixels.')
            image = ImageOps.exif_transpose(source).convert('RGBA')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise SignValidationError('The signature image cannot be read. Choose a valid PNG or JPG.') from exc
    if image.getchannel('A').getextrema()[1] == 0:
        raise SignValidationError('The signature image is fully transparent. Draw or choose a visible signature.')
    width, height = image.size
    rgb = _image_stream(writer, image.convert('RGB').tobytes(), width, height, False)
    if image.getchannel('A').getextrema()[0] < 255:
        rgb.get_object()[NameObject('/SMask')] = _image_stream(writer, image.getchannel('A').tobytes(), width, height, True)
    return rgb


def _place(writer: PdfWriter, page, image_ref, placement: Placement):
    crop = page.cropbox
    left, bottom = float(crop.left), float(crop.bottom)
    width, height = float(crop.width), float(crop.height)
    rotation = page.rotation % 360
    if width <= 0 or height <= 0 or rotation not in (0, 90, 180, 270):
        raise SignValidationError(f'Page {placement.page} has unsupported bounds or rotation.')
    display_width, display_height = (height, width) if rotation in (90, 270) else (width, height)
    validate_rotated_bounds(placement, display_width, display_height)
    a, b, c, d, tx, ty = {
        0: (1, 0, 0, 1, left, bottom),
        90: (0, 1, -1, 0, left + width, bottom),
        180: (-1, 0, 0, -1, left + width, bottom + height),
        270: (0, -1, 1, 0, left, bottom + height),
    }[rotation]
    resources = page.get('/Resources')
    if resources is None:
        resources = DictionaryObject()
        page[NameObject('/Resources')] = resources
    resources = resources.get_object()
    xobjects = resources.get('/XObject')
    if xobjects is None:
        xobjects = DictionaryObject()
        resources[NameObject('/XObject')] = xobjects
    xobjects = xobjects.get_object()
    name = NameObject('/PKSignature')
    suffix = 1
    while name in xobjects:
        name = NameObject(f'/PKSignature{suffix}')
        suffix += 1
    xobjects[name] = image_ref
    center_x = (placement.x + placement.width / 2) * display_width
    center_y = (1 - placement.y - placement.height / 2) * display_height
    image_width = placement.width * display_width
    image_height = placement.height * display_height
    radians = math.radians(placement.angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    stream = DecodedStreamObject()
    stream.set_data((f'q\n{a} {b} {c} {d} {tx:.5f} {ty:.5f} cm\n'
                     f'{cosine:.8f} {-sine:.8f} {sine:.8f} {cosine:.8f} {center_x:.5f} {center_y:.5f} cm\n'
                     f'{image_width:.5f} 0 0 {image_height:.5f} {-image_width / 2:.5f} {-image_height / 2:.5f} cm\n'
                     f'{name} Do\nQ\n').encode('ascii'))
    overlay = writer._add_object(stream)
    original = page.get('/Contents')
    if original is None:
        page[NameObject('/Contents')] = overlay
    else:
        resolved = original.get_object()
        existing = list(resolved) if isinstance(resolved, ArrayObject) else [original]
        page[NameObject('/Contents')] = ArrayObject([*existing, overlay])


def sign_document(pdf_path: Path, signature_path: Path, raw_placements: str,
                  progress: ProgressReporter | None = None) -> BytesIO:
    try:
        reader = PdfReader(pdf_path, strict=False)
        if reader.is_encrypted:
            raise SignValidationError('This PDF is password protected. Choose an unlocked PDF.')
        page_count = len(reader.pages)
        if not page_count:
            raise SignValidationError('This PDF has no pages.')
        from .validation import parse_placements
        placements = parse_placements(raw_placements, page_count)
    except SignValidationError:
        raise
    except PDF_ERRORS as exc:
        raise SignValidationError('This PDF cannot be read. Choose another PDF.') from exc
    output = BytesIO()
    writer = None
    if progress:
        progress.start(len(placements) + 2, 'Preparing signature')
    try:
        writer = PdfWriter(clone_from=reader)
        image_ref = _signature_object(writer, signature_path)
        if progress:
            progress.advance('Preparing signature')
        for placement in placements:
            if progress:
                progress.check()
            _place(writer, writer.pages[placement.page - 1], image_ref, placement)
            if progress:
                progress.advance('Placing signature')
        if progress:
            progress.set_phase('Writing signed PDF')
        writer.write(output)
        if progress:
            progress.advance('Writing signed PDF')
    except SignValidationError:
        raise
    except PDF_ERRORS as exc:
        raise SignValidationError('The signature could not be added. Check the PDF and try again.') from exc
    finally:
        if writer is not None:
            writer.close()
    output.seek(0)
    return output
