# backend/core/urls.py

from django.contrib import admin
from django.urls import path, include  # Ensure 'include' is imported

urlpatterns = [
    # Admin Panel URL
    path('admin/', admin.site.urls),

    # Authentication URLs (from the 'users' app) - MUST COME FIRST
    # All URLs starting with /api/auth/ will be handled by users.urls
    path('api/auth/', include('users.urls')),

    # Chatbot URLs (from the 'chatbot' app)
    # All URLs starting with /api/chatbot/ will be handled by chatbot.urls
    path('api/chatbot/', include('chatbot.urls')),
    
    # Products URLs
    path('api/products/', include('products.urls')),

    # Deals URLs
    path('api/deals/', include('deals.urls')),

    # Community hubs
    path('api/communities/', include('communities.urls')),

    # Future Contracts
    path('api/contracts/', include('contracts.urls')),

    # Notifications
    path('api/notifications/', include('notifications.urls')),

    # Locations (for pincode lookups)
    path('api/locations/', include('locations.urls')),
    
    # General API URLs (health check, etc. from the 'api' app) - MUST COME LAST
    # All URLs starting with /api/ will be handled by api.urls
    path('api/', include('api.urls')),
]