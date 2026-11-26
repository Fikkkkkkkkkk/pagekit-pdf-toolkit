"""PDF merging, in the same order as the uploaded files."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from ...shared.progress import ProgressReporter

from .validation import MergeValidationError


def merge_documents(paths: list[Path], progress: ProgressReporter | None = None) -> BytesIO:
    output = BytesIO()
    writer = PdfWriter()
    if progress:
        progress.start(len(paths) + 1, "Merging files")
    for position, path in enumerate(paths, start=1):
        if progress:
            progress.check()
        try:
            reader = PdfReader(path, strict=False)
            if reader.is_encrypted:
                raise MergeValidationError(f"File {position} is password protected. Unlock it before merging.")
            if not reader.pages:
                raise MergeValidationError(f"File {position} has no pages to merge.")
            writer.append(reader)
            if progress:
                progress.advance("Merging files")
        except MergeValidationError:
            raise
        except (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise MergeValidationError(f"File {position} cannot be read as a PDF. Replace it and try again.") from exc
    try:
        if progress:
            progress.set_phase("Writing merged PDF")
        writer.write(output)
        if progress:
            progress.advance("Writing merged PDF")
    except (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise MergeValidationError("One of the PDFs could not be merged. Replace the unreadable file and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
