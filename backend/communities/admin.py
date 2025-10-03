from django.contrib import admin
from .models import CommunityHub, AgentMessage


@admin.register(CommunityHub)
class CommunityHubAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'region', 'crop')
    search_fields = ('name', 'region', 'crop__name')
    list_filter = ('region', 'crop')


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'hub', 'created_at')
    search_fields = ('hub__name', 'content')
    list_filter = ('hub',)


