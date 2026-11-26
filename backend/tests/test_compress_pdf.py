"""Compress PDF output, level validation, and cleanup tests."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, TextStringObject

from app import create_app
from app.features.compress_pdf import storage
from app.features.compress_pdf.jobs import get_job
from app.features.compress_pdf.processing import compress_document


def blank_pdf(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    first = writer.add_blank_page(width=210, height=300)
    drawing = DecodedStreamObject()
    drawing.set_data(b"q 10 20 30 40 re S Q\n")
    first[NameObject("/Contents")] = writer._add_object(drawing)
    writer.add_blank_page(width=320, height=400)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def image_pdf(*, resolution: int = 300, quality: int = 95) -> bytes:
    image = Image.effect_noise((1400, 900), 100).convert("RGB")
    first = io.BytesIO()
    image.save(first, format="PDF", resolution=resolution, quality=quality)
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(first.getvalue())).pages[0])
    writer.add_blank_page(width=320, height=400)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class CompressPdfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(storage, "TEMP_ROOT", Path(self.temp.name) / "compress_pdf")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def upload(self, content: bytes, *, level: str = "gentle", name: str = "notes.pdf"):
        return self.client.post(
            "/api/compress-pdf",
            data={"file": (io.BytesIO(content), name), "level": level},
            content_type="multipart/form-data",
        )

    def test_gentle_preserves_page_order_and_dimensions(self):
        response = self.upload(blank_pdf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("PageKit-compressed.pdf", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        pages = PdfReader(io.BytesIO(response.data)).pages
        self.assertEqual([int(page.mediabox.width) for page in pages], [210, 320])
        self.assertIn(b"10 20 30 40 re S", pages[0].get_contents().get_data())
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_balanced_and_strong_recompress_images_locally(self):
        original = image_pdf()
        for level, target_dpi in (("balanced", 185), ("strong", 120)):
            with self.subTest(level=level):
                response = self.upload(original, level=level)
                self.assertEqual(response.status_code, 200)
                pages = PdfReader(io.BytesIO(response.data)).pages
                self.assertEqual(len(pages), 2)
                self.assertEqual(int(pages[1].mediabox.width), 320)
                self.assertLessEqual(pages[0].images[0].image.width, round(1400 * target_dpi / 300) + 1)
                self.assertLess(len(response.data), len(original))
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_keeps_image_when_reencoding_is_larger(self):
        original = image_pdf(resolution=72, quality=15)
        source = PdfReader(io.BytesIO(original)).pages[0].images[0].indirect_reference.get_object()
        response = self.upload(original, level="balanced")
        self.assertEqual(response.status_code, 200)
        result = PdfReader(io.BytesIO(response.data)).pages[0].images[0].indirect_reference.get_object()
        self.assertEqual(result._data, source._data)

    def test_keeps_document_structure(self):
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=400)
        writer.add_outline_item("Chapter one", 0)
        writer.add_annotation(0, Link(rect=(20, 20, 80, 40), url="https://example.org"))
        writer.add_metadata({"/Title": "Course notes", "/Author": "PageKit test"})
        writer.set_page_label(0, 0, prefix="A-", start=3)
        field = DictionaryObject({NameObject("/FT"): NameObject("/Tx"),
                                  NameObject("/T"): TextStringObject("student"),
                                  NameObject("/V"): TextStringObject("Ada")})
        field_ref = writer._add_object(field)
        writer._root_object[NameObject("/AcroForm")] = writer._add_object(
            DictionaryObject({NameObject("/Fields"): ArrayObject([field_ref])}))
        source = io.BytesIO()
        writer.write(source)
        expected_labels = PdfReader(io.BytesIO(source.getvalue())).page_labels
        for level in ("gentle", "balanced", "strong"):
            with self.subTest(level=level):
                response = self.upload(source.getvalue(), level=level)
                self.assertEqual(response.status_code, 200)
                result = PdfReader(io.BytesIO(response.data))
                self.assertEqual(result.metadata.title, "Course notes")
                self.assertEqual(result.outline[0].title, "Chapter one")
                self.assertEqual(result.page_labels, expected_labels)
                self.assertEqual(result.get_fields()["student"].value, "Ada")
                annotations = result.pages[0]["/Annots"]
                self.assertEqual(annotations[0].get_object()["/A"]["/URI"], "https://example.org")

    def test_rejects_bad_levels_and_invalid_uploads(self):
        valid = blank_pdf()
        self.assertIn("Choose Gentle", self.upload(valid, level="extreme").json["error"])
        self.assertIn("cannot be read", self.upload(b"%PDF-broken").json["error"])
        self.assertIn("password protected", self.upload(blank_pdf(encrypted=True)).json["error"])
        self.assertIn(".pdf", self.upload(valid, name="notes.txt").json["error"])
        with patch("app.features.compress_pdf.validation.MAX_FILE_BYTES", 10):
            oversized = self.upload(valid)
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

    def test_job_reports_completed_units_and_downloads(self):
        job_id = self.client.post("/api/compress-pdf/jobs").json["jobId"]
        response = self.client.post(
            f"/api/compress-pdf/jobs/{job_id}/upload",
            data={"file": (io.BytesIO(blank_pdf()), "notes.pdf"), "level": "gentle"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 202)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = self.client.get(f"/api/compress-pdf/jobs/{job_id}").json
            if status["state"] == "ready":
                break
            time.sleep(0.01)
        self.assertEqual(status["state"], "ready")
        self.assertEqual(status["completed"], status["total"])
        self.assertEqual(status["total"], 4)  # Two pages, object pass, output write.
        result = self.client.get(f"/api/compress-pdf/jobs/{job_id}/download")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(result.data)).pages), 2)
        self.assertEqual(self.client.delete(f"/api/compress-pdf/jobs/{job_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/compress-pdf/jobs/{job_id}").status_code, 404)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_job_failure_cancellation_and_progress_checkpoints(self):
        bad_id = self.client.post("/api/compress-pdf/jobs").json["jobId"]
        bad = self.client.post(
            f"/api/compress-pdf/jobs/{bad_id}/upload",
            data={"file": (io.BytesIO(b"%PDF-broken"), "bad.pdf"), "level": "balanced"},
            content_type="multipart/form-data",
        )
        self.assertEqual(bad.status_code, 202)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = self.client.get(f"/api/compress-pdf/jobs/{bad_id}").json
            if status["state"] == "error":
                break
            time.sleep(0.01)
        self.assertEqual(status["state"], "error")
        self.assertIn("cannot be read", status["error"])
        self.client.delete(f"/api/compress-pdf/jobs/{bad_id}")

        started = Event()
        def wait_for_cancel(_source, _level, on_progress, check_cancel):
            on_progress("Compressing pages", 1, 4)
            started.set()
            while True:
                check_cancel()
                time.sleep(0.01)

        with patch("app.features.compress_pdf.jobs.compress_document", side_effect=wait_for_cancel):
            job_id = self.client.post("/api/compress-pdf/jobs").json["jobId"]
            response = self.client.post(
                f"/api/compress-pdf/jobs/{job_id}/upload",
                data={"file": (io.BytesIO(blank_pdf()), "notes.pdf"), "level": "gentle"},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 202)
            self.assertTrue(started.wait(2))
            progress = self.client.get(f"/api/compress-pdf/jobs/{job_id}").json
            self.assertEqual((progress["phase"], progress["completed"], progress["total"]),
                             ("Compressing pages", 1, 4))
            self.assertEqual(self.client.delete(f"/api/compress-pdf/jobs/{job_id}").status_code, 204)
            self.assertEqual(self.client.get(f"/api/compress-pdf/jobs/{job_id}").status_code, 404)
        self.assertEqual(list(storage.TEMP_ROOT.iterdir()), [])

    def test_processing_progress_reaches_final_unit_only_after_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pdf"
            path.write_bytes(blank_pdf())
            updates = []
            result = compress_document(path, "gentle", lambda phase, done, total: updates.append((phase, done, total)))
        self.assertTrue(result.getvalue().startswith(b"%PDF-"))
        self.assertEqual(updates[-1], ("Writing output PDF", 3, 4))
        self.assertTrue(all(done < total for _, done, total in updates))

    def test_expired_progress_job_is_removed(self):
        job_id = self.client.post("/api/compress-pdf/jobs").json["jobId"]
        job = get_job(job_id)
        job.created_at = time.time() - storage.RETENTION_SECONDS - 1
        self.assertEqual(self.client.get(f"/api/compress-pdf/jobs/{job_id}").status_code, 404)
        self.assertTrue(job.cancelled.is_set())


if __name__ == "__main__":
    unittest.main()
