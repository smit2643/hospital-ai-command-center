# API Reference (v1)

Base path: `/api/v1`

## Health
- `GET /health/`
  - returns service status

## Session Auth
- `POST /auth/login/`
  - body: `email`, `password`
- `POST /auth/logout/`
- `GET /auth/me/`

## Doctors
- `GET /doctors/pending/` (admin)
- `POST /doctors/{profile_id}/approval/` (admin)
  - body: `decision` = `APPROVED` or `REJECTED`

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
