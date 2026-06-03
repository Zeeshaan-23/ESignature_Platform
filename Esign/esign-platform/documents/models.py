# documents/models.py

import uuid
import hashlib
from django.db import models
from django.conf import settings


def document_upload_path(instance, filename):
    """
    Generates a structured storage path per user.
    Result: uploads/documents/<user_id>/<filename>
    Using user ID in path prevents filename collisions between users.
    """
    return f"uploads/documents/{instance.uploaded_by.id}/{filename}"


class Document(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        ARCHIVED = 'ARCHIVED', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ForeignKey links every document to a user who uploaded it
    # on_delete=CASCADE means: if the user is deleted, their documents go too
    # related_name lets you do user.documents.all() later
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_hash = models.CharField(max_length=64, help_text="SHA-256 hash for tamper detection")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class DocumentTemplate(models.Model):
    """
    Phase 7.33 — Document templates.
    A named, optionally locked template that wraps an uploaded Document.
    When used, it spawns a new Document copy for signing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_templates'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name='templates',
        help_text='The source document this template is based on.'
    )

    name = models.CharField(max_length=200, help_text='Human-friendly template name.')
    description = models.TextField(blank=True, default='')

    # Versioning — auto-incremented by the application when the template file is updated
    version = models.PositiveIntegerField(default=1)

    # Locking — a locked template cannot be modified or deleted
    is_locked = models.BooleanField(default=False)

    # Track how many packages have been created from this template
    use_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version}"