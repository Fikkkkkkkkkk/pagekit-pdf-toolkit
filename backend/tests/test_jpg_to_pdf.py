"""Ordered image conversion, orientation, transparency, validation, and cleanup."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

from app import create_app
from app.features.jpg_to_pdf import storage


def image_bytes(format: str, size=(40, 20), color="red", exif_orientation=None) -> bytes:
    image = Image.new("RGB", size, color)
    output = io.BytesIO()
    kwargs = {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        kwargs["exif"] = exif
    image.save(output, format=format, **kwargs)
    return output.getvalue()


def transparent_png() -> bytes:
    image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 255, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class JpgToPdfTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(temp.name) / "jpg_to_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, files, page_size="a4", orientation="portrait", progress_id=None):
        headers = {"X-PageKit-Progress-ID": progress_id} if progress_id else {}
        return self.client.post("/api/jpg-to-pdf", data={
            "files": [(io.BytesIO(content), name) for name, content in files],
            "page_size": page_size, "orientation": orientation,
        }, content_type="multipart/form-data", headers=headers)

    def test_order_page_size_transparency_and_progress(self):
        progress_id = self.client.post("/api/progress").json["id"]
        response = self.upload([("red.jpg", image_bytes("JPEG")), ("clear.png", transparent_png())], progress_id=progress_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        reader = PdfReader(io.BytesIO(response.data))
        self.assertEqual(len(reader.pages), 2)
        for page in reader.pages:
            self.assertAlmostEqual(float(page.mediabox.width), 595.28, places=2)
            self.assertAlmostEqual(float(page.mediabox.height), 841.89, places=2)
        first = Image.open(io.BytesIO(reader.pages[0]["/Resources"]["/XObject"]["/PKImage"].get_object()._data))
        second = Image.open(io.BytesIO(reader.pages[1]["/Resources"]["/XObject"]["/PKImage"].get_object()._data))
        self.assertGreater(first.getpixel((0, 0))[0], 200)
        self.assertLess(first.getpixel((0, 0))[2], 50)
        self.assertGreater(second.getpixel((0, 0))[2], 150)
        self.assertTrue(all(channel > 220 for channel in second.getpixel((19, 19))))
        status = self.client.get(f"/api/progress/{progress_id}").json
        self.assertEqual((status["completed"], status["total"]), (3, 3))
        self.client.delete(f"/api/progress/{progress_id}")
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_exif_and_fit_orientation(self):
        portrait = self.upload([("camera.jpg", image_bytes("JPEG", size=(40, 20), exif_orientation=6))], page_size="fit")
        self.assertEqual(portrait.status_code, 200)
        page = PdfReader(io.BytesIO(portrait.data)).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), 15)
        self.assertAlmostEqual(float(page.mediabox.height), 30)
        landscape = self.upload([("camera.jpg", image_bytes("JPEG", size=(40, 20), exif_orientation=6))], page_size="fit", orientation="landscape")
        self.assertEqual(landscape.status_code, 200)
        page = PdfReader(io.BytesIO(landscape.data)).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), 30)
        self.assertAlmostEqual(float(page.mediabox.height), 15)
        letter = self.upload([("red.jpg", image_bytes("JPEG"))], page_size="letter", orientation="landscape")
        page = PdfReader(io.BytesIO(letter.data)).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), 792)
        self.assertAlmostEqual(float(page.mediabox.height), 612)

    def test_rejects_bad_uploads_and_options(self):
        valid = image_bytes("JPEG")
        self.assertIn("at least one", self.upload([]).json["error"])
        self.assertIn("page size", self.upload([("ok.jpg", image_bytes("JPEG"))], page_size="bad").json["error"])
        self.assertIn("orientation", self.upload([("ok.jpg", image_bytes("JPEG"))], orientation="sideways").json["error"])
        self.assertIn(".jpg", self.upload([("bad.txt", b"not an image")]).json["error"])
        self.assertIn("not a valid", self.upload([("bad.jpg", b"not an image")]).json["error"])
        self.assertIn("cannot be read", self.upload([("bad.png", b"\x89PNG\r\n\x1a\n" + b"bad")]).json["error"])
        with patch("app.features.jpg_to_pdf.validation.MAX_FILE_BYTES", 10):
            self.assertIn("25 MB", self.upload([("ok.jpg", valid)]).json["error"])
        with patch("app.features.jpg_to_pdf.validation.MAX_TOTAL_BYTES", 10):
            self.assertIn("100 MB", self.upload([("ok.jpg", valid)]).json["error"])
        self.assertIn("no more than 20", self.upload([(f"{index}.jpg", valid) for index in range(21)]).json["error"])
        with patch("app.features.jpg_to_pdf.processing.MAX_PIXELS", 10):
            self.assertIn("too many pixels", self.upload([("ok.jpg", valid)]).json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_stale_request_cleanup(self):
        storage.TEMP_ROOT.mkdir(parents=True)
        stale = storage.TEMP_ROOT / "request-old"
        stale.mkdir()
        (stale / "image.jpg").write_bytes(b"private")
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
