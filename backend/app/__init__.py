"""PageKit Flask application factory."""

from flask import Flask, jsonify, request

from .features.merge_pdf.routes import merge_pdf_blueprint
from .features.merge_pdf.storage import cleanup_stale_requests as cleanup_stale_merge_requests
from .features.organize_pages.routes import organize_pages_blueprint
from .features.organize_pages.storage import cleanup_stale_requests as cleanup_stale_organize_requests
from .features.split_pdf.routes import split_pdf_blueprint
from .features.split_pdf.storage import cleanup_stale_requests as cleanup_stale_split_requests


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 101 * 1024 * 1024
    cleanup_stale_merge_requests()
    cleanup_stale_organize_requests()
    cleanup_stale_split_requests()
    app.register_blueprint(merge_pdf_blueprint)
    app.register_blueprint(organize_pages_blueprint)
    app.register_blueprint(split_pdf_blueprint)

    @app.before_request
    def remove_stale_pdf_files():
        cleanup_stale_merge_requests()
        cleanup_stale_organize_requests()
        cleanup_stale_split_requests()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(413)
    def request_too_large(_error):
        if request.path == "/api/organize-pages":
            return jsonify(error="The upload is too large. Choose PDFs up to 25 MB each."), 413
        if request.path == "/api/split-pdf":
            return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413
        return jsonify(error="The upload is too large. Choose up to 20 PDFs, 25 MB each, with a 100 MB total limit."), 413

    return app
