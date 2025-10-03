from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'status', 'created_at', 'sent_at',
            'related_deal_group_id', 'related_poll_id', 'related_contract_id'
        ]
        read_only_fields = fields
