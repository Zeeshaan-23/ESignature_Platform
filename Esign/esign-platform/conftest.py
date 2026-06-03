# conftest.py

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sender_user(db):
    return User.objects.create_user(
        email='sender@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Sender',
        role='SENDER'
    )


@pytest.fixture
def another_user(db):
    return User.objects.create_user(
        email='another@test.com',
        password='testpass123',
        first_name='Another',
        last_name='User',
        role='SENDER'
    )


@pytest.fixture
def auth_client(api_client, sender_user):
    """Authenticated API client."""
    api_client.force_authenticate(user=sender_user)
    return api_client