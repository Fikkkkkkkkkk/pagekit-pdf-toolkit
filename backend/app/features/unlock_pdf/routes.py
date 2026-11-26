"""Unlock PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import unlock_document
from .storage import request_directory
from .validation import UnlockValidationError, save_validated_pdf, validate_password

unlock_pdf_blueprint = Blueprint("unlock_pdf", __name__)


@unlock_pdf_blueprint.post("/api/unlock-pdf")
def unlock_pdf():
    progress = progress_for_request()
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one password-protected PDF."), 400
    try:
        password = validate_password(request.form.get("password", ""))
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = unlock_document(path, password, progress)
        response = send_file(result, mimetype="application/pdf", as_attachment=True,
                             download_name="PageKit-unlocked.pdf")
        response.headers["Cache-Control"] = "no-store"
        return response
    except UnlockValidationError as exc:
        return jsonify(error=str(exc)), 400
