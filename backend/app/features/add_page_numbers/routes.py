"""Add page numbers HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from .processing import number_document
from .storage import request_directory
from .validation import PageNumberValidationError, save_validated_pdf

add_page_numbers_blueprint = Blueprint("add_page_numbers", __name__)


@add_page_numbers_blueprint.post("/api/add-page-numbers")
def add_page_numbers():
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to number."), 400
    try:
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = number_document(path, request.form.get("position", ""), request.form.get("start", ""))
        return send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-numbered.pdf")
    except PageNumberValidationError as exc:
        return jsonify(error=str(exc)), 400
