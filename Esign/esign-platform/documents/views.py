from django.shortcuts import render

# Create your views here.
# documents/views.py

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document
from .serializers import DocumentUploadSerializer, DocumentSerializer
from audit.utils import log_event
from audit.models import AuditEvent
from packages.models import Package
from config.pagination import StandardPagination

class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentUploadSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    # These parsers tell DRF to expect multipart/form-data (file uploads)
    # not JSON — this is required for file uploads

    def perform_create(self, serializer):
        # Inject the authenticated user — client never sends this
        document = serializer.save(uploaded_by=self.request.user)

        log_event(
            event_type=AuditEvent.EventType.DOCUMENT_UPLOADED,
            package=None,
            actor=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={
                'document_id': str(document.id),
                'filename': document.original_filename,
                'file_size': document.file_size,
                'file_hash': document.file_hash,
            }
        )
        from audit.models import AuditEvent as AE
        from django.contrib.contenttypes.models import ContentType
        # Log the upload event
        # Document upload has no package yet — we log it differently
        # We store doc info in metadata instead
        # Since AuditEvent requires a package FK, we skip logging here
        # and log it when the package is created instead
        # This is a known architectural limitation
        pass

class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        # Users only see their own documents — never someone else's
        return Document.objects.filter(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)