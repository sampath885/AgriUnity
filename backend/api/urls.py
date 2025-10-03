# backend/api/urls.py

from django.urls import path
from .views import health_check, get_states, get_districts, pin_lookup

# This defines the URL patterns specifically for the 'api' app
urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('locations/states/', get_states, name='get_states'),
    path('locations/districts/<str:state>/', get_districts, name='get_districts'),
    path('locations/pin/<str:code>/', pin_lookup, name='pin_lookup'),
]