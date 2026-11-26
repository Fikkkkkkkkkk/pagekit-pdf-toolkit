"""Rotate PDF endpoint, validation, output, and cleanup tests."""

import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from app import create_app
from app.features.rotate_pdf import storage


def pdf_bytes(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for width in (101, 202, 303):
        writer.add_blank_page(width=width, height=200)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class RotatePdfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "rotate_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, rotations: object, *, name: str = "notes.pdf"):
        return self.client.post(
            "/api/rotate-pdf",
            data={"file": (io.BytesIO(content), name), "rotations": json.dumps(rotations)},
            content_type="multipart/form-data",
        )

    def test_rotates_selected_pages_and_preserves_order_and_untouched_pages(self):
        original = pdf_bytes()
        response = self.upload(original, [90, 0, 270])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-rotated.pdf", response.headers["Content-Disposition"])
        pages = PdfReader(io.BytesIO(response.data)).pages
        self.assertEqual([int(page.mediabox.width) for page in pages], [101, 202, 303])
        self.assertEqual([page.rotation for page in pages], [90, 0, 270])
        self.assertEqual([page.rotation for page in PdfReader(io.BytesIO(original)).pages], [0, 0, 0])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_invalid_angles_and_page_count(self):
        original = pdf_bytes()
        for rotations in ([90], [0, 45, 0], [0, True, 0], [0, "90", 0], {"1": 90}):
            with self.subTest(rotations=rotations):
                response = self.upload(original, rotations)
                self.assertEqual(response.status_code, 400)
                self.assertIn("rotation", response.json["error"])
        response = self.client.post(
            "/api/rotate-pdf",
            data={"file": (io.BytesIO(original), "notes.pdf"), "rotations": "not-json"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid", response.json["error"])

    def test_rejects_unreadable_encrypted_wrong_type_and_oversize(self):
        unreadable = self.upload(b"%PDF-broken", [0])
        self.assertEqual(unreadable.status_code, 400)
        self.assertIn("cannot be read", unreadable.json["error"])
        locked = self.upload(pdf_bytes(encrypted=True), [0, 0, 0])
        self.assertEqual(locked.status_code, 400)
        self.assertIn("password protected", locked.json["error"])
        wrong_type = self.upload(pdf_bytes(), [0, 0, 0], name="notes.txt")
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn(".pdf", wrong_type.json["error"])
        with patch("app.features.rotate_pdf.validation.MAX_FILE_BYTES", 10):
            large = self.upload(pdf_bytes(), [0, 0, 0])
        self.assertEqual(large.status_code, 400)
        self.assertIn("25 MB", large.json["error"])
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
