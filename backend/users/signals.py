# backend/users/signals.py
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from users.models import CustomUser
from locations.models import PinCode


def _subscribe_farmer_to_hubs(user: CustomUser):
    # Lazy import to avoid AppRegistryNotReady during app loading
    from communities.models import CommunityHub
    if user.role != CustomUser.Role.FARMER:
        return
    if not user.region:
        return
    primary_crops = list(user.primary_crops.all())
    if not primary_crops:
        return
    for crop in primary_crops:
        hub, _ = CommunityHub.objects.get_or_create(crop=crop, region=user.region)
        hub.members.add(user)


@receiver(post_save, sender=CustomUser)
def subscribe_new_farmer_to_hubs(sender, instance: CustomUser, created, **kwargs):
    if created:
        # Derive region from PIN if provided
        if instance.pincode:
            try:
                pc = PinCode.objects.get(code=instance.pincode)
                instance.region = f"{pc.district}, {pc.state}"
                instance.save(update_fields=['region'])
            except PinCode.DoesNotExist:
                pass
        # If there are already primary crops assigned in the create payload, attempt subscription.
        _subscribe_farmer_to_hubs(instance)


@receiver(m2m_changed, sender=CustomUser.primary_crops.through)
def subscribe_on_primary_crops_change(sender, instance: CustomUser, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        _subscribe_farmer_to_hubs(instance)


