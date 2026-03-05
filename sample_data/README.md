# Sample OCR Documents

This folder contains demo-friendly hospital-like sample files for OCR testing.

- `hospital_dummy_lab_report.png`: upload this file from UI at `/documents/upload/`.

If the file is missing, regenerate it with:

```bash
docker compose exec web python scripts/generate_dummy_lab_report.py
```
