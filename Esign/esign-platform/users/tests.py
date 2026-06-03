from django.test import TestCase

# Create your tests here.
# users/tests.py

import pytest
from django.urls import reverse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch

@pytest.mark.django_db
class TestRegistration:

    def test_register_success(self, api_client):
        res = api_client.post('/api/users/register/', {
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'testpass123',
            'role': 'SENDER'
        })
        assert res.status_code == 201
        assert 'tokens' in res.data
        assert 'access' in res.data['tokens']
        assert 'refresh' in res.data['tokens']

    def test_register_duplicate_email(self, api_client, sender_user):
        res = api_client.post('/api/users/register/', {
            'email': 'sender@test.com',  # already exists
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123',
            'role': 'SENDER'
        })
        assert res.status_code == 400

    def test_register_missing_fields(self, api_client):
        res = api_client.post('/api/users/register/', {
            'email': 'incomplete@test.com'
        })
        assert res.status_code == 400


@pytest.mark.django_db
class TestLogin:

    def test_login_success(self, api_client, sender_user):
        res = api_client.post('/api/users/login/', {
            'email': 'sender@test.com',
            'password': 'testpass123'
        })
        assert res.status_code == 200
        assert 'access' in res.data
        assert 'refresh' in res.data

    def test_login_wrong_password(self, api_client, sender_user):
        res = api_client.post('/api/users/login/', {
            'email': 'sender@test.com',
            'password': 'wrongpassword'
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        res = api_client.post('/api/users/login/', {
            'email': 'ghost@test.com',
            'password': 'testpass123'
        })
        assert res.status_code == 401


@pytest.mark.django_db
class TestMeEndpoint:

    def test_me_authenticated(self, auth_client, sender_user):
        res = auth_client.get('/api/users/me/')
        assert res.status_code == 200
        assert res.data['email'] == sender_user.email

    def test_me_unauthenticated(self, api_client):
        res = api_client.get('/api/users/me/')
        assert res.status_code == 401

@pytest.mark.django_db
class TestHealthCheck:

    def test_health_check_returns_200(self, api_client):
        res = api_client.get('/api/health/')
        assert res.status_code == 200

        data = res.json()
        assert data['status'] == 'ok'
        assert data['db'] == 'ok'

@pytest.mark.django_db
class TestCSPHeaders:

    def test_csp_header_present_on_api_response(self, api_client):
        res = api_client.get('/api/health/')
        assert 'Content-Security-Policy' in res.headers

    def test_csp_default_src_none(self, api_client):
        res = api_client.get('/api/health/')
        csp = res.headers['Content-Security-Policy']
        assert "default-src 'none'" in csp

    def test_csp_script_src_self(self, api_client):
        res = api_client.get('/api/health/')
        csp = res.headers['Content-Security-Policy']
        assert "script-src 'self'" in csp

    def test_csp_frame_ancestors_none(self, api_client):
        res = api_client.get('/api/health/')
        csp = res.headers['Content-Security-Policy']
        assert "frame-ancestors 'none'" in csp

    def test_csp_connect_src_self(self, api_client):
        res = api_client.get('/api/health/')
        csp = res.headers['Content-Security-Policy']
        assert "connect-src 'self'" in csp

    def test_csp_img_src_includes_data_uri(self, api_client):
        res = api_client.get('/api/health/')
        csp = res.headers['Content-Security-Policy']
        assert "img-src" in csp
        assert "data:" in csp

    def test_csp_report_only_header_absent(self, api_client):
        # SECURE_CSP_REPORT_ONLY = {} means report-only header not set
        res = api_client.get('/api/health/')
        assert 'Content-Security-Policy-Report-Only' not in res.headers

@pytest.mark.django_db
class TestPasswordReset:

    @patch('users.views.send_password_reset_email.delay')
    def test_request_known_email_returns_200(self, mock_task, api_client, sender_user):
        res = api_client.post('/api/users/password-reset/', {
            'email': 'sender@test.com'
        })
        assert res.status_code == 200
        assert 'message' in res.data

    @patch('users.views.send_password_reset_email.delay')
    def test_request_unknown_email_still_returns_200(self, mock_task, api_client):
        res = api_client.post('/api/users/password-reset/', {
            'email': 'nobody@test.com'
        })
        assert res.status_code == 200

    @patch('users.views.send_password_reset_email.delay')
    def test_request_triggers_celery_task(self, mock_task, api_client, sender_user):
        api_client.post('/api/users/password-reset/', {
            'email': 'sender@test.com'
        })
        assert mock_task.called
        call_args = mock_task.call_args[0]
        assert call_args[0] == 'sender@test.com'
        assert 'reset-password' in call_args[1]

    @patch('users.views.send_password_reset_email.delay')
    def test_request_unknown_email_does_not_trigger_task(self, mock_task, api_client):
        api_client.post('/api/users/password-reset/', {
            'email': 'nobody@test.com'
        })
        mock_task.assert_not_called()

    def test_request_invalid_email_format_returns_400(self, api_client):
        res = api_client.post('/api/users/password-reset/', {
            'email': 'not-an-email'
        })
        assert res.status_code == 400

    def test_confirm_valid_token_resets_password(self, api_client, sender_user):
        uid = urlsafe_base64_encode(force_bytes(sender_user.pk))
        token = PasswordResetTokenGenerator().make_token(sender_user)

        res = api_client.post('/api/users/password-reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'newpassword456'
        })
        assert res.status_code == 200

        login_res = api_client.post('/api/users/login/', {
            'email': 'sender@test.com',
            'password': 'newpassword456'
        })
        assert login_res.status_code == 200

    def test_confirm_invalid_token_returns_400(self, api_client, sender_user):
        uid = urlsafe_base64_encode(force_bytes(sender_user.pk))

        res = api_client.post('/api/users/password-reset/confirm/', {
            'uid': uid,
            'token': 'invalid-token',
            'new_password': 'newpassword456'
        })
        assert res.status_code == 400

    def test_confirm_invalid_uid_returns_400(self, api_client):
        res = api_client.post('/api/users/password-reset/confirm/', {
            'uid': 'not-a-valid-uid',
            'token': 'sometoken',
            'new_password': 'newpassword456'
        })
        assert res.status_code == 400

    def test_confirm_token_used_twice_returns_400(self, api_client, sender_user):
        uid = urlsafe_base64_encode(force_bytes(sender_user.pk))
        token = PasswordResetTokenGenerator().make_token(sender_user)

        api_client.post('/api/users/password-reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'newpassword456'
        })
        res = api_client.post('/api/users/password-reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'yetanotherpass789'
        })
        assert res.status_code == 400

    def test_confirm_weak_password_returns_400(self, api_client, sender_user):
        uid = urlsafe_base64_encode(force_bytes(sender_user.pk))
        token = PasswordResetTokenGenerator().make_token(sender_user)

        res = api_client.post('/api/users/password-reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': '123'
        })
        assert res.status_code == 400