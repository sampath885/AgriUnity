# Utils Package
# Include necessary functions directly to avoid circular imports

from __future__ import annotations
from datetime import datetime
from typing import Optional, Iterable
from django.db import transaction
from django.db.models import Sum

# Import models using absolute imports to avoid import issues
from deals.models import DealGroup
from products.models import ProductListing, CropProfile
from notifications.services import notify_group_formed

# Default minimum group size when crop profile does not specify
DEFAULT_MIN_GROUP_QUANTITY_KG = 20000


def _generate_group_id(crop_name: str, grade: str, region: str | None = None) -> str:
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    # Use the actual grade from the CSV data (FAQ, Medium, Large, Local, Non-FAQ, Ref grade-1, Ref grade-2)
    # Remove region from group ID since we're no longer using region-based grouping
    return f"{crop_name.upper()}-{grade}-{timestamp}"


def _listings_queryset_for(listing: ProductListing):
    return (
        ProductListing.objects
        .select_related('crop', 'farmer')
        .filter(
            status=ProductListing.StatusChoices.AVAILABLE,
            crop=listing.crop,
            grade=listing.grade,
            # Removed region filter to allow farmers from different regions to group together
        )
        .order_by('created_at')
    )


def _find_open_group_for(listing: ProductListing) -> Optional[DealGroup]:
    """Find an existing open (FORMED only) group for the same crop/grade."""
    return (
        DealGroup.objects
        .filter(
            status=DealGroup.StatusChoices.FORMED,  # Only FORMED groups can accept new farmers
            products__crop=listing.crop,
            products__grade=listing.grade,
            # Removed region filter to allow farmers from different regions to group together
        )
        .order_by('created_at')
        .first()
    )


def _threshold_for_listing(listing: ProductListing) -> int:
    try:
        crop_profile: CropProfile = listing.crop
        return int(getattr(crop_profile, 'min_group_kg', DEFAULT_MIN_GROUP_QUANTITY_KG))
    except Exception:
        return DEFAULT_MIN_GROUP_QUANTITY_KG


def check_and_form_groups(listing: ProductListing) -> Optional[DealGroup]:
    """Check whether the provided listing can form/complete a group."""
    if listing is None:
        return None

    print(f"🔍 Checking group formation for listing {listing.id}")
    print(f"🔍 Crop: {listing.crop.name}, Grade: {listing.grade}")
    print(f"🔍 Quantity: {listing.quantity_kg} kg")
    print(f"🔍 Status: {listing.status}")
    print(f"🔍 Note: Grouping by crop and grade only (region-independent)")

    qs = _listings_queryset_for(listing)
    print(f"🔍 Found {qs.count()} matching listings")

    # Find existing open group
    existing_group = _find_open_group_for(listing)
    if existing_group is not None:
        print(f"✅ Found existing group {existing_group.id} - {existing_group.group_id}")
        with transaction.atomic():
            product_ids_to_add = list(qs.values_list('id', flat=True))
            if product_ids_to_add:
                # Only add listings that are not already part of any group
                already_in_group_ids = list(
                    existing_group.products.values_list('id', flat=True)
                )
                new_product_ids = [pid for pid in product_ids_to_add if pid not in already_in_group_ids]
                
                if new_product_ids:
                    existing_group.products.add(*new_product_ids)
                    print(f"✅ Added {len(new_product_ids)} new listings to existing group")
                else:
                    print(f"ℹ️ All listings already in group")
                
                # Check if group is now complete
                total_quantity = existing_group.products.aggregate(
                    total=Sum('quantity_kg')
                )['total'] or 0
                
                # Update the group's total quantity
                existing_group.total_quantity_kg = total_quantity
                existing_group.save()
                
                threshold = _threshold_for_listing(listing)
                if total_quantity >= threshold:
                    print(f"🎉 Group {existing_group.id} is now complete! Total: {total_quantity}kg >= {threshold}kg")
                    existing_group.status = DealGroup.StatusChoices.FORMED
                    existing_group.save()
                    
                    # Notify farmers that group is formed
                    notify_group_formed(existing_group)
                    
                    return existing_group
                else:
                    print(f"⏳ Group {existing_group.id} still needs {threshold - total_quantity}kg more")
                    return existing_group
            else:
                print(f"ℹ️ No new listings to add")
                return existing_group

    # No existing group found, check if we can form a new one
    total_quantity = qs.aggregate(total=Sum('quantity_kg'))['total'] or 0
    threshold = _threshold_for_listing(listing)
    
    if total_quantity >= threshold:
        print(f"🎉 Can form new group! Total: {total_quantity}kg >= {threshold}kg")
        
        with transaction.atomic():
            # Create new group with calculated total quantity
            group_id = _generate_group_id(listing.crop.name, listing.grade)
            new_group = DealGroup.objects.create(
                group_id=group_id,
                status=DealGroup.StatusChoices.FORMED,
                total_quantity_kg=total_quantity  # Set the total quantity
            )
            
            # Add all matching listings to the group
            new_group.products.add(*qs)
            print(f"✅ Created new group {new_group.id} - {group_id} with {qs.count()} listings")
            print(f"✅ Total quantity: {total_quantity}kg")
            
            # Notify farmers that group is formed
            notify_group_formed(new_group)
            
            return new_group
    else:
        print(f"⏳ Cannot form group yet. Need {threshold - total_quantity}kg more (current: {total_quantity}kg)")
        return None


# Export the functions
__all__ = [
    'check_and_form_groups',
    '_generate_group_id',
    '_listings_queryset_for',
    '_find_open_group_for',
    '_threshold_for_listing'
]
