# documents/urls.py

from django.urls import path
from .views import (
    DocumentUploadView, 
    DocumentListView, 
    DocumentDetailView,
    DocumentTamperCheckView,
    DocumentTemplateListCreateView,
    DocumentTemplateDetailView,
    DocumentTemplateCreatePackageView
)

urlpatterns = [
    # Document core
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('', DocumentListView.as_view(), name='document-list'),
    path('<uuid:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('<uuid:pk>/verify/', DocumentTamperCheckView.as_view(), name='document-verify'),

    # Document templates (Phase 7.33)
    path('templates/', DocumentTemplateListCreateView.as_view(), name='template-list'),
    path('templates/<uuid:pk>/', DocumentTemplateDetailView.as_view(), name='template-detail'),
    path('templates/<uuid:pk>/use/', DocumentTemplateCreatePackageView.as_view(), name='template-use'),
]