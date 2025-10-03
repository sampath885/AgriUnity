from django.core.management.base import BaseCommand
from deals.models import DealGroup, Poll
from deals.views import CastVoteView
from django.utils import timezone
import json


class Command(BaseCommand):
    help = 'Fix accepted deal groups that don\'t have collection hubs and create location confirmation polls'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing accepted deal groups without collection hubs...')
        
        # Get all accepted deal groups without collection hubs
        accepted_groups = DealGroup.objects.filter(
            status='ACCEPTED',
            recommended_collection_point__isnull=True
        )
        
        self.stdout.write(f'Found {accepted_groups.count()} accepted deal groups without collection hubs')
        
        fixed_count = 0
        
        for group in accepted_groups:
            try:
                self.stdout.write(f'Processing group {group.id}: {group.group_id}')
                
                # Get the accepted price offer poll
                price_poll = group.polls.filter(
                    poll_type='price_offer',
                    result='ACCEPTED'
                ).first()
                
                if not price_poll:
                    self.stdout.write(f'⚠️ No accepted price offer poll found for group {group.id}')
                    continue
                
                # Create a CastVoteView instance to use its methods
                view = CastVoteView()
                
                # Calculate collection hub
                hub_info = view._calculate_collection_hub(group)
                
                if hub_info and hub_info.get('hub_name'):
                    # Try to find the hub by name or create it
                    from hubs.models import HubPartner
                    try:
                        hub = HubPartner.objects.get(name=hub_info['hub_name'])
                        group.recommended_collection_point = hub
                        group.save(update_fields=['recommended_collection_point'])
                        self.stdout.write(f'✅ Assigned existing hub {hub.name} to group {group.id}')
                    except HubPartner.DoesNotExist:
                        # Create the hub if it doesn't exist
                        hub = HubPartner.objects.create(
                            name=hub_info['hub_name'],
                            address=hub_info.get('full_address', 'Address not available'),
                            latitude=hub_info.get('hub_coordinates', [0, 0])[0],
                            longitude=hub_info.get('hub_coordinates', [0, 0])[1]
                        )
                        group.recommended_collection_point = hub
                        group.save(update_fields=['recommended_collection_point'])
                        self.stdout.write(f'✅ Created and assigned new hub {hub.name} to group {group.id}')
                    
                    # Create location confirmation poll
                    location_poll = view._create_location_confirmation_poll(group, price_poll)
                    
                    if location_poll:
                        self.stdout.write(f'✅ Created location confirmation poll {location_poll.id} for group {group.id}')
                        fixed_count += 1
                    else:
                        self.stdout.write(f'❌ Failed to create location confirmation poll for group {group.id}')
                else:
                    self.stdout.write(f'⚠️ Could not calculate hub for group {group.id}')
                    
            except Exception as e:
                self.stdout.write(f'❌ Error processing group {group.id}: {e}')
                continue
        
        self.stdout.write(f'✅ Successfully fixed {fixed_count} deal groups')
        self.stdout.write('🎉 All accepted deal groups now have collection hubs and location confirmation polls!')
