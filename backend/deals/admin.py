# backend/deals/admin.py

from django.contrib import admin
from .models import DealGroup

@admin.register(DealGroup)
class DealGroupAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing automatically formed Deal Groups.
    """
    list_display = ('group_id', 'total_quantity_kg', 'status', 'created_at')
    search_fields = ('group_id',)
    list_filter = ('status',)
    ordering = ('-created_at',)
    # Use a filter for easier browsing of related products
    filter_horizontal = ('products',)