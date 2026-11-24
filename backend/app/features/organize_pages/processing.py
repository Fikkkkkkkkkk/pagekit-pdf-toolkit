"""Read source PDFs and write the validated page order."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .validation import OrganizeValidationError, PageSelection, validate_page_order

PDF_ERRORS = (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError)


def read_pdf(path: Path, label: str) -> PdfReader:
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise OrganizeValidationError(f"{label} is password protected. Choose an unlocked PDF.")
        if not reader.pages:
            raise OrganizeValidationError(f"{label} has no pages to organize.")
        return reader
    except OrganizeValidationError:
        raise
    except PDF_ERRORS as exc:
        raise OrganizeValidationError(f"{label} cannot be read as a PDF. Replace it and try again.") from exc


def organize_document(
    original_path: Path,
    added_path: Path | None,
    raw_order: str,
    raw_insert_position: str | None,
) -> BytesIO:
    original = read_pdf(original_path, "The original PDF")
    added = read_pdf(added_path, "The second PDF") if added_path else None
    order: list[PageSelection] = validate_page_order(
        raw_order, len(original.pages), len(added.pages) if added else 0, raw_insert_position
    )
    writer = PdfWriter()
    output = BytesIO()
    try:
        for item in order:
            reader = original if item["source"] == "original" else added
            assert reader is not None  # The order validator rejects missing added PDFs.
            writer.add_page(reader.pages[item["page"] - 1])
        writer.write(output)
    except PDF_ERRORS as exc:
        raise OrganizeValidationError("A selected page could not be processed. Reload the PDFs and try again.") from exc
    finally:
        writer.close()
    output.seek(0)
    return output
