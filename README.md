# Hospital AI Command Center

Production-style hospital workflow platform with role-based access, OCR-assisted document processing, and secure e-signature lifecycle.

## Current implemented flow
1. User login with role: `Admin`, `Doctor`, `Patient`.
2. Doctor registration requires admin approval before protected doctor actions.
3. Admin/approved doctor manages patient records and assignments.
4. Documents are uploaded to a patient vault.
5. OCR is run from the document review screen.
6. Extracted values are shown as editable fields and can be saved.
7. Admin/doctor can generate a patient-level summary across all uploaded documents.
8. Summary renders as a structured intelligence board (not raw OCR dump): doctor-ready summary, abnormal tests, medications, notes, and timelines.
9. System builds normalized year-wise medical test trends across documents (example: `Hemoglobin -> 2021: 11.2, 2022: 10.5, 2023: 9.1`).
10. Summary headline is generated from structured `summary_data` for stable UI readability.
11. From OCR review, user can `Save` or `Save + Send For Signature`.
12. Patient receives signature email with secure tokenized link.
13. Patient signs on the signing page (draw + place signature on document).
14. Signed PDF is generated, stored, and downloadable from patient documents list.

## Role permissions (enforced in UI + backend)
- `Admin`
  - Full access across users, patients, documents, OCR, signature workflows.
- `Doctor`
  - Must be approved.
  - Can access assigned patients and related documents/flows.
- `Patient`
  - Can view/update own profile and upload own documents.
  - Cannot access global patient list, OCR execution/review, or signature-request creation.

## Key features live now
- Custom user model with role-based access control.
- Doctor approval workflow for operational safety.
- Patient profile management (expanded profile fields).
- Patient document vault with add/list/detail actions.
- Patient intelligence summary card (cross-document clinical snapshot).
- Structured patient intelligence board with sections:
  - Executive headline (from `summary_data`)
  - Doctor-ready consolidated summary
  - Abnormal lab indicators
  - Health history timeline (year-wise test trends)
  - Medication mentions
  - Clinical notes highlights
  - Recent document timeline
- OCR extraction workflow with editable mapped fields.
- OCR live status checks (no manual full-page workflow dependency).
- Signature email request flow with styled HTML email template.
- Token-based signature page with signature placement.
- Signed artifact storage and signed-document download action in vault.
- DRF API namespace under `/api/v1/`.

## Technology stack
- Django 5 + Django REST Framework
- PostgreSQL (`psycopg`)
- Celery + Redis
- Tesseract OCR + OpenCV + Pillow
- ReportLab (signed PDF generation)
- Docker Compose

## Run with Docker (recommended)
1. Create env file:
   - `cp .env.example .env`
2. Start services:
   - `docker compose up --build -d`
3. Run migrations:
   - `docker compose exec web python manage.py migrate`
4. Seed demo data:
   - `docker compose exec web python manage.py seed_demo`
5. Open app:
   - `http://localhost:8000`

If `service "web" is not running`, start the stack first with `docker compose up -d`.

## Demo credentials (`seed_demo`)
- Admin: `admin@hospitalai.local` / `DemoPass@123`
- Doctor: `doctor@hospitalai.local` / `DemoPass@123`
- Patient: `patient@hospitalai.local` / `DemoPass@123`

## Email setup (signature delivery)
Configure in `.env`:
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `SITE_BASE_URL` (must be reachable by recipient for sign link)

For local testing without SMTP:
- `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`

## Important routes
- `/login/`
- `/register/doctor/`
- `/register/patient/`
- `/admin/doctor-approvals/`
- `/patients/`
- `/patients/<id>/documents/`
- `/documents/upload/`
- `/documents/<id>/ocr/result/`
- `/signatures/request/<document_id>/`
- `/sign/<token>/`

## Patient Summary Logic (Current)
- Model: `PatientDocumentSummary`
- Trigger: `POST /patients/<id>/documents/summary/generate/`
- Data sources:
  - `PatientDocument`
  - `DocumentExtraction`
  - `DocumentLabTest`
  - `DocumentExtractedField`
- Stored output:
  - `summary_text` (concise executive sentence)
  - `summary_data` (structured JSON for UI cards + doctor-ready narrative + trends)
- Summary provider options:
  - `rule_based` (default, no API usage)
  - `gemini` (free-tier capable when API key is configured)
- Environment toggles:
  - `SUMMARY_LLM_PROVIDER=rule_based|gemini`
  - `SUMMARY_GEMINI_MODEL=gemini-2.0-flash-lite` (single-model override)
  - `SUMMARY_GEMINI_MODELS=gemini-2.0-flash-lite,gemini-2.0-flash,gemini-1.5-flash` (auto fallback order)
  - `GEMINI_API_KEY=...` (required only for Gemini mode)
- Fallback behavior:
  - If Gemini key/dependency/API call fails, system keeps rule-based summary generation.
- Abnormal test logic:
  - Numeric value is parsed from test value text.
  - Reference ranges like `12.0-16.0` / `70-100` / `12 to 16` are parsed safely.
  - Test is marked abnormal only if value is outside `[low, high]`.
- Timeline logic:
  - Report year is taken from report date text when available.
  - Otherwise document creation year is used as fallback.
  - Numeric test values are grouped by test name and sorted year-wise.
- UX note:
  - If old summary content is visible, click `Regenerate Summary` to rebuild using latest logic.

## API highlights
- `/api/v1/auth/login/`
- `/api/v1/auth/me/`
- `/api/v1/documents/`
- `/api/v1/ocr-results/`
- `/api/v1/signature-requests/`

## Documentation
- [Executive Summary](docs/01_EXECUTIVE_SUMMARY.md)
- [Problem and Solution Fit](docs/02_PROBLEM_SOLUTION.md)
- [System Architecture](docs/03_SYSTEM_ARCHITECTURE.md)
- [API Reference](docs/04_API_REFERENCE.md)
- [Security and Compliance](docs/05_SECURITY_AND_COMPLIANCE.md)
- [Demo Runbook](docs/06_DEMO_RUNBOOK.md)
- [Roadmap](docs/07_ROADMAP.md)
- [Judging Criteria Mapping](docs/08_JUDGING_CRITERIA_MAPPING.md)
- [Branching Strategy](docs/09_BRANCHING_STRATEGY.md)
- [OCR Review + Signature Flow](docs/10_OCR_REVIEW_AND_SIGNATURE_FLOW.md)
- [Admin + Patient Profile Enhancements](docs/11_ADMIN_AND_PATIENT_PROFILE_ENHANCEMENTS.md)
