from django.contrib import messages
from django.forms import formset_factory
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from apps.patients.models import PatientProfile
from apps.signatures.models import SignatureRequest
from apps.signatures.services import build_signature_expiry
from apps.signatures.tasks import dispatch_signature_request_email
from .forms import DocumentUploadForm, OCRLabTestForm, OCRReviewForm
from .models import DocumentLabTest, PatientDocument
from .services import mark_extraction_reviewed, upsert_extraction_from_parsed
from .tasks import process_document_ocr


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

    extraction = getattr(document, "extraction", None)
    if extraction is None:
        parsed_source = latest_result.parsed_fields if latest_result else {}
        if parsed_source:
            extraction = upsert_extraction_from_parsed(document, parsed_source)

    LabTestFormSet = formset_factory(OCRLabTestForm, extra=1)
    initial_test_rows = []
    if extraction:
        initial_test_rows = [
            {
                "test_name": row.test_name,
                "value": row.value,
                "unit": row.unit,
                "reference_range": row.reference_range,
            }
            for row in extraction.tests.all()
        ]
    elif latest_result and isinstance(latest_result.parsed_fields.get("tests"), list):
        initial_test_rows = latest_result.parsed_fields.get("tests", [])

    if not initial_test_rows:
        initial_test_rows = [{"test_name": "", "value": "", "unit": "", "reference_range": ""}]

    if request.method == "POST":
        if extraction is None:
            extraction = upsert_extraction_from_parsed(document, {})
        form = OCRReviewForm(request.POST, instance=extraction)
        formset = LabTestFormSet(request.POST, prefix="tests")
        if form.is_valid() and formset.is_valid():
            extraction = form.save()
            extraction.tests.all().delete()
            rows = []
            for idx, test_form in enumerate(formset):
                if test_form.cleaned_data.get("DELETE"):
                    continue
                if not test_form.row_has_data():
                    continue
                rows.append(
                    DocumentLabTest(
                        extraction=extraction,
                        test_name=test_form.cleaned_data["test_name"].strip(),
                        value=test_form.cleaned_data["value"].strip(),
                        unit=test_form.cleaned_data["unit"].strip(),
                        reference_range=test_form.cleaned_data["reference_range"].strip(),
                        order_index=idx,
                    )
                )
            if rows:
                DocumentLabTest.objects.bulk_create(rows)
            mark_extraction_reviewed(extraction, request.user)

            document.extracted_summary = {}
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
                    sent, error = dispatch_signature_request_email(sign_request.id)
                    log_audit(
                        actor=request.user,
                        action="signature.requested_from_ocr_review",
                        object_type="SignatureRequest",
                        object_id=sign_request.id,
                        metadata={"document_id": document.id},
                    )
                    if sent:
                        messages.success(request, "OCR details saved and signature request sent to patient email.")
                    else:
                        messages.warning(request, f"OCR details saved. Email failed: {error}")
                else:
                    messages.info(request, "OCR details saved. Signature already pending or completed.")
            else:
                messages.success(request, "OCR details reviewed and saved successfully.")

            return redirect("documents:ocr_result", document_id=document.id)
    else:
        if extraction is None:
            parsed = latest_result.parsed_fields if latest_result else {}
            extraction = upsert_extraction_from_parsed(document, parsed)
        form = OCRReviewForm(instance=extraction, initial={"signer_email": document.patient.user.email})
        formset = LabTestFormSet(initial=initial_test_rows, prefix="tests")

    context = {
        "document": document,
        "latest_result": latest_result,
        "latest_signature_request": latest_signature_request,
        "form": form,
        "formset": formset,
        "extraction": extraction,
    }
    return render(request, "documents/ocr_result.html", context)
