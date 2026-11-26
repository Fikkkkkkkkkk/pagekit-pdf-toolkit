"""Package ordered JPG pages into a ZIP without storing them as files."""

from io import BytesIO
from zipfile import ZIP_STORED, ZipFile

from werkzeug.datastructures import FileStorage

from ...shared.progress import ProgressReporter
from .validation import PdfToJpgValidationError, read_jpg_page


def package_pages(files: list[FileStorage], progress: ProgressReporter | None = None) -> BytesIO:
    if not files:
        raise PdfToJpgValidationError("No converted pages were received. Choose a PDF and try again.")
    archive = BytesIO()
    total_bytes = 0
    digits = max(3, len(str(len(files))))
    if progress:
        progress.start(len(files) + 1, "Packaging JPG pages")
    try:
        with ZipFile(archive, "w", compression=ZIP_STORED) as zipped:
            for position, upload in enumerate(files, start=1):
                if progress:
                    progress.check()
                content = read_jpg_page(upload, position, total_bytes)
                total_bytes += len(content)
                zipped.writestr(f"page-{position:0{digits}d}.jpg", content)
                if progress:
                    progress.advance("Packaging JPG pages")
        if progress:
            progress.advance("Finalizing ZIP")
    except PdfToJpgValidationError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise PdfToJpgValidationError("The JPG pages could not be packaged. Try converting again.") from exc
    archive.seek(0)
    return archive
