# System Architecture

## High-Level Architecture
- Frontend: Django templates + JS polling interactions
- API: Django REST Framework (`/api/v1`)
- Core app: Django 5
- Database: PostgreSQL
- Async: Celery workers + Redis broker
- OCR: Tesseract + OpenCV preprocessing + schema-aware parser
- Signature: ReportLab PDF artifact generation + SHA-256 hashing

## Service Boundaries
1. Accounts
- custom user model, auth/session endpoints

2. Doctors
- onboarding and approval states

3. Patients
- profile and doctor assignment mapping

4. Documents
- upload/versioning/OCR task orchestration
- structured extraction storage:
  - `DocumentExtraction` (core fields)
  - `DocumentExtractedField` (dynamic per document type)
  - `DocumentLabTest` (structured test rows)

5. Signatures
- request creation, tokenized signing, artifact lifecycle

6. Core
- audit logs, health endpoints, shared permission helpers

## Request and Task Flow
1. Upload request persists `PatientDocument` metadata.
2. OCR task runs async, extracts raw text, parses schema fields, runs identity verification.
3. Results persist to relational extraction models.
4. OCR review page auto-polls status and refreshes when OCR completes.
5. Reviewer edits and saves; optional signature request triggers email dispatch.

## Deployment Topology (Docker)
- `web`: Django + gunicorn
- `worker`: Celery
- `db`: Postgres
- `redis`: broker/result backend
