# packages/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.PackageListView.as_view(), name='package-list'),
    path('create/', views.PackageCreateView.as_view(), name='package-create'),
    path('<uuid:pk>/send/', views.SendPackageView.as_view(), name='package-send'),
    path('<uuid:pk>/', views.PackageDetailView.as_view(), name='package-detail'),
    path('<uuid:pk>/cancel/', views.PackageCancelView.as_view(), name='package-cancel'),
]