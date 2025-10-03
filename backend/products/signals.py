from django.db.models.signals import post_save
from django.dispatch import receiver

from products.models import ProductListing
from deals.utils import check_and_form_groups


@receiver(post_save, sender=ProductListing)
def auto_group_on_listing_save(sender, instance: ProductListing, created: bool, **kwargs):
    """Automatically attempt grouping when a listing is created or updated to AVAILABLE.

    Only triggers when status is AVAILABLE, grading is completed, and a grade is present.
    """
    print(f"🔔 Signal triggered for ProductListing {instance.id}")
    print(f"🔔 Created: {created}, Status: {instance.status}")
    print(f"🔔 Grading Status: {instance.grading_status}")
    print(f"🔔 Grade: {instance.grade}")
    print(f"🔔 Crop: {instance.crop.name if instance.crop else 'NO_CROP'}")
    print(f"🔔 Farmer: {instance.farmer.username if instance.farmer else 'NO_FARMER'}")
    
    if (instance.status == ProductListing.StatusChoices.AVAILABLE and 
        instance.grading_status == ProductListing.GradingStatusChoices.COMPLETED and 
        instance.grade and instance.grade != 'PENDING'):
        print(f"✅ All conditions met - attempting group formation")
        try:
            result = check_and_form_groups(instance)
            if result:
                print(f"✅ Group formation successful: {result.group_id}")
            else:
                print(f"⚠️ Group formation returned None")
        except Exception as e:
            # Fail-safe: do not block the save pipeline
            print(f"❌ Grouping error for listing {instance.id}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Conditions not met for group formation:")
        print(f"   - Status AVAILABLE: {instance.status == ProductListing.StatusChoices.AVAILABLE}")
        print(f"   - Grading completed: {instance.grading_status == ProductListing.GradingStatusChoices.COMPLETED}")
        print(f"   - Grade present: {instance.grade and instance.grade != 'PENDING'}")


