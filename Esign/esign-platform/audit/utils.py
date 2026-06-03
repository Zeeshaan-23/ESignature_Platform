# audit/utils.py

from .models import AuditEvent


def log_event(event_type, package, recipient=None, actor=None, 
               ip_address=None, metadata=None):
    """
    Central function for creating audit events.
    Call this from any view where something significant happens.
    """
    AuditEvent.objects.create(
        event_type=event_type,
        package=package,
        recipient=recipient,
        actor=actor,
        ip_address=ip_address,
        metadata=metadata or {}
    )