from django import forms


class DoctorApprovalForm(forms.Form):
    decision = forms.ChoiceField(choices=(("APPROVED", "Approve"), ("REJECTED", "Reject")))
