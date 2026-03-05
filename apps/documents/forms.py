from django import forms
from .models import PatientDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ["patient", "document_type", "file"]
