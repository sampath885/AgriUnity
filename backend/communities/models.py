# backend/communities/models.py
from django.conf import settings
from django.db import models


class CommunityHub(models.Model):
    name = models.CharField(max_length=255, blank=True)
    crop = models.ForeignKey('products.CropProfile', on_delete=models.CASCADE, related_name='community_hubs')
    region = models.CharField(max_length=100)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='community_hubs', blank=True)

    class Meta:
        unique_together = ('crop', 'region')

    def save(self, *args, **kwargs):
        if not self.name and self.crop_id and self.region:
            self.name = f"{self.region}-{self.crop.name}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name or f"{self.region}-{getattr(self.crop, 'name', 'Unknown')}"


class AgentMessage(models.Model):
    hub = models.ForeignKey(CommunityHub, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Message to {self.hub.name} @ {self.created_at:%Y-%m-%d %H:%M}"


