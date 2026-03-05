from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from apps.patients.models import PatientProfile
from apps.signatures.models import SignatureRequest
from apps.signatures.services import build_signature_expiry
from apps.signatures.tasks import send_signature_request_email
from .forms import DocumentUploadForm, OCRReviewForm
from .models import PatientDocument
from .tasks import process_document_ocr
import json


@login_required
def upload(request):
    require_role(request.user, request.user.Role.ADMIN, request.user.Role.DOCTOR, request.user.Role.PATIENT)
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.cleaned_data["patient"]
            if not doctor_can_access_patient(request.user, patient):
                messages.error(request, "You cannot upload for this patient")
                return redirect("documents:upload")

            previous = (
                PatientDocument.objects.filter(patient=patient, document_type=form.cleaned_data["document_type"])\
                .order_by("-version")
                .first()
            )
            document = form.save(commit=False)
            document.uploaded_by = request.user
            if previous:
                document.version = previous.version + 1
                document.previous_version = previous
            document.save()
            log_audit(
                actor=request.user,
                action="document.uploaded",
                object_type="PatientDocument",
                object_id=document.id,
                metadata={"patient_id": patient.id},
            )
            messages.success(request, "Document uploaded")
            return redirect("documents:patient_docs", patient_id=patient.id)
    else:
        form = DocumentUploadForm()
        if request.user.role == request.user.Role.PATIENT:
            form.fields["patient"].queryset = PatientProfile.objects.filter(user=request.user)
        elif request.user.role == request.user.Role.DOCTOR:
            form.fields["patient"].queryset = PatientProfile.objects.filter(
                assignments__doctor__user=request.user, assignments__is_active=True
            ).distinct()
    return render(request, "documents/upload.html", {"form": form})


@login_required
def patient_documents(request, patient_id: int):
    patient = get_object_or_404(PatientProfile.objects.select_related("user"), id=patient_id)
    if not doctor_can_access_patient(request.user, patient):
        require_role(request.user, request.user.Role.ADMIN)

    docs = patient.documents.select_related("uploaded_by").prefetch_related("signature_requests").all()
    return render(request, "documents/patient_documents.html", {"patient": patient, "documents": docs})


@login_required
def trigger_ocr(request, document_id: int):
    document = get_object_or_404(PatientDocument.objects.select_related("patient"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    process_document_ocr.delay(document.id)
    messages.success(request, "OCR started")
    return redirect("documents:ocr_result", document_id=document.id)


@login_required
def ocr_result(request, document_id: int):
    document = get_object_or_404(PatientDocument.objects.select_related("patient__user"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    latest_result = document.ocr_results.first()
    latest_signature_request = document.signature_requests.order_by("-created_at").first()

    source = latest_result.parsed_fields if latest_result else document.extracted_summary or {}
    initial_tests = source.get("tests", [])
    initial = {
        "patient_name": source.get("patient_name", ""),
        "report_date": source.get("report_date", ""),
        "hospital_name": source.get("hospital_name", ""),
        "doctor_name": source.get("doctor_name", ""),
        "tests_json": json.dumps(initial_tests, indent=2) if initial_tests else "[]",
        "notes": source.get("notes", ""),
        "signer_email": document.patient.user.email,
    }

    if request.method == "POST":
        form = OCRReviewForm(request.POST)
        if form.is_valid():
            reviewed_payload = {
                "patient_name": form.cleaned_data["patient_name"],
                "report_date": form.cleaned_data["report_date"],
                "hospital_name": form.cleaned_data["hospital_name"],
                "doctor_name": form.cleaned_data["doctor_name"],
                "tests": form.cleaned_data["tests_json"],
                "notes": form.cleaned_data["notes"],
                "ocr_reviewed": True,
                "reviewed_by_user_id": request.user.id,
            }

            document.extracted_summary = reviewed_payload
            if document.ocr_status != PatientDocument.OCRStatus.DONE:
                document.ocr_status = PatientDocument.OCRStatus.DONE
            document.save(update_fields=["extracted_summary", "ocr_status", "updated_at"])

            log_audit(
                actor=request.user,
                action="document.ocr_review_saved",
                object_type="PatientDocument",
                object_id=document.id,
                metadata={"patient_id": document.patient_id},
            )

            if form.cleaned_data.get("send_for_signature"):
                already_open = document.signature_requests.filter(status__in=["SENT", "VIEWED"]).exists()
                already_signed = document.signature_requests.filter(status="SIGNED").exists()
                if not already_open and not already_signed:
                    sign_request = SignatureRequest.objects.create(
                        document=document,
                        requester=request.user,
                        signer_email=form.cleaned_data["signer_email"],
                        expires_at=build_signature_expiry(),
                    )
                    send_signature_request_email.delay(sign_request.id)
                    log_audit(
                        actor=request.user,
                        action="signature.requested_from_ocr_review",
                        object_type="SignatureRequest",
                        object_id=sign_request.id,
                        metadata={"document_id": document.id},
                    )
                    messages.success(request, "OCR details saved and signature request sent to patient email.")
                else:
                    messages.info(request, "OCR details saved. Signature already pending or completed.")
            else:
                messages.success(request, "OCR details reviewed and saved successfully.")

            return redirect("documents:ocr_result", document_id=document.id)
    else:
        form = OCRReviewForm(initial=initial)

    context = {
        "document": document,
        "latest_result": latest_result,
        "latest_signature_request": latest_signature_request,
        "form": form,
    }
    return render(request, "documents/ocr_result.html", context)
