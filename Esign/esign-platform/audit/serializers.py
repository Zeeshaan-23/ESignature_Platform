# audit/serializers.py

from rest_framework import serializers
from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source='actor.email', 
        read_only=True, 
        default=None
    )
    recipient_email = serializers.EmailField(
        source='recipient.email', 
        read_only=True, 
        default=None
    )

    class Meta:
        model = AuditEvent
        fields = [
            'id', 'event_type', 'actor_email',
            'recipient_email', 'ip_address',
            'metadata', 'created_at'
        ]