"""Local, text-first PDF to editable DOCX conversion."""

import re
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ...shared.progress import ProgressReporter

from .layout import add_repeated_header, centered_footer_number, decimal_list_lines, extract_lines, render_page, top_right_header_line
from .validation import WordConversionError

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError)
MIN_PAGE_TEXT_CHARS = 5


def _add_numbered_footer(section, first_number: int, footer_line, page_height: float) -> None:
    """Use a Word PAGE field for a repeated sequence of source footer numbers."""
    section.footer_distance = Pt(max(12, min(72, page_height - footer_line.y - footer_line.size * 0.7)))
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    span = footer_line.spans[0]

    def field_run(kind: str) -> None:
        run = paragraph.add_run()
        element = OxmlElement("w:fldChar")
        element.set(qn("w:fldCharType"), kind)
        if kind == "begin":
            element.set(qn("w:dirty"), "true")
        run._r.append(element)
        run.font.size = Pt(span.size)

    field_run("begin")
    instruction = OxmlElement("w:instrText")
    instruction.text = " PAGE "
    paragraph.add_run()._r.append(instruction)
    field_run("separate")
    paragraph.add_run(str(first_number)).font.size = Pt(span.size)
    field_run("end")
    if first_number != 1:
        numbering = OxmlElement("w:pgNumType")
        numbering.set(qn("w:start"), str(first_number))
        section._sectPr.append(numbering)


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


def convert_pdf(source: Path, progress: ProgressReporter | None = None) -> BytesIO:
    try:
        reader = PdfReader(source, strict=False)
        if reader.is_encrypted:
            raise WordConversionError("This PDF is password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise WordConversionError("This PDF has no pages to convert.")

        if progress:
            progress.start(2 * len(reader.pages) + 1, "Reading source pages")

        page_text: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            if progress:
                progress.check()
            text = page.extract_text() or ""
            if len(re.findall(r"\w", text)) < MIN_PAGE_TEXT_CHARS and page.images.keys():
                raise WordConversionError(
                    f"Page {number} appears scanned or image-only. OCR is not available yet; choose a PDF with selectable text."
                )
            page_text.append(text)
            if progress:
                progress.advance("Reading source pages")
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
        # PDF body text and printed page numbers can sit close to the edge.
        # Leave enough usable Word height for the source page to fit.
        section.top_margin = section.bottom_margin = Inches(0.15)
        section.left_margin = section.right_margin = Inches(0.75)
        available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches
        available_height = section.page_height.inches - section.top_margin.inches - section.bottom_margin.inches

        if progress:
            progress.set_phase("Inspecting page layout")
        extractions = [extract_lines(page) for page in reader.pages]
        numbered_lines = decimal_list_lines(extractions)
        list_num_id = document.styles["List Number"]._element.pPr.numPr.numId.val if numbered_lines else None
        header_candidates = [
            top_right_header_line(lines, float(page.cropbox.width), float(page.cropbox.height))
            for page, (lines, _) in zip(reader.pages, extractions)
        ]
        repeated_header = (
            len(header_candidates) > 1
            and all(line is not None for line in header_candidates)
            and all(
                " ".join(" ".join(span.text for span in line.spans).split())
                == " ".join(" ".join(span.text for span in header_candidates[0].spans).split())
                for line in header_candidates
            )
            and max(line.y / float(page.cropbox.height) for page, line in zip(reader.pages, header_candidates))
            - min(line.y / float(page.cropbox.height) for page, line in zip(reader.pages, header_candidates)) < 0.02
            and max(line.x / float(page.cropbox.width) for page, line in zip(reader.pages, header_candidates))
            - min(line.x / float(page.cropbox.width) for page, line in zip(reader.pages, header_candidates)) < 0.02
        )
        if repeated_header:
            add_repeated_header(section, header_candidates[0], float(first_page.cropbox.width))
        body_top_pt = section.top_margin.pt
        if repeated_header:
            # Word moves the body below a header even when the section's top
            # margin is smaller. Measure the first paragraph from that body
            # origin so the PDF's top offset is not applied twice.
            body_top_pt = max(body_top_pt, section.header_distance.pt + header_candidates[0].size * 0.85)
        footer_candidates = [
            centered_footer_number(lines, float(page.cropbox.width), float(page.cropbox.height))
            for page, (lines, _) in zip(reader.pages, extractions)
        ]
        numbered_footers = (
            len(footer_candidates) > 1
            and all(candidate is not None for candidate in footer_candidates)
            and all(candidate[0] == footer_candidates[0][0] + index for index, candidate in enumerate(footer_candidates))
            and max(candidate[1].y / float(page.cropbox.height) for page, candidate in zip(reader.pages, footer_candidates))
            - min(candidate[1].y / float(page.cropbox.height) for page, candidate in zip(reader.pages, footer_candidates)) < 0.03
        )
        if numbered_footers:
            _add_numbered_footer(section, footer_candidates[0][0], footer_candidates[0][1], float(first_page.cropbox.height))
            update_fields = OxmlElement("w:updateFields")
            update_fields.set(qn("w:val"), "true")
            document.settings._element.append(update_fields)

        for index, (page, text, extraction) in enumerate(zip(reader.pages, page_text, extractions)):
            if progress:
                progress.check()
            render_page(
                document,
                page,
                text,
                section.page_width.pt - section.left_margin.pt - section.right_margin.pt,
                start_new_page=index > 0,
                page_top_pt=body_top_pt,
                page_bottom_pt=section.bottom_margin.pt,
                extraction=extraction,
                footer_line=footer_candidates[index][1] if numbered_footers else None,
                header_line=header_candidates[index] if repeated_header else None,
                numbered_lines=numbered_lines,
                list_num_id=list_num_id,
            )
            _add_images(document, page, available_width, available_height)
            if progress:
                progress.advance("Building Word pages")

        output = BytesIO()
        if progress:
            progress.set_phase("Writing Word document")
        document.save(output)
        if progress:
            progress.advance("Writing Word document")
        output.seek(0)
        return output
    except WordConversionError:
        raise
    except PDF_ERRORS as exc:
        raise WordConversionError("This PDF could not be read. Choose a readable PDF and try again.") from exc
