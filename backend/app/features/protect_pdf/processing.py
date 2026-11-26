"""Write a password-protected copy with explicit AES-256 encryption."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from ...shared.progress import ProgressReporter
from .validation import ProtectValidationError

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)


def protect_document(path: Path, password: str, progress: ProgressReporter | None = None) -> BytesIO:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise ProtectValidationError("This PDF is already password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise ProtectValidationError("This PDF has no pages to protect.")
    except ProtectValidationError:
        raise
    except PDF_ERRORS as exc:
        raise ProtectValidationError("This PDF cannot be read. Replace it and try again.") from exc

    writer = None
    output = BytesIO()
    try:
        if progress:
            progress.start(3, "Copying document")
        writer = PdfWriter(clone_from=reader)
        if progress:
            progress.advance("Copying document")
            progress.check()
        writer.encrypt(user_password=password, algorithm="AES-256")
        if progress:
            progress.advance("Applying AES-256 protection")
            progress.check()
            progress.set_phase("Writing protected PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing protected PDF")
    except PDF_ERRORS as exc:
        raise ProtectValidationError("This PDF could not be protected. Choose another file and try again.") from exc
    finally:
        if writer is not None:
            writer.close()
    output.seek(0)
    return output
