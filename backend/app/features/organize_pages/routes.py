"""Organize pages HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from .processing import organize_document
from .storage import request_directory
from .validation import OrganizeValidationError, save_validated_pdf

organize_pages_blueprint = Blueprint("organize_pages", __name__)


@organize_pages_blueprint.post("/api/organize-pages")
def organize_pages():
    originals = request.files.getlist("original")
    additions = request.files.getlist("added")
    if len(originals) != 1 or len(additions) > 1:
        return jsonify(error="Choose one original PDF and at most one second PDF."), 400
    try:
        with request_directory() as directory:
            original_path = directory / "original.pdf"
            save_validated_pdf(originals[0], original_path, "The original PDF")
            added_path = directory / "added.pdf" if additions else None
            if added_path:
                save_validated_pdf(additions[0], added_path, "The second PDF")
            result = organize_document(
                original_path,
                added_path,
                request.form.get("order", ""),
                request.form.get("insertion_position"),
            )
        return send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-organized.pdf")
    except OrganizeValidationError as exc:
        return jsonify(error=str(exc)), 400
