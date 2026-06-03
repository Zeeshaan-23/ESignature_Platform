import json
import hmac
import hashlib
import requests
from celery import shared_task
from .models import Webhook, WebhookDelivery

@shared_task(bind=True, max_retries=3)
def dispatch_webhook(self, webhook_id, event_type, payload):
    try:
        webhook = Webhook.objects.get(id=webhook_id)
    except Webhook.DoesNotExist:
        return

    if not webhook.is_active or event_type not in webhook.events:
        return

    payload_json = json.dumps(payload)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'eSign-Webhook/1.0',
        'X-eSign-Event': event_type,
    }

    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        headers['X-eSign-Signature'] = f"sha256={signature}"

    delivery = WebhookDelivery.objects.create(
        webhook=webhook,
        event_type=event_type,
        payload=payload
    )

    try:
        response = requests.post(
            webhook.url,
            data=payload_json,
            headers=headers,
            timeout=10
        )
        delivery.status_code = response.status_code
        delivery.response_body = response.text[:2000]
        delivery.success = 200 <= response.status_code < 300
        delivery.save()

        if not delivery.success:
            self.retry(countdown=60 * (2 ** self.request.retries))

    except requests.RequestException as e:
        delivery.response_body = str(e)[:2000]
        delivery.success = False
        delivery.save()
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
