"""Add page numbers endpoint, placement, validation, and cleanup tests."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, NameObject

from app import create_app
from app.features.add_page_numbers import storage


def pdf_bytes(*, encrypted: bool = False, rotate_second: bool = False) -> bytes:
    writer = PdfWriter()
    for width in (200, 300, 400):
        writer.add_blank_page(width=width, height=500)
    if rotate_second:
        writer.pages[1].rotate(90)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class AddPageNumbersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "add_page_numbers")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, *, position: str = "bottom-center", start: str = "7", name: str = "notes.pdf"):
        return self.client.post(
            "/api/add-page-numbers",
            data={"file": (io.BytesIO(content), name), "position": position, "start": start},
            content_type="multipart/form-data",
        )

    def test_numbers_every_page_in_order_without_changing_original(self):
        original = pdf_bytes(rotate_second=True)
        response = self.upload(original)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-numbered.pdf", response.headers["Content-Disposition"])
        pages = PdfReader(io.BytesIO(response.data)).pages
        self.assertEqual([int(page.mediabox.width) for page in pages], [200, 300, 400])
        self.assertEqual([page.rotation for page in pages], [0, 90, 0])
        self.assertEqual([page.extract_text().strip() for page in pages], ["7", "8", "9"])
        self.assertEqual([page.extract_text() for page in PdfReader(io.BytesIO(original)).pages], ["", "", ""])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_all_positions_write_numbered_output(self):
        for vertical in ("top", "bottom"):
            for horizontal in ("left", "center", "right"):
                position = f"{vertical}-{horizontal}"
                with self.subTest(position=position):
                    response = self.upload(pdf_bytes(), position=position)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(PdfReader(io.BytesIO(response.data)).pages[0].extract_text().strip(), "7")

    def test_existing_content_streams_remain_and_rotated_placement_is_upright(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=200, height=300)
        drawing = b"q 10 20 30 40 re S Q\n"
        stream = DecodedStreamObject()
        stream.set_data(drawing)
        page[NameObject("/Contents")] = writer._add_object(ArrayObject([writer._add_object(stream)]))
        page.rotate(90)
        source = io.BytesIO()
        writer.write(source)
        response = self.upload(source.getvalue(), position="top-right", start="4")
        self.assertEqual(response.status_code, 200)
        numbered = PdfReader(io.BytesIO(response.data)).pages[0]
        self.assertEqual(numbered.rotation, 90)
        content = numbered.get_contents().get_data()
        self.assertIn(drawing, content)
        self.assertIn(b"0 1 -1 0", content)
        self.assertEqual(numbered.extract_text().strip(), "4")

    def test_rejects_bad_options_and_files(self):
        valid = pdf_bytes()
        for position, start in (("middle", "1"), ("bottom-center", "0"), ("bottom-center", "1.5"), ("bottom-center", "999999"), ("bottom-center", "9" * 5000)):
            with self.subTest(position=position, start=start):
                response = self.upload(valid, position=position, start=start)
                self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be read", self.upload(b"%PDF-broken").json["error"])
        self.assertIn("password protected", self.upload(pdf_bytes(encrypted=True)).json["error"])
        self.assertIn(".pdf", self.upload(valid, name="notes.txt").json["error"])
        with patch("app.features.add_page_numbers.validation.MAX_FILE_BYTES", 10):
            oversized = self.upload(valid)
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("25 MB", oversized.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_cleans_stale_request_folders_at_startup_and_on_request(self):
        storage.TEMP_ROOT.mkdir(parents=True)
        stale = storage.TEMP_ROOT / "request-old"
        stale.mkdir()
        (stale / "source.pdf").write_bytes(b"private")
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
