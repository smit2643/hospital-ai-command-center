# Demo Runbook

## Objective
Deliver a crisp, high-confidence demo in 6-8 minutes.

## Setup
1. `cp .env.example .env`
2. `docker compose up --build -d`
3. `docker compose exec web python manage.py migrate`
4. `docker compose exec web python manage.py seed_demo`
5. Open `http://localhost:8000`

## Script
1. Admin login
- show doctor approval queue
- approve a pending doctor

2. Doctor login
- open assigned patient documents
- upload lab report image
- trigger OCR
- show live OCR completion without manual refresh
- show doctor/hospital/patient/date + dynamic fields auto-filled
- show `Full OCR Text` fallback retained for unmatched text

3. Signature flow
- enable `send for signature` on OCR review page
- submit and open signature status
- open sign link as patient
- draw/type/upload signature
- show signed PDF + SHA-256 hash

4. Governance close
- open audit logs
- explain traceability and extensibility

## Demo Credentials
- Admin: `admin@hospitalai.local / DemoPass@123`
- Doctor: `doctor@hospitalai.local / DemoPass@123`
- Patient: `patient@hospitalai.local / DemoPass@123`
