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
        self.assertIn("PageKit-converted.docx", response.headers["Content-Disposition"])
        document = Document(io.BytesIO(response.data))
        text = " ".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("First page notes for class", text)
        self.assertIn("Second page assignment text", text)
        self.assertLess(text.index("First page"), text.index("Second page"))
        self.assertEqual(len(document.inline_shapes), 1)
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
