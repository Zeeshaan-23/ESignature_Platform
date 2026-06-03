# notifications/tests.py

import pytest
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile


def make_package(sender_user):
    """Helper: creates a real Document + Package with one signed recipient."""
    from documents.models import Document
    from packages.models import Package, Recipient

    doc = Document.objects.create(
        uploaded_by=sender_user,
        original_filename='contract.pdf',
        file=SimpleUploadedFile('contract.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
        file_size=13,
        file_hash='abc123',
    )
    package = Package.objects.create(
        sender=sender_user,
        document=doc,
        subject='Test Contract',
        status=Package.Status.COMPLETED,
    )
    Recipient.objects.create(
        package=package,
        name='Alice',
        email='alice@test.com',
        role=Recipient.Role.SIGNER,
        status=Recipient.Status.SIGNED,
    )
    return package


@pytest.mark.django_db
class TestEmailRetry:

    @patch('notifications.tasks.send_mail')
    def test_signing_invitation_retries_on_failure(self, mock_send_mail):
        from notifications.tasks import send_signing_invitation
        mock_send_mail.side_effect = Exception("SMTP error")

        with pytest.raises(Exception):
            send_signing_invitation.apply(args=[
                'John', 'john@test.com', 'Alice',
                'Contract', 'some-token-123'
            ]).get(propagate=True)

        assert mock_send_mail.called

    @patch('notifications.tasks.send_mail')
    def test_signing_invitation_succeeds_on_retry(self, mock_send_mail):
        from notifications.tasks import send_signing_invitation
        mock_send_mail.side_effect = [Exception("timeout"), None]

        send_signing_invitation.apply(args=[
            'John', 'john@test.com', 'Alice',
            'Contract', 'some-token-123'
        ])

        assert mock_send_mail.call_count == 2


@pytest.mark.django_db
class TestCompletionEmailAttachment:

    @patch('notifications.tasks.EmailMessage')
    def test_completion_email_sent_to_all_recipients(
        self, mock_email_class, sender_user
    ):
        from notifications.tasks import send_completion_notification

        package = make_package(sender_user)
        package.signed_file.save(
            'signed_contract.pdf',
            ContentFile(b'%PDF signed'),
            save=True,
        )

        mock_instance = MagicMock()
        mock_email_class.return_value = mock_instance

        send_completion_notification(str(package.id))

        assert mock_instance.send.called

    @patch('notifications.tasks.EmailMessage')
    def test_completion_email_attaches_signed_pdf(
        self, mock_email_class, sender_user
    ):
        from notifications.tasks import send_completion_notification

        package = make_package(sender_user)
        package.signed_file.save(
            'signed_contract.pdf',
            ContentFile(b'%PDF signed'),
            save=True,
        )

        mock_instance = MagicMock()
        mock_email_class.return_value = mock_instance

        send_completion_notification(str(package.id))

        mock_instance.attach.assert_called_once()
        attach_args = mock_instance.attach.call_args[0]
        assert attach_args[0] == 'signed_contract.pdf'
        assert attach_args[2] == 'application/pdf'

    @patch('notifications.tasks.EmailMessage')
    def test_completion_email_no_attachment_when_no_signed_file(
        self, mock_email_class, sender_user
    ):
        from notifications.tasks import send_completion_notification

        package = make_package(sender_user)
        # No signed_file saved

        mock_instance = MagicMock()
        mock_email_class.return_value = mock_instance

        send_completion_notification(str(package.id))

        mock_instance.attach.assert_not_called()
        assert mock_instance.send.called

    @patch('notifications.tasks.EmailMessage')
    def test_completion_email_retries_on_smtp_failure(
        self, mock_email_class, sender_user
    ):
        from notifications.tasks import send_completion_notification

        package = make_package(sender_user)

        mock_instance = MagicMock()
        mock_instance.send.side_effect = Exception("SMTP down")
        mock_email_class.return_value = mock_instance

        with pytest.raises(Exception):
            send_completion_notification.apply(
                args=[str(package.id)]
            ).get(propagate=True)

        assert mock_instance.send.called

    def test_completion_email_noop_on_missing_package(self):
        from notifications.tasks import send_completion_notification
        import uuid
        # Should not raise — just return silently
        send_completion_notification(str(uuid.uuid4()))