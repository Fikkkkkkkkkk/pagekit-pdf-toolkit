"""Create one PDF per range and package results in range order."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .validation import SplitValidationError, parse_ranges


def split_document(source: Path, ranges_text: str) -> BytesIO:
    try:
        reader = PdfReader(source, strict=False)
        if reader.is_encrypted:
            raise SplitValidationError("This PDF is password protected. Choose an unlocked PDF.")
        page_count = len(reader.pages)
        if page_count == 0:
            raise SplitValidationError("This PDF has no pages to split.")
        ranges = parse_ranges(ranges_text, page_count)
        archive = BytesIO()
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
            for position, (start, end) in enumerate(ranges, start=1):
                writer = PdfWriter()
                try:
                    for page_number in range(start - 1, end):
                        writer.add_page(reader.pages[page_number])
                    output = BytesIO()
                    writer.write(output)
                    suffix = f"pages-{start}" if start == end else f"pages-{start}-{end}"
                    zipped.writestr(f"{position:02d}-{suffix}.pdf", output.getvalue())
                finally:
                    writer.close()
        archive.seek(0)
        return archive
    except SplitValidationError:
        raise
    except (PdfReadError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise SplitValidationError("This PDF could not be read or split. Choose another PDF and try again.") from exc
