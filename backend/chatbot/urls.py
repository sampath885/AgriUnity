# backend/chatbot/urls.py
from django.urls import path
from .views import ChatbotAPI

urlpatterns = [
    path('ask/', ChatbotAPI.as_view(), name='chatbot_ask'),
]