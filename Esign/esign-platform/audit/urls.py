# audit/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('packages/<uuid:package_id>/', 
         views.PackageAuditView.as_view(), 
         name='package-audit'),
]