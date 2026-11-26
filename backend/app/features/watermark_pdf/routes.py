"""Watermark PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import watermark_document
from .storage import request_directory
from .validation import WatermarkValidationError, save_validated_pdf, validate_options

watermark_pdf_blueprint = Blueprint("watermark_pdf", __name__)


@watermark_pdf_blueprint.post("/api/watermark-pdf")
def watermark_pdf():
    progress = progress_for_request()
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to watermark."), 400
    try:
        options = validate_options(request.form.get("text", ""), request.form.get("position", ""),
                                   request.form.get("rotation", ""), request.form.get("color", ""),
                                   request.form.get("opacity", ""), request.form.get("font_family", "helvetica"),
                                   request.form.get("font_size", "36"), request.form.get("bold", "false"),
                                   request.form.get("italic", "false"), request.form.get("underline", "false"),
                                   request.form.get("mosaic", "false"), request.form.get("layer", "over"))
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = watermark_document(path, options, progress)
        response = send_file(result, mimetype="application/pdf", as_attachment=True,
                             download_name="PageKit-watermarked.pdf")
        response.headers["Cache-Control"] = "no-store"
        return response
    except WatermarkValidationError as exc:
        return jsonify(error=str(exc)), 400
