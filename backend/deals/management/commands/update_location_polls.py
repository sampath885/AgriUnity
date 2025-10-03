"""
Management command to update existing location confirmation polls to use structured data format.
"""

from django.core.management.base import BaseCommand
from deals.models import Poll
import json


class Command(BaseCommand):
    help = 'Update existing location confirmation polls to use structured data format'

    def handle(self, *args, **options):
        location_polls = Poll.objects.filter(poll_type='location_confirmation')
        updated_count = 0
        
        for poll in location_polls:
            try:
                # Check if this poll already has structured data
                if poll.agent_justification and poll.agent_justification.startswith('{'):
                    self.stdout.write(f"Poll {poll.id} already has structured data, skipping...")
                    continue
                
                # Get the deal group's recommended collection point
                if not poll.deal_group or not poll.deal_group.recommended_collection_point:
                    self.stdout.write(f"Poll {poll.id} has no recommended collection point, skipping...")
                    continue
                
                hub = poll.deal_group.recommended_collection_point
                
                # Parse city and state from hub name (assuming format: "City Name, State")
                hub_parts = hub.name.split(',') if hub.name and ',' in hub.name else [hub.name, 'Central Region']
                city = hub_parts[0].strip() if hub_parts[0] else 'Central Location'
                state = hub_parts[1].strip() if len(hub_parts) > 1 and hub_parts[1] else 'Central Region'
                
                # Create structured agent justification
                agent_justification = {
                    'real_location_info': {
                        'city_name': city,
                        'state_name': state,
                        'coordinates': {
                            'latitude': hub.latitude,
                            'longitude': hub.longitude
                        },
                        'total_distance_km': 50,  # Default distance
                        'travel_time_minutes': 100,  # Default travel time
                        'distance_api_used': 'Hub Optimizer'
                    },
                    'logistics_details': {
                        'hub_name': hub.name,
                        'hub_address': hub.address,
                        'city_name': city,
                        'state_name': state,
                        'hub_coordinates': {
                            'latitude': hub.latitude,
                            'longitude': hub.longitude
                        },
                        'total_distance_km': 50,
                        'travel_time_minutes': 100,
                        'logistics_efficiency': 'Optimized for cost and time',
                        'estimated_transport_cost': '₹25/kg'
                    },
                    'market_insights': {
                        'crop_name': 'Collection Hub Location',
                        'current_market_price': 'N/A',
                        'quality_premium': 'N/A'
                    },
                    'agent_analysis': {
                        'action': 'LOCATION_CONFIRMATION',
                        'confidence_level': 'High',
                        'justification_for_farmers': f'AI-calculated optimal collection point in {city}, {state} to minimize transport costs for all farmers.'
                    }
                }
                
                # Update the poll with structured data
                poll.agent_justification = json.dumps(agent_justification)
                poll.save(update_fields=['agent_justification'])
                
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated poll {poll.id} with structured location data')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating poll {poll.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} location confirmation polls'
            )
        )
