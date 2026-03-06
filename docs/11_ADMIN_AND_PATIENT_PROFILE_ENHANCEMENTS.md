# Admin and Patient Profile Enhancements

## Added in This Update

### 1. Complete Patient Profile Model
Patient profile now supports:
- Demographics: DOB, gender, blood group, marital status, occupation
- Address: line1, line2, city, state, postal code, country
- Clinical context: allergies, chronic conditions, current medications
- Insurance: provider and policy number
- Emergency details: name, relation, contact number

### 2. Admin Patient Management
- Admin can edit full patient profile from patient detail page.
- Patient detail page now shows complete profile table.
- Patient list includes email, phone, blood group for quick triage.

### 3. Assignment Management
- Admin can assign doctor.
- Admin can edit assignment (doctor + active/inactive).
- Admin can remove assignment with confirmation page.

### 4. Document Management by Admin
From patient document vault, admin can now:
- Edit document metadata (`document_type`, `status`)
- Delete document with confirmation page

## New/Updated Routes
- `GET/POST /patients/{id}/` (admin edit enabled)
- `GET/POST /patients/assignments/{id}/edit/`
- `GET/POST /patients/assignments/{id}/delete/`
- `GET/POST /documents/{id}/edit/`
- `GET/POST /documents/{id}/delete/`

## Migration
- `patients.0002_patientprofile_extended_fields`
