from django.contrib import admin

# Register your models here.
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'uploaded_by', 'status', 'file_size', 'created_at']
    list_filter = ['status']
    search_fields = ['original_filename', 'uploaded_by__email']
    readonly_fields = ['file_hash', 'file_size', 'created_at', 'updated_at']