from django.test import TestCase

# Create your tests here.
# signing/tests.py

import pytest
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from packages.models import Package, Recipient


def make_pdf():
    return SimpleUploadedFile(
        'test.pdf',
        b'%PDF-1.4 fake pdf content',
        content_type='application/pdf'
    )


@pytest.fixture
def uploaded_document(auth_client):
    res = auth_client.post(
        '/api/documents/upload/',
        {'file': make_pdf()},
        format='multipart'
    )
    return res.data


@pytest.fixture
def sent_package(auth_client, uploaded_document):
    res = auth_client.post('/api/packages/create/', {
        'subject': 'Expiry Test',
        'message': 'Please sign',
        'document': uploaded_document['id'],
        'routing_mode': 'SERIAL',
        'recipients': [{
            'name': 'John Doe',
            'email': 'john@test.com',
            'role': 'SIGNER',
            'signing_order': 1
        }]
    }, format='json')
    package_id = res.data['id']
    auth_client.post(f'/api/packages/{package_id}/send/')
    return Package.objects.get(id=package_id)


@pytest.mark.django_db
class TestSigningExpiry:

    def test_submit_after_expiry_returns_410(
        self, api_client, sent_package
    ):
        # Backdate expiry so package is already expired
        sent_package.expires_at = timezone.now() - timedelta(seconds=1)
        sent_package.save()

        token = sent_package.recipients.first().signing_token
        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        assert res.status_code == 410
        sent_package.refresh_from_db()
        assert sent_package.status == Package.Status.EXPIRED

    def test_submit_marks_recipients_expired(
        self, api_client, sent_package
    ):
        sent_package.expires_at = timezone.now() - timedelta(seconds=1)
        sent_package.save()

        token = sent_package.recipients.first().signing_token
        api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        statuses = list(
            sent_package.recipients.values_list('status', flat=True)
        )
        assert all(s == Recipient.Status.EXPIRED for s in statuses)

    def test_submit_before_expiry_succeeds(
        self, api_client, sent_package
    ):
        sent_package.expires_at = timezone.now() + timedelta(hours=1)
        sent_package.save()

        token = sent_package.recipients.first().signing_token
        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        assert res.status_code == 200

    def test_submit_no_expiry_set_succeeds(
        self, api_client, sent_package
    ):
        # expires_at is None — should never block signing
        assert sent_package.expires_at is None

        token = sent_package.recipients.first().signing_token
        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        assert res.status_code == 200

@pytest.mark.django_db
class TestSigningDecline:

    def test_decline_success(self, api_client, sent_package):
        token = sent_package.recipients.first().signing_token
        res = api_client.post(f'/api/signing/{token}/decline/', {
            'reason': 'I do not agree with the terms.'
        }, format='json')

        assert res.status_code == 200
        sent_package.refresh_from_db()
        assert sent_package.status == Package.Status.DECLINED

    def test_decline_marks_recipient_declined(self, api_client, sent_package):
        token = sent_package.recipients.first().signing_token
        api_client.post(f'/api/signing/{token}/decline/', {}, format='json')

        recipient = sent_package.recipients.first()
        recipient.refresh_from_db()
        assert recipient.status == Recipient.Status.DECLINED

    def test_cannot_decline_twice(self, api_client, sent_package):
        token = sent_package.recipients.first().signing_token
        api_client.post(f'/api/signing/{token}/decline/', {}, format='json')
        res = api_client.post(f'/api/signing/{token}/decline/', {}, format='json')

        assert res.status_code == 400

    def test_cannot_decline_after_signing(self, api_client, sent_package):
        token = sent_package.recipients.first().signing_token
        api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        res = api_client.post(f'/api/signing/{token}/decline/', {}, format='json')
        assert res.status_code == 400

    def test_decline_invalid_token(self, api_client):
        import uuid
        res = api_client.post(
            f'/api/signing/{uuid.uuid4()}/decline/', {}, format='json'
        )
        assert res.status_code == 404

@pytest.mark.django_db
class TestSigningThrottle:

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    def test_access_throttled_after_limit(self, api_client, sent_package, settings):
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['signing_token'] = '3/minute'
        token = sent_package.recipients.first().signing_token

        for _ in range(3):
            res = api_client.get(f'/api/signing/{token}/')
            assert res.status_code != 429

        res = api_client.get(f'/api/signing/{token}/')
        assert res.status_code == 429

    def test_submit_throttled_after_limit(self, api_client, sent_package, settings):
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['signing_token'] = '3/minute'
        token = sent_package.recipients.first().signing_token

        for _ in range(3):
            api_client.post(f'/api/signing/{token}/submit/', {
                'signature_data': 'data:image/png;base64,abc123'
            }, format='json')

        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')
        assert res.status_code == 429

    def test_decline_throttled_after_limit(self, api_client, sent_package, settings):
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['signing_token'] = '3/minute'
        token = sent_package.recipients.first().signing_token

        for _ in range(3):
            api_client.post(f'/api/signing/{token}/decline/', {}, format='json')

        res = api_client.post(f'/api/signing/{token}/decline/', {}, format='json')
        assert res.status_code == 429

    def test_different_tokens_independent_counters(
        self, api_client, auth_client, sent_package, settings
    ):
        """Two different tokens should have separate throttle buckets."""
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['signing_token'] = '2/minute'

        # Create a second package with a second token
        res = auth_client.post('/api/documents/upload/',
            {'file': make_pdf()}, format='multipart')
        doc_id = res.data['id']
        res = auth_client.post('/api/packages/create/', {
            'subject': 'Second',
            'message': 'Sign',
            'document': doc_id,
            'routing_mode': 'SERIAL',
            'recipients': [{'name': 'Jane', 'email': 'jane@test.com',
                            'role': 'SIGNER', 'signing_order': 1}]
        }, format='json')
        pkg2_id = res.data['id']
        auth_client.post(f'/api/packages/{pkg2_id}/send/')
        pkg2 = Package.objects.get(id=pkg2_id)

        token1 = sent_package.recipients.first().signing_token
        token2 = pkg2.recipients.first().signing_token

        # exhaust token1
        for _ in range(2):
            api_client.get(f'/api/signing/{token1}/')
        res = api_client.get(f'/api/signing/{token1}/')
        assert res.status_code == 429

        # token2 should still be allowed
        res = api_client.get(f'/api/signing/{token2}/')
        assert res.status_code != 429