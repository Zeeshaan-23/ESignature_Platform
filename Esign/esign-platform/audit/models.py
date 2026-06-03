from django.db import models

# Create your models here.
import uuid
from django.conf import settings


class AuditEvent(models.Model):

    class EventType(models.TextChoices):
        DOCUMENT_UPLOADED   = 'document.uploaded',   'Document Uploaded'
        PACKAGE_CREATED     = 'package.created',     'Package Created'
        PACKAGE_SENT        = 'package.sent',        'Package Sent'
        SIGNING_VIEWED      = 'signing.viewed',      'Signing Link Viewed'
        SIGNING_SIGNED      = 'signing.signed',      'Document Signed'
        PACKAGE_COMPLETED   = 'package.completed',   'Package Completed'
        PACKAGE_EXPIRED     = 'package.expired',     'Package Expired'
        PACKAGE_DECLINED    = 'package.declined',    'Package Declined'
        PACKAGE_CANCELLED   = 'package.cancelled',   'Package Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_type = models.CharField(max_length=50, choices=EventType.choices)

    # Who performed this action — null for signers (no account)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_events'
    )

    # Always link to the package for easy filtering
    package = models.ForeignKey(
        'packages.Package',
        on_delete=models.CASCADE,
        related_name='audit_events',
        null=True,
        blank=True,
    )

    # For signer events — link to the specific recipient
    recipient = models.ForeignKey(
        'packages.Recipient',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_events'
    )

    # IP address of whoever triggered this event
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Any extra context stored as JSON
    # e.g. {"filename": "contract.pdf", "file_size": 25000}
    metadata = models.JSONField(default=dict, blank=True)

    # Immutable timestamp — never updated after creation
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # chronological order matters for audit logs

    def __str__(self):
        return f"{self.event_type} — {self.created_at}"