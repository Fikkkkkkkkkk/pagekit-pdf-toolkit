# PageKit

PageKit is a student-focused PDF toolkit. Split PDF is available; the other catalog tools are planned and unavailable in this checkout. Flask handles Split PDF and provides a health check.

## Requirements

- Node.js 20.19+ or 22.12+ and npm
- Python 3.10+

## Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). On Windows PowerShell systems that block `npm.ps1`, use `npm.cmd` in the commands above. Vite proxies `/api` requests to Flask at `127.0.0.1:5000`.

## Start the backend

In a second terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app run --debug
```

The health check is at `http://127.0.0.1:5000/api/health` and returns `{"status":"ok"}`.

## Try Split PDF

1. Start both servers and open the frontend URL.
2. Open **Split PDF** from its catalog card and choose one PDF, up to 25 MB.
3. Enter comma-separated page ranges, such as `1-3, 5, 8-10`.
4. Choose **Split PDF**, then **Download ZIP**. Each range becomes a separate PDF, in the entered order.

Ranges must use positive page numbers, stay within the document, and not overlap. Password-protected or unreadable PDFs are rejected. The original PDF is unchanged. The backend uses `pypdf` and Python's `zipfile`. Uploads are kept in a private request folder and removed after processing or an error; abandoned folders are cleaned at startup and on later requests once 15 minutes old. ZIP output is returned directly and not stored on the server.

## Checks

Run `npm run build` in `frontend/` to type-check and build the frontend. Backend tests can be run with `python -m unittest discover -s tests` after installing its requirements.

See [DESIGN.md](DESIGN.md) for the locked first-release scope, full planned catalog, and delivery rules. No accounts, database, or environment variables are needed.
