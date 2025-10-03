# backend/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone



class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        FARMER = 'FARMER', 'Farmer'
        BUYER = 'BUYER', 'Buyer'
        ADMIN = 'ADMIN', 'Admin'

    
    
    # We will use 'name' instead for the full name
    name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.FARMER)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    region = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    trust_score = models.IntegerField(default=10)
    is_verified = models.BooleanField(default=False)

    # Make email optional for now, username will be primary identifier for login
    email = models.EmailField(blank=True, null=True)

    # Primary crops a farmer typically grows; used for auto-subscribing to Community Hubs
    # Use a string reference to avoid circular imports with products app
    primary_crops = models.ManyToManyField('products.CropProfile', blank=True, related_name='primary_farmers')

    # Location coordinates for logistics optimization
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.username


class BuyerProfile(models.Model):
    # This creates a one-to-one link. Each user can have at most one buyer profile.
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='buyer_profile')
    business_name = models.CharField(max_length=255)
    gst_number = models.CharField(max_length=15, unique=True)
    # You could add more fields here later, like address, license number, etc.

    def __str__(self):
        return f"Profile for Buyer: {self.user.username}"

# --- A "Signal" to automatically create a profile when a Buyer registers ---
# This is a bit of Django magic that keeps things clean.
@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if instance.role == 'BUYER':
        if created:
            BuyerProfile.objects.create(user=instance)
        instance.buyer_profile.save()


class OTPCode(models.Model):
    """One-time password for phone-based authentication."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes', null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])