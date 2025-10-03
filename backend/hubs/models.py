from django.db import models


class HubPartner(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self) -> str:
        return self.name


