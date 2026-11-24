"""End-to-end merge API behavior and temporary-file cleanup."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from app import create_app
from app.features.merge_pdf import storage


def pdf_bytes(width: int, *, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=200)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class MergePdfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "merge_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, entries):
        return self.client.post(
            "/api/merge-pdf",
            data={"files": [(io.BytesIO(data), name) for name, data in entries]},
            content_type="multipart/form-data",
        )

    def test_merges_in_uploaded_order_and_removes_request_files(self):
        response = self.upload([("first.pdf", pdf_bytes(111)), ("second.pdf", pdf_bytes(222))])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-merged.pdf", response.headers["Content-Disposition"])
        pages = PdfReader(io.BytesIO(response.data)).pages
        self.assertEqual([int(page.mediabox.width) for page in pages], [111, 222])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_requires_two_files(self):
        response = self.upload([("one.pdf", pdf_bytes(111))])
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least two", response.json["error"])

    def test_rejects_non_pdf_and_unreadable_pdf(self):
        wrong_type = self.upload([("notes.txt", pdf_bytes(111)), ("two.pdf", pdf_bytes(222))])
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn(".pdf extension", wrong_type.json["error"])
        unreadable = self.upload([("bad.pdf", b"%PDF-not a real document"), ("two.pdf", pdf_bytes(222))])
        self.assertEqual(unreadable.status_code, 400)
        self.assertIn("cannot be read", unreadable.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_password_protected_pdf(self):
        response = self.upload([("locked.pdf", pdf_bytes(111, encrypted=True)), ("two.pdf", pdf_bytes(222))])
        self.assertEqual(response.status_code, 400)
        self.assertIn("password protected", response.json["error"])

    def test_rejects_oversized_file_and_cleans_up(self):
        with patch("app.features.merge_pdf.validation.MAX_FILE_BYTES", 10):
            response = self.upload([("large.pdf", pdf_bytes(111)), ("two.pdf", pdf_bytes(222))])
        self.assertEqual(response.status_code, 400)
        self.assertIn("25 MB", response.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_removes_stale_request_directories_at_startup_and_on_request(self):
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
