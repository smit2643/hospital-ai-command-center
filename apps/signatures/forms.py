from django import forms
from .models import SignatureRequest


class SignatureRequestForm(forms.ModelForm):
    class Meta:
        model = SignatureRequest
        fields = ["signer_email"]


class SignatureSubmitForm(forms.Form):
    signature_type = forms.ChoiceField(choices=(("DRAWN", "Drawn"), ("TYPED", "Typed"), ("UPLOADED", "Upload Image")))
    typed_signature = forms.CharField(required=False, max_length=120)
    drawn_signature_data = forms.CharField(required=False)
    signature_image_file = forms.ImageField(required=False)

    def clean(self):
        cleaned = super().clean()
        signature_type = cleaned.get("signature_type")
        if signature_type == "DRAWN" and not cleaned.get("drawn_signature_data"):
            self.add_error("drawn_signature_data", "Please draw your signature")
        if signature_type == "TYPED" and not cleaned.get("typed_signature"):
            self.add_error("typed_signature", "Please type your signature")
        if signature_type == "UPLOADED" and not cleaned.get("signature_image_file"):
            self.add_error("signature_image_file", "Please upload your signature image")
        return cleaned
