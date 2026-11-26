# PageKit design and delivery plan

## Goal and users

PageKit is a responsive PDF toolkit for students handling lecture notes, assignments, readings, forms, and applications. It should make common document tasks easy to find and understand on a phone or laptop. The first release focuses on local, single-task document work with no account requirement.

## Product principles

- Make the next step obvious, with plain language and useful previews.
- Respect students' time, devices, and privacy. Keep controls lightweight and usable on small screens.
- Show the real availability of every tool. A planned tool must never appear to work before it does.
- Give PageKit its own identity, layout, typography, color, and interaction patterns. Tool categories can reflect familiar PDF tasks, but do not copy iLovePDF branding, page designs, assets, or copy.
- Prefer focused feature modules over a shared abstraction that anticipates requirements we have not built.

## Complete long-term tool catalog

### Organize
- Merge PDF
- Split PDF
- Organize pages: reorder, add, and delete pages
- Rotate PDF
- Add page numbers
- Crop PDF
- Repair PDF
- Scan to PDF

### Optimize
- Compress PDF

### Convert
- PDF to Word
- PDF to PowerPoint
- PDF to Excel
- PDF to JPG and extract images
- PDF to PDF/A
- PDF to Markdown
- Word to PDF
- PowerPoint to PDF
- Excel to PDF
- JPG to PDF (JPG and PNG images; the original Images to PDF scope)
- HTML/webpage to PDF

### Edit
- Edit PDF with text, images, shapes, and annotations
- Add a text or image watermark
- Create, fill, and edit PDF forms

### Security and review
- Protect PDF with a password
- Unlock PDF
- Sign PDF
- Redact PDF
- Compare two PDFs

### PDF intelligence
- OCR for scanned PDFs
- AI PDF summarizer
- Translate PDF

Batch processing and reusable workflows that chain multiple tools are long-term capabilities. Accounts, cloud storage connections, mobile apps, desktop apps, team features, and a public API are future possibilities outside the first release.

## Milestones

### Active release scope (agreed expansion of the original first-release scope)
- Merge PDF
- Split PDF
- Organize pages
- Rotate PDF
- Images to PDF
- Compress PDF
- Add page numbers
- Crop PDF
- PDF to Word
- PDF to JPG (page images; embedded-image extraction remains later)
- Protect PDF
- Unlock PDF
- Watermark PDF (text only in version one)
- Sign PDF (visual signature only)

The foundation milestone built the app shell, catalog, documentation, and backend health check. Merge PDF, Split PDF, Organize pages, Rotate PDF, Add page numbers, Crop PDF, Compress PDF, PDF to Word, PDF to JPG, Protect PDF, Unlock PDF, text-only Watermark PDF, JPG to PDF, and visual Sign PDF are now available. JPG to PDF implements the original Images to PDF release item for JPG and PNG input. PDF to Word was moved into the active release at the user's request on 2026-11-25; Crop PDF, Protect PDF, Watermark PDF, and Unlock PDF on 2026-11-26; and PDF to JPG and visual Sign PDF on 2026-11-27. The original seven-tool scope is otherwise unchanged.

### Later milestones
- Document preparation: Repair PDF, Scan to PDF.
- Conversion: PDF to PowerPoint, PDF to Excel, extract embedded images from PDF, PDF to PDF/A, PDF to Markdown, Word to PDF, PowerPoint to PDF, Excel to PDF, HTML/webpage to PDF.
- Editing and review: Edit PDF with text, images, shapes, and annotations; Add an image watermark; Create, fill, and edit PDF forms; Redact PDF; Compare two PDFs.
- Intelligence: OCR for scanned PDFs, AI PDF summarizer, Translate PDF.
- Productivity: Batch processing and reusable workflows that chain multiple tools.

The milestone ordering after the active release is provisional. Moving another tool into or out of the active-release scope requires an explicit agreed change recorded below.

## Main user flow

Choose tool → select files → preview/options → process → download. Each implemented tool should explain accepted file types, size limits, and what processing will do before the user starts. The user can remove or replace files before processing and can retry recoverable errors.

## Architecture and technology

- Frontend: React, TypeScript, and Vite in `frontend/`.
- Backend: Python and Flask in `backend/`.
- Merge PDF uses `pypdf` to combine pages in upload order. It rejects password-protected, invalid, and unreadable files with useful errors.
- Split PDF uses `pypdf` to create one PDF per entered range and Python's standard `zipfile` module to package them in range order. Neither feature uses an external document service or native binary dependency.
- Organize pages uses `pypdf` to validate uploaded PDFs and write a new document in the submitted page order. The frontend uses Mozilla's [`pdfjs-dist`](https://www.npmjs.com/package/pdfjs-dist) to render numbered thumbnails locally in the browser; its worker is bundled with Vite. The backend validates the final page references and insertion position independently of the preview. The original PDFs are not modified.
- Rotate PDF uses the existing `pypdf` to rotate selected pages in 90-degree steps while preserving page order and unselected pages. The frontend uses the existing `pdfjs-dist` dependency to preview every page locally and show chosen orientations. The Flask endpoint validates the uploaded PDF and one rotation value per page before producing a new PDF in memory. The original PDF is not modified.
- Crop PDF uses `pypdf` to set a new crop box on every page from the same relative rectangle. The browser uses `pdfjs-dist` to preview a chosen page and show the selected visible area before processing. The backend maps that area through each page's existing crop box and rotation, preserving page content and order. Cropping hides content outside the box; it is not secure redaction and does not remove that content from the file.
- Compress PDF uses the existing `pypdf` and Pillow dependencies locally. Gentle applies lossless content-stream compression and removes duplicate or unused PDF objects. Balanced recompresses eligible RGB or grayscale images at JPEG quality 75 and downsamples images whose effective resolution at their largest displayed size exceeds 185 dpi. Strong uses JPEG quality 55 and a 120 dpi target, so fine image detail can soften more. Recompressed image streams replace originals only when their encoded bytes are smaller. Images with unknown placement, masks, transparency, unsupported color modes, or inline storage are left unchanged. Text and vector content are not rasterized. The writer clones the whole source document before compression; regression tests check that bookmarks, URL link annotations, a basic form field, document metadata, and page labels survive this path. More complex PDF features, appearance behavior, and digital signatures are not guaranteed; rewriting a signed PDF can invalidate its signature. Results can be larger or nearly unchanged, especially when already optimized; the UI reports actual input and output sizes and percentage saved, including negative savings. Its preview shows the source PDF, so users should inspect the downloaded copy for image quality.
- Add page numbers uses `pypdf` to append a numbered text overlay to every page. Users choose top or bottom and left, center, or right placement, plus a positive starting number. The frontend uses `pdfjs-dist` to preview the first page and approximate number placement. The backend maps positions through each page's existing rotation and crop box, preserves source page order and content, and returns a new PDF in memory. Tight page margins or existing headers and footers may overlap the added number.
- PDF to Word uses the existing `pypdf` for text and image extraction, plus [`python-docx`](https://pypi.org/project/python-docx/) to write editable DOCX files and the `pypdf[image]` Pillow dependency to decode embedded images. `python-docx` 1.2 is MIT licensed and supports Python 3.9+; [Pillow 12.3](https://pypi.org/project/pillow/12.3.0/) is MIT-CMU licensed and supports Python 3.10+. Both were checked for this project's Python 3.10 runtime. This approach keeps conversion local and avoids a paid service.
- Protect PDF uses `pypdf` with `algorithm="AES-256"` explicitly to create a new PDF that requires an opening password. The installed backend lacked the optional AES dependency, so the existing requirement now includes `pypdf[crypto]`, which installs `cryptography`; no separate PDF library or service was added. The backend rejects already-encrypted and unreadable PDFs, checks both password fields, clones the source document, and writes the protected copy in memory. Passwords are used only during the request and are not logged or stored in files or progress state. The user must retain the password; PageKit cannot recover it. The original remains unchanged.
- Unlock PDF uses the same local `pypdf[crypto]` dependency to decrypt a PDF only with a password supplied by the user. It rejects unencrypted and unreadable files, distinguishes an incorrect password from a file that cannot be decrypted, and clones the decrypted document into an unencrypted copy in memory. The source remains unchanged. Tests verify page order, bookmarks, and metadata in the copied PDF; other complex document features are not guaranteed. Passwords are used only during the request and are not logged or saved in files or progress state. PageKit does not guess, recover, or bypass passwords.
- Watermark PDF version one uses the existing `pypdf` and browser `pdfjs-dist` dependencies; no new package or external service is needed. The editor places controls beside a large page preview on desktop and above it on narrow screens. Users set one line of text; built-in Helvetica, Times, or Courier at 8–72 points; bold, italic, and underline; one of nine positions or a repeated Mosaic; rotation from -180 to 180 degrees; a six-digit RGB color; opacity from 1% to 100%; and over or behind layering. The backend writes a text stream with a PDF transparency graphics state on every page, mapped through each page's crop box and rotation, and keeps the source PDF unchanged. It appends the stream for over-content marks and prepends it for behind-content marks; opaque backgrounds can cover the latter. The built-in fonts use WinAnsi encoding and support Western European characters; unsupported symbols are rejected with a clear message. Long text is reduced to fit the page or a Mosaic tile. A live browser preview approximates font metrics and layering over the source page; the browser then renders the actual generated PDF at the same scale for review before download, with a page selector. Image watermarks remain a later milestone. A watermark is not secure redaction, and rewriting signed PDFs can invalidate their signatures.
- JPG to PDF uses the existing Pillow and `pypdf` dependencies locally. The browser previews JPG and PNG images and submits them in the chosen order; the backend independently validates file count, extension, signature, size, and image decoding. EXIF orientation is applied before embedding. Transparent PNG pixels are composited onto white, and images are encoded as JPEG at quality 90 in the output PDF; this can change image appearance slightly, but source files remain unchanged. A4 and Letter pages keep each image upright within 36-point white margins. Fit to image uses 96 pixels per inch, caps the longest page side at 2000 points, and rotates images when necessary to match the selected portrait or landscape orientation. The PDF contains one page per image. Each file is limited to 25 MB, with 20 files and 100 MB total; images above 50 million pixels are rejected to limit memory use. No new dependency or external service is added.
- PDF to JPG renders every page with the already-installed browser PDF.js at up to 144 dpi and 2400 pixels per side. Users choose compact, balanced, or high browser JPEG quality. The source PDF remains in the browser and is unchanged. Rendered JPG pages, limited to 25 MB each and 100 MB total, are uploaded to the local Flask backend, which validates them with existing Pillow and packages them in order using Python's standard-library `zipfile` as `page-001.jpg`, etc. JPGs and the ZIP are held only for the request, with no feature-specific server temporary files. Page conversion progress counts completed rendered pages; upload progress uses actual bytes sent; ZIP progress counts validated pages and finalization. The UI shows 100% only after the ZIP response is ready. This feature exports page images only; extraction of embedded images remains planned. No new dependency or external processing service is added.
- Sign PDF uses existing browser PDF.js for source and generated page previews, browser canvas for drawing and typed signatures, Pillow for image validation and orientation, and pypdf to add a transparent image object to chosen pages. Users can place one signature per page on multiple pages, resize it, move it, and set a separate rotation angle for each page. Browser placement controls keep the full rotated mark inside the visible page; Flask validates that bound as well as the PDF, image, and page numbers. The output is a new PDF; the original remains unchanged. This is a visual signature only, with no cryptographic signing or signer verification. Rewriting an already digitally signed PDF may invalidate its existing digital signature. No new dependency or external service is added.
- Conversion reconstructs editable text from positioned PDF fragments. It uses available font names, sizes, and drawing information to approximate bold, italic, underlined text, centered and right-aligned paragraphs, line and paragraph spacing, page breaks, and simple two-column regions (as Word tables). A consistent repeated top-right line is placed in the Word header at its source position; body offsets are measured below that header. It preserves basic page size and extracts embedded images after the text on their source page. Complex columns, tables, exact font metrics, and image placement can still differ because PDF content does not carry Word paragraph or table structure. PDF text extraction order can vary with the source document. A page with too little selectable text and images is treated as likely scanned/image-only, and conversion stops with an OCR-unavailable message. No OCR is performed.
- [`pdf2docx`](https://github.com/ArtifexSoftware/pdf2docx/discussions/374) was considered but not selected: Artifex says it is no longer actively maintained. Its PyMuPDF dependency offers [AGPLv3 or commercial licensing](https://pymupdf.io/licensing), which would require a separate deployment decision. No exact layout preservation is promised.
- Frontend and backend live in separate folders. No database or user accounts in the first release.
- `frontend/src/app/` owns application composition and routing when needed. `frontend/src/features/tool-catalog/` owns the catalog. Future PDF tools each get their own folder under `frontend/src/features/` and `backend/app/features/`.
- Each PDF tool owns its UI, API interaction, validation, and processing logic. Put code in `shared/` only when multiple features genuinely need it. Shared modules may hold common UI primitives, styles, and backend file utilities once they are needed.
- `backend/app/` owns Flask setup and health check. `backend/app/shared/` owns the progress reporter used by all available tools; `tests/` holds meaningful tests.
- All available tools use a shared progress ID for each request. The browser measures upload bytes with XMLHttpRequest and polls a short-lived Flask progress record during processing. Each feature reports completed files, page ranges, pages, or source pages at its own processing boundaries, plus final output writing. The UI keeps processing below 100% until the completed output response arrives. Polling is limited to roughly three requests per second; no elapsed-time estimate is presented. Cancellation signals the processing loop and each tool's request directory is removed as the request exits. Progress records expire after 15 minutes or are deleted by the client after success, error, or cancellation. Progress state is process-local and a multiworker deployment would need worker affinity or a shared store.
- Do not silently change these technology or first-release scope decisions. Explain a blocker and propose the smallest adjustment before changing either.

## File privacy and temporary files

- Temporary uploaded files have a 15-minute maximum retention threshold. The main request flow for every available tool with a private request directory, including Protect PDF, Unlock PDF, Watermark PDF, Sign PDF, and JPG to PDF, deletes it immediately after processing or an error. Abandoned directories are cleaned at startup and during later requests once they reach 15 minutes. Outputs are returned from memory and are not stored as server files. PDF to JPG keeps the PDF in the browser and packages uploaded JPGs from request streams in memory, without a feature-specific temporary directory; the request closes its streams on completion or failure. The older Compress PDF job endpoints also remain available; they delete uploaded files after validation and hold results in memory until download, cancellation, or expiry. Organize pages and Rotate PDF render thumbnails locally before upload; Add page numbers, Crop PDF, Compress PDF, Watermark PDF, JPG to PDF, PDF to JPG, and Sign PDF render previews locally.
- Use private, per-request temporary storage outside public web assets, with unpredictable names and strict file-size and type checks. Never trust a client-supplied path or filename for storage.
- Delete temporary inputs and outputs after completion, failure, cancellation, and expiration. Account for interrupted requests and process restarts with a cleanup mechanism.
- Do not log document contents, passwords, or sensitive filenames. Use HTTPS in deployment and return only the files the request produced.
- Document any third-party processing before introducing it. No cloud storage or external document processing is part of the first release.

## Experience requirements

- Support keyboard use, visible focus, semantic headings, accessible names, adequate contrast, and screen-reader announcements for meaningful status changes.
- Adapt layouts, navigation, file controls, and previews to narrow screens without horizontal scrolling.
- Every tool must provide clear empty, loading/progress, success, and error states. Errors should explain a useful next action; success should identify the output and provide download.
- Confirm potentially destructive page edits before processing and show the resulting order or page selection in the preview.

## Definition of done for a future PDF tool

- The tool implements the choose → select → preview/options → process → download flow and accurately communicates its limits.
- Its frontend and backend logic live in dedicated feature modules; only proven reusable code is shared.
- Input validation, safe temporary-file handling, cleanup, failure handling, and output naming are implemented.
- Keyboard, screen-reader, responsive, loading, empty, success, and error states are verified.
- Meaningful automated tests cover successful processing and important invalid or failure cases; README and catalog availability are updated.
- A user can complete the task end to end on supported file examples without an account.

## Change log
- 2026-11-27: Added a per-page Sign PDF rotation angle and matching preview/PDF placement, with rotated-bound validation and a reset-to-zero control. Other tools are unchanged.
- 2026-11-27: At the user's request, moved Sign PDF into the active release and implemented visual signatures using existing PDF.js, Pillow, and pypdf dependencies. This does not provide a cryptographic digital signature.
- 2026-11-27: At the user's request, moved PDF to JPG page export into the active release while leaving embedded-image extraction for later. Reused browser PDF.js, Pillow, and Python `zipfile` for local rendering and ZIP packaging, with page-based conversion progress, shared upload and ZIP progress, validation, and no new dependency. Other tools are unchanged.
- 2026-11-26: At the user's request, moved Unlock PDF into the active release. Added local known-password decryption with `pypdf`, validation, shared progress, and 15-minute temporary-file cleanup. No new dependency or other-tool behavior change.
- 2026-11-26: Implemented the original Images to PDF release item as JPG to PDF, accepting ordered JPG and PNG uploads with A4, Letter, or fit-to-image pages and portrait or landscape orientation. Added local EXIF handling, white compositing for transparent PNGs, shared progress, validation, and 15-minute temporary cleanup. No dependency or other-tool behavior change.
- 2026-11-26: Expanded the Watermark PDF editor with a responsive controls-and-preview layout, three built-in font families, size and style controls, a 3×3 position grid, Mosaic, and over/behind layering. Wired the options through validation, local PDF generation, and approximate and generated previews. No new dependency or other-tool change.
- 2026-11-26: Enlarged and centered Watermark PDF previews for desktop and narrow screens. Added a live approximate source-page overlay for text, position, rotation, color, and opacity; the generated-page preview remains the actual output. Backend processing and other tools are unchanged.
- 2026-11-26: At the user's request, moved text-only Watermark PDF into the active release. Added local pypdf text overlays with position, rotation, color, and opacity controls, a rendered preview of the generated PDF, validation, shared progress, and 15-minute temporary-file cleanup. Image watermarks remain planned; no new dependency or other-tool behavior change.
- 2026-11-26: At the user's request, moved Protect PDF into the active release and implemented local AES-256 password protection. Added pypdf's optional crypto dependency after confirming it was missing, along with validation, shared progress, and temporary-file cleanup. Other tools remain unchanged.
- 2026-11-26: Added shared real upload and processing progress to Merge PDF, Split PDF, Organize pages, Rotate PDF, Crop PDF, Add page numbers, Compress PDF, and PDF to Word. Feature processing loops report completed work units; the UI reaches 100% only when the response is ready. Added cancellation and 15-minute progress expiry without changing PDF processing behavior.
- 2026-11-26: Added Compress PDF processing progress based on completed page and image units, with separate upload progress and cancellation. The output is marked 100% only after the PDF is written and ready. Jobs are held in process memory for up to 15 minutes; a multiworker deployment would need a shared job store or worker affinity. Compression settings and other tools are unchanged.
- 2026-11-26: Added Compress PDF upload progress from browser transfer events, an indeterminate state while Flask processes the file, and a completion state. Compression settings and other tools are unchanged.
- 2026-11-26: Lowered only Balanced Compress PDF's displayed-size target from 200 to 185 dpi; Gentle, Strong, JPEG quality, and image-retention behavior are unchanged.
- 2026-11-26: Improved Compress PDF image handling with displayed-size DPI targets and a smaller-encoded-stream check. Cloned the full document and added preservation tests for bookmarks, links, annotations, a basic form, metadata, and page labels. Clarified quality trade-offs and the source-only preview; no dependency or release-scope change.

- 2026-11-26: Implemented Compress PDF with three local compression levels, actual size and savings reporting, image-quality trade-offs, validation, and the 15-minute temporary-file policy. It uses existing dependencies and leaves other PDF tool behavior unchanged.
- 2026-11-26: At the user's request, moved Crop PDF from later milestones into the active release and implemented it with a browser crop preview, relative crop boxes on every page, local validation and processing, and 15-minute temporary-file cleanup. It hides content without securely erasing it. Other tool behavior and technology choices remain unchanged.
- 2026-11-26: Implemented Add page numbers with six placements, a selectable starting number, browser preview, local `pypdf` overlay, validation, and the existing 15-minute temporary-file policy. Marked it available without changing the release scope or other tools.
- 2026-11-26: Implemented Rotate PDF with per-page and whole-document 90-degree turns, browser page previews, backend validation, and the existing 15-minute temporary-file policy. Marked it available without changing the active-release scope or other tools.
- 2026-11-25: Preserved spaces at mixed-font run boundaries, detected underlines drawn as thin filled rectangles, and applied the source's list-paragraph styling to literal bracketed legal markers without automatic numbering. Kept party numbering, header, footer, and page placement rules unchanged.
- 2026-11-25: Changed consecutive, consistently positioned `1.`, `2.`, ... party entries from literal marker text to a real Word numbered list, matching the source list behavior. Bracketed legal markers remain literal text; header, footer, and page placement rules are unchanged.
- 2026-11-25: Reconstructed separately positioned party-list numbers and bracketed legal paragraph markers as literal editable text with PDF-derived tab stops. Kept party continuations aligned to the text column without using automatic Word numbering.
- 2026-11-25: Place consistent repeated top-right PDF text in the Word header and measure the first body paragraph from Word's effective body origin below the header. Kept footer numbering and page-break rules unchanged.
- 2026-11-25: Give each PDF-to-Word download a unique name and disable response caching so a new conversion can be distinguished from older DOCX files during pagination review.
- 2026-11-25: Corrected PDF-to-Word page assembly so each source page starts with a break on its first Word paragraph instead of a standalone break that could create an empty page after overflow. Text outside a PDF page's visible crop area is omitted from Word layout. A consistent sequence of centered page numbers near the page bottom is placed in an editable Word footer field instead of body paragraphs, and near-edge body spacing is adjusted to fit. Added regression coverage for full and blank source pages.
- 2026-11-25: Improved PDF to Word layout reconstruction using positioned text and available font/style information. Added editable alignment, spacing, underlines, and simple column tables without changing dependencies or other PDF tools.
- 2026-11-25: At the user's request, added PDF to Word to the active release scope and implemented local conversion with `pypdf`, `python-docx`, and Pillow. Recorded the converter's layout limits and OCR boundary. Other scope and technology decisions remain unchanged.
- 2026-11-25: Implemented Organize pages with local PDF.js thumbnails and backend `pypdf` processing. Kept the first-release scope, frameworks, and 15-minute temporary-file policy unchanged.
- 2026-11-25: Combined the Merge PDF and Split PDF implementations. Merge PDF uses `pypdf`; Split PDF uses `pypdf` and standard-library ZIP creation. Both use a 15-minute temporary-file retention threshold. No scope or framework change.
- 2026-11-24: Initial product plan, locked first-release scope, technology choices, and foundation milestone recorded.
