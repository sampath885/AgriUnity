# backend/communities/urls.py
from django.urls import path
from .views import MyHubsListView, HubDetailView, CommunityHubMembersView

urlpatterns = [
    path('my-hubs/', MyHubsListView.as_view(), name='my-hubs'),
    path('hubs/<int:hub_id>/', HubDetailView.as_view(), name='hub-detail'),
    path('hubs/<int:hub_id>/members/', CommunityHubMembersView.as_view(), name='hub-members'),
]


