# backend/communities/serializers.py
from rest_framework import serializers
from .models import CommunityHub, AgentMessage


class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = ('id', 'content', 'created_at')


class CommunityHubSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    recent_messages = serializers.SerializerMethodField()

    class Meta:
        model = CommunityHub
        fields = ('id', 'name', 'crop', 'crop_name', 'region', 'recent_messages')

    def get_recent_messages(self, obj: CommunityHub):
        limit = int(self.context.get('messages_limit', 20))
        messages = obj.messages.all().order_by('-created_at')[:limit]
        return AgentMessageSerializer(messages, many=True).data


