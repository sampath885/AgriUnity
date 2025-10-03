from rest_framework import serializers
from .models import ChatbotMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatbotMessage
        fields = ['id', 'sender', 'sender_name', 'content', 'created_at']
        read_only_fields = fields

    def get_sender_name(self, obj):
        return 'AgriGenie' if obj.sender == ChatbotMessage.SenderType.AGENT else 'You'


