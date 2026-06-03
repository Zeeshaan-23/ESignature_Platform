# notifications/tasks.py

from celery import shared_task, chain
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.core.files.base import ContentFile
from documents.pdf_utils import generate_signature_certificate, merge_pdf_with_certificate
from audit.models import AuditEvent



@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,        # 60s, 120s, 240s
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_signing_invitation(
    recipient_name,
    recipient_email,
    sender_name,
    package_subject,
    signing_token
):
    signing_url = f"{settings.FRONTEND_URL}/sign/{signing_token}"

    subject = f"You have been requested to sign: {package_subject}"

    message = f"""
Hi {recipient_name},

{sender_name} has requested your signature on: {package_subject}

Click the link below to review and sign the document:

{signing_url}

This link is unique to you. Do not share it.

Regards,
eSign Platform
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_completion_notification(package_id):
    """
    Sends completion email with signed PDF attached.
    Called after generate_signed_pdf completes.
    """
    from packages.models import Package

    try:
        package = Package.objects.select_related('sender').prefetch_related(
            'recipients'
        ).get(id=package_id)
    except Package.DoesNotExist:
        return

    subject = f"Document signed: {package.subject}"

    message = f"""The document "{package.subject}" has been signed by all parties.

All signing parties have been notified.

Regards,
eSign Platform"""

    for recipient in package.recipients.all():
        email = EmailMessage(
            subject=subject,
            body=f"Hi {recipient.name},\n\n{message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
        )

        if package.signed_file:
            try:
                package.signed_file.open('rb')
                email.attach(
                    f"signed_{package.document.original_filename}",
                    package.signed_file.read(),
                    'application/pdf'
                )
                package.signed_file.close()
            except Exception:
                pass  # Send without attachment rather than failing entirely

        email.send(fail_silently=False)

        
@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_signed_pdf(package_id):
    from packages.models import Package

    try:
        package = Package.objects.select_related(
            'document', 'sender'
        ).prefetch_related('recipients').get(id=package_id)
    except Package.DoesNotExist:
        return

    # Gather all signed recipients with their audit data
    recipients_data = []
    for r in package.recipients.filter(
        role='SIGNER',
        status='SIGNED'
    ).order_by('signing_order'):

        # Get IP from audit log
        audit = AuditEvent.objects.filter(
            package=package,
            recipient=r,
            event_type='signing.signed'
        ).first()

        recipients_data.append({
            'name': r.name,
            'email': r.email,
            'signed_at': r.signed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if r.signed_at else 'N/A',
            'ip_address': audit.ip_address if audit else None,
            'signature_data': r.signature_data,
        })

    # Generate certificate page
    certificate_buffer = generate_signature_certificate(package, recipients_data)

    # Merge with original document
    original_file = package.document.file
    merged_pdf = merge_pdf_with_certificate(original_file, certificate_buffer)

    # Save signed file to package
    filename = f"signed_{package.document.original_filename}"
    package.signed_file.save(
        filename,
        ContentFile(merged_pdf.read()),
        save=True
    )
    
@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_password_reset_email(email, reset_url):
    send_mail(
        subject='Reset your eSign password',
        message=(
            f'You requested a password reset.\n\n'
            f'Click the link below to set a new password:\n\n'
            f'{reset_url}\n\n'
            f'This link expires in 1 hour.\n\n'
            f'If you did not request this, ignore this email.\n\n'
            f'Regards,\neSign Platform'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )