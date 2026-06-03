# notifications/tasks.py

from celery import shared_task, chain
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.core.files.base import ContentFile
from documents.pdf_utils import (
    generate_signature_certificate,
    merge_pdf_with_certificate,
    stamp_signatures_on_pdf,
)
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
    from packages.models import Package, SignatureField

    try:
        package = Package.objects.select_related(
            'document', 'sender'
        ).prefetch_related('recipients').get(id=package_id)
    except Package.DoesNotExist:
        return

    # Gather all signed/approved recipients with their audit data
    signed_recipients = package.recipients.filter(
        role__in=['SIGNER', 'APPROVER'],
        status__in=['SIGNED', 'APPROVED']
    ).order_by('signing_order')

    recipients_data = []
    for r in signed_recipients:
        audit = AuditEvent.objects.filter(
            package=package,
            recipient=r,
            event_type__in=['signing.signed', 'signing.approved']
        ).first()

        recipients_data.append({
            'name': r.name,
            'email': r.email,
            'signed_at': r.signed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if r.signed_at else 'N/A',
            'ip_address': audit.ip_address if audit else None,
            'signature_data': r.signature_data,
        })

    # Build signature_fields_by_page:
    # { page_number: [ {x, y, width, height, signature_data}, ... ] }
    # A recipient signs once; that signature is applied to ALL their fields.
    signature_fields_by_page = {}
    fields_qs = SignatureField.objects.filter(
        package=package
    ).select_related('recipient').order_by('page_number', 'y', 'x')

    for field in fields_qs:
        recipient = field.recipient
        # Only stamp if the recipient has actually signed
        if recipient.status not in ('SIGNED',) or not recipient.signature_data:
            continue
        page = field.page_number
        if page not in signature_fields_by_page:
            signature_fields_by_page[page] = []
        signature_fields_by_page[page].append({
            'x': field.x,
            'y': field.y,
            'width': field.width,
            'height': field.height,
            'signature_data': recipient.signature_data,
        })

    original_file = package.document.file

    # Stamp signatures onto PDF pages (no-op if no fields defined)
    if signature_fields_by_page:
        stamped_pdf = stamp_signatures_on_pdf(original_file, signature_fields_by_page)
    else:
        # No fields placed — use original file directly
        import io as _io
        original_file.open('rb')
        stamped_pdf = _io.BytesIO(original_file.read())
        original_file.close()
        stamped_pdf.seek(0)

    # Generate certificate and merge
    certificate_buffer = generate_signature_certificate(package, recipients_data)
    merged_pdf = merge_pdf_with_certificate(stamped_pdf, certificate_buffer)

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

@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_cc_notification(
    recipient_name,
    recipient_email,
    sender_name,
    package_subject
):
    subject = f"FYI: You were CC'd on '{package_subject}'"

    message = f"""
Hi {recipient_name},

{sender_name} has copied you on a document: {package_subject}

You do not need to sign this document. You will receive a copy of the final document once all parties have signed.

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

@shared_task
def process_expirations():
    from django.utils import timezone
    from packages.models import Package, Recipient
    from audit.utils import log_event
    from audit.models import AuditEvent

    expired_packages = Package.objects.filter(
        status=Package.Status.SENT,
        expires_at__lt=timezone.now()
    )

    for package in expired_packages:
        package.status = Package.Status.EXPIRED
        package.save()
        
        package.recipients.filter(
            status__in=[Recipient.Status.PENDING, Recipient.Status.SENT, Recipient.Status.VIEWED]
        ).update(status=Recipient.Status.EXPIRED)

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_EXPIRED,
            package=package,
            metadata={"expired_at": package.expires_at.isoformat()}
        )
        
        subject = f"Expired: {package.subject}"
        message = f"The document '{package.subject}' has expired and can no longer be signed."
        
        emails = [package.sender.email] + [r.email for r in package.recipients.all()]
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(set(emails)),
            fail_silently=True,
        )

@shared_task
def process_reminders():
    from django.utils import timezone
    from packages.models import Package, Recipient
    from audit.utils import log_event
    from audit.models import AuditEvent
    import datetime

    # Get packages that are sent and have reminder_days > 0
    packages = Package.objects.filter(
        status=Package.Status.SENT,
        reminder_days__gt=0
    )

    now = timezone.now()

    for package in packages:
        # Check if reminder is due
        # We can use updated_at as the baseline for the next reminder, 
        # and update it when a reminder is sent. Wait, updating updated_at might have side effects.
        # Let's find the last reminder audit event.
        last_reminder = AuditEvent.objects.filter(
            package=package,
            event_type=AuditEvent.EventType.REMINDER_SENT
        ).order_by('-created_at').first()
        
        baseline_time = last_reminder.created_at if last_reminder else package.created_at
        
        if now >= baseline_time + datetime.timedelta(days=package.reminder_days):
            # Send reminder to pending/sent/viewed signers
            signers = package.recipients.filter(
                role=Recipient.Role.SIGNER,
                status__in=[Recipient.Status.PENDING, Recipient.Status.SENT, Recipient.Status.VIEWED]
            )
            
            for r in signers:
                send_signing_invitation.delay(
                    recipient_name=r.name,
                    recipient_email=r.email,
                    sender_name=package.sender.get_full_name() or package.sender.email,
                    package_subject=package.subject,
                    signing_token=str(r.signing_token)
                )
                
            log_event(
                event_type=AuditEvent.EventType.REMINDER_SENT,
                package=package,
                metadata={"reminder_days": package.reminder_days, "recipients": [r.email for r in signers]}
            )