# Hospital AI Command Center

A competition-ready hospital management platform built with Django, PostgreSQL, OCR, asynchronous processing, and secure e-sign workflows.

## Why this project stands out
- End-to-end healthcare document lifecycle: upload -> OCR -> extract -> review -> sign -> archive.
- Multi-role workflow with strict access controls: `Admin`, `Doctor`, `Patient`.
- Signature trust layer with SHA-256 integrity hash and full audit trail.
- Async architecture (Celery + Redis) built for real workloads.
- Deployment-ready packaging with Docker, migrations, seed data, and API layer.

## Documentation Pack
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

## Git Workflow
- Default branch: `main`
- Integration branch: `develop`
- Feature branches by capability (auth, doctor, patient, OCR, signature, UI, API)
- Supporting branches for `devops`, `docs`, `release`, and `hotfix`
- CI workflow added at `.github/workflows/ci.yml`

## Core capabilities
- Doctor and patient registration
- Admin doctor approval queue
- Patient-doctor assignment
- Document versioning and metadata tracking
- OCR extraction for lab-report style image documents
- Signature request by email via secure token links
- OCR review console with editable extracted fields before final save
- Optional send-for-signature from OCR review screen
- Public sign endpoint with expiration guard
- Signed PDF artifact storage and hash persistence
- Audit logging across sensitive operations
- REST API namespace: `/api/v1/`

## Tech stack
- Django 5, DRF
- PostgreSQL (`psycopg`)
- Celery + Redis
- Tesseract OCR + OpenCV + Pillow
- ReportLab for signed PDFs
- Docker + docker-compose

## Quickstart (Docker, recommended)
1. Copy env:
   - `cp .env.example .env`
2. Start stack:
   - `docker compose up --build -d`
3. Seed demo users:
   - `docker compose exec web python manage.py seed_demo`
4. Open app:
   - `http://localhost:8000`

## Quickstart (local)
1. Create venv and install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Install system dependencies:
   - Ubuntu/Debian: `sudo apt install tesseract-ocr`
3. Configure env:
   - `cp .env.example .env`
4. Run DB migrations:
   - `python manage.py migrate`
5. Create superuser or seed demo:
   - `python manage.py createsuperuser`
   - or `python manage.py seed_demo`
6. Run app and worker:
   - `python manage.py runserver`
   - `celery -A hospital_ai worker -l info`

## Demo credentials (after `seed_demo`)
- Admin: `admin@hospitalai.local` / `DemoPass@123`
- Doctor: `doctor@hospitalai.local` / `DemoPass@123`
- Patient: `patient@hospitalai.local` / `DemoPass@123`

## Important routes
- `/register/doctor/`
- `/register/patient/`
- `/admin/doctor-approvals/`
- `/patients/`
- `/documents/upload/`
- `/patients/<id>/documents/`
- `/documents/<id>/ocr/trigger/`
- `/signatures/request/<document_id>/`
- `/sign/<token>/`
- `/health/`

## API routes
- `/api/v1/health/`
- `/api/v1/auth/login/`
- `/api/v1/auth/me/`
- `/api/v1/doctors/pending/`
- `/api/v1/documents/`
- `/api/v1/ocr-results/`
- `/api/v1/signature-requests/`

## Environment variables
Use `.env.example` as baseline. Most important:
- `DATABASE_URL`
- `SITE_BASE_URL`
- `EMAIL_*`
- `REDIS_URL`, `CELERY_BROKER_URL`
- `SIGN_LINK_TTL_HOURS`

## Notes
- OCR in v1 is tuned for image-based lab reports (`png/jpg/jpeg/tiff/bmp`).
- Sample OCR document: `sample_data/hospital_dummy_lab_report.png`
- You can regenerate sample: `docker compose exec web python scripts/generate_dummy_lab_report.py`
- OCR provider defaults to open-source Tesseract. Optional Gemini integration is supported via env variables.
- For laptop-only demo without worker, set `CELERY_TASK_ALWAYS_EAGER=True`.
- For local testing without SMTP, set:
  - `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`
