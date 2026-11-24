# PageKit

PageKit is a student-focused PDF toolkit in its foundation stage. The current app is a responsive catalog of planned tools. PDF processing has not been implemented; every tool is visibly unavailable. The Flask service currently provides a health check only.

## Requirements

- Node.js 20.19+ or 22.12+ and npm
- Python 3.10+

## Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). On Windows PowerShell systems that block `npm.ps1`, use `npm.cmd` in the commands above.

## Start the backend

In a second terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app run --debug
```

The health check is at `http://127.0.0.1:5000/api/health` and returns `{"status":"ok"}`. The frontend does not call the backend yet because no tool API exists.

## Checks

Run `npm run build` in `frontend/` to type-check and build the frontend. Backend tests can be run with `python -m unittest discover -s tests` after installing its requirements.

See [DESIGN.md](DESIGN.md) for the locked first-release scope, full planned catalog, and delivery rules. No accounts, database, or environment variables are needed for this foundation.
