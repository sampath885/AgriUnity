# backend/chatbot/models.py
from django.db import models
import json
from django.conf import settings

class KnowledgeChunk(models.Model):
    source = models.CharField(max_length=255)  # e.g., 'pm_kisan.pdf' or 'data.gov.in API'
    content = models.TextField()
    embedding_json = models.TextField() # We'll store the vector as a JSON string
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def embedding(self):
        # Helper to convert the JSON string back to a list of numbers
        return json.loads(self.embedding_json)

    def __str__(self):
        return f"Chunk from {self.source}"


class ChatbotMessage(models.Model):
    """Stores AgriGenie chat history per user."""
    class SenderType(models.TextChoices):
        USER = 'user', 'User'
        AGENT = 'agent', 'Agent'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.CharField(max_length=10, choices=SenderType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} [{self.sender}] {self.content[:30]}"