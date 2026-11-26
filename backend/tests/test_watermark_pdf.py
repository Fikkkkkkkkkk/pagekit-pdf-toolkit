"""Watermark validation, overlay preservation, progress, and cleanup."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app import create_app
from app.features.watermark_pdf import storage


def sample_pdf(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for page in (writer.add_blank_page(width=300, height=400), writer.add_blank_page(width=420, height=300).rotate(90)):
        source = DecodedStreamObject()
        source.set_data(b"q\n0 0 m 10 10 l S\nQ\n")
        page[NameObject("/Contents")] = writer._add_object(source)
    writer.add_metadata({"/Title": "Study notes"})
    writer.add_outline_item("Chapter one", 0)
    if encrypted:
        writer.encrypt("secret", algorithm="AES-256")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class WatermarkPdfTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(temp.name) / "watermark_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, **overrides):
        data = {"file": (io.BytesIO(content), "notes.pdf"), "text": "DRAFT (2026) ©",
                "position": "middle-center", "rotation": "-30", "color": "#5964a8", "opacity": "30"}
        data.update(overrides)
        return self.client.post("/api/watermark-pdf", data=data, content_type="multipart/form-data")

    def test_watermarks_each_page_and_preserves_source_and_metadata(self):
        original = sample_pdf()
        progress_id = self.client.post("/api/progress").json["id"]
        response = self.client.post("/api/watermark-pdf", data={
            "file": (io.BytesIO(original), "notes.pdf"), "text": "DRAFT (2026) ©",
            "position": "middle-center", "rotation": "-30", "color": "#5964a8", "opacity": "30",
        }, content_type="multipart/form-data", headers={"X-PageKit-Progress-ID": progress_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        reader = PdfReader(io.BytesIO(response.data))
        self.assertEqual(len(reader.pages), 2)
        self.assertEqual([page.rotation for page in reader.pages], [0, 90])
        self.assertEqual(reader.metadata.title, "Study notes")
        self.assertEqual(reader.outline[0].title, "Chapter one")
        for page in reader.pages:
            self.assertIn("DRAFT (2026) ©", page.extract_text())
            states = page["/Resources"]["/ExtGState"]
            self.assertTrue(any(float(state.get_object()["/ca"]) == 0.3 for state in states.values()))
        status = self.client.get(f"/api/progress/{progress_id}").json
        self.assertEqual((status["completed"], status["total"]), (4, 4))
        self.client.delete(f"/api/progress/{progress_id}")
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_rejects_invalid_options_and_pdfs(self):
        original = sample_pdf()
        cases = [
            ({"text": " "}, "Enter text"),
            ({"text": "\u6c34"}, "Western European"),
            ({"position": "sideways"}, "position"),
            ({"rotation": "181"}, "rotation"),
            ({"color": "red"}, "color"),
            ({"opacity": "0"}, "opacity"),
            ({"font_family": "unknown"}, "font"),
            ({"font_size": "7"}, "font size"),
            ({"bold": "yes"}, "bold"),
            ({"layer": "under"}, "over or behind"),
        ]
        for change, message in cases:
            with self.subTest(change=change):
                response = self.upload(original, **change)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json["error"])
        self.assertIn("password protected", self.upload(sample_pdf(encrypted=True)).json["error"])
        self.assertIn("cannot be read", self.upload(b"%PDF-broken").json["error"])
        self.assertIn(".pdf", self.upload(original, file=(io.BytesIO(original), "notes.txt")).json["error"])
        with patch("app.features.watermark_pdf.validation.MAX_FILE_BYTES", 10):
            response = self.upload(original)
        self.assertEqual(response.status_code, 400)
        self.assertIn("25 MB", response.json["error"])
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_style_mosaic_and_layer_order(self):
        original = sample_pdf()
        settings = {"font_family": "times", "font_size": "24", "bold": "true", "italic": "true",
                    "underline": "true", "mosaic": "true", "position": "top-left", "layer": "behind"}
        behind = self.upload(original, **settings)
        self.assertEqual(behind.status_code, 200)
        page = PdfReader(io.BytesIO(behind.data)).pages[0]
        streams = page["/Contents"].get_object()
        self.assertEqual(len(streams), 2)
        overlay = streams[0].get_object().get_data()
        self.assertIn(b"/PKWatermark", overlay)
        self.assertEqual(overlay.count(b" Tj"), 12)
        self.assertEqual(overlay.count(b"\nS\n"), 12)
        self.assertIn(b"0 0 m 10 10 l S", streams[1].get_object().get_data())
        fonts = page["/Resources"]["/Font"]
        self.assertTrue(any(font.get_object()["/BaseFont"] == "/Times-BoldItalic" for font in fonts.values()))

        over = self.upload(original, **{**settings, "mosaic": "false", "layer": "over"})
        self.assertEqual(over.status_code, 200)
        over_streams = PdfReader(io.BytesIO(over.data)).pages[0]["/Contents"].get_object()
        self.assertIn(b"0 0 m 10 10 l S", over_streams[0].get_object().get_data())
        self.assertEqual(over_streams[1].get_object().get_data().count(b" Tj"), 1)

    def test_stale_cleanup_at_startup_and_later_request(self):
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
