"""HTTP endpoint for visual PDF signatures."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request
from .processing import sign_document
from .storage import request_directory
from .validation import SignValidationError, save_pdf, save_signature

sign_pdf_blueprint = Blueprint('sign_pdf', __name__)


@sign_pdf_blueprint.post('/api/sign-pdf')
def sign_pdf():
    pdfs = request.files.getlist('file')
    signatures = request.files.getlist('signature')
    if len(pdfs) != 1 or len(signatures) != 1:
        return jsonify(error='Choose one PDF and one signature image.'), 400
    try:
        with request_directory() as directory:
            pdf_path = directory / 'source.pdf'
            signature_path = directory / 'signature.png'
            save_pdf(pdfs[0], pdf_path)
            save_signature(signatures[0], signature_path)
            output = sign_document(pdf_path, signature_path, request.form.get('placements', ''), progress_for_request())
        response = send_file(output, mimetype='application/pdf', as_attachment=True,
                             download_name='PageKit-visual-signature.pdf')
        response.headers['Cache-Control'] = 'no-store'
        return response
    except SignValidationError as exc:
        return jsonify(error=str(exc)), 400
