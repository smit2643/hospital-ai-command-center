from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from apps.core.services import log_audit

from .models import SignatureRequest


@shared_task
def send_signature_request_email(signature_request_id: int):
    sign_request = SignatureRequest.objects.select_related("document", "requester").get(id=signature_request_id)
    sign_url = reverse("signatures:sign_public", kwargs={"token": str(sign_request.token)})
    full_url = f"{settings.SITE_BASE_URL}{sign_url}"
    subject = f"Signature request for document #{sign_request.document_id}"
    body = (
        f"You have a signature request.\n"
        f"Open this secure link: {full_url}\n"
        f"This link expires at {sign_request.expires_at.isoformat()}"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [sign_request.signer_email],
        fail_silently=False,
    )
    log_audit(
        actor=sign_request.requester,
        action="signature.email_sent",
        object_type="SignatureRequest",
        object_id=sign_request.id,
        metadata={"signer_email": sign_request.signer_email, "url": full_url},
    )
    return signature_request_id
