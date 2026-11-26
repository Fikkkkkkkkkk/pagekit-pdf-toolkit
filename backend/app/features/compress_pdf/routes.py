"""Compress PDF HTTP endpoint."""

from flask import Blueprint, jsonify, request, send_file

from ...shared.progress import progress_for_request

from .jobs import (CompressionCancelled, cleanup_expired_jobs, create_job,
                   delete_job, get_job, start_job)
from .processing import compress_document
from .storage import request_directory
from .validation import CompressValidationError, save_validated_pdf, validate_level

compress_pdf_blueprint = Blueprint("compress_pdf", __name__)


@compress_pdf_blueprint.before_app_request
def remove_expired_compression_jobs():
    cleanup_expired_jobs()


@compress_pdf_blueprint.post("/api/compress-pdf")
def compress_pdf():
    progress = progress_for_request()
    uploads = request.files.getlist("file")
    if len(uploads) != 1:
        return jsonify(error="Choose exactly one PDF to compress."), 400
    try:
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            result = compress_document(
                path, request.form.get("level", ""),
                progress.update if progress else None,
                progress.check if progress else None,
            )
            if progress:
                progress.advance("Output ready")
        response = send_file(result, mimetype="application/pdf", as_attachment=True, download_name="PageKit-compressed.pdf")
        response.headers["Cache-Control"] = "no-store"
        return response
    except CompressValidationError as exc:
        return jsonify(error=str(exc)), 400


@compress_pdf_blueprint.post("/api/compress-pdf/jobs")
def create_compression_job():
    job = create_job()
    response = jsonify(jobId=job.id)
    response.status_code = 201
    response.headers["Cache-Control"] = "no-store"
    return response


@compress_pdf_blueprint.post("/api/compress-pdf/jobs/<job_id>/upload")
def upload_compression_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify(error="This compression job expired. Start again."), 404
    with job.lock:
        if job.state != "created":
            return jsonify(error="This compression job has already started."), 409
        job.state = "uploading"
    try:
        level = validate_level(request.form.get("level", ""))
        uploads = request.files.getlist("file")
        if len(uploads) != 1:
            raise CompressValidationError("Choose exactly one PDF to compress.")
        with request_directory() as directory:
            path = directory / "source.pdf"
            save_validated_pdf(uploads[0], path)
            job.check_cancel()
            source = path.read_bytes()
        job.check_cancel()
        start_job(job, source, level)
        response = jsonify(jobId=job.id)
        response.status_code = 202
        response.headers["Cache-Control"] = "no-store"
        return response
    except CompressionCancelled:
        delete_job(job_id)
        return jsonify(error="Compression was cancelled."), 409
    except CompressValidationError as exc:
        delete_job(job_id)
        return jsonify(error=str(exc)), 400
    except Exception:
        delete_job(job_id)
        raise


@compress_pdf_blueprint.get("/api/compress-pdf/jobs/<job_id>")
def compression_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify(error="This compression job expired. Start again."), 404
    response = jsonify(job.snapshot())
    response.headers["Cache-Control"] = "no-store"
    return response


@compress_pdf_blueprint.get("/api/compress-pdf/jobs/<job_id>/download")
def download_compressed_pdf(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify(error="This compression job expired. Start again."), 404
    with job.lock:
        result = job.result if job.state == "ready" else None
    if result is None:
        return jsonify(error="The compressed PDF is not ready yet."), 409
    response = send_file(result, mimetype="application/pdf", as_attachment=True,
                         download_name="PageKit-compressed.pdf")
    response.headers["Cache-Control"] = "no-store"
    return response


@compress_pdf_blueprint.delete("/api/compress-pdf/jobs/<job_id>")
def cancel_compression_job(job_id: str):
    delete_job(job_id)
    return "", 204
