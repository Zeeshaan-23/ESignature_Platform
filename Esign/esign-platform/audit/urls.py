# audit/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('packages/<uuid:package_id>/', 
         views.PackageAuditView.as_view(), 
         name='package-audit'),
    path('packages/<uuid:package_id>/export/csv/', 
         views.PackageAuditExportCSVView.as_view(), 
         name='package-audit-export-csv'),
    path('packages/<uuid:package_id>/export/json/', 
         views.PackageAuditExportJSONView.as_view(), 
         name='package-audit-export-json'),
]