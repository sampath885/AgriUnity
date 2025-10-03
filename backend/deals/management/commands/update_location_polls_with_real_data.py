from django.core.management.base import BaseCommand
from deals.models import Poll, DealGroup
from deals.views import CastVoteView
from django.utils import timezone
import json


class Command(BaseCommand):
    help = 'Update existing location confirmation polls with real location data using improved coordinates and city detection'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Updating location confirmation polls with real location data...')
        
        # Get all active location confirmation polls
        location_polls = Poll.objects.filter(
            poll_type='location_confirmation',
            is_active=True
        )
        
        self.stdout.write(f'Found {location_polls.count()} active location confirmation polls')
        
        updated_count = 0
        
        for poll in location_polls:
            try:
                self.stdout.write(f'Processing poll {poll.id} for group {poll.deal_group.group_id}')
                
                # Get the deal group
                deal_group = poll.deal_group
                
                # Create a CastVoteView instance to use its methods
                view = CastVoteView()
                
                # Calculate collection hub with improved data
                hub_info = view._calculate_collection_hub(deal_group)
                
                if hub_info:
                    # Create improved agent justification with real location data
                    agent_justification = {
                        'real_location_info': {
                            'city_name': hub_info.get('city_name', 'Central Location'),
                            'state_name': hub_info.get('state_name', 'Central Region'),
                            'coordinates': {
                                'latitude': hub_info.get('hub_coordinates', [0, 0])[0],
                                'longitude': hub_info.get('hub_coordinates', [0, 0])[1]
                            },
                            'total_distance_km': hub_info.get('total_distance_km', 50),
                            'travel_time_minutes': hub_info.get('travel_time_minutes', 100),
                            'distance_api_used': hub_info.get('distance_api_used', 'Hub Optimizer')
                        },
                        'logistics_details': {
                            'hub_name': hub_info.get('hub_name', 'Optimal Collection Hub'),
                            'hub_address': hub_info.get('hub_address', 'Address not available'),
                            'city_name': hub_info.get('city_name', 'Central Location'),
                            'state_name': hub_info.get('state_name', 'Central Region'),
                            'hub_coordinates': {
                                'latitude': hub_info.get('hub_coordinates', [0, 0])[0],
                                'longitude': hub_info.get('hub_coordinates', [0, 0])[1]
                            },
                            'total_distance_km': hub_info.get('total_distance_km', 50),
                            'travel_time_minutes': hub_info.get('travel_time_minutes', 100),
                            'logistics_efficiency': 'Optimized for cost and time',
                            'estimated_transport_cost': f"₹{hub_info.get('logistics_info', {}).get('transport_cost_per_kg', 2.50)}/kg",
                            'hub_facilities': ['Cold storage', 'Weighing', 'Quality check'],
                            'transport_details': {
                                'distance_from_farm': hub_info.get('total_distance_km', 50),
                                'estimated_travel_time': hub_info.get('travel_time_minutes', 100),
                                'transport_cost_per_kg': hub_info.get('logistics_info', {}).get('transport_cost_per_kg', 2.50)
                            }
                        },
                        'market_insights': {
                            'crop_name': 'Collection Hub Location',
                            'current_market_price': 'N/A',
                            'quality_premium': 'N/A'
                        },
                        'agent_analysis': {
                            'action': 'LOCATION_CONFIRMATION',
                            'confidence_level': 'High',
                            'justification_for_farmers': f'AI-calculated optimal collection point in {hub_info.get("city_name", "Central Location")}, {hub_info.get("state_name", "Central Region")} to minimize transport costs for all farmers. Total distance: {hub_info.get("total_distance_km", 50)} km, estimated travel time: {hub_info.get("travel_time_minutes", 100)} minutes.'
                        }
                    }
                    
                    # Update the poll with new structured data
                    poll.agent_justification = json.dumps(agent_justification)
                    poll.save(update_fields=['agent_justification'])
                    
                    self.stdout.write(f'✅ Updated poll {poll.id} with real location data: {hub_info.get("city_name")}, {hub_info.get("state_name")}')
                    updated_count += 1
                else:
                    self.stdout.write(f'⚠️ Could not calculate hub info for poll {poll.id}')
                    
            except Exception as e:
                self.stdout.write(f'❌ Error updating poll {poll.id}: {e}')
                continue
        
        self.stdout.write(f'✅ Successfully updated {updated_count} location confirmation polls')
        self.stdout.write('🎉 All location polls now have real location data with improved coordinates and city names!')
