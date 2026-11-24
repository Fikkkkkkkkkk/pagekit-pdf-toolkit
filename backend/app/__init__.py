"""PageKit Flask application factory."""

from flask import Flask, jsonify

from .features.merge_pdf.routes import merge_pdf_blueprint
from .features.merge_pdf.storage import cleanup_stale_requests


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
    cleanup_stale_requests()
    app.register_blueprint(merge_pdf_blueprint)

    @app.before_request
    def remove_stale_merge_files():
        cleanup_stale_requests()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="The upload is too large. Choose up to 20 PDFs, 25 MB each, with a 100 MB total limit."), 413

    return app
