"""PDF merging, in the same order as the uploaded files."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .validation import MergeValidationError


def merge_documents(paths: list[Path]) -> BytesIO:
    output = BytesIO()
    writer = PdfWriter()
    for position, path in enumerate(paths, start=1):
        try:
            reader = PdfReader(path, strict=False)
            if reader.is_encrypted:
                raise MergeValidationError(f"File {position} is password protected. Unlock it before merging.")
            if not reader.pages:
                raise MergeValidationError(f"File {position} has no pages to merge.")
            writer.append(reader)
        except MergeValidationError:
            raise
        except (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise MergeValidationError(f"File {position} cannot be read as a PDF. Replace it and try again.") from exc
    try:
        writer.write(output)
    except (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise MergeValidationError("One of the PDFs could not be merged. Replace the unreadable file and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
