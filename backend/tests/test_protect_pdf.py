"""AES protection, validation, progress, and temporary-file cleanup."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from app import create_app
from app.features.protect_pdf import storage


def sample_pdf(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=320, height=420)
    writer.add_metadata({"/Title": "Course notes"})
    writer.add_outline_item("First section", 0)
    if encrypted:
        writer.encrypt("existing-password", algorithm="AES-256")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ProtectPdfTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(temp.name) / "protect_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, *, password: str = "student secret", confirmation: str = "student secret", name: str = "notes.pdf", progress_id: str | None = None):
        headers = {"X-PageKit-Progress-ID": progress_id} if progress_id else {}
        return self.client.post(
            "/api/protect-pdf",
            data={"file": (io.BytesIO(content), name), "password": password, "confirmation": confirmation},
            content_type="multipart/form-data", headers=headers,
        )

    def test_explicit_aes_256_requires_password_and_keeps_pages(self):
        progress_id = self.client.post("/api/progress").json["id"]
        response = self.upload(sample_pdf(), progress_id=progress_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-protected.pdf", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        reader = PdfReader(io.BytesIO(response.data))
        self.assertTrue(reader.is_encrypted)
        self.assertEqual(reader.trailer["/Encrypt"]["/R"], 6)
        self.assertEqual(reader.decrypt("wrong-password"), 0)
        self.assertGreater(reader.decrypt("student secret"), 0)
        self.assertEqual([int(page.mediabox.width) for page in reader.pages], [300, 320])
        self.assertEqual(reader.metadata.title, "Course notes")
        self.assertEqual(reader.outline[0].title, "First section")
        status = self.client.get(f"/api/progress/{progress_id}").json
        self.assertEqual((status["completed"], status["total"]), (3, 3))
        self.assertNotIn("student secret", str(status))
        self.client.delete(f"/api/progress/{progress_id}")
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_password_errors_and_invalid_pdfs(self):
        source = sample_pdf()
        self.assertIn("passwords do not match", self.upload(source, confirmation="different").json["error"])
        self.assertIn("Enter a password", self.upload(source, password=" ", confirmation=" ").json["error"])
        self.assertIn("already password protected", self.upload(sample_pdf(encrypted=True)).json["error"])
        self.assertIn("cannot be read", self.upload(b"%PDF-broken").json["error"])
        self.assertIn(".pdf", self.upload(source, name="notes.txt").json["error"])
        with patch("app.features.protect_pdf.validation.MAX_FILE_BYTES", 10):
            oversized = self.upload(source)
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("25 MB", oversized.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_removes_stale_request_folders(self):
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
