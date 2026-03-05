# System Architecture

## High-Level Architecture
- Frontend: Django templates + JS interactions
- API: Django REST Framework (`/api/v1`)
- Core app: Django 5
- Database: PostgreSQL
- Async: Celery workers + Redis broker
- OCR: Tesseract + OpenCV preprocessing + parser
- Signature: ReportLab PDF artifact generation + SHA-256 hashing

## Service Boundaries
1. Accounts
- custom user model, auth/session endpoints

2. Doctors
- onboarding and approval states

3. Patients
- profile and doctor assignment mapping

4. Documents
- upload/versioning/OCR trigger/result persistence

5. Signatures
- request creation, tokenized signing, artifact lifecycle

6. Core
- audit logs, health endpoints, shared permission helpers

## Request and Task Flow
1. Sync web request handles user action
2. DB persists initial state
3. Async worker processes OCR/email tasks
4. State transition updates status fields
5. UI/API reflects progression and results

## Deployment Topology (Docker)
- `web`: Django + gunicorn
- `worker`: Celery
- `db`: Postgres
- `redis`: broker/result backend
