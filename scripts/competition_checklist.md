# Competition Demo Checklist

1. Stack up (`docker compose up --build -d`)
2. Seed users (`docker compose exec web python manage.py seed_demo`)
3. Admin approves pending doctors (if any)
4. Doctor uploads lab report and triggers OCR
5. Show extracted structured fields + confidence
6. Send signature request to patient email
7. Patient signs via token link
8. Show signed PDF + hash + audit entries
9. Hit health endpoints (`/health`, `/api/v1/health`)
10. Close with architecture and scalability roadmap
