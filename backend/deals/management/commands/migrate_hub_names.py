"""
Management command to migrate existing deal groups from old hub names to new hub names.
"""

from django.core.management.base import BaseCommand
from deals.models import DealGroup
from hubs.models import HubPartner


class Command(BaseCommand):
    help = 'Migrate existing deal groups from old hub names to new hub names'

    def handle(self, *args, **options):
        # Mapping from old hub names to new hub names
        hub_mapping = {
            'Kadapa Central Hub': 'Kadapa, Andhra Pradesh',
            'Anantapur Collection Center': 'Anantapur, Andhra Pradesh',
            'Kurnool Agricultural Hub': 'Kurnool, Andhra Pradesh',
            'Chittoor Farmers Market': 'Chittoor, Andhra Pradesh',
            'Nellore Collection Point': 'Nellore, Andhra Pradesh',
            'Guntur Central Hub': 'Guntur, Andhra Pradesh',
            'Vijayawada Agricultural Center': 'Vijayawada, Andhra Pradesh',
            'Rajahmundry Hub': 'Rajahmundry, Andhra Pradesh'
        }
        
        migrated_count = 0
        
        for old_name, new_name in hub_mapping.items():
            try:
                # Find old hub
                old_hub = HubPartner.objects.filter(name=old_name).first()
                if not old_hub:
                    self.stdout.write(f"Old hub '{old_name}' not found, skipping...")
                    continue
                
                # Find new hub
                new_hub = HubPartner.objects.filter(name=new_name).first()
                if not new_hub:
                    self.stdout.write(f"New hub '{new_name}' not found, skipping...")
                    continue
                
                # Update deal groups that reference the old hub
                deal_groups = DealGroup.objects.filter(recommended_collection_point=old_hub)
                updated_groups = deal_groups.update(recommended_collection_point=new_hub)
                
                if updated_groups > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"Migrated {updated_groups} deal groups from '{old_name}' to '{new_name}'")
                    )
                    migrated_count += updated_groups
                
                # Delete the old hub
                old_hub.delete()
                self.stdout.write(f"Deleted old hub: {old_name}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error migrating hub '{old_name}': {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully migrated {migrated_count} deal groups to new hub names'
            )
        )
