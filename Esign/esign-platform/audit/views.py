from django.shortcuts import render

# Create your views here.
# audit/views.py

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import AuditEvent
from .serializers import AuditEventSerializer
from packages.models import Package
from django.http import HttpResponse
import csv
import json


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


class PackageAuditExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, package_id):
        events = AuditEvent.objects.filter(
            package__id=package_id,
            package__sender=request.user
        ).select_related('actor', 'recipient')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_trail_{package_id}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Event Type', 'Actor', 'Recipient', 'IP Address', 'Metadata'])

        for event in events:
            actor = event.actor.email if event.actor else 'System'
            recipient = event.recipient.email if event.recipient else ''
            
            writer.writerow([
                event.created_at.isoformat(),
                event.get_event_type_display(),
                actor,
                recipient,
                event.ip_address or '',
                str(event.metadata)
            ])

        return response


class PackageAuditExportJSONView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, package_id):
        events = AuditEvent.objects.filter(
            package__id=package_id,
            package__sender=request.user
        ).select_related('actor', 'recipient')

        serializer = AuditEventSerializer(events, many=True)
        
        response = HttpResponse(
            json.dumps(serializer.data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="audit_trail_{package_id}.json"'
        return response
