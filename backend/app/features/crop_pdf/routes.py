"""Crop PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from .processing import crop_document
from .storage import request_directory
from .validation import CropValidationError, save_validated_pdf

crop_pdf_blueprint = Blueprint("crop_pdf", __name__)


@crop_pdf_blueprint.post("/api/crop-pdf")
def crop_pdf():
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to crop."), 400
    try:
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = crop_document(path, request.form.get("crop", ""))
        return send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-cropped.pdf")
    except CropValidationError as exc:
        return jsonify(error=str(exc)), 400
