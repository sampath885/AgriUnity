# backend/chatbot/admin.py
from django.contrib import admin
from .models import KnowledgeChunk

@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ('source', 'last_updated')
    search_fields = ('content',)