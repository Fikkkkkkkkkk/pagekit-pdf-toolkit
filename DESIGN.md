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
- Images to PDF
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

### First release: locked scope
- Merge PDF
- Split PDF
- Organize pages
- Rotate PDF
- Images to PDF
- Compress PDF
- Add page numbers

The foundation milestone built the app shell, catalog, documentation, and backend health check. Split PDF is now available; the other six first-release tools remain planned and unavailable in this checkout.

### Later milestones
- Document preparation: Crop PDF, Repair PDF, Scan to PDF.
- Conversion: PDF to Word, PDF to PowerPoint, PDF to Excel, PDF to JPG and extract images, PDF to PDF/A, PDF to Markdown, Word to PDF, PowerPoint to PDF, Excel to PDF, HTML/webpage to PDF.
- Editing and review: Edit PDF with text, images, shapes, and annotations; Add a text or image watermark; Create, fill, and edit PDF forms; Protect PDF with a password; Unlock PDF; Sign PDF; Redact PDF; Compare two PDFs.
- Intelligence: OCR for scanned PDFs, AI PDF summarizer, Translate PDF.
- Productivity: Batch processing and reusable workflows that chain multiple tools.

The milestone ordering after the first release is provisional. Moving a tool into or out of the locked first-release scope requires an explicit agreed change recorded below.

## Main user flow

Choose tool → select files → preview/options → process → download. Each implemented tool should explain accepted file types, size limits, and what processing will do before the user starts. The user can remove or replace files before processing and can retry recoverable errors.

## Architecture and technology

- Frontend: React, TypeScript, and Vite in `frontend/`.
- Backend: Python and Flask in `backend/`.
- Split PDF uses `pypdf` to read and create PDFs. It preserves the entered range order and packages one PDF per range using Python's standard `zipfile` module. No external document service is used.
- Frontend and backend live in separate folders. No database or user accounts in the first release.
- `frontend/src/app/` owns application composition and routing when needed. `frontend/src/features/tool-catalog/` owns the catalog. Future PDF tools each get their own folder under `frontend/src/features/` and `backend/app/features/`.
- Each PDF tool owns its UI, API interaction, validation, and processing logic. Put code in `shared/` only when multiple features genuinely need it. Shared modules may hold common UI primitives, styles, and backend file utilities once they are needed.
- `backend/app/` owns Flask setup and health check. `backend/app/shared/` and `tests/` are reserved for later reusable code and meaningful tests.
- Do not silently change these technology or first-release scope decisions. Explain a blocker and propose the smallest adjustment before changing either.

## File privacy and temporary files

- Temporary uploaded files have a 15-minute maximum retention threshold. Split PDF deletes its private request directory immediately after processing or an error. Abandoned directories are cleaned at startup and during later requests once they reach 15 minutes. The ZIP is returned from memory, not stored as a server file.
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

- 2026-11-25: Implemented Split PDF in this checkout, using `pypdf` and standard-library ZIP creation. Set temporary-file retention to 15 minutes. The previously discussed Merge PDF implementation was not present in this checkout; first-release scope and frameworks remain unchanged.
- 2026-11-24: Initial product plan, locked first-release scope, technology choices, and foundation milestone recorded.
