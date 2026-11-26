"""Embed ordered JPG and PNG images as PDF pages."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from ...shared.progress import ProgressReporter
from .validation import ImagePdfValidationError

PAPER_SIZES = {"a4": (595.28, 841.89), "letter": (612.0, 792.0)}
PAPER_MARGIN = 36.0
FIT_DPI = 96.0
MAX_FIT_POINTS = 2000.0
MAX_PIXELS = 50_000_000


def _prepared_image(path: Path, position: int, page_size: str, orientation: str) -> Image.Image:
    try:
        with Image.open(path) as source:
            if source.format not in ("JPEG", "PNG"):
                raise ImagePdfValidationError(f"Image {position} is not a readable JPG or PNG. Replace it and try again.")
            if source.width * source.height > MAX_PIXELS:
                raise ImagePdfValidationError(f"Image {position} has too many pixels to process safely. Choose a smaller image.")
            source.load()
            oriented = ImageOps.exif_transpose(source)
            if page_size == "fit" and oriented.width != oriented.height:
                is_landscape = oriented.width > oriented.height
                if is_landscape != (orientation == "landscape"):
                    oriented = oriented.rotate(90, expand=True)
            if "A" in oriented.getbands() or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
                return rgb
            return oriented.convert("RGB")
    except ImagePdfValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError) as exc:
        raise ImagePdfValidationError(f"Image {position} cannot be read. Replace it with a valid JPG or PNG and try again.") from exc


def _page_geometry(image: Image.Image, page_size: str, orientation: str) -> tuple[float, float, float, float, float, float]:
    if page_size == "fit":
        scale = min(72.0 / FIT_DPI, MAX_FIT_POINTS / max(image.size))
        width, height = image.width * scale, image.height * scale
        return width, height, 0.0, 0.0, width, height
    paper_width, paper_height = PAPER_SIZES[page_size]
    if orientation == "landscape":
        paper_width, paper_height = paper_height, paper_width
    max_width, max_height = paper_width - 2 * PAPER_MARGIN, paper_height - 2 * PAPER_MARGIN
    scale = min(max_width / image.width, max_height / image.height)
    draw_width, draw_height = image.width * scale, image.height * scale
    return paper_width, paper_height, (paper_width - draw_width) / 2, (paper_height - draw_height) / 2, draw_width, draw_height


def combine_images(paths: list[Path], page_size: str, orientation: str,
                   progress: ProgressReporter | None = None) -> BytesIO:
    writer = PdfWriter()
    output = BytesIO()
    if progress:
        progress.start(len(paths) + 1, "Adding images")
    try:
        for position, path in enumerate(paths, start=1):
            if progress:
                progress.check()
            image = _prepared_image(path, position, page_size, orientation)
            try:
                width, height, x, y, draw_width, draw_height = _page_geometry(image, page_size, orientation)
                encoded = BytesIO()
                image.save(encoded, format="JPEG", quality=90, subsampling=0)
                image_stream = DecodedStreamObject()
                image_stream.set_data(encoded.getvalue())
                image_stream.update({
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(image.width),
                    NameObject("/Height"): NumberObject(image.height),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                    NameObject("/Filter"): NameObject("/DCTDecode"),
                })
                image_ref = writer._add_object(image_stream)
                page = writer.add_blank_page(width=width, height=height)
                page[NameObject("/Resources")] = DictionaryObject({
                    NameObject("/XObject"): DictionaryObject({NameObject("/PKImage"): image_ref})
                })
                content = DecodedStreamObject()
                content.set_data(f"q\n{draw_width:.4f} 0 0 {draw_height:.4f} {x:.4f} {y:.4f} cm\n/PKImage Do\nQ\n".encode("ascii"))
                page[NameObject("/Contents")] = writer._add_object(content)
            finally:
                image.close()
            if progress:
                progress.advance("Adding images")
        if progress:
            progress.set_phase("Writing PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing PDF")
    except ImagePdfValidationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise ImagePdfValidationError("The images could not be combined. Replace the unreadable image and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
