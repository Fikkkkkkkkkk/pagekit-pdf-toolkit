"""Split PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request

from .processing import split_document
from .storage import request_directory
from .validation import SplitValidationError, save_validated_pdf

split_pdf_blueprint = Blueprint("split_pdf", __name__)


@split_pdf_blueprint.post("/api/split-pdf")
def split_pdf():
    progress = progress_for_request()
    files = request.files.getlist("file")
    if len(files) != 1:
        return jsonify(error="Choose exactly one PDF file to split."), 400
    try:
        with request_directory() as directory:
            source = directory / "input.pdf"
            save_validated_pdf(files[0], source)
            result = split_document(source, request.form.get("ranges", ""), progress)
        return send_file(result, mimetype="application/zip", as_attachment=True, download_name="PageKit-split.zip")
    except SplitValidationError as exc:
        return jsonify(error=str(exc)), 400
