from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings

class Package(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        EXPIRED = 'EXPIRED', 'Expired'
        DECLINED = 'DECLINED', 'Declined'
        CANCELLED = 'CANCELLED', 'Cancelled'
        RETURNED = 'RETURNED', 'Returned'  # Approver/reviewer returned for rework

    class RoutingMode(models.TextChoices):
        SERIAL = 'SERIAL', 'Serial'       # one at a time, in order
        PARALLEL = 'PARALLEL', 'Parallel' # everyone signs simultaneously

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who created this signing request
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_packages'
    )

    # The document being signed
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.PROTECT,  # PROTECT: prevent deleting a doc that's in a package
        related_name='packages'
    )

    subject = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    routing_mode = models.CharField(
        max_length=20,
        choices=RoutingMode.choices,
        default=RoutingMode.SERIAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    signed_file = models.FileField(
        upload_to='signed_documents/',
        null=True,
        blank=True,
        help_text="Generated signed PDF after all parties have signed"
    )

    expires_at = models.DateTimeField(null=True, blank=True)
    reminder_days = models.PositiveIntegerField(default=0, help_text="Send reminders every N days. 0 disables reminders.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.status})"


class Recipient(models.Model):

    class Role(models.TextChoices):
        SIGNER = 'SIGNER', 'Signer'
        APPROVER = 'APPROVER', 'Approver'
        CC = 'CC', 'CC'               # receives a copy, no action needed

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'       # not yet sent to them
        SENT = 'SENT', 'Sent'               # invite email sent
        VIEWED = 'VIEWED', 'Viewed'         # opened the signing link
        SIGNED = 'SIGNED', 'Signed'         # completed signing
        APPROVED = 'APPROVED', 'Approved'   # approver approved (no signature needed)
        RETURNED = 'RETURNED', 'Returned'   # approver returned for rework
        DELEGATED = 'DELEGATED', 'Delegated' # signer delegated to someone else
        DECLINED = 'DECLINED', 'Declined'   # refused to sign
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'      # time ran out

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Every recipient belongs to exactly one package
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name='recipients'
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    # Serial routing: order=1 signs before order=2
    # Parallel routing: order is ignored, all sign simultaneously
    signing_order = models.PositiveIntegerField(default=1)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SIGNER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)


    # Unique token for the signing link — no account required
    # e.g. /sign/<signing_token>/ is how the signer accesses the document
    signing_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    signed_at = models.DateTimeField(null=True, blank=True)
    signature_data = models.TextField(blank=True, null=True, help_text="Base64 encoded signature image")

    # Delegation: when this recipient delegates, we track the new recipient
    delegated_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='delegated_from',
        help_text="If this recipient delegated their signing, points to the new recipient."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['signing_order', 'created_at']
        # NOTE: unique_together removed to allow delegation (new recipient with same email
        # in a different slot). Uniqueness for non-delegated recipients is enforced in the view.

    def __str__(self):
        return f"{self.name} <{self.email}> - {self.role} ({self.status})"


class SignatureField(models.Model):
    """
    Represents a signature box placed by the sender on a specific page of the document.
    Coordinates are stored as percentages (0.0 – 1.0) of page width/height so they
    remain consistent regardless of screen size, zoom level, or PDF dimensions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name='signature_fields'
    )
    recipient = models.ForeignKey(
        Recipient,
        on_delete=models.CASCADE,
        related_name='signature_fields'
    )

    page_number = models.PositiveIntegerField(
        default=1,
        help_text="1-indexed page number in the PDF"
    )

    # All coordinates are percentages of the page dimensions (0.0 – 1.0)
    x = models.FloatField(help_text="Left edge as fraction of page width")
    y = models.FloatField(help_text="Top edge as fraction of page height")
    width = models.FloatField(help_text="Width as fraction of page width", default=0.2)
    height = models.FloatField(help_text="Height as fraction of page height", default=0.07)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page_number', 'y', 'x']

    def __str__(self):
        return (
            f"Field for {self.recipient.email} on page {self.page_number} "
            f"of package {self.package.subject}"
        )