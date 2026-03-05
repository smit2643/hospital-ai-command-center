from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from apps.documents.models import PatientDocument
from .forms import SignatureRequestForm, SignatureSubmitForm
from .models import SignatureRequest
from .services import build_signature_expiry, finalize_signature, sign_request_expired
from .tasks import send_signature_request_email


@login_required
def request_signature(request, document_id: int):
    require_role(request.user, request.user.Role.ADMIN, request.user.Role.DOCTOR)
    document = get_object_or_404(PatientDocument.objects.select_related("patient__user"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    if request.method == "POST":
        form = SignatureRequestForm(request.POST)
        if form.is_valid():
            sign_request = SignatureRequest.objects.create(
                document=document,
                requester=request.user,
                signer_email=form.cleaned_data["signer_email"],
                expires_at=build_signature_expiry(),
            )
            send_signature_request_email.delay(sign_request.id)
            log_audit(
                actor=request.user,
                action="signature.requested",
                object_type="SignatureRequest",
                object_id=sign_request.id,
                metadata={"document_id": document.id},
            )
            messages.success(request, "Signature request sent")
            return redirect("signatures:status", request_id=sign_request.id)
    else:
        form = SignatureRequestForm(initial={"signer_email": document.patient.user.email})

    return render(request, "signatures/request_signature.html", {"form": form, "document": document})


def sign_public(request, token):
    sign_request = get_object_or_404(SignatureRequest.objects.select_related("document__patient__user"), token=token)

    if sign_request_expired(sign_request):
        if sign_request.status not in {SignatureRequest.Status.SIGNED, SignatureRequest.Status.EXPIRED}:
            sign_request.status = SignatureRequest.Status.EXPIRED
            sign_request.save(update_fields=["status"])
        return render(request, "signatures/sign_expired.html", {"sign_request": sign_request})

    if sign_request.status == SignatureRequest.Status.SIGNED:
        return redirect("signatures:status", request_id=sign_request.id)

    if sign_request.status == SignatureRequest.Status.SENT:
        sign_request.status = SignatureRequest.Status.VIEWED
        sign_request.save(update_fields=["status"])

    if request.method == "POST":
        form = SignatureSubmitForm(request.POST)
        if form.is_valid():
            artifact = finalize_signature(
                sign_request=sign_request,
                signature_type=form.cleaned_data["signature_type"],
                typed_signature=form.cleaned_data.get("typed_signature", ""),
                drawn_signature_data=form.cleaned_data.get("drawn_signature_data", ""),
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            log_audit(
                actor=None,
                action="signature.completed",
                object_type="SignatureArtifact",
                object_id=artifact.id,
                metadata={"request_id": sign_request.id},
            )
            messages.success(request, "Document signed successfully")
            return redirect("signatures:status", request_id=sign_request.id)
    else:
        form = SignatureSubmitForm(initial={"signature_type": "DRAWN"})

    return render(request, "signatures/sign_public.html", {"sign_request": sign_request, "form": form})


@login_required
def status(request, request_id: int):
    sign_request = get_object_or_404(
        SignatureRequest.objects.select_related("document__patient__user", "requester"), id=request_id
    )
    if request.user.role == request.user.Role.PATIENT and sign_request.document.patient.user_id != request.user.id:
        require_role(request.user, request.user.Role.ADMIN, request.user.Role.DOCTOR)
    if request.user.role == request.user.Role.DOCTOR and sign_request.requester_id != request.user.id:
        require_role(request.user, request.user.Role.ADMIN)

    return render(request, "signatures/status.html", {"sign_request": sign_request})
