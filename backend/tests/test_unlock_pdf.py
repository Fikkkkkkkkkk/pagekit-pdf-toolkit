"""Known-password decryption, validation, progress, and cleanup."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from app import create_app
from app.features.unlock_pdf import storage


def sample_pdf(*, encrypted: bool = True) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=320, height=420)
    writer.add_metadata({"/Title": "Study packet"})
    writer.add_outline_item("Chapter one", 0)
    if encrypted:
        writer.encrypt(user_password="known password", owner_password="owner password", algorithm="AES-256")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class UnlockPdfTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(temp.name) / "unlock_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, *, password="known password", name="locked.pdf", progress_id=None):
        headers = {"X-PageKit-Progress-ID": progress_id} if progress_id else {}
        return self.client.post("/api/unlock-pdf", data={
            "file": (io.BytesIO(content), name), "password": password,
        }, content_type="multipart/form-data", headers=headers)

    def test_correct_password_returns_unencrypted_copy_with_document_structure(self):
        source = sample_pdf()
        progress_id = self.client.post("/api/progress").json["id"]
        response = self.upload(source, progress_id=progress_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("PageKit-unlocked.pdf", response.headers["Content-Disposition"])
        reader = PdfReader(io.BytesIO(response.data))
        self.assertFalse(reader.is_encrypted)
        self.assertEqual([int(page.mediabox.width) for page in reader.pages], [300, 320])
        self.assertEqual(reader.metadata.title, "Study packet")
        self.assertEqual(reader.outline[0].title, "Chapter one")
        self.assertTrue(PdfReader(io.BytesIO(source)).is_encrypted)
        status = self.client.get(f"/api/progress/{progress_id}").json
        self.assertEqual((status["completed"], status["total"]), (3, 3))
        self.assertNotIn("known password", str(status))
        self.client.delete(f"/api/progress/{progress_id}")
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_wrong_password_and_unreadable_files(self):
        source = sample_pdf()
        self.assertIn("incorrect", self.upload(source, password="wrong").json["error"])
        self.assertIn("Enter the known password", self.upload(source, password=" ").json["error"])
        self.assertIn("not password protected", self.upload(sample_pdf(encrypted=False)).json["error"])
        self.assertIn("cannot be read", self.upload(b"%PDF-broken").json["error"])
        self.assertIn(".pdf", self.upload(source, name="locked.txt").json["error"])
        with patch("app.features.unlock_pdf.validation.MAX_FILE_BYTES", 10):
            response = self.upload(source)
        self.assertEqual(response.status_code, 400)
        self.assertIn("25 MB", response.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_stale_request_cleanup(self):
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
