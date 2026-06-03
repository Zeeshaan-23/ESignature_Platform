from django.shortcuts import render

# Create your views here.
# packages/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Package
from .serializers import PackageSerializer, PackageListSerializer, PackageDetailSerializer

from rest_framework.views import APIView
from django.utils import timezone
from .models import Package, Recipient

from audit.utils import log_event
from audit.models import AuditEvent

from notifications.tasks import send_signing_invitation
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