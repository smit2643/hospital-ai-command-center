import base64
import hashlib
import io
import os
from datetime import timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
from apps.documents.models import PatientDocument
from .models import SignatureArtifact, SignatureRequest


def build_signature_expiry():
    return timezone.now() + timedelta(hours=settings.SIGN_LINK_TTL_HOURS)


def _decode_base64_image(data: str) -> bytes:
    if "," in data:
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def _make_typed_signature_image(text: str) -> bytes:
    image = Image.new("RGB", (500, 120), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 30), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_signed_pdf(document: PatientDocument, signer_email: str, signature_kind: str) -> bytes:
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 50, "Signed Document")
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 80, f"Original document ID: {document.id}")
    c.drawString(40, height - 100, f"Patient: {document.patient.user.full_name}")
    c.drawString(40, height - 120, f"Signer email: {signer_email}")
    c.drawString(40, height - 140, f"Signature type: {signature_kind}")
    c.drawString(40, height - 160, f"Signed at (UTC): {timezone.now().isoformat()}")
    c.drawString(40, height - 200, "This signed artifact references the original uploaded file.")

    c.showPage()
    c.save()
    return output.getvalue()


def finalize_signature(
    *,
    sign_request: SignatureRequest,
    signature_type: str,
    typed_signature: str,
    drawn_signature_data: str,
    ip_address: str,
    user_agent: str,
) -> SignatureArtifact:
    if sign_request.status == SignatureRequest.Status.SIGNED:
        return sign_request.artifact

    if signature_type == SignatureArtifact.SignatureType.DRAWN:
        image_bytes = _decode_base64_image(drawn_signature_data)
        image_ext = "png"
    else:
        image_bytes = _make_typed_signature_image(typed_signature or sign_request.signer_email)
        image_ext = "png"

    pdf_bytes = _make_signed_pdf(sign_request.document, sign_request.signer_email, signature_type)
    digest = hashlib.sha256(pdf_bytes).hexdigest()

    artifact = SignatureArtifact(
        signature_request=sign_request,
        signature_type=signature_type,
        document_hash_sha256=digest,
        ip_address=ip_address,
        user_agent=user_agent[:255],
    )
    artifact.signature_image.save(f"signature.{image_ext}", ContentFile(image_bytes), save=False)
    artifact.signed_pdf.save("signed_document.pdf", ContentFile(pdf_bytes), save=False)
    artifact.save()

    sign_request.status = SignatureRequest.Status.SIGNED
    sign_request.save(update_fields=["status"])
    return artifact


def sign_request_expired(sign_request: SignatureRequest) -> bool:
    return timezone.now() > sign_request.expires_at
