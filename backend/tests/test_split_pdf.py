"""Split PDF API, range validation, and cleanup tests."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from pypdf import PdfReader, PdfWriter

from app import create_app
from app.features.split_pdf import storage


def pdf_bytes(page_count: int = 10, *, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for number in range(1, page_count + 1):
        writer.add_blank_page(width=100 + number, height=200)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class SplitPdfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "split_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, document: bytes, ranges: str, filename: str = "notes.pdf"):
        return self.client.post(
            "/api/split-pdf",
            data={"file": (io.BytesIO(document), filename), "ranges": ranges},
            content_type="multipart/form-data",
        )

    def test_zip_preserves_entered_range_order_and_original_pdf(self):
        original = pdf_bytes()
        response = self.upload(original, "8-10, 1-3, 5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("PageKit-split.zip", response.headers["Content-Disposition"])
        with ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(archive.namelist(), ["01-pages-8-10.pdf", "02-pages-1-3.pdf", "03-pages-5.pdf"])
            widths = [
                [int(page.mediabox.width) for page in PdfReader(io.BytesIO(archive.read(name))).pages]
                for name in archive.namelist()
            ]
            self.assertEqual(widths, [[108, 109, 110], [101, 102, 103], [105]])
        self.assertEqual(len(PdfReader(io.BytesIO(original)).pages), 10)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_malformed_ranges(self):
        for ranges in ("", "1--3", "1-3,", "1 to 3", "0", "5-3", "1, two"):
            with self.subTest(ranges=ranges):
                response = self.upload(pdf_bytes(), ranges)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json["error"])

    def test_rejects_out_of_bounds_and_overlap(self):
        outside = self.upload(pdf_bytes(4), "1-5")
        self.assertEqual(outside.status_code, 400)
        self.assertIn("beyond", outside.json["error"])
        overlap = self.upload(pdf_bytes(), "3-5, 1-3")
        self.assertEqual(overlap.status_code, 400)
        self.assertIn("overlaps", overlap.json["error"])

    def test_rejects_unreadable_locked_and_wrong_type(self):
        unreadable = self.upload(b"%PDF-not a real PDF", "1")
        self.assertEqual(unreadable.status_code, 400)
        self.assertIn("could not be read", unreadable.json["error"])
        locked = self.upload(pdf_bytes(encrypted=True), "1")
        self.assertEqual(locked.status_code, 400)
        self.assertIn("password protected", locked.json["error"])
        wrong_type = self.upload(pdf_bytes(), "1", "notes.txt")
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn(".pdf extension", wrong_type.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_oversized_file_and_cleans_up(self):
        with patch("app.features.split_pdf.validation.MAX_FILE_BYTES", 10):
            response = self.upload(pdf_bytes(), "1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("25 MB", response.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_removes_stale_requests_at_startup_and_on_request(self):
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
