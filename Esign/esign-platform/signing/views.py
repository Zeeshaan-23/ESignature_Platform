from django.shortcuts import render

# Create your views here.
# signing/views.py

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from packages.models import Recipient, Package
from documents.serializers import DocumentSerializer

from audit.utils import log_event
from audit.models import AuditEvent

from notifications.tasks import send_signing_invitation
from notifications.tasks import generate_signed_pdf, send_completion_notification

from celery import chain
from signing.throttles import SigningTokenRateThrottle


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
        if recipient.package.expires_at and recipient.package.expires_at < timezone.now():
            # Mark package as expired
            recipient.package.status = Package.Status.EXPIRED
            recipient.package.save()
            # Mark all unsigned recipients as expired
            recipient.package.recipients.filter(
                status__in=[
                    Recipient.Status.PENDING,
                    Recipient.Status.SENT,
                    Recipient.Status.VIEWED
                ]
            ).update(status=Recipient.Status.EXPIRED)
            return Response(
                {"error": "This signing link has expired."},
                status=status.HTTP_410_GONE
            )
                
        # Check recipient hasn't already signed
        if recipient.status == Recipient.Status.SIGNED:
            return Response(
                {"error": "You have already signed this document."},
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
            }
        })


class SigningSubmitView(APIView):
    """
    Signer submits their signature.
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

        if recipient.status == Recipient.Status.SIGNED:
            return Response(
                {"error": "You have already signed this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package = recipient.package
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

        # Accept signature data from request body
        signature_data = request.data.get('signature_data', '')
        if not signature_data:
            return Response(
                {"error": "Signature is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark recipient as signed
        recipient.status = Recipient.Status.SIGNED
        recipient.signed_at = timezone.now()
        recipient.signature_data = signature_data
        recipient.save()

        log_event(
            event_type=AuditEvent.EventType.SIGNING_SIGNED,
            package=package,
            recipient=recipient,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"signed_at": str(recipient.signed_at)}
        )

        # Serial routing — notify next recipient after this one signs
        if package.routing_mode == Package.RoutingMode.SERIAL:
            next_recipient = package.recipients.filter(
                role=Recipient.Role.SIGNER,
                status=Recipient.Status.PENDING,
            ).order_by('signing_order').first()

            if next_recipient:
                next_recipient.status = Recipient.Status.SENT
                next_recipient.save()

                send_signing_invitation.delay(
                    recipient_name=next_recipient.name,
                    recipient_email=next_recipient.email,
                    sender_name=package.sender.email,
                    package_subject=package.subject,
                    signing_token=str(next_recipient.signing_token)
                )
                # Later: trigger email to next_recipient here
        #check if ALL signers have signed
        unsigned = package.recipients.filter(
            role=Recipient.Role.SIGNER,
            status__in=[
                Recipient.Status.PENDING,
                Recipient.Status.SENT,
                Recipient.Status.VIEWED
            ]
        )

        if not unsigned.exists():
            package.status = Package.Status.COMPLETED
            package.save()
            log_event(
                event_type=AuditEvent.EventType.PACKAGE_COMPLETED,
                package=package,
                ip_address=request.META.get('REMOTE_ADDR')
            )

         # Generate PDF first, then email with attachment (chained)
        chain(
            generate_signed_pdf.s(str(package.id)),
            send_completion_notification.si(str(package.id))
        ).delay()  

        return Response({
            "message": "Document signed successfully.",
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

        if recipient.status == Recipient.Status.SIGNED:
            return Response(
                {"error": "You have already signed this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if recipient.status == Recipient.Status.DECLINED:
            return Response(
                {"error": "You have already declined this document."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package = recipient.package

        if package.expires_at and package.expires_at < timezone.now():
            return Response(
                {"error": "This signing link has expired."},
                status=status.HTTP_410_GONE
            )

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