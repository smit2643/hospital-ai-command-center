import json
from django import forms
from .models import PatientDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ["patient", "document_type", "file"]


class OCRReviewForm(forms.Form):
    patient_name = forms.CharField(required=False, max_length=255)
    report_date = forms.CharField(required=False, max_length=100)
    hospital_name = forms.CharField(required=False, max_length=255)
    doctor_name = forms.CharField(required=False, max_length=255)
    tests_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="JSON array format: [{\"test_name\":\"Hemoglobin\",\"value\":\"13.2\",\"unit\":\"g/dL\",\"reference_range\":\"12-16\"}]",
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    send_for_signature = forms.BooleanField(required=False)
    signer_email = forms.EmailField(required=False)

    def clean_tests_json(self):
        raw = self.cleaned_data.get("tests_json", "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Invalid JSON: {exc}") from exc

        if not isinstance(parsed, list):
            raise forms.ValidationError("Tests JSON must be an array/list.")

        normalized = []
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"Item {idx + 1} must be an object.")
            normalized.append(
                {
                    "test_name": str(item.get("test_name", "")).strip(),
                    "value": str(item.get("value", "")).strip(),
                    "unit": str(item.get("unit", "")).strip(),
                    "reference_range": str(item.get("reference_range", "")).strip(),
                }
            )
        return normalized

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("send_for_signature") and not cleaned.get("signer_email"):
            self.add_error("signer_email", "Signer email is required when sending for signature.")
        return cleaned
