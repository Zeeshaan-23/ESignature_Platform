from django.contrib import admin

# Register your models here.
# packages/admin.py
from .models import Package, Recipient


class RecipientInline(admin.TabularInline):
    model = Recipient
    extra = 0
    readonly_fields = ['signing_token', 'signed_at', 'created_at']


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'status', 'routing_mode', 'created_at']
    list_filter = ['status', 'routing_mode']
    search_fields = ['subject', 'sender__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [RecipientInline]


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'role', 'status', 'signing_order', 'package']
    list_filter = ['role', 'status']
    search_fields = ['name', 'email']
    readonly_fields = ['signing_token', 'signed_at']