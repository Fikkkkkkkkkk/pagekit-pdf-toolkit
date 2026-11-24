"""PDF to Word conversion, validation, and cleanup tests."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject, StreamObject

from app import create_app
from app.features.pdf_to_word import storage


def pdf_bytes(texts: list[str], *, image_pages: set[int] | None = None, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for index, text in enumerate(texts):
        page = writer.add_blank_page(width=612, height=792)
        resources = DictionaryObject()
        commands = []
        if text:
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            resources[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): writer._add_object(font)})
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"BT /F1 12 Tf 72 700 Td ({escaped}) Tj ET".encode("latin-1"))
        if image_pages and index in image_pages:
            picture = Image.new("RGB", (30, 30), "red")
            data = io.BytesIO()
            picture.save(data, format="JPEG")
            image = StreamObject()
            image._data = data.getvalue()
            image.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(30),
                NameObject("/Height"): NumberObject(30),
                NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                NameObject("/BitsPerComponent"): NumberObject(8),
                NameObject("/Filter"): NameObject("/DCTDecode"),
            })
            resources[NameObject("/XObject")] = DictionaryObject({NameObject("/Im1"): writer._add_object(image)})
            commands.append(b"q 80 0 0 80 72 500 cm /Im1 Do Q")
        page[NameObject("/Resources")] = resources
        contents = DecodedStreamObject()
        contents.set_data(b"\n".join(commands))
        page[NameObject("/Contents")] = writer._add_object(contents)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def positioned_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    fonts = DictionaryObject()
    for key, name in (("/F1", "/Helvetica"), ("/F2", "/Helvetica-Bold"), ("/F3", "/Helvetica-Oblique")):
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject(name),
        })
        fonts[NameObject(key)] = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
    contents = DecodedStreamObject()
    contents.set_data(b"\n".join((
        b"BT /F2 20 Tf 251 730 Td (Class Notes) Tj ET",
        b"BT /F1 11 Tf 480 700 Td (Nov 25) Tj ET",
        b"BT /F1 12 Tf 72 660 Td (First paragraph) Tj ET",
        b"BT /F1 12 Tf 72 644 Td (continues here) Tj ET",
        b"BT /F3 12 Tf 72 600 Td (Underlined) Tj ET",
        b"72 598 m 132 598 l S",
        b"BT /F1 12 Tf 72 580 Td (Read ) Tj ET",
        b"BT /F3 12 Tf 120 580 Td (this) Tj ET",
        b"BT /F1 12 Tf 145 580 Td (.) Tj ET",
        b"BT /F1 12 Tf 72 560 Td (Filled underline) Tj ET",
        b"72 558 90 1.2 re f*",
        b"BT /F1 12 Tf 72 540 Td (Left one) Tj ET",
        b"BT /F1 12 Tf 330 540 Td (Right one) Tj ET",
        b"BT /F1 12 Tf 72 520 Td (Left two) Tj ET",
        b"BT /F1 12 Tf 330 520 Td (Right two) Tj ET",
    )))
    page[NameObject("/Contents")] = writer._add_object(contents)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def full_page_pdf() -> bytes:
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for page_number in (1, 2):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        commands = []
        if page_number == 1:
            for line_number in range(44):
                commands.append(f"BT /F1 12 Tf 72 {730 - line_number * 15} Td (Page one line {line_number:02}) Tj ET".encode())
        else:
            commands.append(b"BT /F1 12 Tf 72 730 Td (Page two opening paragraph) Tj ET")
            commands.append(b"BT /F1 12 Tf 72 700 Td (Page two remains editable) Tj ET")
            commands.append(b"BT /F1 12 Tf 72 -100 Td (Hidden beyond crop edge) Tj ET")
        commands.append(f"BT /F1 10 Tf 300 24 Td ({page_number}) Tj ET".encode())
        contents = DecodedStreamObject()
        contents.set_data(b"\n".join(commands))
        page[NameObject("/Contents")] = writer._add_object(contents)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def repeated_header_pdf() -> bytes:
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for number in (1, 2):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        contents = DecodedStreamObject()
        contents.set_data(b"\n".join((
            b"BT /F1 11 Tf 460 744 Td (COURSE 2026) Tj ET",
            f"BT /F1 12 Tf 72 680 Td (Page {number} body starts here) Tj ET".encode(),
        )))
        page[NameObject("/Contents")] = writer._add_object(contents)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def positioned_numbering_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=792)
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    contents = DecodedStreamObject()
    contents.set_data(b"\n".join((
        b"BT /F1 12 Tf 72 700 Td (1.) Tj ET",
        b"BT /F1 12 Tf 108 700 Td (First party) Tj ET",
        b"BT /F1 12 Tf 72 660 Td (2.) Tj ET",
        b"BT /F1 12 Tf 108 660 Td (Second party) Tj ET",
        b"BT /F1 12 Tf 108 644 Td (continuation of the second party and role label across the line) Tj ET",
        b"BT /F1 12 Tf 72 580 Td ([1] Inline marker) Tj ET",
        b"BT /F1 12 Tf 72 540 Td ([2]) Tj ET",
        b"BT /F1 12 Tf 108 540 Td (Separate legal text) Tj ET",
        b"BT /F1 12 Tf 72 500 Td ([3]) Tj ET",
        b"BT /F1 12 Tf 108 500 Td (More legal text) Tj ET",
    )))
    page[NameObject("/Contents")] = writer._add_object(contents)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class PdfToWordTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "pdf_to_word")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, data: bytes, name: str = "notes.pdf"):
        return self.client.post(
            "/api/pdf-to-word",
            data={"file": (io.BytesIO(data), name)},
            content_type="multipart/form-data",
        )

    def test_converts_all_pages_to_editable_text_and_images(self):
        response = self.upload(pdf_bytes(["First page notes for class", "Second page assignment text"], image_pages={0}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertRegex(response.headers["Content-Disposition"], r"PageKit-converted-\d{8}T\d{12}Z\.docx")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        document = Document(io.BytesIO(response.data))
        text = " ".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("First page notes for class", text)
        self.assertIn("Second page assignment text", text)
        self.assertLess(text.index("First page"), text.index("Second page"))
        self.assertEqual(len(document.inline_shapes), 1)
        self.assertIn("w:pageBreakBefore", document._body._body.xml)
        self.assertNotIn('w:type="page"', document._body._body.xml)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_near_full_page_moves_sequential_numbers_to_footer(self):
        response = self.upload(full_page_pdf())
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        paragraphs = document.paragraphs
        second_opening = next(index for index, paragraph in enumerate(paragraphs) if "Page two opening" in paragraph.text)
        self.assertIn("Page one line 43", " ".join(paragraph.text for paragraph in paragraphs[:second_opening]))
        self.assertFalse(any(paragraph.text in ("1", "2") for paragraph in paragraphs))
        self.assertTrue(paragraphs[second_opening].paragraph_format.page_break_before)
        self.assertNotIn('w:type="page"', document._body._body.xml)
        self.assertNotIn("Hidden beyond crop edge", " ".join(paragraph.text for paragraph in paragraphs))
        self.assertIn("PAGE", document.sections[0].footer._element.xml)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_preserves_an_empty_source_page_between_text_pages(self):
        response = self.upload(pdf_bytes(["First page text", "", "Third page text"]))
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        self.assertEqual([paragraph.text for paragraph in document.paragraphs], ["First page text", "", "Third page text"])
        self.assertTrue(document.paragraphs[1].paragraph_format.page_break_before)
        self.assertTrue(document.paragraphs[2].paragraph_format.page_break_before)

    def test_repeated_top_reference_is_a_header_above_each_page_body(self):
        response = self.upload(repeated_header_pdf())
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        self.assertEqual(document.sections[0].header.paragraphs[0].text, "COURSE 2026")
        self.assertEqual(document.sections[0].header.paragraphs[0].alignment, WD_ALIGN_PARAGRAPH.RIGHT)
        self.assertEqual([paragraph.text for paragraph in document.paragraphs], [
            "Page 1 body starts here", "Page 2 body starts here",
        ])
        self.assertTrue(document.paragraphs[1].paragraph_format.page_break_before)
        self.assertGreater(document.paragraphs[1].paragraph_format.space_before.pt, 0)

    def test_uses_real_party_list_and_keeps_legal_markers_literal(self):
        response = self.upload(positioned_numbering_pdf())
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        parties = [paragraph for paragraph in document.paragraphs if paragraph._p.pPr is not None and paragraph._p.pPr.numPr is not None]
        legal = [paragraph for paragraph in document.paragraphs if paragraph.text.startswith(("[1]", "[2]", "[3]"))]
        self.assertEqual([paragraph.text for paragraph in parties], ["First party", "Second party"])
        self.assertEqual(len({paragraph._p.pPr.numPr.numId.val for paragraph in parties}), 1)
        self.assertTrue(all(paragraph._p.pPr.numPr.ilvl.val == 0 for paragraph in parties))
        continuation = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("continuation"))
        self.assertEqual(continuation.paragraph_format.left_indent.pt, 54)
        self.assertIsNone(continuation.paragraph_format.first_line_indent)
        self.assertEqual(parties[0].paragraph_format.left_indent.pt, 54)
        self.assertEqual(parties[0].paragraph_format.first_line_indent.pt, -36)
        self.assertEqual([paragraph.text.split("\t", 1)[0] for paragraph in legal], ["[1] Inline marker", "[2]", "[3]"])
        self.assertEqual(legal[1].paragraph_format.left_indent.pt, 18)
        self.assertIsNone(legal[1].paragraph_format.first_line_indent)
        self.assertEqual(legal[1].paragraph_format.tab_stops[0].position.pt, 54)
        self.assertTrue(all("w:numPr" not in paragraph._p.xml for paragraph in legal))
        self.assertTrue(all(paragraph.style.name == "List Paragraph" for paragraph in legal))

    def test_reconstructs_alignment_styles_lines_and_columns(self):
        response = self.upload(positioned_pdf())
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        heading = next(paragraph for paragraph in document.paragraphs if "Class Notes" in paragraph.text)
        self.assertEqual(heading.alignment, WD_ALIGN_PARAGRAPH.CENTER)
        self.assertTrue(heading.runs[0].bold)
        self.assertEqual(heading.runs[0].font.size.pt, 20)
        date = next(paragraph for paragraph in document.paragraphs if "Nov 25" in paragraph.text)
        self.assertEqual(date.alignment, WD_ALIGN_PARAGRAPH.RIGHT)
        body = next(paragraph for paragraph in document.paragraphs if "First paragraph" in paragraph.text)
        self.assertIn("continues here", body.text)
        self.assertIn("<w:br", body._p.xml)
        underlined = next(paragraph for paragraph in document.paragraphs if "Underlined" in paragraph.text)
        self.assertTrue(underlined.runs[0].underline)
        self.assertGreater(underlined.paragraph_format.space_before.pt, 0)
        filled_underline = next(paragraph for paragraph in document.paragraphs if "Filled underline" in paragraph.text)
        self.assertTrue(filled_underline.runs[0].underline)
        mixed = next(paragraph for paragraph in document.paragraphs if "Read this." in paragraph.text)
        self.assertIn("Read this.", mixed.text)
        self.assertTrue(next(run for run in mixed.runs if "this" in run.text).italic)
        self.assertFalse(next(run for run in mixed.runs if run.text == ".").italic)
        self.assertEqual(len(document.tables), 1)
        self.assertIn("Left one", document.tables[0].cell(0, 0).text)
        self.assertIn("Right one", document.tables[0].cell(0, 1).text)
        self.assertNotIn("Right one", document.tables[0].cell(0, 0).text)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_image_only_and_empty_documents(self):
        scanned = self.upload(pdf_bytes([""], image_pages={0}))
        self.assertEqual(scanned.status_code, 400)
        self.assertIn("OCR is not available", scanned.json["error"])
        blank = self.upload(pdf_bytes([""]))
        self.assertEqual(blank.status_code, 400)
        self.assertIn("no extractable text", blank.json["error"])
        mixed = self.upload(pdf_bytes(["Selectable text on page one", ""], image_pages={1}))
        self.assertEqual(mixed.status_code, 400)
        self.assertIn("Page 2", mixed.json["error"])

    def test_rejects_unreadable_locked_wrong_type_and_oversized(self):
        unreadable = self.upload(b"%PDF-not readable")
        self.assertEqual(unreadable.status_code, 400)
        self.assertIn("could not be read", unreadable.json["error"])
        locked = self.upload(pdf_bytes(["Private text for a test"], encrypted=True))
        self.assertEqual(locked.status_code, 400)
        self.assertIn("password protected", locked.json["error"])
        wrong_type = self.upload(pdf_bytes(["Readable text for test"]), "notes.txt")
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn(".pdf", wrong_type.json["error"])
        with patch("app.features.pdf_to_word.validation.MAX_FILE_BYTES", 10):
            oversized = self.upload(pdf_bytes(["Readable text for test"]))
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("25 MB", oversized.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_removes_stale_request_directories(self):
        storage.TEMP_ROOT.mkdir(parents=True)
        stale = storage.TEMP_ROOT / "request-old"
        stale.mkdir()
        (stale / "input.pdf").write_bytes(b"private")
        old = time.time() - storage.RETENTION_SECONDS - 10
        os.utime(stale, (old, old))
        create_app()
        self.assertFalse(stale.exists())
        stale.mkdir()
        os.utime(stale, (old, old))
        self.client.get("/api/health")
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
