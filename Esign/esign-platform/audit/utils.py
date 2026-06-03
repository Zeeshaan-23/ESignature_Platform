# audit/utils.py

from .models import AuditEvent


def log_event(event_type, package, recipient=None, actor=None, 
               ip_address=None, metadata=None):
    """
    Central function for creating audit events.
    Call this from any view where something significant happens.
    """
    event = AuditEvent.objects.create(
        event_type=event_type,
        package=package,
        recipient=recipient,
        actor=actor,
        ip_address=ip_address,
        metadata=metadata or {}
    )

    # Dispatch webhooks if package exists
    if package and hasattr(package, 'sender'):
        from webhooks.models import Webhook
        from webhooks.tasks import dispatch_webhook
        
        webhooks = Webhook.objects.filter(
            user=package.sender,
            is_active=True,
            events__contains=event_type
        )
        
        payload = {
            'event_type': event_type,
            'package_id': str(package.id),
            'timestamp': event.created_at.isoformat(),
            'metadata': event.metadata,
        }
        if recipient:
            payload['recipient_id'] = str(recipient.id)
            payload['recipient_email'] = recipient.email
        
        for wh in webhooks:
            dispatch_webhook.delay(str(wh.id), event_type, payload)
            
    return event