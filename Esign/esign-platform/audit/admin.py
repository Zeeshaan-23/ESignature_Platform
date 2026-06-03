from django.contrib import admin

# Register your models here.
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'package', 'actor', 'recipient', 
                    'ip_address', 'created_at']
    list_filter = ['event_type']
    search_fields = ['package__subject', 'actor__email', 'recipient__email']
    readonly_fields = ['id', 'event_type', 'actor', 'package', 
                       'recipient', 'ip_address', 'metadata', 'created_at']

    # Prevent anyone from adding or deleting audit events through admin
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False