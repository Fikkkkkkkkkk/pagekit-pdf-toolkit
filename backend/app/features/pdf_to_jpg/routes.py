"""PDF to JPG ZIP endpoint for locally rendered pages."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import package_pages
from .validation import PdfToJpgValidationError

pdf_to_jpg_blueprint = Blueprint("pdf_to_jpg", __name__)


@pdf_to_jpg_blueprint.post("/api/pdf-to-jpg")
def pdf_to_jpg():
    progress = progress_for_request()
    try:
        archive = package_pages(request.files.getlist("pages"), progress)
        response = send_file(archive, mimetype="application/zip", as_attachment=True,
                             download_name="PageKit-jpg-pages.zip")
        response.headers["Cache-Control"] = "no-store"
        return response
    except PdfToJpgValidationError as exc:
        return jsonify(error=str(exc)), 400
