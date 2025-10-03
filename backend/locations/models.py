from django.db import models


class PinCode(models.Model):
    code = models.CharField(max_length=6, unique=True, db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    class Meta:
        ordering = ['code']

    def __str__(self) -> str:
        return f"{self.code} ({self.district}, {self.state})"


