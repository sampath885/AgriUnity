# backend/communities/views.py
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import CommunityHub
from .serializers import CommunityHubSerializer
from users.serializers import PublicUserSerializer


class MyHubsListView(generics.ListAPIView):
    serializer_class = CommunityHubSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CommunityHub.objects.filter(members=user).select_related('crop').prefetch_related('messages')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['messages_limit'] = self.request.query_params.get('limit', 20)
        return context


class HubDetailView(generics.RetrieveAPIView):
    serializer_class = CommunityHubSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'hub_id'
    queryset = CommunityHub.objects.select_related('crop').prefetch_related('messages')

    def get_object(self):
        hub = super().get_object()
        if not hub.members.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You are not a member of this hub.")
        return hub

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['messages_limit'] = self.request.query_params.get('limit', 50)
        return context


class CommunityHubMembersView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        hub_id = self.kwargs.get('hub_id')
        hub = CommunityHub.objects.prefetch_related('members').filter(id=hub_id).first()
        if not hub:
            # Default DRF will turn empty queryset into 200. Better to raise 404
            from django.http import Http404
            raise Http404("Hub not found")
        if not hub.members.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You are not a member of this hub.")
        # Exclude the requesting user if we only want 'other' members
        return hub.members.exclude(id=self.request.user.id)

