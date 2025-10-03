from django.urls import path
from .views import MyNotificationsView

urlpatterns = [
    path('my/', MyNotificationsView.as_view(), name='my-notifications'),
]
