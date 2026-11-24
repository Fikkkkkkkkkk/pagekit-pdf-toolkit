"""Upload and page-order validation for Organize pages."""

import json
import re
from pathlib import Path
from typing import Literal, TypedDict

from werkzeug.datastructures import FileStorage

MAX_FILE_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class OrganizeValidationError(ValueError):
    pass


class PageSelection(TypedDict):
    source: Literal["original", "added"]
    page: int


def save_validated_pdf(upload: FileStorage, target: Path, label: str) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise OrganizeValidationError(f"{label} must be a .pdf file.")
    size = 0
    with target.open("wb") as output:
        while chunk := upload.stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise OrganizeValidationError(f"{label} is over the 25 MB limit.")
            output.write(chunk)
    if not size:
        raise OrganizeValidationError(f"{label} is empty. Choose a readable PDF.")
    with target.open("rb") as saved:
        if saved.read(5) != b"%PDF-":
            raise OrganizeValidationError(f"{label} is not a valid PDF.")


def validate_page_order(
    raw_order: str,
    original_count: int,
    added_count: int,
    raw_insert_position: str | None,
) -> list[PageSelection]:
    try:
        order = json.loads(raw_order)
    except (TypeError, ValueError) as exc:
        raise OrganizeValidationError("The page order is invalid. Reload the PDF and try again.") from exc
    if not isinstance(order, list):
        raise OrganizeValidationError("The page order is invalid. Reload the PDF and try again.")
    if not order:
        raise OrganizeValidationError("At least one page must remain. You cannot delete every page.")
    if len(order) > original_count + added_count:
        raise OrganizeValidationError("The page order contains more pages than the uploaded PDFs.")

    if added_count:
        if raw_insert_position is None or not re.fullmatch(r"[0-9]+", raw_insert_position):
            raise OrganizeValidationError("Choose a valid insertion position for the added PDF.")
        if int(raw_insert_position) > original_count:
            raise OrganizeValidationError(f"The insertion position must be between 0 and {original_count}.")
    elif raw_insert_position not in (None, ""):
        raise OrganizeValidationError("An insertion position requires a second PDF.")

    seen: set[tuple[str, int]] = set()
    validated: list[PageSelection] = []
    for position, item in enumerate(order, start=1):
        if not isinstance(item, dict) or set(item) != {"source", "page"}:
            raise OrganizeValidationError(f"Page selection {position} is invalid.")
        source, page = item["source"], item["page"]
        if source not in ("original", "added") or type(page) is not int:
            raise OrganizeValidationError(f"Page selection {position} is invalid.")
        page_count = original_count if source == "original" else added_count
        if page < 1 or page > page_count:
            raise OrganizeValidationError(f"Page selection {position} is outside the {source} PDF.")
        key = (source, page)
        if key in seen:
            raise OrganizeValidationError(f"Page selection {position} repeats a page. Choose each page once.")
        seen.add(key)
        validated.append({"source": source, "page": page})
    if added_count and not any(item["source"] == "added" for item in validated):
        raise OrganizeValidationError("Select at least one page from the second PDF, or remove that PDF.")
    return validated
