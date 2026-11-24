"""HTTP route for ordered PDF merging."""

from flask import Blueprint, jsonify, request, send_file

from .processing import merge_documents
from .storage import request_directory
from .validation import MergeValidationError, save_validated_file, validate_file_count

merge_pdf_blueprint = Blueprint("merge_pdf", __name__)


@merge_pdf_blueprint.post("/api/merge-pdf")
def merge_pdf():
    files = request.files.getlist("files")
    try:
        validate_file_count(files)
        with request_directory() as directory:
            paths = []
            total_bytes = 0
            for position, upload in enumerate(files, start=1):
                path = directory / f"input-{position}.pdf"
                total_bytes += save_validated_file(upload, path, position, total_bytes)
                paths.append(path)
            result = merge_documents(paths)
        return send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-merged.pdf")
    except MergeValidationError as exc:
        return jsonify(error=str(exc)), 400
