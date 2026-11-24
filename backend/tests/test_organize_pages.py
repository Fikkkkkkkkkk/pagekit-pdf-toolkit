"""Organize pages API validation, output order, and cleanup tests."""

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
from app.features.organize_pages import storage


def pdf_bytes(widths: list[int], *, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=200)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def selection(source: str, page: int) -> dict:
    return {"source": source, "page": page}


class OrganizePagesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "organize_pages")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, original: bytes, order, *, added: bytes | None = None, position: str | None = None, name: str = "original.pdf"):
        data = {"original": (io.BytesIO(original), name), "order": json.dumps(order)}
        if added is not None:
            data["added"] = (io.BytesIO(added), "added.pdf")
        if position is not None:
            data["insertion_position"] = position
        return self.client.post("/api/organize-pages", data=data, content_type="multipart/form-data")

    def test_reorders_deletes_and_inserts_pages_without_changing_inputs(self):
        original = pdf_bytes([101, 102, 103])
        added = pdf_bytes([201, 202])
        order = [selection("original", 3), selection("added", 1), selection("original", 1), selection("added", 2)]
        response = self.upload(original, order, added=added, position="1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-organized.pdf", response.headers["Content-Disposition"])
        widths = [int(page.mediabox.width) for page in PdfReader(io.BytesIO(response.data)).pages]
        self.assertEqual(widths, [103, 201, 101, 202])
        self.assertEqual([int(page.mediabox.width) for page in PdfReader(io.BytesIO(original)).pages], [101, 102, 103])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_deleting_every_page_and_invalid_selections(self):
        original = pdf_bytes([101, 102])
        empty = self.upload(original, [])
        self.assertEqual(empty.status_code, 400)
        self.assertIn("cannot delete every page", empty.json["error"])
        outside = self.upload(original, [selection("original", 3)])
        self.assertEqual(outside.status_code, 400)
        self.assertIn("outside", outside.json["error"])
        duplicate = self.upload(original, [selection("original", 1), selection("original", 1)])
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("repeats", duplicate.json["error"])
        malformed = self.client.post(
            "/api/organize-pages",
            data={"original": (io.BytesIO(original), "original.pdf"), "order": "not-json"},
            content_type="multipart/form-data",
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertIn("page order is invalid", malformed.json["error"])

    def test_rejects_invalid_insertion_positions(self):
        original = pdf_bytes([101, 102])
        added = pdf_bytes([201])
        order = [selection("original", 1), selection("added", 1)]
        for position in (None, "-1", "3", "start"):
            with self.subTest(position=position):
                response = self.upload(original, order, added=added, position=position)
                self.assertEqual(response.status_code, 400)
                self.assertIn("insertion position", response.json["error"])

    def test_rejects_unreadable_encrypted_and_wrong_type_pdfs(self):
        valid = pdf_bytes([101])
        unreadable = self.upload(b"%PDF-not readable", [selection("original", 1)])
        self.assertEqual(unreadable.status_code, 400)
        self.assertIn("cannot be read", unreadable.json["error"])
        locked = self.upload(pdf_bytes([101], encrypted=True), [selection("original", 1)])
        self.assertEqual(locked.status_code, 400)
        self.assertIn("password protected", locked.json["error"])
        wrong_type = self.upload(valid, [selection("original", 1)], name="notes.txt")
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn(".pdf", wrong_type.json["error"])
        unreadable_added = self.upload(valid, [selection("original", 1), selection("added", 1)], added=b"%PDF-broken", position="1")
        self.assertEqual(unreadable_added.status_code, 400)
        self.assertIn("second PDF", unreadable_added.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_oversized_file_and_cleans_up(self):
        with patch("app.features.organize_pages.validation.MAX_FILE_BYTES", 10):
            response = self.upload(pdf_bytes([101]), [selection("original", 1)])
        self.assertEqual(response.status_code, 400)
        self.assertIn("25 MB", response.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_removes_stale_request_directories(self):
        storage.TEMP_ROOT.mkdir(parents=True)
        stale = storage.TEMP_ROOT / "request-old"
        stale.mkdir()
        (stale / "original.pdf").write_bytes(b"private")
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
