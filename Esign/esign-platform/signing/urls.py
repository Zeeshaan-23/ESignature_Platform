# signing/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:token>/', views.SigningAccessView.as_view(), name='signing-access'),
    path('<uuid:token>/submit/', views.SigningSubmitView.as_view(), name='signing-submit'),
    path('<uuid:token>/decline/', views.SigningDeclineView.as_view(), name='signing-decline'),
    # Phase 6
    path('<uuid:token>/return/', views.SigningReturnView.as_view(), name='signing-return'),
    path('<uuid:token>/delegate/', views.SigningDelegateView.as_view(), name='signing-delegate'),
]