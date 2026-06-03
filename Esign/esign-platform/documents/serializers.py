# documents/serializers.py

from rest_framework import serializers
from django.conf import settings
from .models import Document
from .utils import hash_file

ALLOWED_EXTENSIONS = ['pdf']

class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'original_filename', 'file', 'file_size', 
                  'file_hash', 'status', 'created_at']
        read_only_fields = ['id', 'original_filename', 'file_size', 
                            'file_hash', 'status', 'created_at']

    def validate_file(self, file):
        # Check file extension
        ext = file.name.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Check file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        return file

    def create(self, validated_data):
        file = validated_data['file']

        # These fields are derived from the file — not sent by the client
        validated_data['original_filename'] = file.name
        validated_data['file_size'] = file.size
        validated_data['file_hash'] = hash_file(file)

        return super().create(validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    """Read serializer — used for listing and retrieving documents."""
    uploaded_by_email = serializers.EmailField(
        source='uploaded_by.email', 
        read_only=True
    )

    class Meta:
        model = Document
        fields = ['id', 'original_filename', 'file_size', 'file_hash',
                  'status', 'uploaded_by_email', 'created_at']