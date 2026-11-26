# PageKit

PageKit is a student-focused PDF toolkit. Merge PDF, Split PDF, Organize pages, Rotate PDF, Add page numbers, Crop PDF, Compress PDF, PDF to Word, Protect PDF, Watermark PDF, and JPG to PDF are available; the other catalog tools are planned and unavailable. Flask handles these features and provides a health check.

## Requirements

- Node.js 20.19+ or 22.12+ and npm
- Python 3.10+

## Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). On Windows PowerShell systems that block `npm.ps1`, use `npm.cmd` in the commands above. Vite proxies `/api` requests to the Flask server at `127.0.0.1:5000`.

## Start the backend

In a second terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app run --debug
```

The health check is at `http://127.0.0.1:5000/api/health` and returns `{"status":"ok"}`.

## Try Merge PDF

1. Start both servers, then open the frontend URL.
2. Choose **Open Merge PDF** from the Merge PDF card.
3. Select at least two PDFs. Use the up/down buttons to set their order, or remove a file.
4. Choose **Merge PDFs**, then **Download merged PDF**. The output follows the order shown on the page.

Merge PDF accepts 2–20 PDFs, up to 25 MB per file and 100 MB total. It rejects empty, unreadable, and password-protected PDFs.

## Try Split PDF

1. Start both servers and open the frontend URL.
2. Open **Split PDF** from its catalog card and choose one PDF, up to 25 MB.
3. Enter comma-separated page ranges, such as `1-3, 5, 8-10`.
4. Choose **Split PDF**, then **Download ZIP**. Each range becomes a separate PDF, in the entered order.

Ranges must use positive page numbers, stay within the document, and not overlap. Password-protected or unreadable PDFs are rejected. The original PDF is unchanged. Merge PDF and Split PDF use `pypdf`; Split PDF also uses Python's `zipfile`. Uploads are kept in private request folders and removed after processing or an error; abandoned folders are cleaned at startup and on later requests once 15 minutes old. Results are returned directly and are not stored on the server.

## Try Organize pages

1. Start both servers and open **Organize pages** from the catalog.
2. Choose one PDF, up to 25 MB. Numbered page thumbnails are rendered locally in your browser.
3. Drag thumbnails to reorder them, or use the up/down buttons. Use the delete button to remove individual pages; at least one page must remain.
4. Optionally select an insertion position and choose a second PDF, up to 25 MB. Its pages are inserted together, and you can then reorder or remove them individually.
5. Review the thumbnail order, choose **Create organized PDF**, then **Download organized PDF**.

The backend validates both PDFs, the page order, and the insertion position. Password-protected or unreadable PDFs are rejected. Original files remain unchanged. The frontend uses Mozilla's `pdfjs-dist` for local thumbnails; the backend uses `pypdf` for the resulting PDF. Temporary uploads are deleted after processing or failure, with abandoned directories cleaned at startup and on later requests once 15 minutes old.

## Try Rotate PDF

1. Start both servers and open **Rotate PDF** from the catalog.
2. Choose one PDF, up to 25 MB. Numbered page previews appear in your browser.
3. Use **Left** or **Right** on individual pages, or **Turn left** or **Turn right** for all pages. Each click turns 90 degrees; review the preview before creating the output.
4. Choose **Create rotated PDF**, then **Download rotated PDF**.

Page order and pages you do not turn are preserved. The original file is unchanged. Password-protected or unreadable PDFs are rejected. `pdfjs-dist` renders local previews, and Flask uses `pypdf` to write the result. Uploads are removed after processing or failure; abandoned request folders are cleaned at startup and on later requests once 15 minutes old.

## Try Add page numbers

1. Start both servers and open **Add page numbers** from the catalog.
2. Choose one PDF, up to 25 MB. PageKit shows a preview of its first page.
3. Choose top or bottom placement, then left, center, or right. Enter the number to use on the first page.
4. Check the approximate placement preview, choose **Create numbered PDF**, then **Download numbered PDF**.

Each following page receives the next number. The original PDF, its page order, and existing page content stay unchanged. Review the downloaded result for overlap with existing headers, footers, or content near the margin. Password-protected or unreadable PDFs are rejected. `pdfjs-dist` renders the local preview, and Flask uses `pypdf` for the numbered copy. Uploads are removed after processing or failure; abandoned request folders are cleaned at startup and on later requests once 15 minutes old.

## Try Crop PDF

1. Start both servers and open **Crop PDF** from the catalog.
2. Choose one PDF, up to 25 MB. Select a page to preview if the document has multiple pages.
3. Drag on the preview to select a rectangle, or adjust its left edge, top edge, width, and height using the percentage fields. Review the cropped preview.
4. Choose **Create cropped PDF**, then **Download cropped PDF**.

The same relative crop is applied to every page, including pages with different dimensions. Page order and underlying content are preserved. **Cropping hides content outside the selected area; it does not securely erase or redact it.** Check the downloaded PDF before sharing. The frontend renders previews locally with `pdfjs-dist`; the Flask backend uses `pypdf`. Password-protected, unreadable, and oversized PDFs are rejected. Uploads are removed after processing or failure, and abandoned request folders are cleaned at startup and on later requests once 15 minutes old.

## Try Compress PDF

1. Start both servers and open **Compress PDF** from the catalog.
2. Choose one PDF, up to 25 MB. PageKit shows its original size, page count, and a source-page preview.
3. Choose **Gentle** for lossless stream compression, **Balanced** for JPEG quality 75 and a 185 dpi target at displayed size, or **Strong** for JPEG quality 55 and a 120 dpi target. Stronger levels can soften fine image detail.
4. Choose **Compress PDF**. Upload progress shows bytes sent; compression progress shows completed page and image work units. You can cancel while processing. Once the output is ready, compare the original size, output size, and percentage saved, then download the PDF copy. The page preview shows the source PDF; inspect the downloaded copy for image quality.

Text and vector content stay as PDF content, and page order is preserved. Balanced and Strong recompress eligible RGB or grayscale images only when the new encoded image is smaller. Downsampling depends on each image's largest displayed size. Transparent, masked, unsupported, inline, and images with unknown placement remain unchanged. The backend clones the source document before compression; tests verify bookmarks, URL link annotations, a basic form field, metadata, and page labels. Complex interactive behavior and digital signatures are not guaranteed; rewriting a signed PDF can invalidate its signature. An already optimized PDF may save very little or become larger, which the result panel reports plainly. Processing uses the existing `pypdf` and Pillow libraries locally. Password-protected, unreadable, and oversized PDFs are rejected. The request directory is removed after processing or failure. Progress records are cleared after success, error, or cancellation, or expire after 15 minutes on a later request.

All eleven available PDF tools show real upload progress from bytes sent and processing progress from completed work units. Cancel stops the client request and signals the backend to stop at its next processing boundary. Processing percentages reflect completed units, not elapsed time, and reach 100% only when the output response is ready. Progress records are held in this Flask process, so a multiworker deployment would need worker affinity or a shared progress store.

## Try Protect PDF

1. Start both servers and open **Protect PDF** from the catalog.
2. Choose one unlocked PDF, up to 25 MB. Enter an opening password and confirm it.
3. Choose **Protect PDF**, then download the protected copy. Open it in a PDF reader to confirm it asks for the password.

PageKit uses pypdf's explicit AES-256 encryption locally. Its optional `crypto` extra installs `cryptography`, which is required for AES. The original PDF is unchanged. Already-encrypted, unreadable, and oversized PDFs are rejected with an error. PageKit does not log or save the password; keep it somewhere safe because PageKit cannot recover it. The temporary upload is deleted after processing or failure, and abandoned request folders are cleared at startup or on later requests once 15 minutes old.

## Try Watermark PDF

1. Start both servers and open **Watermark PDF** from the catalog.
2. Choose one unlocked PDF, up to 25 MB. In the editor, enter a single line of text, choose Helvetica, Times, or Courier, set a font size from 8 to 72 points, and toggle bold, italic, or underline. Choose one position on the 3×3 grid or enable **Mosaic** to repeat the mark across the page. Set rotation, color, opacity, and whether the mark goes over or behind page content. The large source-page preview updates as you change settings and is labeled approximate.
3. Choose **Create watermarked PDF**. Review the rendered result, including other pages using the page selector, before choosing **Download watermarked PDF**.

Watermark PDF uses the existing `pypdf` library locally to add text to every page; the generated PDF is previewed with the existing browser PDF renderer. The original file stays unchanged. Version one supports the PDF built-in Helvetica, Times, and Courier families, with WinAnsi Western European characters. Unsupported scripts and image watermarks remain planned. Long text may be reduced to fit the page or a Mosaic tile. The approximate preview uses browser fonts, so compare it with the actual generated preview and inspect the downloaded copy. A mark behind content may be covered by opaque page backgrounds. A watermark does not securely redact content, and rewriting a signed PDF can invalidate its signature. Password-protected, unreadable, and oversized PDFs are rejected. Temporary uploads are removed after processing or failure; abandoned request folders are cleared at startup or on later requests once 15 minutes old.

## Try JPG to PDF

1. Start both servers and open **JPG to PDF** from the catalog.
2. Choose one or more JPG or PNG images, up to 20 files, 25 MB each, and 100 MB total. Review their thumbnails. Drag to reorder, use the up/down buttons, or remove an image.
3. Choose A4, Letter, or **Fit to image**, then portrait or landscape. Choose **Create PDF** and download the result.

Each selected image becomes one PDF page in the displayed order. A4 and Letter keep images upright inside white margins. Fit to image follows each image's shape at 96 pixels per inch, caps the longest page side at 2000 points, and rotates an image if needed to match the chosen orientation. Camera EXIF orientation is applied first; transparent PNG areas become white. Images are embedded as JPEG at quality 90, so review the downloaded PDF for any quality change. Processing uses the existing Pillow and `pypdf` dependencies locally; originals are unchanged. Invalid, unreadable, oversized, or unusually large images are rejected. Uploads are removed after processing or failure, and abandoned request folders are cleared at startup or on later requests once 15 minutes old.

## Try PDF to Word

1. Start both servers and open **PDF to Word** from the catalog.
2. Choose one PDF, up to 25 MB, with selectable text.
3. Choose **Convert to Word**, then **Download DOCX**.

Each conversion gets a uniquely named download. When comparing versions, open the newest file and restart the Flask server after changing backend code.

The converter includes all pages and produces editable text. It uses PDF text positions and available font information to approximate alignment, bold, italic, underline, font size, line and paragraph spacing, and simple two-column sections as Word tables. A consistent repeated top-right reference is placed in the Word header while body text stays below it. It also tries to include embedded images and page breaks. When every source page has a consistent sequence of centered footer numbers, it places a Word page-number field in the footer so numbers do not flow as body paragraphs. Review the DOCX against the original: complex columns, tables, fonts, image positions, and pagination can still change. Likely scanned or image-only pages are rejected with an OCR-unavailable message instead of a blank Word file. The backend uses `pypdf`, `python-docx`, and Pillow locally. No document is sent to an external service. Uploaded files are removed after processing or failure; abandoned temporary folders are cleaned at startup and on later requests once 15 minutes old.

## Checks

Run `npm run build` in `frontend/` to type-check and build the frontend. Backend tests can be run with `python -m unittest discover -s tests` after installing its requirements.

See [DESIGN.md](DESIGN.md) for the agreed active-release scope, full planned catalog, and delivery rules. No accounts, database, or environment variables are needed.
