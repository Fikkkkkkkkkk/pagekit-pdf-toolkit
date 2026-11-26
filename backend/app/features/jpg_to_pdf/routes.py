"""JPG and PNG to PDF endpoint."""

from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import combine_images
from .storage import request_directory
from .validation import ImagePdfValidationError, save_validated_image, validate_file_count, validate_options

jpg_to_pdf_blueprint = Blueprint("jpg_to_pdf", __name__)


@jpg_to_pdf_blueprint.post("/api/jpg-to-pdf")
def jpg_to_pdf():
    progress = progress_for_request()
    files = request.files.getlist("files")
    try:
        validate_file_count(files)
        page_size = request.form.get("page_size", "")
        orientation = request.form.get("orientation", "")
        validate_options(page_size, orientation)
        with request_directory() as directory:
            paths = []
            total_bytes = 0
            for position, upload in enumerate(files, start=1):
                extension = Path(upload.filename or "").suffix.lower()
                path = directory / f"input-{position}{extension}"
                total_bytes += save_validated_image(upload, path, position, total_bytes)
                paths.append(path)
            result = combine_images(paths, page_size, orientation, progress)
        response = send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-images.pdf")
        response.headers["Cache-Control"] = "no-store"
        return response
    except ImagePdfValidationError as exc:
        return jsonify(error=str(exc)), 400
