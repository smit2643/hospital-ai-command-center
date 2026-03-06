from django import forms

from .models import DocumentExtraction, PatientDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ["patient", "document_type", "file"]


class OCRReviewForm(forms.ModelForm):
    send_for_signature = forms.BooleanField(required=False)
    signer_email = forms.EmailField(required=False)

    class Meta:
        model = DocumentExtraction
        fields = [
            "patient_name",
            "patient_email",
            "patient_phone",
            "patient_dob_text",
            "report_date_text",
            "hospital_name",
            "doctor_name",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "patient_name": forms.TextInput(attrs={"readonly": "readonly"}),
            "patient_email": forms.EmailInput(attrs={"readonly": "readonly"}),
            "patient_phone": forms.TextInput(attrs={"readonly": "readonly"}),
            "patient_dob_text": forms.TextInput(attrs={"readonly": "readonly"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("send_for_signature") and not cleaned.get("signer_email"):
            self.add_error("signer_email", "Signer email is required when sending for signature.")
        return cleaned


class OCRLabTestForm(forms.Form):
    test_name = forms.CharField(required=False, max_length=255)
    value = forms.CharField(required=False, max_length=64)
    unit = forms.CharField(required=False, max_length=32)
    reference_range = forms.CharField(required=False, max_length=128)
    DELETE = forms.BooleanField(required=False)

    def row_has_data(self) -> bool:
        cleaned = getattr(self, "cleaned_data", {})
        return any(cleaned.get(field) for field in ("test_name", "value", "unit", "reference_range"))


class OCRDynamicFieldForm(forms.Form):
    field_key = forms.CharField(widget=forms.HiddenInput())
    label = forms.CharField(widget=forms.HiddenInput())
    value_type = forms.CharField(widget=forms.HiddenInput())
    value_short = forms.CharField(required=False, max_length=255)
    value_text = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
