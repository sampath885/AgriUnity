# backend/users/urls.py
from django.urls import path
from .views import RegisterAPI, LoginAPI, SendOTPAPI, VerifyOTPAPI

urlpatterns = [
    path('register/', RegisterAPI.as_view(), name='register'),
    path('login/', LoginAPI.as_view(), name='login'),
    path('otp/send/', SendOTPAPI.as_view(), name='otp_send'),
    path('otp/verify/', VerifyOTPAPI.as_view(), name='otp_verify'),
]