# documents/views.py

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from .models import Document, DocumentTemplate
from .serializers import DocumentUploadSerializer, DocumentSerializer, DocumentTemplateSerializer
from audit.utils import log_event
from audit.models import AuditEvent
from config.pagination import StandardPagination


class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentUploadSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
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


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)


class DocumentTamperCheckView(APIView):
    """
    Phase 7.32 — Post-sign hash re-verification.
    GET /api/documents/<id>/verify/
    Re-reads the stored file, computes its SHA-256, and compares it to the
    hash that was captured at upload time.  Returns { intact: bool, ... }.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk, uploaded_by=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        from documents.pdf_utils import verify_file_hash
        try:
            document.file.open('rb')
            intact, computed = verify_file_hash(document.file, document.file_hash)
            document.file.close()
        except Exception as e:
            return Response(
                {"error": f"Could not read file for verification: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        log_event(
            event_type=AuditEvent.EventType.DOCUMENT_VERIFIED,
            package=None,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                'document_id': str(document.id),
                'intact': intact,
                'stored_hash': document.file_hash,
                'computed_hash': computed,
            }
        )

        return Response({
            "document_id": str(document.id),
            "filename": document.original_filename,
            "intact": intact,
            "stored_hash": document.file_hash,
            "computed_hash": computed,
            "message": "File integrity verified." if intact else "⚠️ File hash mismatch — document may have been tampered with.",
        })


# ─── Phase 7.33 — Document Templates ──────────────────────────────────────────

class DocumentTemplateListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/documents/templates/        — list the user's templates
    POST /api/documents/templates/        — create a new template from an uploaded document
    """
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return DocumentTemplate.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DocumentTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/documents/templates/<id>/  — retrieve a template
    PATCH  /api/documents/templates/<id>/  — update name / description (not the file)
    DELETE /api/documents/templates/<id>/  — delete template
    """
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DocumentTemplate.objects.filter(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        # Prevent modifying a locked template
        instance = self.get_object()
        if instance.is_locked and request.method != 'GET':
            return Response(
                {"error": "This template is locked and cannot be modified."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_locked:
            return Response(
                {"error": "This template is locked and cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class DocumentTemplateCreatePackageView(APIView):
    """
    POST /api/documents/templates/<id>/use/
    Creates a new Document (copy of the template file) so the sender can then
    create a signing package from it.  The template's use_count is incremented.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            template = DocumentTemplate.objects.get(pk=pk, created_by=request.user)
        except DocumentTemplate.DoesNotExist:
            return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)

        import io
        from django.core.files.base import ContentFile
        from documents.utils import hash_file as _hash_file

        # Copy the template file into a fresh Document
        template.document.file.open('rb')
        file_bytes = template.document.file.read()
        template.document.file.close()

        import hashlib
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        new_doc = Document.objects.create(
            uploaded_by=request.user,
            original_filename=template.document.original_filename,
            file=ContentFile(file_bytes, name=template.document.original_filename),
            file_size=len(file_bytes),
            file_hash=file_hash,
            status=Document.Status.DRAFT,
        )

        template.use_count += 1
        template.save(update_fields=['use_count'])

        return Response({
            "document_id": str(new_doc.id),
            "original_filename": new_doc.original_filename,
            "message": "Document created from template. You can now create a signing package.",
        }, status=status.HTTP_201_CREATED)