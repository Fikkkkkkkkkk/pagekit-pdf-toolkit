# PageKit

PageKit is a student-focused PDF toolkit. Merge PDF, Split PDF, Organize pages, Rotate PDF, and PDF to Word are available; the other catalog tools are planned and unavailable. Flask handles these features and provides a health check.

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

## Try PDF to Word

1. Start both servers and open **PDF to Word** from the catalog.
2. Choose one PDF, up to 25 MB, with selectable text.
3. Choose **Convert to Word**, then **Download DOCX**.

Each conversion gets a uniquely named download. When comparing versions, open the newest file and restart the Flask server after changing backend code.

The converter includes all pages and produces editable text. It uses PDF text positions and available font information to approximate alignment, bold, italic, underline, font size, line and paragraph spacing, and simple two-column sections as Word tables. A consistent repeated top-right reference is placed in the Word header while body text stays below it. It also tries to include embedded images and page breaks. When every source page has a consistent sequence of centered footer numbers, it places a Word page-number field in the footer so numbers do not flow as body paragraphs. Review the DOCX against the original: complex columns, tables, fonts, image positions, and pagination can still change. Likely scanned or image-only pages are rejected with an OCR-unavailable message instead of a blank Word file. The backend uses `pypdf`, `python-docx`, and Pillow locally. No document is sent to an external service. Uploaded files are removed after processing or failure; abandoned temporary folders are cleaned at startup and on later requests once 15 minutes old.

## Checks

Run `npm run build` in `frontend/` to type-check and build the frontend. Backend tests can be run with `python -m unittest discover -s tests` after installing its requirements.

See [DESIGN.md](DESIGN.md) for the agreed active-release scope, full planned catalog, and delivery rules. No accounts, database, or environment variables are needed.
