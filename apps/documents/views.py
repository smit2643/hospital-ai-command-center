from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from apps.patients.models import PatientProfile
from .forms import DocumentUploadForm
from .models import PatientDocument
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

    docs = patient.documents.select_related("uploaded_by").all()
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
    return render(request, "documents/ocr_result.html", {"document": document, "latest_result": latest_result})
