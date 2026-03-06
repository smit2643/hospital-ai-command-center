# API Reference (v1)

Base path: `/api/v1`

## Health
- `GET /health/`

## Session Auth
- `POST /auth/login/`
- `POST /auth/logout/`
- `GET /auth/me/`

## Doctors
- `GET /doctors/pending/` (admin)
- `POST /doctors/{profile_id}/approval/` (admin)

## Documents
- `GET /documents/`
- `POST /documents/`
- `GET /documents/{id}/`
- `PATCH /documents/{id}/`
- `DELETE /documents/{id}/`
- `POST /documents/{id}/trigger_ocr/`

## OCR Results
- `GET /ocr-results/`
- `GET /ocr-results/{id}/`

## Signature Requests
- `GET /signature-requests/`
- `POST /signature-create/`
- `GET /signature-status/{id}/`

## Audit
- `GET /audit-logs/` (admin)

## Web-only OCR Status Endpoint
Used by template polling (not under `/api/v1`):
- `GET /documents/{id}/ocr/status/`
