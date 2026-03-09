from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from apps.patients.models import PatientProfile
from apps.signatures.models import SignatureRequest
from apps.signatures.services import build_signature_expiry
from apps.signatures.tasks import dispatch_signature_request_email

from .forms import DocumentManageForm, DocumentUploadForm, OCRDynamicFieldForm, OCRLabTestForm, OCRReviewForm
from .models import DocumentExtractedField, DocumentLabTest, PatientDocument
from .schema import get_schema_for_document_type
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
                PatientDocument.objects.filter(patient=patient, document_type=form.cleaned_data["document_type"])
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
                assignments__doctor__user=request.user,
                assignments__is_active=True,
            ).distinct()
    return render(request, "documents/upload.html", {"form": form})


@login_required
def patient_documents(request, patient_id: int):
    patient = get_object_or_404(PatientProfile.objects.select_related("user"), id=patient_id)
    if not doctor_can_access_patient(request.user, patient):
        require_role(request.user, request.user.Role.ADMIN)

    docs = patient.documents.select_related("uploaded_by").prefetch_related("signature_requests__artifact").all()
    return render(
        request,
        "documents/patient_documents.html",
        {"patient": patient, "documents": docs, "can_manage_docs": request.user.role == request.user.Role.ADMIN},
    )


@login_required
def trigger_ocr(request, document_id: int):
    document = get_object_or_404(PatientDocument.objects.select_related("patient"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    process_document_ocr.delay(document.id)
    messages.success(request, "OCR started")
    return redirect("documents:ocr_result", document_id=document.id)


@login_required
def edit_document(request, document_id: int):
    require_role(request.user, request.user.Role.ADMIN)
    document = get_object_or_404(PatientDocument.objects.select_related("patient"), id=document_id)

    if request.method == "POST":
        form = DocumentManageForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, "Document updated.")
            return redirect("documents:patient_docs", patient_id=document.patient_id)
    else:
        form = DocumentManageForm(instance=document)

    return render(request, "documents/edit_document.html", {"document": document, "form": form})


@login_required
def delete_document(request, document_id: int):
    require_role(request.user, request.user.Role.ADMIN)
    document = get_object_or_404(PatientDocument.objects.select_related("patient"), id=document_id)
    if request.method == "POST":
        patient_id = document.patient_id
        document.delete()
        messages.success(request, "Document deleted.")
        return redirect("documents:patient_docs", patient_id=patient_id)
    return render(request, "documents/delete_document.html", {"document": document})


@login_required
def ocr_status(request, document_id: int):
    document = get_object_or_404(PatientDocument.objects.select_related("patient"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    extraction = getattr(document, "extraction", None)
    latest_result = document.ocr_results.first()
    payload = {
        "document_id": document.id,
        "ocr_status": document.ocr_status,
        "confidence": document.extracted_confidence,
        "signature_status": document.signature_status,
        "latest_error": latest_result.parsed_fields.get("error", "") if latest_result else "",
        "raw_text": latest_result.raw_text if latest_result else "",
        "extraction": {
            "identity_verified": extraction.identity_verified if extraction else False,
            "identity_message": extraction.identity_message if extraction else "",
            "report_date_text": extraction.report_date_text if extraction else "",
            "hospital_name": extraction.hospital_name if extraction else "",
            "doctor_name": extraction.doctor_name if extraction else "",
            "notes": extraction.notes if extraction else "",
            "extra_fields": [
                {
                    "field_key": row.field_key,
                    "value_type": row.value_type,
                    "value_short": row.value_short,
                    "value_text": row.value_text,
                }
                for row in extraction.extra_fields.all()
            ] if extraction else [],
            "tests": [
                {
                    "test_name": row.test_name,
                    "value": row.value,
                    "unit": row.unit,
                    "reference_range": row.reference_range,
                }
                for row in extraction.tests.all()
            ] if extraction else [],
        },
    }
    return JsonResponse(payload)


def _dynamic_fields_initial(document: PatientDocument, extraction) -> list[dict]:
    if extraction and extraction.extra_fields.exists():
        return [
            {
                "field_key": row.field_key,
                "label": row.label,
                "value_type": row.value_type,
                "value_short": row.value_short,
                "value_text": row.value_text,
            }
            for row in extraction.extra_fields.all()
        ]

    initial = []
    for spec in get_schema_for_document_type(document.document_type):
        initial.append(
            {
                "field_key": spec["key"],
                "label": spec["label"],
                "value_type": spec["value_type"],
                "value_short": "",
                "value_text": "",
            }
        )
    return initial


def _decorate_dynamic_forms(dynamic_formset) -> None:
    for form in dynamic_formset.forms:
        form.display_label = form.initial.get("label") or form.data.get(form.add_prefix("label"), "Field")
        form.display_type = form.initial.get("value_type") or form.data.get(form.add_prefix("value_type"), "SHORT")
        key = (form.initial.get("field_key") or form.data.get(form.add_prefix("field_key"), "")).strip().lower()
        if form.is_bound:
            value_short = (form.data.get(form.add_prefix("value_short")) or "").strip()
            value_text = (form.data.get(form.add_prefix("value_text")) or "").strip()
        else:
            value_short = (form.initial.get("value_short") or "").strip()
            value_text = (form.initial.get("value_text") or "").strip()
        has_data = bool(value_short or value_text)
        always_show = ("date" in key) or ("doctor" in key)
        form.visible_row = has_data or always_show


@login_required
def ocr_result(request, document_id: int):
    document = get_object_or_404(PatientDocument.objects.select_related("patient__user"), id=document_id)
    if not doctor_can_access_patient(request.user, document.patient):
        require_role(request.user, request.user.Role.ADMIN)

    latest_result = document.ocr_results.first()
    latest_signature_request = document.signature_requests.order_by("-created_at").first()

    extraction = getattr(document, "extraction", None)
    # Always sync extraction with the latest OCR payload when OCR result is newer.
    # This prevents stale/blank fields in UI after OCR re-runs.
    if latest_result and (extraction is None or latest_result.created_at > extraction.updated_at):
        extraction = upsert_extraction_from_parsed(
            document,
            latest_result.parsed_fields,
            raw_text=latest_result.raw_text or "",
            identity_verified=getattr(extraction, "identity_verified", False),
            identity_message=getattr(extraction, "identity_message", ""),
        )
    elif extraction is None:
        extraction = upsert_extraction_from_parsed(document, {}, raw_text="")

    lab_extra = 1 if document.document_type == PatientDocument.DocumentType.LAB_REPORT else 0
    LabTestFormSet = formset_factory(OCRLabTestForm, extra=lab_extra)
    DynamicFieldFormSet = formset_factory(OCRDynamicFieldForm, extra=0)

    initial_test_rows = []
    if extraction and document.document_type == PatientDocument.DocumentType.LAB_REPORT:
        initial_test_rows = [
            {
                "test_name": row.test_name,
                "value": row.value,
                "unit": row.unit,
                "reference_range": row.reference_range,
            }
            for row in extraction.tests.all()
        ]
    if not initial_test_rows and document.document_type == PatientDocument.DocumentType.LAB_REPORT:
        initial_test_rows = [{"test_name": "", "value": "", "unit": "", "reference_range": ""}]

    if request.method == "POST":
        form = OCRReviewForm(request.POST, instance=extraction)
        formset = LabTestFormSet(request.POST, prefix="tests")
        dynamic_formset = DynamicFieldFormSet(request.POST, prefix="dynamic")
        _decorate_dynamic_forms(dynamic_formset)

        all_valid = form.is_valid() and dynamic_formset.is_valid()
        if document.document_type == PatientDocument.DocumentType.LAB_REPORT:
            all_valid = all_valid and formset.is_valid()

        if all_valid:
            extraction = form.save(commit=False)
            extraction.patient_name = document.patient.user.full_name
            extraction.patient_email = document.patient.user.email
            extraction.patient_phone = document.patient.user.phone
            extraction.patient_dob_text = document.patient.dob.isoformat() if document.patient.dob else ""
            extraction.save()

            extraction.extra_fields.all().delete()
            dynamic_rows = []
            for idx, dynamic_form in enumerate(dynamic_formset):
                key = dynamic_form.cleaned_data.get("field_key", "").strip()
                label = dynamic_form.cleaned_data.get("label", "").strip()
                value_type = dynamic_form.cleaned_data.get("value_type", "SHORT")
                value_short = dynamic_form.cleaned_data.get("value_short", "").strip()
                value_text = dynamic_form.cleaned_data.get("value_text", "").strip()
                if value_type == DocumentExtractedField.ValueType.TEXT:
                    dynamic_rows.append(
                        DocumentExtractedField(
                            extraction=extraction,
                            field_key=key,
                            label=label,
                            value_type=value_type,
                            value_short="",
                            value_text=value_text,
                            order_index=idx,
                        )
                    )
                else:
                    dynamic_rows.append(
                        DocumentExtractedField(
                            extraction=extraction,
                            field_key=key,
                            label=label,
                            value_type=value_type,
                            value_short=value_short,
                            value_text="",
                            order_index=idx,
                        )
                    )
            if dynamic_rows:
                DocumentExtractedField.objects.bulk_create(dynamic_rows)

            if document.document_type == PatientDocument.DocumentType.LAB_REPORT:
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
            else:
                extraction.tests.all().delete()

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
                metadata={"patient_id": document.patient_id, "document_type": document.document_type},
            )

            should_send_signature = form.cleaned_data.get("send_for_signature") or request.POST.get("action") == "save_send"
            if should_send_signature:
                already_open = document.signature_requests.filter(status__in=["SENT", "VIEWED"]).exists()
                already_signed = document.signature_requests.filter(status="SIGNED").exists()
                if not already_open and not already_signed:
                    signer_email = form.cleaned_data["signer_email"] or document.patient.user.email
                    sign_request = SignatureRequest.objects.create(
                        document=document,
                        requester=request.user,
                        signer_email=signer_email,
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
                elif already_open:
                    existing_request = (
                        document.signature_requests.filter(status__in=["SENT", "VIEWED"]).order_by("-created_at").first()
                    )
                    sent, error = dispatch_signature_request_email(existing_request.id)
                    if sent:
                        messages.success(request, "OCR details saved and signature email was re-sent.")
                    else:
                        messages.warning(request, f"OCR details saved. Re-send email failed: {error}")
                else:
                    messages.info(request, "OCR details saved. Signature already pending or completed.")
            else:
                messages.success(request, "OCR details reviewed and saved successfully.")

            return redirect("documents:ocr_result", document_id=document.id)
    else:
        form = OCRReviewForm(instance=extraction, initial={"signer_email": document.patient.user.email})
        formset = LabTestFormSet(initial=initial_test_rows, prefix="tests")
        dynamic_formset = DynamicFieldFormSet(initial=_dynamic_fields_initial(document, extraction), prefix="dynamic")
        _decorate_dynamic_forms(dynamic_formset)

    context = {
        "document": document,
        "latest_result": latest_result,
        "latest_signature_request": latest_signature_request,
        "form": form,
        "formset": formset,
        "dynamic_formset": dynamic_formset,
        "extraction": extraction,
        "is_lab_report": document.document_type == PatientDocument.DocumentType.LAB_REPORT,
        "latest_error": (latest_result.parsed_fields.get("error", "") if latest_result else ""),
        "ocr_status_url": f"/documents/{document.id}/ocr/status/",
        "ocr_is_pending": document.ocr_status in {PatientDocument.OCRStatus.PENDING, PatientDocument.OCRStatus.PROCESSING},
    }
    return render(request, "documents/ocr_result.html", context)
