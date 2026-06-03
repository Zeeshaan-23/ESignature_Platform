from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Webhook, WebhookDelivery
from .serializers import WebhookSerializer, WebhookDeliverySerializer

class WebhookListCreateView(generics.ListCreateAPIView):
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Webhook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WebhookDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Webhook.objects.filter(user=self.request.user)

class WebhookDeliveryListView(generics.ListAPIView):
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebhookDelivery.objects.filter(
            webhook__user=self.request.user,
            webhook_id=self.kwargs['webhook_id']
        ).order_by('-created_at')
