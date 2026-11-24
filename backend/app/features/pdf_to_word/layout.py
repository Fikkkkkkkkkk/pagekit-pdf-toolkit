"""Reconstruct editable Word layout from positioned PDF text fragments."""

from dataclasses import dataclass
from math import hypot
import re

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from pypdf import mult


@dataclass
class TextSpan:
    text: str
    x: float
    y: float  # Distance from the top of the PDF page, in points.
    baseline: float  # PDF y coordinate, measured from the bottom.
    size: float
    bold: bool
    italic: bool
    underline: bool
    font_name: str | None
    width: float
    leading_space: bool = False
    trailing_space: bool = False


@dataclass
class TextLine:
    spans: list[TextSpan]
    marker_text: str | None = None
    marker_body_x: float | None = None

    @property
    def x(self) -> float:
        return min(span.x for span in self.spans)

    @property
    def x_end(self) -> float:
        return max(span.x + span.width for span in self.spans)

    @property
    def y(self) -> float:
        return min(span.y for span in self.spans)

    @property
    def size(self) -> float:
        return max(span.size for span in self.spans)

    @property
    def bold(self) -> bool:
        return all(span.bold for span in self.spans)


def _clean_text(value: str) -> str:
    return "".join(
        char for char in value
        if char in "\t\n\r" or 32 <= ord(char) <= 0xD7FF or 0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF
    )


def _font_style(font) -> tuple[bool, bool, bool, str | None]:
    base = str(font.get("/BaseFont", "")) if font else ""
    base = base.split("+")[-1].lstrip("/")
    lower = base.lower()
    descriptor = font.get("/FontDescriptor") if font else None
    if descriptor is not None and hasattr(descriptor, "get_object"):
        descriptor = descriptor.get_object()
    weight = int(descriptor.get("/FontWeight", 0)) if descriptor else 0
    bold = any(word in lower for word in ("bold", "black", "semibold", "demi")) or weight >= 600
    italic = "italic" in lower or "oblique" in lower
    underline = "underline" in lower
    if "helvetica" in lower or "arial" in lower:
        family = "Arial"
    elif "times" in lower:
        family = "Times New Roman"
    elif "courier" in lower:
        family = "Courier New"
    else:
        family = None
    return bold, italic, underline, family


def _estimated_width(text: str, size: float, font) -> float:
    widths = font.get("/Widths") if font else None
    first_char = int(font.get("/FirstChar", 0)) if font else 0
    if widths:
        try:
            return sum(float(widths[ord(char) - first_char]) if first_char <= ord(char) < first_char + len(widths) else 500 for char in text) * size / 1000
        except (IndexError, TypeError, ValueError):
            pass
    units = sum(0.25 if char in " ilI.,:;!'" else 0.8 if char in "MW@%" else 0.55 for char in text)
    return max(1.0, units * size)


def _transform_point(x: float, y: float, matrix) -> tuple[float, float]:
    return (matrix[0] * x + matrix[2] * y + matrix[4], matrix[1] * x + matrix[3] * y + matrix[5])


def extract_lines(page) -> tuple[list[TextLine], bool]:
    """Collect positioned fragments and nearby drawn horizontal underlines."""
    spans: list[TextSpan] = []
    text_positions: list[tuple[float, float]] = []
    strokes: list[tuple[float, float, float]] = []
    pending: list[tuple[float, float, float]] = []
    last_point: tuple[float, float] | None = None
    last_text_position: tuple[float, float] | None = None
    had_text_fragments = False
    crop = page.cropbox
    crop_left, crop_bottom = float(crop.left), float(crop.bottom)
    crop_right, crop_top = float(crop.right), float(crop.top)
    page_height = crop_top - crop_bottom

    def visit_text(text, cm, tm, font, font_size):
        nonlocal had_text_fragments
        raw = _clean_text(text)
        cleaned = raw.strip()
        if not cleaned:
            return
        had_text_fragments = True
        matrix = mult(tm, cm)
        x, baseline = float(matrix[4]), float(matrix[5])
        # pypdf can emit a same-baseline fragment at (0, 0) even though its
        # preceding text-show operator has a valid text matrix.
        if x == 0 and baseline == 0 and last_text_position is not None:
            x, baseline = last_text_position
        scale = hypot(float(matrix[0]), float(matrix[1])) or 1.0
        size = max(1.0, float(font_size) * scale)
        bold, italic, underline, family = _font_style(font)
        width = _estimated_width(cleaned, size, font)
        # Some PDFs retain selectable text beyond the displayed page. Word must
        # only receive fragments that intersect the PDF's visible crop area.
        if x + width <= crop_left or x >= crop_right or baseline + size <= crop_bottom or baseline - size * 0.25 >= crop_top:
            return
        spans.append(TextSpan(cleaned, x - crop_left, crop_top - baseline, baseline - crop_bottom, size, bold, italic, underline, family, width, raw[0].isspace(), raw[-1].isspace()))

    def visit_operator(operator, operands, cm, _tm):
        nonlocal last_point, last_text_position
        if operator in (b"Tj", b"TJ", b"'", b'"'):
            matrix = mult(_tm, cm)
            last_text_position = float(matrix[4]), float(matrix[5])
            pieces = operands[0] if operands else []
            if not isinstance(pieces, (list, tuple)):
                pieces = [pieces]
            if any(isinstance(piece, bytes) and piece.strip(b"\x00 \t\r\n") for piece in pieces):
                text_positions.append((last_text_position[0] - crop_left, crop_top - last_text_position[1]))
        if operator == b"m" and len(operands) >= 2:
            last_point = _transform_point(float(operands[0]), float(operands[1]), cm)
            pending.clear()
        elif operator == b"l" and len(operands) >= 2 and last_point is not None:
            current = _transform_point(float(operands[0]), float(operands[1]), cm)
            if abs(last_point[1] - current[1]) <= 1.5 and abs(last_point[0] - current[0]) >= 3:
                pending.append((min(last_point[0], current[0]) - crop_left, max(last_point[0], current[0]) - crop_left, current[1] - crop_bottom))
            last_point = current
        elif operator == b"re" and len(operands) >= 4:
            x, y, width, height = map(float, operands[:4])
            start = _transform_point(x, y, cm)
            end = _transform_point(x + width, y + height, cm)
            if abs(start[1] - end[1]) <= 2.5 and abs(start[0] - end[0]) >= 3:
                pending.append((min(start[0], end[0]) - crop_left, max(start[0], end[0]) - crop_left, min(start[1], end[1]) - crop_bottom))
        elif operator in (b"S", b"s"):
            strokes.extend(pending)
            pending.clear()
            last_point = None
        elif operator in (b"f", b"F", b"f*", b"B", b"b"):
            strokes.extend(pending)
            pending.clear()
            last_point = None
        elif operator == b"n":
            pending.clear()
            last_point = None

    page.extract_text(visitor_text=visit_text, visitor_operand_before=visit_operator)
    for span in spans:
        if any(
            0.5 <= span.baseline - stroke_y <= 5
            and max(0, min(span.x + span.width, end) - max(span.x, start)) >= min(span.width, end - start) * 0.5
            for start, end, stroke_y in strokes
        ):
            span.underline = True

    rows: list[list[TextSpan]] = []
    for span in sorted(spans, key=lambda item: (item.y, item.x)):
        row = next((candidate for candidate in rows if abs(candidate[0].y - span.y) <= max(2.5, min(candidate[0].size, span.size) * 0.3)), None)
        if row is None:
            rows.append([span])
        else:
            row.append(span)

    lines: list[TextLine] = []
    page_width = float(crop.width)
    for row in rows:
        ordered = sorted(row, key=lambda item: item.x)
        group = [ordered[0]]
        for span in ordered[1:]:
            previous = group[-1]
            gap = span.x - (previous.x + previous.width)
            if gap > page_width * 0.12 and previous.x + previous.width < page_width * 0.53 and span.x > page_width * 0.47 and not re.fullmatch(r"[.,;:!?]+", span.text):
                lines.append(TextLine(group))
                group = [span]
            else:
                group.append(span)
        lines.append(TextLine(group))
    for line in lines:
        if len(line.spans) > 1:
            first_span, second_span = sorted(line.spans, key=lambda span: span.x)[:2]
            if re.fullmatch(r"\[\d+\]|\d+\.", first_span.text) and line.size * 1.2 <= second_span.x - first_span.x <= max(72, page_width * 0.12):
                line.marker_text = first_span.text
                line.marker_body_x = second_span.x
            continue
        if not line.spans:
            continue
        match = re.match(r"^(\[\d+\]|\d+\.)\s+\S", line.spans[0].text)
        if not match:
            continue
        positions = sorted(
            x for x, y in text_positions
            if abs(y - line.y) <= max(2.5, line.size * 0.3) and x > line.x + line.size * 0.8
        )
        if positions and line.size * 1.2 <= positions[0] - line.x <= max(72, page_width * 0.12):
            line.marker_text = match.group(1)
            line.marker_body_x = positions[0]
    return sorted(lines, key=lambda line: (line.y, line.x)), had_text_fragments


def _alignment(line: TextLine, page_width: float) -> WD_ALIGN_PARAGRAPH:
    center = (line.x + line.x_end) / 2
    if line.x > page_width * 0.18 and abs(center - page_width / 2) <= max(18, page_width * 0.04):
        return WD_ALIGN_PARAGRAPH.CENTER
    if line.x > page_width * 0.4 and (line.x_end >= page_width - 82 or line.x >= page_width * 0.67):
        return WD_ALIGN_PARAGRAPH.RIGHT
    return WD_ALIGN_PARAGRAPH.LEFT


def centered_footer_number(lines: list[TextLine], page_width: float, page_height: float) -> tuple[int, TextLine] | None:
    """Find a lone page number near the bottom, pending document-wide validation."""
    candidates = [
        line for line in lines
        if len(line.spans) == 1
        and line.spans[0].text.isdecimal()
        and line.y >= page_height * 0.88
        and abs((line.x + line.x_end) / 2 - page_width / 2) <= page_width * 0.08
    ]
    if len(candidates) != 1:
        return None
    return int(candidates[0].spans[0].text), candidates[0]


def top_right_header_line(lines: list[TextLine], page_width: float, page_height: float) -> TextLine | None:
    """Find a distinct top-right line for document-wide repeated-header checks."""
    candidates = [
        line for line in lines
        if line.y <= page_height * 0.15
        and line.x >= page_width * 0.55
        and len("".join(span.text for span in line.spans).strip()) >= 3
        and not "".join(span.text for span in line.spans).isdecimal()
    ]
    return min(candidates, key=lambda line: line.y) if len(candidates) == 1 else None


def add_repeated_header(section, line: TextLine, page_width: float) -> None:
    """Place a repeated source line in Word's editable header at its PDF y."""
    section.header_distance = Pt(max(0, line.y - line.size * 0.9))
    paragraph = section.header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.right_indent = Pt(max(0, page_width - section.right_margin.pt - line.x_end))
    _write_line(paragraph, line)


def decimal_list_lines(extractions: list[tuple[list[TextLine], bool]]) -> set[int]:
    """Recognize one consistently positioned 1., 2., ... PDF list."""
    candidates = [
        line for lines, _ in extractions for line in lines
        if line.marker_text and re.fullmatch(r"\d+\.", line.marker_text) and line.marker_body_x is not None
    ]
    if len(candidates) < 2:
        return set()
    first = candidates[0]
    if any(
        int(line.marker_text[:-1]) != index + 1
        or abs(line.x - first.x) > 3
        or abs(line.marker_body_x - first.marker_body_x) > 3
        for index, line in enumerate(candidates)
    ):
        return set()
    return {id(line) for line in candidates}


def _write_line(paragraph, line: TextLine, *, automatic_number: bool = False) -> None:
    if line.marker_text is not None and line.marker_body_x is not None:
        marker_span = line.spans[0]
        if not automatic_number:
            _add_styled_run(paragraph, line.marker_text, marker_span)
            paragraph.add_run("\t")
        if len(line.spans) == 1:
            _add_styled_run(paragraph, marker_span.text[len(line.marker_text):].lstrip(), marker_span)
        else:
            for span in sorted(line.spans[1:], key=lambda item: item.x):
                _add_styled_run(paragraph, span.text, span)
        return
    previous_end: float | None = None
    previous_span: TextSpan | None = None
    for span in sorted(line.spans, key=lambda item: item.x):
        gap = span.x - previous_end if previous_end is not None else 0
        needs_space = previous_span is not None and (previous_span.trailing_space or span.leading_space or gap > span.size * 0.2)
        prefix = " " if needs_space and not re.match(r"^[.,;:!?)}\]]", span.text) else ""
        _add_styled_run(paragraph, prefix + span.text, span)
        previous_end = span.x + span.width
        previous_span = span


def _add_styled_run(paragraph, value: str, span: TextSpan) -> None:
    run = paragraph.add_run(value)
    run.bold = span.bold
    run.italic = span.italic
    run.underline = span.underline
    run.font.size = Pt(min(max(span.size, 6), 72))
    if span.font_name:
        run.font.name = span.font_name


def _render_lines(container, lines: list[TextLine], page_width: float, left_edge: float, *, in_column: bool = False, start_new_page: bool = False, page_top_pt: float | None = None, vertical_scale: float = 1, numbered_lines: set[int] | None = None, list_num_id: int | None = None) -> None:
    previous: TextLine | None = None
    paragraph = None
    for line in lines:
        automatic_number = list_num_id is not None and numbered_lines is not None and id(line) in numbered_lines
        legal_marker = line.x <= page_width * 0.2 and bool(
            line.marker_text and re.fullmatch(r"\[\d+\]", line.marker_text)
            or line.spans and re.match(r"^\[\d+\](?:\s|$)", line.spans[0].text)
        )
        alignment = WD_ALIGN_PARAGRAPH.LEFT if in_column else _alignment(line, page_width)
        gap = (line.y - previous.y) * vertical_scale if previous else 0
        party_continuation = bool(
            previous
            and previous.marker_text
            and previous.marker_text.endswith(".")
            and previous.marker_body_x is not None
            and abs(line.x - previous.marker_body_x) <= max(3, line.size * 0.2)
            and gap <= max(previous.size, line.size) * 1.55
        )
        if party_continuation:
            alignment = WD_ALIGN_PARAGRAPH.LEFT
        new_paragraph = (
            party_continuation
            or previous is None
            or gap > max(previous.size, line.size) * 1.55
            or alignment != paragraph.alignment
            or abs(line.size - previous.size) > max(previous.size, line.size) * 0.25
            or (line.bold and not previous.bold)
        )
        if new_paragraph:
            if in_column and previous is None:
                paragraph = container.paragraphs[0]
            else:
                paragraph = container.add_paragraph()
            paragraph.alignment = alignment
            if automatic_number or legal_marker:
                paragraph.style = "List Paragraph"
            if automatic_number:
                num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
                num_pr.get_or_add_ilvl().val = 0
                num_pr.get_or_add_numId().val = list_num_id
            if previous is None and start_new_page:
                paragraph.paragraph_format.page_break_before = True
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.05
            if previous:
                paragraph.paragraph_format.space_before = Pt(min(72, max(0, gap - previous.size * 1.15)))
            elif page_top_pt is not None:
                paragraph.paragraph_format.space_before = Pt(max(0, line.y - page_top_pt - line.size * 0.85))
            if alignment == WD_ALIGN_PARAGRAPH.LEFT:
                indent = max(0, line.x - left_edge)
                paragraph.paragraph_format.left_indent = Pt(min(indent, page_width * (0.18 if in_column else 0.35)))
                if line.marker_body_x is not None:
                    body_indent = max(0, line.marker_body_x - left_edge)
                    paragraph.paragraph_format.tab_stops.add_tab_stop(Pt(body_indent))
                    if line.marker_text and line.marker_text.endswith("."):
                        paragraph.paragraph_format.left_indent = Pt(body_indent)
                        paragraph.paragraph_format.first_line_indent = Pt(line.x - line.marker_body_x)
        else:
            paragraph.paragraph_format.line_spacing = Pt(max(line.size, gap))
            paragraph.add_run().add_break()
        _write_line(paragraph, line, automatic_number=automatic_number)
        previous = line


def _column_region(lines: list[TextLine], page_width: float) -> tuple[float, float] | None:
    left = [line for line in lines if line.x_end < page_width * 0.52]
    right = [line for line in lines if line.x > page_width * 0.52]
    if len(left) < 2 or len(right) < 2:
        return None
    paired = [
        (left_line, right_line)
        for right_line in right
        for left_line in left
        if abs(left_line.y - right_line.y) <= max(left_line.size, right_line.size) * 1.25
    ]
    if len({id(pair[0]) for pair in paired}) < 2 or len({id(pair[1]) for pair in paired}) < 2:
        return None
    top = min(min(pair[0].y, pair[1].y) for pair in paired)
    bottom = max(max(pair[0].y, pair[1].y) for pair in paired)
    typical_size = max(8, min(line.size for pair in paired for line in pair))
    return top - typical_size * 0.5, bottom + typical_size * 0.5


def render_page(document, page, fallback_text: str, available_width_pt: float, *, start_new_page: bool = False, page_top_pt: float = 0, page_bottom_pt: float = 0, extraction: tuple[list[TextLine], bool] | None = None, footer_line: TextLine | None = None, header_line: TextLine | None = None, numbered_lines: set[int] | None = None, list_num_id: int | None = None) -> None:
    """Render positioned text as editable paragraphs and optional two-column table."""
    lines, had_text_fragments = extraction if extraction is not None else extract_lines(page)
    if footer_line is not None or header_line is not None:
        lines = [line for line in lines if line is not footer_line and line is not header_line]
    page_width = float(page.cropbox.width)
    if not lines:
        first = True
        for text in fallback_text.splitlines() if not had_text_fragments else []:
            if text.strip():
                paragraph = document.add_paragraph(_clean_text(text.strip()))
                if first and start_new_page:
                    paragraph.paragraph_format.page_break_before = True
                first = False
        if first:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.page_break_before = start_new_page
        return

    first_y = min(line.y for line in lines)
    last_line = max(lines, key=lambda line: line.y)
    target_last_y = float(page.cropbox.height) - page_bottom_pt - max(12, last_line.size * 0.9) - 5
    vertical_scale = min(1.0, max(0.75, (target_last_y - first_y) / (last_line.y - first_y))) if last_line.y > first_y else 1.0

    region = _column_region(lines, page_width)
    if region is None:
        _render_lines(document, lines, page_width, 54, start_new_page=start_new_page, page_top_pt=page_top_pt, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
        return

    top, bottom = region
    column_lines = [line for line in lines if top <= line.y <= bottom and (line.x_end < page_width * 0.52 or line.x > page_width * 0.52)]
    if len(column_lines) < 4:
        _render_lines(document, lines, page_width, 54, start_new_page=start_new_page, page_top_pt=page_top_pt, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
        return
    before = [line for line in lines if line.y < top]
    after = [line for line in lines if line.y > bottom]
    middle_other = [line for line in lines if top <= line.y <= bottom and line not in column_lines]
    opening_lines = before + [line for line in middle_other if line.y < min(item.y for item in column_lines)]
    _render_lines(document, opening_lines, page_width, 54, start_new_page=start_new_page, page_top_pt=page_top_pt if opening_lines else None, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
    if not opening_lines:
        # A page that begins with columns needs a body-level anchor before its table.
        anchor = document.add_paragraph()
        anchor.paragraph_format.page_break_before = start_new_page
        anchor.paragraph_format.space_after = Pt(0)
        anchor.paragraph_format.line_spacing = Pt(1)
        anchor.paragraph_format.space_before = Pt(max(0, min(item.y for item in column_lines) - page_top_pt))
        anchor.add_run().font.size = Pt(1)
    table = document.add_table(rows=1, cols=2)
    table.autofit = False
    for column in table.columns:
        column.width = Pt(available_width_pt / 2)
    left_cell, right_cell = table.rows[0].cells
    left_cell.width = right_cell.width = Pt(available_width_pt / 2)
    _render_lines(left_cell, sorted((line for line in column_lines if line.x_end < page_width * 0.52), key=lambda line: line.y), page_width, 54, in_column=True, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
    _render_lines(right_cell, sorted((line for line in column_lines if line.x > page_width * 0.52), key=lambda line: line.y), page_width, page_width * 0.52, in_column=True, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
    _render_lines(document, [line for line in middle_other if line.y >= min(item.y for item in column_lines)] + after, page_width, 54, vertical_scale=vertical_scale, numbered_lines=numbered_lines, list_num_id=list_num_id)
