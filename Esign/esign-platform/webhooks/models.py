from django.db import models
from django.conf import settings
import uuid

class Webhook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='webhooks')
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=255, blank=True, help_text="Used to sign webhook payloads")
    is_active = models.BooleanField(default=True)
    events = models.JSONField(default=list, help_text="List of events to subscribe to, e.g. ['package.completed']")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Webhook {self.url} for {self.user.email}"

class WebhookDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery to {self.webhook.url} - {self.event_type} - Success: {self.success}"
