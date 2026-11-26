"""Measured progress remains tied to successful PDF work."""

import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from pypdf import PdfWriter

from app import create_app
from app.features.merge_pdf import storage as merge_storage
from app.shared.progress import RETENTION_SECONDS, _progress
from test_pdf_to_word import pdf_bytes as text_pdf


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=300, height=400)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class SharedProgressTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_all_available_tool_routes_report_completed_units(self):
        source = blank_pdf()
        cases = [
            ("/api/merge-pdf", {"files": [(io.BytesIO(source), "a.pdf"), (io.BytesIO(source), "b.pdf")]}, 3),
            ("/api/split-pdf", {"file": (io.BytesIO(source), "a.pdf"), "ranges": "1, 2"}, 3),
            ("/api/organize-pages", {"original": (io.BytesIO(source), "a.pdf"),
                                     "order": json.dumps([{"source": "original", "page": 2},
                                                          {"source": "original", "page": 1}])}, 3),
            ("/api/rotate-pdf", {"file": (io.BytesIO(source), "a.pdf"), "rotations": "[90, 0]"}, 3),
            ("/api/crop-pdf", {"file": (io.BytesIO(source), "a.pdf"),
                               "crop": json.dumps({"left": 0.1, "top": 0.1, "right": 0.9, "bottom": 0.9})}, 3),
            ("/api/add-page-numbers", {"file": (io.BytesIO(source), "a.pdf"),
                                       "position": "bottom-center", "start": "1"}, 3),
            ("/api/compress-pdf", {"file": (io.BytesIO(source), "a.pdf"), "level": "gentle"}, 4),
            ("/api/pdf-to-word", {"file": (io.BytesIO(text_pdf(["Course notes one", "Course notes two"])), "a.pdf")}, 5),
        ]
        for route, data, expected_total in cases:
            with self.subTest(route=route):
                progress_id = self.client.post("/api/progress").json["id"]
                response = self.client.post(route, data=data, content_type="multipart/form-data",
                                            headers={"X-PageKit-Progress-ID": progress_id})
                self.assertEqual(response.status_code, 200, response.json if response.is_json else None)
                status = self.client.get(f"/api/progress/{progress_id}").json
                self.assertEqual((status["completed"], status["total"]),
                                 (expected_total, expected_total))
                self.assertEqual(self.client.delete(f"/api/progress/{progress_id}").status_code, 204)
                self.assertEqual(self.client.get(f"/api/progress/{progress_id}").status_code, 404)

    def test_cancelled_progress_rejects_request(self):
        progress_id = self.client.post("/api/progress").json["id"]
        self.client.delete(f"/api/progress/{progress_id}")
        response = self.client.post("/api/split-pdf", data={"file": (io.BytesIO(blank_pdf()), "a.pdf"),
                                                             "ranges": "1"},
                                    content_type="multipart/form-data",
                                    headers={"X-PageKit-Progress-ID": progress_id})
        self.assertEqual(response.status_code, 409)

    def test_progress_expires_after_fifteen_minutes(self):
        progress_id = self.client.post("/api/progress").json["id"]
        item = _progress[progress_id]
        item.created_at = time.time() - RETENTION_SECONDS - 1
        self.assertEqual(self.client.get(f"/api/progress/{progress_id}").status_code, 404)
        self.assertTrue(item.cancelled.is_set())

    def test_cancellation_cleans_active_upload_directory(self):
        progress_id = self.client.post("/api/progress").json["id"]
        started = Event()
        responses = []

        def paused_merge(_paths, progress):
            progress.start(3, "Merging files")
            started.set()
            while True:
                progress.check()
                time.sleep(0.01)

        def upload():
            with create_app().test_client() as client:
                responses.append(client.post(
                    "/api/merge-pdf",
                    data={"files": [(io.BytesIO(blank_pdf()), "a.pdf"),
                                    (io.BytesIO(blank_pdf()), "b.pdf")]},
                    content_type="multipart/form-data",
                    headers={"X-PageKit-Progress-ID": progress_id},
                ))

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(merge_storage, "TEMP_ROOT", Path(directory) / "merge_pdf"), \
             patch("app.features.merge_pdf.routes.merge_documents", side_effect=paused_merge):
            worker = Thread(target=upload)
            worker.start()
            self.assertTrue(started.wait(3))
            self.assertEqual(self.client.delete(f"/api/progress/{progress_id}").status_code, 204)
            worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(responses[0].status_code, 409)
            self.assertEqual(list(merge_storage.TEMP_ROOT.iterdir()), [])
