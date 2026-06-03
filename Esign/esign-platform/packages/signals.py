# packages/signals.py

import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Package


@receiver(post_delete, sender=Package)
def delete_signed_file(sender, instance, **kwargs):
    """Delete signed PDF from disk when a package is deleted."""
    if instance.signed_file:
        if os.path.isfile(instance.signed_file.path):
            os.remove(instance.signed_file.path)