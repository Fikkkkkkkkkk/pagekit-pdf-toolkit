"""JPG ZIP order, validation, and shared processing progress."""

import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from app import create_app


def jpg(color: str) -> bytes:
    image = Image.new("RGB", (20, 20), color)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


class PdfToJpgTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def upload(self, pages, progress_id=None):
        headers = {"X-PageKit-Progress-ID": progress_id} if progress_id else {}
        return self.client.post("/api/pdf-to-jpg", data={
            "pages": [(io.BytesIO(content), f"input-{index}.jpg") for index, content in enumerate(pages)]
        }, content_type="multipart/form-data", headers=headers)

    def test_ordered_zip_and_progress(self):
        progress_id = self.client.post("/api/progress").json["id"]
        response = self.upload([jpg("red"), jpg("blue")], progress_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        with ZipFile(io.BytesIO(response.data)) as zipped:
            self.assertEqual(zipped.namelist(), ["page-001.jpg", "page-002.jpg"])
            red = Image.open(io.BytesIO(zipped.read("page-001.jpg"))).getpixel((10, 10))
            blue = Image.open(io.BytesIO(zipped.read("page-002.jpg"))).getpixel((10, 10))
            self.assertGreater(red[0], red[2])
            self.assertGreater(blue[2], blue[0])
        status = self.client.get(f"/api/progress/{progress_id}").json
        self.assertEqual((status["completed"], status["total"]), (3, 3))
        self.client.delete(f"/api/progress/{progress_id}")

    def test_rejects_empty_invalid_and_oversized_pages(self):
        self.assertIn("No converted pages", self.upload([]).json["error"])
        self.assertIn("not a valid JPG", self.upload([b"not an image"]).json["error"])
        self.assertIn("could not be read", self.upload([b"\xff\xd8\xffbroken"]).json["error"])
        valid = jpg("red")
        with patch("app.features.pdf_to_jpg.validation.MAX_PAGE_BYTES", 10):
            self.assertIn("25 MB", self.upload([valid]).json["error"])
        with patch("app.features.pdf_to_jpg.validation.MAX_TOTAL_BYTES", 10):
            self.assertIn("100 MB", self.upload([valid]).json["error"])


if __name__ == "__main__":
    unittest.main()
