# PageKit

PageKit is a student-focused PDF toolkit. Merge PDF is available; the other catalog tools are visibly planned and unavailable. The Flask service handles Merge PDF and provides a health check.

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

Merge PDF accepts 2–20 PDFs, up to 25 MB per file and 100 MB total. It rejects empty, unreadable, and password-protected PDFs. The backend uses `pypdf`. Uploaded files are kept in a private request folder and removed after processing or an error; abandoned folders are cleaned at startup and on later requests after 15 minutes. The result is returned directly and is not stored on the server.

## Checks

Run `npm run build` in `frontend/` to type-check and build the frontend. Backend tests can be run with `python -m unittest discover -s tests` after installing its requirements.

See [DESIGN.md](DESIGN.md) for the locked first-release scope, full planned catalog, and delivery rules. No accounts, database, or environment variables are needed.
