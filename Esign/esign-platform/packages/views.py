from django.shortcuts import render

# Create your views here.
# packages/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Package, SignatureField
from .serializers import (
    PackageSerializer, PackageListSerializer, PackageDetailSerializer,
    SignatureFieldSerializer,
)

from rest_framework.views import APIView
from django.utils import timezone
from .models import Package, Recipient

from audit.utils import log_event
from audit.models import AuditEvent

from notifications.tasks import send_signing_invitation, send_cc_notification
from config.pagination import StandardPagination



class PackageCreateView(generics.CreateAPIView):
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        package = serializer.save(sender=self.request.user)
        log_event(
            event_type=AuditEvent.EventType.PACKAGE_CREATED,
            package=package,
            actor=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={
                'subject': package.subject,
                'routing_mode': package.routing_mode,
                'recipient_count': package.recipients.count(),
            }
        )

class PackageListView(generics.ListAPIView):
    serializer_class = PackageListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Package.objects.filter(
            sender=self.request.user
        ).select_related('sender').prefetch_related('recipients')
    

class SendPackageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            package = Package.objects.get(pk=pk, sender=request.user)
        except Package.DoesNotExist:
            return Response(
                {"error": "Package not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if package.status != Package.Status.DRAFT:
            return Response(
                {"error": f"Cannot send a package with status '{package.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not package.recipients.exists():
            return Response(
                {"error": "Package has no recipients."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Move package forward
        package.status = Package.Status.SENT
        package.save()

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_SENT,
            package=package,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"recipient_count": package.recipients.count()}
        )

        # Queue invitation emails
        if package.routing_mode == Package.RoutingMode.PARALLEL:
            recipients_to_notify = package.recipients.filter(
                role=Recipient.Role.SIGNER
            )
        else:
            # Serial — only notify first recipient
            first = package.recipients.filter(
                role=Recipient.Role.SIGNER
            ).order_by('signing_order').first()
            recipients_to_notify = [first] if first else []

        for r in recipients_to_notify:
            send_signing_invitation.delay(
                recipient_name=r.name,
                recipient_email=r.email,
                sender_name=package.sender.get_full_name() or package.sender.email,
                package_subject=package.subject,
                signing_token=str(r.signing_token)
            )

        # Notify all CC recipients immediately
        cc_recipients = package.recipients.filter(role=Recipient.Role.CC)
        for r in cc_recipients:
            send_cc_notification.delay(
                recipient_name=r.name,
                recipient_email=r.email,
                sender_name=package.sender.get_full_name() or package.sender.email,
                package_subject=package.subject
            )
            r.status = Recipient.Status.SENT
            r.save()

        # Routing logic
        if package.routing_mode == Package.RoutingMode.PARALLEL:
            # All recipients notified simultaneously
            package.recipients.update(status=Recipient.Status.SENT)
        else:
            # SERIAL — only notify the first recipient
            first = package.recipients.filter(
                role=Recipient.Role.SIGNER
            ).order_by('signing_order').first()

            if first:
                first.status = Recipient.Status.SENT
                first.save()

        return Response(
                {
                    "message": "Package sent successfully.",
                    "status": package.status,
                },
                status=status.HTTP_200_OK
            )
    
class PackageDetailView(generics.RetrieveAPIView):
    serializer_class = PackageDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Package.objects.filter(
            sender=self.request.user
        ).select_related(
            'sender', 'document'
        ).prefetch_related('recipients')
    
class PackageCancelView(APIView):
    """
    Sender cancels/revokes a package that hasn't completed yet.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            package = Package.objects.get(pk=pk, sender=request.user)
        except Package.DoesNotExist:
            return Response(
                {"error": "Package not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if package.status in [
            Package.Status.COMPLETED,
            Package.Status.CANCELLED,
        ]:
            return Response(
                {"error": f"Cannot cancel a package with status '{package.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        package.status = Package.Status.CANCELLED
        package.save()

        # Mark all non-terminal recipients as cancelled
        package.recipients.filter(
            status__in=[
                Recipient.Status.PENDING,
                Recipient.Status.SENT,
                Recipient.Status.VIEWED,
            ]
        ).update(status=Recipient.Status.DECLINED)

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_CANCELLED,
            package=package,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"cancelled_by": request.user.email}
        )

        return Response(
            {"message": "Package cancelled successfully.", "status": package.status},
            status=status.HTTP_200_OK
        )

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        packages = Package.objects.filter(sender=request.user)
        total = packages.count()
        completed = packages.filter(status=Package.Status.COMPLETED).count()
        pending = packages.filter(
            status__in=[Package.Status.SENT, Package.Status.IN_PROGRESS]
        ).count()
        drafts = packages.filter(status=Package.Status.DRAFT).count()
        
        # Monthly breakdown for charts
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        monthly_stats = packages.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        chart_data = [
            {"month": entry['month'].strftime("%Y-%m"), "count": entry['count']}
            for entry in monthly_stats if entry['month']
        ]

        return Response({
            "total": total,
            "completed": completed,
            "pending": pending,
            "drafts": drafts,
            "chart_data": chart_data
        })


# ─────────────────────────────────────────────────────────────────────────────
# Feature 38 – Signature Field Placement (DRAFT packages only)
# ─────────────────────────────────────────────────────────────────────────────

class SignatureFieldListCreateView(APIView):
    """
    GET  /packages/<pk>/fields/  — list all signature fields for a package.
    POST /packages/<pk>/fields/  — create a new signature field.
    Only allowed while the package is in DRAFT status.
    """
    permission_classes = [IsAuthenticated]

    def _get_package(self, pk, user):
        try:
            return Package.objects.get(pk=pk, sender=user)
        except Package.DoesNotExist:
            return None

    def get(self, request, pk):
        package = self._get_package(pk, request.user)
        if not package:
            return Response({"error": "Package not found."}, status=status.HTTP_404_NOT_FOUND)

        fields = SignatureField.objects.filter(package=package).select_related('recipient')
        serializer = SignatureFieldSerializer(fields, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        package = self._get_package(pk, request.user)
        if not package:
            return Response({"error": "Package not found."}, status=status.HTTP_404_NOT_FOUND)

        if package.status != Package.Status.DRAFT:
            return Response(
                {"error": "Signature fields can only be placed while the package is in DRAFT status."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SignatureFieldSerializer(data=request.data)
        if serializer.is_valid():
            recipient = serializer.validated_data['recipient']
            # Ensure the recipient belongs to this package
            if recipient.package_id != package.pk:
                return Response(
                    {"error": "Recipient does not belong to this package."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(package=package)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignatureFieldDeleteView(APIView):
    """
    DELETE /packages/<pk>/fields/<field_id>/  — remove a signature field.
    Only allowed while the package is in DRAFT status.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, field_id):
        try:
            package = Package.objects.get(pk=pk, sender=request.user)
        except Package.DoesNotExist:
            return Response({"error": "Package not found."}, status=status.HTTP_404_NOT_FOUND)

        if package.status != Package.Status.DRAFT:
            return Response(
                {"error": "Cannot modify fields after the package has been sent."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            field = SignatureField.objects.get(pk=field_id, package=package)
        except SignatureField.DoesNotExist:
            return Response({"error": "Signature field not found."}, status=status.HTTP_404_NOT_FOUND)

        field.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 – Resend a RETURNED package
# ─────────────────────────────────────────────────────────────────────────────

class ResendPackageView(APIView):
    """
    POST /packages/<pk>/resend/
    Sender can resend a RETURNED package, which kicks off the signing workflow again
    from the first pending recipient.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            package = Package.objects.get(pk=pk, sender=request.user)
        except Package.DoesNotExist:
            return Response({"error": "Package not found."}, status=status.HTTP_404_NOT_FOUND)

        if package.status != Package.Status.RETURNED:
            return Response(
                {"error": f"Only RETURNED packages can be resent. Current status: '{package.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset all non-terminal recipients back to PENDING so signing starts fresh
        package.recipients.filter(
            status__in=[
                Recipient.Status.RETURNED,
                Recipient.Status.PENDING,
                Recipient.Status.SENT,
                Recipient.Status.VIEWED,
            ]
        ).update(status=Recipient.Status.PENDING)

        package.status = Package.Status.SENT
        package.save()

        log_event(
            event_type=AuditEvent.EventType.PACKAGE_RESENT,
            package=package,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={"resent_by": request.user.email}
        )

        # Notify first signer(s) in the routing order
        from notifications.tasks import send_signing_invitation
        if package.routing_mode == Package.RoutingMode.PARALLEL:
            recipients_to_notify = list(package.recipients.filter(
                role=Recipient.Role.SIGNER,
                status=Recipient.Status.PENDING
            ))
        else:
            first_order = package.recipients.filter(
                role__in=[Recipient.Role.SIGNER, Recipient.Role.APPROVER],
                status=Recipient.Status.PENDING
            ).order_by('signing_order').values_list('signing_order', flat=True).first()

            if first_order is not None:
                recipients_to_notify = list(package.recipients.filter(
                    role__in=[Recipient.Role.SIGNER, Recipient.Role.APPROVER],
                    status=Recipient.Status.PENDING,
                    signing_order=first_order
                ))
            else:
                recipients_to_notify = []

        for r in recipients_to_notify:
            r.status = Recipient.Status.SENT
            r.save()
            send_signing_invitation.delay(
                recipient_name=r.name,
                recipient_email=r.email,
                sender_name=package.sender.get_full_name() or package.sender.email,
                package_subject=package.subject,
                signing_token=str(r.signing_token)
            )

        return Response(
            {"message": "Package resent successfully.", "status": package.status},
            status=status.HTTP_200_OK
        )