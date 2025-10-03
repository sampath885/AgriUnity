# backend/products/admin.py

from django.contrib import admin
from .models import CropProfile, ProductListing

@admin.register(CropProfile)
class CropProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Crop Profiles.
    """
    list_display = ('name', 'perishability_score', 'is_storable', 'has_msp')
    search_fields = ('name',)
    list_filter = ('is_storable', 'has_msp')
    ordering = ('name',)

@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing and managing individual farmer listings.
    """
    list_display = ('farmer', 'crop', 'grade', 'quantity_kg', 'status', 'created_at')
    search_fields = ('farmer__username', 'crop__name')
    list_filter = ('status', 'crop', 'farmer__region')
    ordering = ('-created_at',)
    # Make some fields read-only as they are set by the system
    readonly_fields = ('created_at',)