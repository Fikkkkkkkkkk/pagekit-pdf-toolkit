"""Decrypt with the supplied password and write an unencrypted copy."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError, PdfReadError, WrongPasswordError

from ...shared.progress import ProgressReporter
from .validation import UnlockValidationError

PDF_ERRORS = (PdfReadError, DependencyError, NotImplementedError, OSError, ValueError, TypeError, KeyError, IndexError)


def unlock_document(path: Path, password: str, progress: ProgressReporter | None = None) -> BytesIO:
    try:
        reader = PdfReader(path, strict=False)
        if not reader.is_encrypted:
            raise UnlockValidationError("This PDF is not password protected. Choose a locked PDF.")
    except UnlockValidationError:
        raise
    except PDF_ERRORS as exc:
        raise UnlockValidationError("This PDF cannot be read. Replace it and try again.") from exc

    if progress:
        progress.start(3, "Checking password")
    try:
        if not reader.decrypt(password):
            raise UnlockValidationError("The password is incorrect. Enter the password used to open this PDF.")
        if not reader.pages:
            raise UnlockValidationError("This PDF has no pages to unlock.")
        if progress:
            progress.advance("Checking password")
    except UnlockValidationError:
        raise
    except WrongPasswordError as exc:
        raise UnlockValidationError("The password is incorrect. Enter the password used to open this PDF.") from exc
    except PDF_ERRORS as exc:
        raise UnlockValidationError("This PDF could not be decrypted with that password. Check the file and try again.") from exc

    writer = None
    output = BytesIO()
    try:
        writer = PdfWriter(clone_from=reader)
        if progress:
            progress.advance("Copying unlocked document")
            progress.set_phase("Writing unlocked PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing unlocked PDF")
    except PDF_ERRORS as exc:
        raise UnlockValidationError("This PDF was opened, but an unlocked copy could not be written. Try another PDF reader or file.") from exc
    finally:
        if writer is not None:
            writer.close()
    output.seek(0)
    return output
