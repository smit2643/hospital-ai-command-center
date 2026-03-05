from django import forms
from .models import SignatureRequest


class SignatureRequestForm(forms.ModelForm):
    class Meta:
        model = SignatureRequest
        fields = ["signer_email"]


class SignatureSubmitForm(forms.Form):
    signature_type = forms.ChoiceField(choices=(("DRAWN", "Drawn"), ("TYPED", "Typed")))
    typed_signature = forms.CharField(required=False, max_length=120)
    drawn_signature_data = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        signature_type = cleaned.get("signature_type")
        if signature_type == "DRAWN" and not cleaned.get("drawn_signature_data"):
            self.add_error("drawn_signature_data", "Please draw your signature")
        if signature_type == "TYPED" and not cleaned.get("typed_signature"):
            self.add_error("typed_signature", "Please type your signature")
        return cleaned
