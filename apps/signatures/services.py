import base64
import hashlib
import io
import os
from datetime import timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
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


def _make_signed_pdf(document: PatientDocument, signer_email: str, signature_kind: str, signature_image: bytes, pos_x: float, pos_y: float) -> bytes:
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    page_width, page_height = letter

    source_drawn = False
    suffix = os.path.splitext(document.file.name or "")[1].lower()
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        try:
            doc_img = Image.open(document.file.path).convert("RGB")
            img_reader = ImageReader(doc_img)
            c.drawImage(img_reader, 0, 0, width=page_width, height=page_height, preserveAspectRatio=True, anchor="c")
            source_drawn = True
        except Exception:
            source_drawn = False

    if not source_drawn:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, page_height - 50, "Signed Document")
        c.setFont("Helvetica", 11)
        c.drawString(40, page_height - 80, f"Original document ID: {document.id}")
        c.drawString(40, page_height - 100, f"Patient: {document.patient.user.full_name}")
        c.drawString(40, page_height - 120, f"Signer email: {signer_email}")
        c.drawString(40, page_height - 140, f"Signature type: {signature_kind}")
        c.drawString(40, page_height - 160, f"Signed at (UTC): {timezone.now().isoformat()}")
        c.drawString(40, page_height - 180, f"Original file: {document.file.name}")

    sig_img = Image.open(io.BytesIO(signature_image)).convert("RGBA")
    sig_reader = ImageReader(sig_img)
    sig_w = 180
    sig_h = 60
    x = (max(0.0, min(100.0, pos_x)) / 100.0) * page_width
    y_from_top = (max(0.0, min(100.0, pos_y)) / 100.0) * page_height
    y = page_height - y_from_top - sig_h
    x = max(0, min(page_width - sig_w, x))
    y = max(0, min(page_height - sig_h, y))
    c.drawImage(sig_reader, x, y, width=sig_w, height=sig_h, mask="auto")

    c.setFont("Helvetica", 8)
    c.drawString(20, 12, f"Signed by {signer_email} at {timezone.now().isoformat()} | SHA256 protected artifact")

    c.showPage()
    c.save()
    return output.getvalue()


def finalize_signature(
    *,
    sign_request: SignatureRequest,
    signature_type: str,
    typed_signature: str,
    drawn_signature_data: str,
    uploaded_signature_file,
    signature_pos_x: float,
    signature_pos_y: float,
    ip_address: str,
    user_agent: str,
) -> SignatureArtifact:
    if sign_request.status == SignatureRequest.Status.SIGNED:
        return sign_request.artifact

    if signature_type == SignatureArtifact.SignatureType.DRAWN:
        image_bytes = _decode_base64_image(drawn_signature_data)
        image_ext = "png"
    elif signature_type == SignatureArtifact.SignatureType.UPLOADED:
        image_bytes = uploaded_signature_file.read()
        image_ext = os.path.splitext(uploaded_signature_file.name or "")[1].lstrip(".").lower() or "png"
    else:
        image_bytes = _make_typed_signature_image(typed_signature or sign_request.signer_email)
        image_ext = "png"

    pdf_bytes = _make_signed_pdf(
        sign_request.document,
        sign_request.signer_email,
        signature_type,
        image_bytes,
        signature_pos_x,
        signature_pos_y,
    )
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
