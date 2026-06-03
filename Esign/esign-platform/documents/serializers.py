# documents/serializers.py

from rest_framework import serializers
from django.conf import settings
from .models import Document
from .utils import hash_file

# Phase 7.30: clear, user-friendly list of allowed extensions
ALLOWED_EXTENSIONS = ['pdf', 'docx']


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'original_filename', 'file', 'file_size',
                  'file_hash', 'status', 'created_at']
        read_only_fields = ['id', 'original_filename', 'file_size',
                            'file_hash', 'status', 'created_at']

    def validate_file(self, file):
        ext = file.name.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. "
                f"Only {', '.join(a.upper() for a in ALLOWED_EXTENSIONS)} files are accepted. "
                f"Please convert your document and try again."
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large ({round(file.size / (1024*1024), 1)} MB). "
                f"Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        return file

    def create(self, validated_data):
        file = validated_data['file']
        ext = file.name.rsplit('.', 1)[-1].lower()

        # Phase 7.31: DOCX → PDF auto-conversion
        if ext == 'docx':
            from documents.pdf_utils import convert_docx_to_pdf
            import io
            from django.core.files.uploadedfile import InMemoryUploadedFile

            pdf_buffer = convert_docx_to_pdf(file)
            original_name = file.name.rsplit('.', 1)[0] + '.pdf'
            pdf_bytes = pdf_buffer.read()

            converted_file = InMemoryUploadedFile(
                file=io.BytesIO(pdf_bytes),
                field_name='file',
                name=original_name,
                content_type='application/pdf',
                size=len(pdf_bytes),
                charset=None,
            )
            validated_data['file'] = converted_file
            validated_data['original_filename'] = file.name   # Keep original .docx name for display
            validated_data['file_size'] = len(pdf_bytes)
            validated_data['file_hash'] = _hash_bytes(pdf_bytes)
        else:
            validated_data['original_filename'] = file.name
            validated_data['file_size'] = file.size
            validated_data['file_hash'] = hash_file(file)

        return super().create(validated_data)


def _hash_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


class DocumentSerializer(serializers.ModelSerializer):
    """Read serializer — used for listing, retrieving, and tamper-check responses."""
    uploaded_by_email = serializers.EmailField(
        source='uploaded_by.email',
        read_only=True
    )
    # Expose the file URL so the frontend can pass it to PlaceFieldsUI
    file = serializers.SerializerMethodField()

    def get_file(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    class Meta:
        model = Document
        fields = ['id', 'original_filename', 'file', 'file_size', 'file_hash',
                  'status', 'uploaded_by_email', 'created_at']


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for DocumentTemplate (Phase 7.33)."""
    document_url = serializers.SerializerMethodField()
    document_name = serializers.CharField(source='document.original_filename', read_only=True)

    class Meta:
        from .models import DocumentTemplate
        model = DocumentTemplate
        fields = ['id', 'name', 'description', 'version', 'is_locked', 'use_count',
                  'document', 'document_url', 'document_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'use_count', 'created_at', 'updated_at']

    def get_document_url(self, obj):
        request = self.context.get('request')
        if request and obj.document and obj.document.file:
            return request.build_absolute_uri(obj.document.file.url)
        return obj.document.file.url if (obj.document and obj.document.file) else None