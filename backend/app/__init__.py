"""PageKit Flask application factory."""

from flask import Flask, jsonify

from .features.split_pdf.routes import split_pdf_blueprint
from .features.split_pdf.storage import cleanup_stale_requests


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 26 * 1024 * 1024
    cleanup_stale_requests()
    app.register_blueprint(split_pdf_blueprint)

    @app.before_request
    def remove_stale_split_files():
        cleanup_stale_requests()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="The PDF is too large. Choose a file up to 25 MB."), 413

    return app
