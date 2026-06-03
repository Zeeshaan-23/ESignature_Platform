from django.test import TestCase

# Create your tests here.
# packages/tests.py

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from packages.models import Package, Recipient


def make_pdf():
    return SimpleUploadedFile(
        'test.pdf',
        b'%PDF-1.4 fake pdf content',
        content_type='application/pdf'
    )


@pytest.fixture
def uploaded_document(auth_client, sender_user):
    res = auth_client.post(
        '/api/documents/upload/',
        {'file': make_pdf()},
        format='multipart'
    )
    return res.data


@pytest.fixture
def created_package(auth_client, uploaded_document):
    res = auth_client.post('/api/packages/create/', {
        'subject': 'Test Package',
        'message': 'Please sign',
        'document': uploaded_document['id'],
        'routing_mode': 'SERIAL',
        'recipients': [
            {
                'name': 'John Doe',
                'email': 'john@test.com',
                'role': 'SIGNER',
                'signing_order': 1
            }
        ]
    }, format='json')
    return res.data


@pytest.mark.django_db
class TestPackageCreate:

    def test_create_success(self, auth_client, uploaded_document):
        res = auth_client.post('/api/packages/create/', {
            'subject': 'Test Package',
            'message': 'Please sign',
            'document': uploaded_document['id'],
            'routing_mode': 'SERIAL',
            'recipients': [
                {
                    'name': 'John Doe',
                    'email': 'john@test.com',
                    'role': 'SIGNER',
                    'signing_order': 1
                }
            ]
        }, format='json')
        assert res.status_code == 201
        assert res.data['status'] == 'DRAFT'
        assert len(res.data['recipients']) == 1

    def test_create_no_recipients(self, auth_client, uploaded_document):
        res = auth_client.post('/api/packages/create/', {
            'subject': 'Test',
            'document': uploaded_document['id'],
            'routing_mode': 'SERIAL',
            'recipients': []
        }, format='json')
        assert res.status_code == 400

    def test_create_duplicate_recipient_emails(
        self, auth_client, uploaded_document
    ):
        res = auth_client.post('/api/packages/create/', {
            'subject': 'Test',
            'document': uploaded_document['id'],
            'routing_mode': 'SERIAL',
            'recipients': [
                {
                    'name': 'John',
                    'email': 'john@test.com',
                    'role': 'SIGNER',
                    'signing_order': 1
                },
                {
                    'name': 'John Again',
                    'email': 'john@test.com',
                    'role': 'SIGNER',
                    'signing_order': 2
                }
            ]
        }, format='json')
        assert res.status_code == 400

    def test_cannot_use_another_users_document(
        self, api_client, another_user, uploaded_document
    ):
        api_client.force_authenticate(user=another_user)
        res = api_client.post('/api/packages/create/', {
            'subject': 'Test',
            'document': uploaded_document['id'],
            'routing_mode': 'SERIAL',
            'recipients': [
                {
                    'name': 'John',
                    'email': 'john@test.com',
                    'role': 'SIGNER',
                    'signing_order': 1
                }
            ]
        }, format='json')
        assert res.status_code == 400


@pytest.mark.django_db
class TestPackageSend:

    def test_send_success(self, auth_client, created_package):
        res = auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )
        assert res.status_code == 200
        assert res.data['status'] == 'SENT'

    def test_cannot_send_twice(self, auth_client, created_package):
        auth_client.post(f'/api/packages/{created_package["id"]}/send/')
        res = auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )
        assert res.status_code == 400

    def test_serial_routing_only_first_recipient_sent(
        self, auth_client, uploaded_document
    ):
        res = auth_client.post('/api/packages/create/', {
            'subject': 'Serial Test',
            'document': uploaded_document['id'],
            'routing_mode': 'SERIAL',
            'recipients': [
                {
                    'name': 'First',
                    'email': 'first@test.com',
                    'role': 'SIGNER',
                    'signing_order': 1
                },
                {
                    'name': 'Second',
                    'email': 'second@test.com',
                    'role': 'SIGNER',
                    'signing_order': 2
                }
            ]
        }, format='json')

        package_id = res.data['id']
        auth_client.post(f'/api/packages/{package_id}/send/')

        first = Recipient.objects.get(
            package_id=package_id, email='first@test.com'
        )
        second = Recipient.objects.get(
            package_id=package_id, email='second@test.com'
        )

        assert first.status == 'SENT'
        assert second.status == 'PENDING'


@pytest.mark.django_db
class TestSigningFlow:

    def test_signing_access(self, api_client, auth_client, created_package):
        auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )

        token = Recipient.objects.get(
            package_id=created_package['id']
        ).signing_token

        res = api_client.get(f'/api/signing/{token}/')
        assert res.status_code == 200
        assert 'document' in res.data
        assert 'recipient' in res.data

    def test_signing_submit(self, api_client, auth_client, created_package):
        auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )

        token = Recipient.objects.get(
            package_id=created_package['id']
        ).signing_token

        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        assert res.status_code == 200
        assert res.data['package_status'] == 'COMPLETED'

    def test_cannot_sign_twice(
        self, api_client, auth_client, created_package
    ):
        auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )
        token = Recipient.objects.get(
            package_id=created_package['id']
        ).signing_token

        api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        res = api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        assert res.status_code == 400

    def test_submit_without_signature_data(
        self, api_client, auth_client, created_package
    ):
        auth_client.post(
            f'/api/packages/{created_package["id"]}/send/'
        )
        token = Recipient.objects.get(
            package_id=created_package['id']
        ).signing_token

        res = api_client.post(
            f'/api/signing/{token}/submit/', {}, format='json'
        )
        assert res.status_code == 400

@pytest.mark.django_db
class TestPackageCancel:

    def test_cancel_sent_package(self, auth_client, created_package):
        auth_client.post(f'/api/packages/{created_package["id"]}/send/')
        res = auth_client.post(
            f'/api/packages/{created_package["id"]}/cancel/'
        )
        assert res.status_code == 200
        assert res.data['status'] == 'CANCELLED'

    def test_cancel_draft_package(self, auth_client, created_package):
        res = auth_client.post(
            f'/api/packages/{created_package["id"]}/cancel/'
        )
        assert res.status_code == 200
        assert res.data['status'] == 'CANCELLED'

    def test_cannot_cancel_completed_package(
        self, api_client, auth_client, created_package
    ):
        auth_client.post(f'/api/packages/{created_package["id"]}/send/')
        token = Recipient.objects.get(
            package_id=created_package['id']
        ).signing_token
        api_client.post(f'/api/signing/{token}/submit/', {
            'signature_data': 'data:image/png;base64,abc123'
        }, format='json')

        res = auth_client.post(
            f'/api/packages/{created_package["id"]}/cancel/'
        )
        assert res.status_code == 400

    def test_cannot_cancel_another_users_package(
        self, api_client, another_user, created_package
    ):
        api_client.force_authenticate(user=another_user)
        res = api_client.post(
            f'/api/packages/{created_package["id"]}/cancel/'
        )
        assert res.status_code == 404

    def test_cancel_marks_pending_recipients_declined(
        self, auth_client, created_package
    ):
        auth_client.post(f'/api/packages/{created_package["id"]}/send/')
        auth_client.post(f'/api/packages/{created_package["id"]}/cancel/')

        statuses = list(
            Recipient.objects.filter(
                package_id=created_package['id']
            ).values_list('status', flat=True)
        )
        assert all(s == Recipient.Status.DECLINED for s in statuses)

@pytest.mark.django_db
class TestSignedFileCleanup:

    def test_signed_file_deleted_on_package_delete(
        self, auth_client, created_package
    ):
        import os
        from django.core.files.base import ContentFile

        package = Package.objects.get(id=created_package['id'])
        package.signed_file.save(
            'signed_test.pdf',
            ContentFile(b'%PDF fake signed content'),
            save=True,
        )
        file_path = package.signed_file.path
        assert os.path.isfile(file_path)

        package.delete()

        assert not os.path.isfile(file_path)

    def test_delete_package_without_signed_file_does_not_raise(
        self, auth_client, created_package
    ):
        package = Package.objects.get(id=created_package['id'])
        assert not package.signed_file  # no file attached

        # Should not raise
        package.delete()