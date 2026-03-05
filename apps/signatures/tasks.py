from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from apps.core.services import log_audit

from .models import SignatureRequest


def send_signature_request_email_now(signature_request_id: int):
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


@shared_task
def send_signature_request_email(signature_request_id: int):
    return send_signature_request_email_now(signature_request_id)


def dispatch_signature_request_email(signature_request_id: int):
    delivery_mode = getattr(settings, "SIGNATURE_EMAIL_DELIVERY", "sync").lower()
    if delivery_mode == "async":
        try:
            send_signature_request_email.delay(signature_request_id)
            return True, None
        except Exception:  # noqa: BLE001
            pass
    try:
        send_signature_request_email_now(signature_request_id)
        return True, None
    except Exception as exc:  # noqa: BLE001
        sign_request = SignatureRequest.objects.select_related("requester").filter(id=signature_request_id).first()
        log_audit(
            actor=sign_request.requester if sign_request else None,
            action="signature.email_failed",
            object_type="SignatureRequest",
            object_id=signature_request_id,
            metadata={"error": str(exc)},
        )
        return False, str(exc)
