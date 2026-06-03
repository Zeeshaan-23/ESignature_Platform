from django.shortcuts import render

# Create your views here.
# audit/views.py

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AuditEvent
from .serializers import AuditEventSerializer
from packages.models import Package


class PackageAuditView(generics.ListAPIView):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        package_id = self.kwargs['package_id']
        # Only let the sender see their own package's audit trail
        return AuditEvent.objects.filter(
            package__id=package_id,
            package__sender=self.request.user
        ).select_related('actor', 'recipient')
