"""Rotate PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from .processing import rotate_document
from .storage import request_directory
from .validation import RotateValidationError, save_validated_pdf

rotate_pdf_blueprint = Blueprint("rotate_pdf", __name__)


@rotate_pdf_blueprint.post("/api/rotate-pdf")
def rotate_pdf():
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to rotate."), 400
    try:
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = rotate_document(path, request.form.get("rotations", ""))
        return send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-rotated.pdf")
    except RotateValidationError as exc:
        return jsonify(error=str(exc)), 400
