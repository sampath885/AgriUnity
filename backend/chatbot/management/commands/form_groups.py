# backend/deals/management/commands/form_groups.py
from django.core.management.base import BaseCommand
from products.models import ProductListing
from deals.models import DealGroup
from django.db.models import Sum
from itertools import groupby
from datetime import datetime

class Command(BaseCommand):
    help = 'Scans for available product listings and forms deal groups.'

    def handle(self, *args, **options):
        self.stdout.write("Starting group formation task...")
        
        # Find all listings that are currently available to be grouped
        available_listings = ProductListing.objects.filter(status='AVAILABLE').order_by('crop__name', 'grade', 'farmer__region')
        
        # Group them by crop, grade, and region
        # This key function is crucial for grouping
        keyfunc = lambda x: (x.crop.id, x.grade, x.farmer.region)
        
        for (crop_id, grade, region), listings_group in groupby(available_listings, key=keyfunc):
            listings_list = list(listings_group)
            total_quantity = sum(listing.quantity_kg for listing in listings_list)
            
            # Set a threshold for forming a group, e.g., 10,000 kg (10 tons)
            MIN_GROUP_QUANTITY = 10000 
            
            if total_quantity >= MIN_GROUP_QUANTITY:
                crop_name = listings_list[0].crop.name
                self.stdout.write(self.style.SUCCESS(f"Found a potential group for {total_quantity}kg of {grade} {crop_name} in {region}"))

                # Create a unique ID for the group
                group_id = f"{region.upper()}-{crop_name.upper()}-{grade.upper()}-{datetime.now().strftime('%Y%m%d%H%M')}"

                # Create the DealGroup
                deal_group = DealGroup.objects.create(
                    group_id=group_id,
                    total_quantity_kg=total_quantity
                )
                
                # Add the products to the group and update their status
                product_ids = [listing.id for listing in listings_list]
                deal_group.products.set(product_ids)
                ProductListing.objects.filter(id__in=product_ids).update(status='GROUPED')
                
                self.stdout.write(f"Successfully created DealGroup: {group_id}")

        self.stdout.write("Group formation task finished.")