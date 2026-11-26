"""Crop PDF endpoint, coordinates, validation, and cleanup tests."""

import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, RectangleObject

from app import create_app
from app.features.crop_pdf import storage


def pdf_bytes(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    first = writer.add_blank_page(width=200, height=300)
    drawing = DecodedStreamObject()
    drawing.set_data(b"q 10 20 30 40 re S Q\n")
    first[NameObject("/Contents")] = writer._add_object(drawing)
    second = writer.add_blank_page(width=400, height=200)
    second.rotate(90)
    third = writer.add_blank_page(width=300, height=500)
    third.cropbox = RectangleObject((30, 40, 270, 440))
    third.rotate(270)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class CropPdfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "crop_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, area: object, *, name: str = "notes.pdf"):
        return self.client.post(
            "/api/crop-pdf",
            data={"file": (io.BytesIO(content), name), "crop": json.dumps(area)},
            content_type="multipart/form-data",
        )

    def test_crops_same_relative_area_across_sizes_rotations_and_existing_crop(self):
        original = pdf_bytes()
        area = {"left": 0.1, "top": 0.2, "right": 0.8, "bottom": 0.9}
        response = self.upload(original, area)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-cropped.pdf", response.headers["Content-Disposition"])
        pages = PdfReader(io.BytesIO(response.data)).pages
        expected = [(20, 30, 160, 240), (80, 20, 360, 160), (54, 120, 222, 400)]
        for page, bounds in zip(pages, expected):
            self.assertEqual(tuple(round(float(value)) for value in page.cropbox), bounds)
        self.assertEqual([page.rotation for page in pages], [0, 90, 270])
        self.assertEqual([int(page.mediabox.width) for page in pages], [200, 400, 300])
        self.assertIn(b"10 20 30 40 re S", pages[0].get_contents().get_data())
        self.assertEqual(tuple(PdfReader(io.BytesIO(original)).pages[0].cropbox), (0, 0, 200, 300))
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_invalid_crop_areas(self):
        original = pdf_bytes()
        invalid = [
            {"left": 0.8, "top": 0.1, "right": 0.2, "bottom": 0.9},
            {"left": 0, "top": 0.2, "right": 1, "bottom": 0.2},
            {"left": -0.1, "top": 0, "right": 1, "bottom": 1},
            {"left": True, "top": 0, "right": 1, "bottom": 1},
            {"left": 0, "top": 0, "right": 1},
            [0, 0, 1, 1],
        ]
        for area in invalid:
            with self.subTest(area=area):
                response = self.upload(original, area)
                self.assertEqual(response.status_code, 400)
                self.assertIn("crop", response.json["error"].lower())
        malformed = self.client.post(
            "/api/crop-pdf",
            data={"file": (io.BytesIO(original), "notes.pdf"), "crop": "not-json"},
            content_type="multipart/form-data",
        )
        self.assertEqual(malformed.status_code, 400)

    def test_maps_crop_on_a_half_turn_page(self):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=100).rotate(180)
        source = io.BytesIO()
        writer.write(source)
        area = {"left": 0.1, "top": 0.2, "right": 0.8, "bottom": 0.9}
        response = self.upload(source.getvalue(), area)
        self.assertEqual(response.status_code, 200)
        page = PdfReader(io.BytesIO(response.data)).pages[0]
        self.assertEqual(tuple(round(float(value)) for value in page.cropbox), (40, 20, 180, 90))
        self.assertEqual(page.rotation, 180)

    def test_rejects_unreadable_locked_wrong_type_and_oversized_pdfs(self):
        area = {"left": 0.1, "top": 0.1, "right": 0.9, "bottom": 0.9}
        self.assertIn("cannot be read", self.upload(b"%PDF-broken", area).json["error"])
        self.assertIn("password protected", self.upload(pdf_bytes(encrypted=True), area).json["error"])
        self.assertIn(".pdf", self.upload(pdf_bytes(), area, name="notes.txt").json["error"])
        with patch("app.features.crop_pdf.validation.MAX_FILE_BYTES", 10):
            oversized = self.upload(pdf_bytes(), area)
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
