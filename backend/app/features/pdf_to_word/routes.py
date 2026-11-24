"""PDF to Word HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from .conversion import convert_pdf
from .storage import request_directory
from .validation import WordConversionError, save_validated_pdf

pdf_to_word_blueprint = Blueprint("pdf_to_word", __name__)


@pdf_to_word_blueprint.post("/api/pdf-to-word")
def pdf_to_word():
    files = request.files.getlist("file")
    if len(files) != 1:
        return jsonify(error="Choose exactly one PDF to convert to Word."), 400
    try:
        with request_directory() as directory:
            source = directory / "input.pdf"
            save_validated_pdf(files[0], source)
            result = convert_pdf(source)
        return send_file(
            result,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name="PageKit-converted.docx",
        )
    except WordConversionError as exc:
        return jsonify(error=str(exc)), 400
