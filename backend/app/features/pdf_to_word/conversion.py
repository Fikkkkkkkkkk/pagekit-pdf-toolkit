"""Local, text-first PDF to editable DOCX conversion."""

import re
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .validation import WordConversionError

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)
MIN_PAGE_TEXT_CHARS = 5


def _clean_text(text: str) -> str:
    # XML 1.0 permits tab, line feed, carriage return, and printable code points.
    return "".join(char for char in text if char in "\t\n\r" or ord(char) >= 32)


def _paragraphs(text: str) -> list[str]:
    groups: list[str] = []
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_text(raw_line).strip()
        if not line:
            if lines:
                groups.append(" ".join(lines))
                lines = []
            continue
        if lines and lines[-1].endswith("-"):
            lines[-1] = lines[-1][:-1] + line
        else:
            lines.append(line)
    if lines:
        groups.append(" ".join(lines))
    return groups


def _add_images(document: Document, page, available_width: float, available_height: float) -> None:
    for image_name in page.images.keys():
        try:
            picture = page.images[image_name].image
            if picture is None:
                continue
            width_px, height_px = picture.size
            width_in = min(width_px / 96, available_width, available_height * width_px / height_px)
            image_stream = BytesIO()
            picture.save(image_stream, format="PNG")
            image_stream.seek(0)
            document.add_picture(image_stream, width=Inches(max(width_in, 0.1)))
        except Exception:
            # Keep the omission visible instead of claiming every image was preserved.
            document.add_paragraph("[An image on this page could not be converted.]")


def convert_pdf(source: Path) -> BytesIO:
    try:
        reader = PdfReader(source, strict=False)
        if reader.is_encrypted:
            raise WordConversionError("This PDF is password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise WordConversionError("This PDF has no pages to convert.")

        page_text: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if len(re.findall(r"\w", text)) < MIN_PAGE_TEXT_CHARS and page.images.keys():
                raise WordConversionError(
                    f"Page {number} appears scanned or image-only. OCR is not available yet; choose a PDF with selectable text."
                )
            page_text.append(text)
        if not any(re.search(r"\w", text) for text in page_text):
            raise WordConversionError("This PDF has no extractable text. OCR is not available yet; choose a PDF with selectable text.")

        document = Document()
        first_page = reader.pages[0]
        section = document.sections[0]
        width_pt = float(first_page.mediabox.width)
        height_pt = float(first_page.mediabox.height)
        if 288 <= width_pt <= 1440 and 288 <= height_pt <= 1440:
            section.page_width = Pt(width_pt)
            section.page_height = Pt(height_pt)
        section.top_margin = section.bottom_margin = Inches(0.7)
        section.left_margin = section.right_margin = Inches(0.75)
        available_width = section.page_width / 914400 - 1.5
        available_height = section.page_height / 914400 - 1.4

        for index, (page, text) in enumerate(zip(reader.pages, page_text)):
            if index:
                document.add_page_break()
            for paragraph_text in _paragraphs(text):
                paragraph = document.add_paragraph(paragraph_text)
                paragraph.paragraph_format.space_after = Pt(5)
            _add_images(document, page, available_width, available_height)

        output = BytesIO()
        document.save(output)
        output.seek(0)
        return output
    except WordConversionError:
        raise
    except PDF_ERRORS as exc:
        raise WordConversionError("This PDF could not be read. Choose a readable PDF and try again.") from exc
