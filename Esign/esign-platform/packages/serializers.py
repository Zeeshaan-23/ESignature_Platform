# packages/serializers.py

from rest_framework import serializers
from .models import Package, Recipient, SignatureField


class SignatureFieldSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and reading signature field placements.
    Coordinates are stored as percentages (0.0 – 1.0) of page dimensions.
    """
    class Meta:
        model = SignatureField
        fields = ['id', 'recipient', 'page_number', 'x', 'y', 'width', 'height', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        for coord in ('x', 'y', 'width', 'height'):
            val = data.get(coord)
            if val is not None and not (0.0 <= val <= 1.0):
                raise serializers.ValidationError(
                    {coord: f"'{coord}' must be a percentage between 0.0 and 1.0."}
                )
        return data


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = [
            'id', 'name', 'email', 'role',
            'status', 'signing_order', 'signed_at'
        ]
        read_only_fields = ['id', 'status', 'signed_at']


class PackageSerializer(serializers.ModelSerializer):
    # Nested serializer — recipients are returned inline with the package
    recipients = RecipientSerializer(many=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)

    class Meta:
        model = Package
        fields = [
            'id', 'subject', 'message', 'routing_mode',
            'status', 'sender_email', 'document',
            'recipients', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'sender_email', 'created_at']

    def validate_recipients(self, recipients):
        if len(recipients) == 0:
            raise serializers.ValidationError("At least one recipient is required.")

        emails = [r['email'] for r in recipients]
        if len(emails) != len(set(emails)):
            raise serializers.ValidationError("Duplicate recipient emails are not allowed.")

        return recipients

    def validate_document(self, document):
        request = self.context.get('request')
        # Ensure the document belongs to the requesting user
        if document.uploaded_by != request.user:
            raise serializers.ValidationError("You can only use your own documents.")
        return document

    def create(self, validated_data):
        # Recipients come in as nested data — we handle them separately
        recipients_data = validated_data.pop('recipients')

        package = Package.objects.create(**validated_data)

        for recipient_data in recipients_data:
            Recipient.objects.create(package=package, **recipient_data)

        return package


class PackageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — no nested recipients."""
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    recipient_count = serializers.IntegerField(
        source='recipients.count',
        read_only=True
    )

    class Meta:
        model = Package
        fields = [
            'id', 'subject', 'status', 'routing_mode',
            'sender_email', 'recipient_count', 'created_at'
        ]

class PackageDetailSerializer(serializers.ModelSerializer):
    recipients = RecipientSerializer(many=True, read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    document_name = serializers.CharField(
        source='document.original_filename',
        read_only=True
    )
    document_id = serializers.UUIDField(
        source='document.id',
        read_only=True
    )
    signed_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = [
            'id', 'subject', 'message', 'routing_mode', 'status',
            'sender_email', 'document_id', 'document_name', 
            'signed_file_url',
            'recipients', 'expires_at', 'created_at', 'updated_at'
        ]
    def get_signed_file_url(self, obj):
        if obj.signed_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.signed_file.url)
        return None