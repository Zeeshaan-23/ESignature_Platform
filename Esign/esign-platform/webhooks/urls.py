from django.urls import path
from . import views

urlpatterns = [
    path('', views.WebhookListCreateView.as_view(), name='webhook-list-create'),
    path('<uuid:pk>/', views.WebhookDetailView.as_view(), name='webhook-detail'),
    path('<uuid:webhook_id>/deliveries/', views.WebhookDeliveryListView.as_view(), name='webhook-deliveries'),
]
