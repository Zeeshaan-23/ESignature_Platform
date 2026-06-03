from django.test import TestCase

# Create your tests here.
# documents/tests.py

import pytest
import io
from django.core.files.uploadedfile import SimpleUploadedFile


def make_pdf():
    """Create a minimal fake PDF file for testing."""
    return SimpleUploadedFile(
        'test.pdf',
        b'%PDF-1.4 fake pdf content',
        content_type='application/pdf'
    )


def make_txt():
    return SimpleUploadedFile(
        'test.txt',
        b'plain text content',
        content_type='text/plain'
    )


@pytest.mark.django_db
class TestDocumentUpload:

    def test_upload_success(self, auth_client):
        res = auth_client.post(
            '/api/documents/upload/',
            {'file': make_pdf()},
            format='multipart'
        )
        assert res.status_code == 201
        assert res.data['original_filename'] == 'test.pdf'
        assert 'file_hash' in res.data
        assert res.data['status'] == 'DRAFT'

    def test_upload_invalid_type(self, auth_client):
        res = auth_client.post(
            '/api/documents/upload/',
            {'file': make_txt()},
            format='multipart'
        )
        assert res.status_code == 400
    
    def test_upload_file_too_large(self, auth_client, settings):
            settings.MAX_UPLOAD_SIZE_MB = 1
            big_file = SimpleUploadedFile(
                'big.pdf',
                b'%PDF-1.4 ' + b'x' * (1 * 1024 * 1024 + 1),
                content_type='application/pdf'
            )
            res = auth_client.post(
                '/api/documents/upload/',
                {'file': big_file},
                format='multipart'
            )
            assert res.status_code == 400
            assert 'Maximum size is 1MB' in str(res.data)

    def test_upload_docx_rejected(self, auth_client):
        docx_file = SimpleUploadedFile(
            'test.docx',
            b'PK fake docx content',
            content_type='application/vnd.openxmlformats-officedocument'
                          '.wordprocessingml.document'
        )
        res = auth_client.post(
            '/api/documents/upload/',
            {'file': docx_file},
            format='multipart'
        )
        assert res.status_code == 400

    def test_upload_unauthenticated(self, api_client):
        res = api_client.post(
            '/api/documents/upload/',
            {'file': make_pdf()},
            format='multipart'
        )
        assert res.status_code == 401

    def test_list_only_own_documents(
        self, auth_client, another_user, api_client
    ):
        # Upload with first user
        auth_client.post(
            '/api/documents/upload/',
            {'file': make_pdf()},
            format='multipart'
        )

        # List with second user
        api_client.force_authenticate(user=another_user)
        res = api_client.get('/api/documents/')
        assert res.status_code == 200
        assert res.data['count'] == 0