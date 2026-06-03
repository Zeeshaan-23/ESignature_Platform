# signing/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:token>/', views.SigningAccessView.as_view(), name='signing-access'),
    path('<uuid:token>/submit/', views.SigningSubmitView.as_view(), name='signing-submit'),
    path('<uuid:token>/decline/', views.SigningDeclineView.as_view(), name='signing-decline'),
]