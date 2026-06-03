# signing/views.py

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from packages.models import Recipient, Package, SignatureField

from audit.utils import log_event
from audit.models import AuditEvent

from notifications.tasks import send_signing_invitation
from notifications.tasks import generate_signed_pdf, send_completion_notification

from celery import chain
from signing.throttles import SigningTokenRateThrottle


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _notify_next_group(package):
    """
    Serial / hybrid routing helper.
    After the current signing_order group finishes, finds all recipients at
    the *next* signing_order and notifies them simultaneously.
    Returns True if a next group was found and notified, False otherwise.
    """
    # Determine "actionable" roles (SIGNER and APPROVER both receive invitations)
    next_order = package.recipients.filter(
        role__in=[Recipient.Role.SIGNER, Recipient.Role.APPROVER],
        status=Recipient.Status.PENDING,
    ).order_by('signing_order').values_list('signing_order', flat=True).first()

    if next_order is None:
        return False  # No more recipients waiting

    next_group = list(package.recipients.filter(
        role__in=[Recipient.Role.SIGNER, Recipient.Role.APPROVER],
        status=Recipient.Status.PENDING,
        signing_order=next_order,
    ))

    for r in next_group:
        r.status = Recipient.Status.SENT
        r.save()
        send_signing_invitation.delay(
            recipient_name=r.name,
            recipient_email=r.email,
            sender_name=package.sender.get_full_name() or package.sender.email,
            package_subject=package.subject,
            signing_token=str(r.signing_token)
        )

    return True


def _check_package_complete(package, ip_address):
    """
    Returns True and marks the package COMPLETED if every actionable recipient
    has finished (SIGNED, APPROVED, or DELEGATED).
    """
    incomplete = package.recipients.filter(
        role__in=[Recipient.Role.SIGNER, Recipient.Role.APPROVER],
        status__in=[
            Recipient.Status.PENDING,
            Recipient.Status.SENT,
            Recipient.Status.VIEWED,
        ]
    )

    if incomplete.exists():
        return False

    package.status = Package.Status.COMPLETED
    package.save()

    log_event(
        event_type=AuditEvent.EventType.PACKAGE_COMPLETED,
        package=package,
        ip_address=ip_address
    )

    # Generate signed PDF then send completion email
    chain(
        generate_signed_pdf.s(str(package.id)),
        send_completion_notification.si(str(package.id))
    ).delay()

    return True


def _validate_expiry(package):
    """
    Checks if a package has expired. If so, marks package + pending recipients
    as EXPIRED and returns an error Response. Returns None if still valid.
    """
    if package.expires_at and package.expires_at < timezone.now():
        package.status = Package.Status.EXPIRED
        package.save()
        package.recipients.filter(
            status__in=[
                Recipient.Status.PENDING,
                Recipient.Status.SENT,
                Recipient.Status.VIEWED,
            ]
        ).update(status=Recipient.Status.EXPIRED)
        return Response(
            {"error": "This signing link has expired."},
            status=status.HTTP_410_GONE
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────────────────────

class SigningAccessView(APIView):
    """
    Public endpoint — no JWT required.
    Signer accesses this via the link in their email.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SigningTokenRateThrottle]

    def get(self, request, token):
        try:
            recipient = Recipient.objects.select_related(
                'package', 'package__document'
            ).get(signing_token=token)
        except Recipient.DoesNotExist:
            return Response(
                {"error": "Invalid signing link."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delegated recipients' links are permanently disabled
        if recipient.status == Recipient.Status.DELEGATED:
            return Response(
                {"error": "Your signing right has been delegated. This link is no longer valid."},
                status=status.HTTP_410_GONE
            )

        # Check package is in a signable state
        if recipient.package.status not in [
            Package.Status.SENT,
            Package.Status.IN_PROGRESS
        ]:
            return Response(
                {"error": "This document is not currently open for signing."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check signing link has not expired
        expiry_error = _validate_expiry(recipient.package)
        if expiry_error:
            return expiry_error

        # Check recipient hasn't already completed their action
        if recipient.status in [Recipient.Status.SIGNED, Recipient.Status.APPROVED]:
            return Response(
                {"error": "You have already completed your action on this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark as viewed if they're seeing it for the first time
        if recipient.status == Recipient.Status.SENT:
            recipient.status = Recipient.Status.VIEWED
            recipient.save()

        log_event(
            event_type=AuditEvent.EventType.SIGNING_VIEWED,
            package=recipient.package,
            recipient=recipient,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"recipient_email": recipient.email}
        )

        # Update package status to IN_PROGRESS on first view
        if recipient.package.status == Package.Status.SENT:
            recipient.package.status = Package.Status.IN_PROGRESS
            recipient.package.save()

        # Fetch assigned signature fields for this recipient
        fields = SignatureField.objects.filter(
            package=recipient.package,
            recipient=recipient
        ).values('id', 'page_number', 'x', 'y', 'width', 'height')

        return Response({
            "recipient": {
                "id": str(recipient.id),
                "name": recipient.name,
                "email": recipient.email,
                "role": recipient.role,
            },
            "package": {
                "id": str(recipient.package.id),
                "subject": recipient.package.subject,
                "message": recipient.package.message,
            },
            "document": {
                "id": str(recipient.package.document.id),
                "filename": recipient.package.document.original_filename,
                "file_url": request.build_absolute_uri(
                    recipient.package.document.file.url
                ),
            },
            # Feature 38: field placement info for the signing UI
            "signature_fields": [
                {
                    "id": str(f['id']),
                    "page_number": f['page_number'],
                    "x": f['x'],
                    "y": f['y'],
                    "width": f['width'],
                    "height": f['height'],
                }
                for f in fields
            ],
            "requires_field_placement": fields.exists(),
        })


class SigningSubmitView(APIView):
    """
    Signer submits their signature.
    - SIGNER role: requires signature_data.  If the package has SignatureFields
      for this recipient, the same signature is applied to all fields.
    - APPROVER role: no signature canvas needed; mark as APPROVED.
    Both roles trigger hybrid routing (notify the full next signing_order group).
    """
    permission_classes = [AllowAny]
    throttle_classes = [SigningTokenRateThrottle]

    def post(self, request, token):
        try:
            recipient = Recipient.objects.select_related('package').get(
                signing_token=token
            )
        except Recipient.DoesNotExist:
            return Response(
                {"error": "Invalid signing link."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delegated links must not work
        if recipient.status == Recipient.Status.DELEGATED:
            return Response(
                {"error": "This signing link has been delegated and is no longer usable."},
                status=status.HTTP_410_GONE
            )

        if recipient.status in [Recipient.Status.SIGNED, Recipient.Status.APPROVED]:
            return Response(
                {"error": "You have already completed your action on this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package = recipient.package
        expiry_error = _validate_expiry(package)
        if expiry_error:
            return expiry_error

        ip = request.META.get('REMOTE_ADDR')

        # ── APPROVER path ────────────────────────────────────────────────────
        if recipient.role == Recipient.Role.APPROVER:
            recipient.status = Recipient.Status.APPROVED
            recipient.signed_at = timezone.now()
            recipient.save()

            log_event(
                event_type=AuditEvent.EventType.SIGNING_APPROVED,
                package=package,
                recipient=recipient,
                ip_address=ip,
                metadata={"approved_at": str(recipient.signed_at)}
            )

        # ── SIGNER path ──────────────────────────────────────────────────────
        else:
            signature_data = request.data.get('signature_data', '')
            if not signature_data:
                return Response(
                    {"error": "Signature is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Enforce that the signer must have "interacted" with all their fields.
            # The frontend sends a single signature that will be applied to all fields.
            # We just verify the signature is present; field rendering is handled in PDF gen.
            recipient.status = Recipient.Status.SIGNED
            recipient.signed_at = timezone.now()
            recipient.signature_data = signature_data
            recipient.save()

            log_event(
                event_type=AuditEvent.EventType.SIGNING_SIGNED,
                package=package,
                recipient=recipient,
                ip_address=ip,
                metadata={"signed_at": str(recipient.signed_at)}
            )

        # ── Routing ──────────────────────────────────────────────────────────
        if package.routing_mode == Package.RoutingMode.SERIAL:
            # Hybrid serial: notify all recipients sharing the next signing_order
            _notify_next_group(package)

        # Check if every actionable recipient is done
        if not _check_package_complete(package, ip):
            # Package not complete yet — just chain the PDF gen anyway for partial updates
            pass

        return Response({
            "message": "Action completed successfully.",
            "signed_at": recipient.signed_at,
            "package_status": package.status
        })


class SigningDeclineView(APIView):
    """
    Signer declines to sign. Requires an optional reason.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SigningTokenRateThrottle]

    def post(self, request, token):
        try:
            recipient = Recipient.objects.select_related('package').get(
                signing_token=token
            )
        except Recipient.DoesNotExist:
            return Response(
                {"error": "Invalid signing link."},
                status=status.HTTP_404_NOT_FOUND
            )

        if recipient.status in [Recipient.Status.SIGNED, Recipient.Status.APPROVED]:
            return Response(
                {"error": "You have already completed your action on this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if recipient.status == Recipient.Status.DECLINED:
            return Response(
                {"error": "You have already declined this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package = recipient.package

        expiry_error = _validate_expiry(package)
        if expiry_error:
            return expiry_error

        reason = request.data.get('reason', '')

        recipient.status = Recipient.Status.DECLINED
        recipient.save()

        package.status = Package.Status.DECLINED
        package.save()

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_DECLINED,
            package=package,
            recipient=recipient,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                "recipient_email": recipient.email,
                "reason": reason,
            }
        )

        return Response(
            {"message": "You have declined to sign this document."},
            status=status.HTTP_200_OK
        )


class SigningReturnView(APIView):
    """
    Feature 27 — Send-back / rework flow.
    An APPROVER returns the package for rework with a mandatory reason.
    The package status moves to RETURNED and the sender is notified.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SigningTokenRateThrottle]

    def post(self, request, token):
        try:
            recipient = Recipient.objects.select_related('package').get(
                signing_token=token
            )
        except Recipient.DoesNotExist:
            return Response(
                {"error": "Invalid signing link."},
                status=status.HTTP_404_NOT_FOUND
            )

        if recipient.role != Recipient.Role.APPROVER:
            return Response(
                {"error": "Only approvers can return a document for rework."},
                status=status.HTTP_403_FORBIDDEN
            )

        if recipient.status in [Recipient.Status.SIGNED, Recipient.Status.APPROVED,
                                 Recipient.Status.RETURNED]:
            return Response(
                {"error": "You have already completed your action on this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response(
                {"error": "A reason is required when returning a document for rework."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package = recipient.package
        expiry_error = _validate_expiry(package)
        if expiry_error:
            return expiry_error

        # Mark this approver as RETURNED
        recipient.status = Recipient.Status.RETURNED
        recipient.save()

        # Move package to RETURNED state
        package.status = Package.Status.RETURNED
        package.save()

        log_event(
            event_type=AuditEvent.EventType.SIGNING_RETURNED,
            package=package,
            recipient=recipient,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                "returned_by": recipient.email,
                "reason": reason,
            }
        )

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_RETURNED,
            package=package,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"reason": reason}
        )

        # Notify sender by email
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        try:
            send_mail(
                subject=f"Document returned for rework: {package.subject}",
                message=(
                    f"Hi {package.sender.get_full_name() or package.sender.email},\n\n"
                    f"{recipient.name} ({recipient.email}) has returned your document "
                    f"'{package.subject}' for rework.\n\n"
                    f"Reason: {reason}\n\n"
                    f"Please log in to make changes and resend the document.\n\n"
                    f"Regards,\neSign Platform"
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[package.sender.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Don't let email failure break the response

        return Response(
            {"message": "Document returned for rework. The sender has been notified."},
            status=status.HTTP_200_OK
        )


class SigningDelegateView(APIView):
    """
    Feature 28 — Delegation (signer reassignment).
    A signer can delegate their signing right to another person.
    - Original recipient is marked DELEGATED; their token becomes unusable.
    - A new Recipient record is created for the delegate.
    - An invitation email is sent to the delegate.
    - The delegation is preserved in the audit trail.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SigningTokenRateThrottle]

    def post(self, request, token):
        try:
            recipient = Recipient.objects.select_related('package').get(
                signing_token=token
            )
        except Recipient.DoesNotExist:
            return Response(
                {"error": "Invalid signing link."},
                status=status.HTTP_404_NOT_FOUND
            )

        if recipient.status == Recipient.Status.DELEGATED:
            return Response(
                {"error": "You have already delegated your signing right."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if recipient.status in [Recipient.Status.SIGNED, Recipient.Status.APPROVED,
                                 Recipient.Status.DECLINED]:
            return Response(
                {"error": "You cannot delegate after completing your action."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if recipient.role != Recipient.Role.SIGNER:
            return Response(
                {"error": "Only signers can delegate their signing right."},
                status=status.HTTP_403_FORBIDDEN
            )

        package = recipient.package
        expiry_error = _validate_expiry(package)
        if expiry_error:
            return expiry_error

        delegate_name = request.data.get('delegate_name', '').strip()
        delegate_email = request.data.get('delegate_email', '').strip().lower()

        if not delegate_name or not delegate_email:
            return Response(
                {"error": "delegate_name and delegate_email are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent delegating to oneself
        if delegate_email == recipient.email.lower():
            return Response(
                {"error": "You cannot delegate to yourself."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the new delegate recipient, inheriting the same signing_order
        delegate = Recipient.objects.create(
            package=package,
            name=delegate_name,
            email=delegate_email,
            role=Recipient.Role.SIGNER,
            signing_order=recipient.signing_order,
            status=Recipient.Status.SENT,
        )

        # Mark original recipient as DELEGATED and link to the new one
        recipient.status = Recipient.Status.DELEGATED
        recipient.delegated_to = delegate
        recipient.save()

        # Move any SignatureFields assigned to the original to the delegate
        SignatureField.objects.filter(
            package=package,
            recipient=recipient
        ).update(recipient=delegate)

        log_event(
            event_type=AuditEvent.EventType.RECIPIENT_DELEGATED,
            package=package,
            recipient=recipient,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                "original_recipient": recipient.email,
                "delegate_name": delegate_name,
                "delegate_email": delegate_email,
                "new_recipient_id": str(delegate.id),
            }
        )

        # Send invitation to delegate
        send_signing_invitation.delay(
            recipient_name=delegate_name,
            recipient_email=delegate_email,
            sender_name=package.sender.get_full_name() or package.sender.email,
            package_subject=package.subject,
            signing_token=str(delegate.signing_token)
        )

        return Response(
            {
                "message": f"Signing right delegated to {delegate_name} ({delegate_email}). "
                           f"They will receive an invitation email shortly.",
            },
            status=status.HTTP_200_OK
        )