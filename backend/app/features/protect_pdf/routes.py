"""Protect PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import protect_document
from .storage import request_directory
from .validation import ProtectValidationError, save_validated_pdf, validate_passwords

protect_pdf_blueprint = Blueprint("protect_pdf", __name__)


@protect_pdf_blueprint.post("/api/protect-pdf")
def protect_pdf():
    progress = progress_for_request()
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to protect."), 400
    try:
        password = validate_passwords(request.form.get("password", ""), request.form.get("confirmation", ""))
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = protect_document(path, password, progress)
        response = send_file(result, mimetype="application/pdf", as_attachment=True,
                             download_name="PageKit-protected.pdf")
        response.headers["Cache-Control"] = "no-store"
        return response
    except ProtectValidationError as exc:
        return jsonify(error=str(exc)), 400
