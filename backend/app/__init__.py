"""PageKit Flask application factory."""

from flask import Flask, jsonify, request

from .shared.progress import ProgressCancelled, progress_blueprint

from .features.add_page_numbers.routes import add_page_numbers_blueprint
from .features.add_page_numbers.storage import cleanup_stale_requests as cleanup_stale_number_requests
from .features.compress_pdf.routes import compress_pdf_blueprint
from .features.compress_pdf.storage import cleanup_stale_requests as cleanup_stale_compress_requests
from .features.crop_pdf.routes import crop_pdf_blueprint
from .features.crop_pdf.storage import cleanup_stale_requests as cleanup_stale_crop_requests
from .features.jpg_to_pdf.routes import jpg_to_pdf_blueprint
from .features.jpg_to_pdf.storage import cleanup_stale_requests as cleanup_stale_jpg_requests
from .features.merge_pdf.routes import merge_pdf_blueprint
from .features.merge_pdf.storage import cleanup_stale_requests as cleanup_stale_merge_requests
from .features.organize_pages.routes import organize_pages_blueprint
from .features.organize_pages.storage import cleanup_stale_requests as cleanup_stale_organize_requests
from .features.pdf_to_word.routes import pdf_to_word_blueprint
from .features.pdf_to_word.storage import cleanup_stale_requests as cleanup_stale_word_requests
from .features.protect_pdf.routes import protect_pdf_blueprint
from .features.protect_pdf.storage import cleanup_stale_requests as cleanup_stale_protect_requests
from .features.rotate_pdf.routes import rotate_pdf_blueprint
from .features.rotate_pdf.storage import cleanup_stale_requests as cleanup_stale_rotate_requests
from .features.split_pdf.routes import split_pdf_blueprint
from .features.split_pdf.storage import cleanup_stale_requests as cleanup_stale_split_requests
from .features.unlock_pdf.routes import unlock_pdf_blueprint
from .features.unlock_pdf.storage import cleanup_stale_requests as cleanup_stale_unlock_requests
from .features.watermark_pdf.routes import watermark_pdf_blueprint
from .features.watermark_pdf.storage import cleanup_stale_requests as cleanup_stale_watermark_requests


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 101 * 1024 * 1024
    cleanup_stale_number_requests()
    cleanup_stale_compress_requests()
    cleanup_stale_crop_requests()
    cleanup_stale_jpg_requests()
    cleanup_stale_merge_requests()
    cleanup_stale_organize_requests()
    cleanup_stale_word_requests()
    cleanup_stale_protect_requests()
    cleanup_stale_rotate_requests()
    cleanup_stale_split_requests()
    cleanup_stale_unlock_requests()
    cleanup_stale_watermark_requests()
    app.register_blueprint(add_page_numbers_blueprint)
    app.register_blueprint(compress_pdf_blueprint)
    app.register_blueprint(crop_pdf_blueprint)
    app.register_blueprint(jpg_to_pdf_blueprint)
    app.register_blueprint(merge_pdf_blueprint)
    app.register_blueprint(organize_pages_blueprint)
    app.register_blueprint(pdf_to_word_blueprint)
    app.register_blueprint(protect_pdf_blueprint)
    app.register_blueprint(rotate_pdf_blueprint)
    app.register_blueprint(split_pdf_blueprint)
    app.register_blueprint(unlock_pdf_blueprint)
    app.register_blueprint(watermark_pdf_blueprint)
    app.register_blueprint(progress_blueprint)

    @app.errorhandler(ProgressCancelled)
    def progress_cancelled(_error):
        return jsonify(error="Processing was cancelled or its progress expired. Try again."), 409

    @app.before_request
    def remove_stale_pdf_files():
        cleanup_stale_number_requests()
        cleanup_stale_compress_requests()
        cleanup_stale_crop_requests()
        cleanup_stale_jpg_requests()
        cleanup_stale_merge_requests()
        cleanup_stale_organize_requests()
        cleanup_stale_word_requests()
        cleanup_stale_protect_requests()
        cleanup_stale_rotate_requests()
        cleanup_stale_split_requests()
        cleanup_stale_unlock_requests()
        cleanup_stale_watermark_requests()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(413)
    def request_too_large(_error):
        if request.path == "/api/compress-pdf" or request.path.startswith("/api/compress-pdf/jobs/"):
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/crop-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/jpg-to-pdf":
            return jsonify(error="The upload is too large. Choose up to 20 images, 25 MB each and 100 MB total."), 413
        if request.path == "/api/add-page-numbers":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/rotate-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/pdf-to-word":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/protect-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/unlock-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/watermark-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        if request.path == "/api/organize-pages":
            return jsonify(error="The upload is too large. Choose PDFs up to 25 MB each."), 413
        if request.path == "/api/split-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        return jsonify(error="The upload is too large. Choose up to 20 PDFs, 25 MB each, with a 100 MB total limit."), 413

    return app
