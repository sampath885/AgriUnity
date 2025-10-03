from django.core.management.base import BaseCommand
from deals.models import DealGroup
from products.models import ProductListing
from django.db import transaction
from django.db import models

class Command(BaseCommand):
    help = "Fix broken deal groups that have 0 products"

    def handle(self, *args, **options):
        self.stdout.write("🔧 Fixing broken deal groups...")
        
        # Find groups with 0 products
        broken_groups = DealGroup.objects.filter(products__isnull=True).distinct()
        self.stdout.write(f"Found {broken_groups.count()} groups with no products")
        
        for group in broken_groups:
            self.stdout.write(f"🔍 Checking group {group.id}: {group.group_id}")
            
            # Try to find available products for this group
            if group.group_id:
                group_parts = group.group_id.split('-')
                if len(group_parts) >= 2:
                    crop_name = group_parts[0]
                    grade = group_parts[1]
                    
                    # Find available products for this crop/grade
                    available_products = ProductListing.objects.filter(
                        crop__name__iexact=crop_name,
                        grade__iexact=grade,
                        status='AVAILABLE'
                    )
                    
                    if available_products.exists():
                        self.stdout.write(f"✅ Found {available_products.count()} available products for {crop_name} {grade}")
                        
                        # Add products to group
                        with transaction.atomic():
                            product_ids = list(available_products.values_list('id', flat=True))
                            group.products.set(product_ids)
                            
                            # Update product status
                            ProductListing.objects.filter(id__in=product_ids).update(
                                status=ProductListing.StatusChoices.GROUPED
                            )
                            
                            # Recalculate total quantity
                            total_quantity = available_products.aggregate(
                                total_kg=models.Sum('quantity_kg')
                            )['total_kg'] or 0
                            group.total_quantity_kg = int(total_quantity)
                            group.save(update_fields=['total_quantity_kg'])
                            
                            self.stdout.write(f"✅ Added {len(product_ids)} products to group {group.id}")
                            self.stdout.write(f"📊 Updated total quantity: {total_quantity} kg")
                    else:
                        self.stdout.write(f"❌ No available products found for {crop_name} {grade}")
                        
                        # Delete the empty group
                        with transaction.atomic():
                            group.delete()
                            self.stdout.write(f"🗑️ Deleted empty group {group.id}")
            else:
                self.stdout.write(f"❌ Invalid group_id format: {group.group_id}")
                group.delete()
        
        self.stdout.write("✅ Finished fixing broken groups")
        
        # Show final status
        total_groups = DealGroup.objects.count()
        groups_with_products = DealGroup.objects.filter(products__isnull=False).distinct().count()
        self.stdout.write(f"📊 Final status: {total_groups} total groups, {groups_with_products} with products")
