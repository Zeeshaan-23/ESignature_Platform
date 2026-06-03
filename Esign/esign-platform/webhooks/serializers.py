from rest_framework import serializers
from .models import Webhook, WebhookDelivery

class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ['id', 'url', 'secret', 'is_active', 'events', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ['id', 'webhook', 'event_type', 'status_code', 'success', 'created_at']
        read_only_fields = fields
