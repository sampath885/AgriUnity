"""
Management command to test the logistics system.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from deals.models import DealGroup, ProductListing
from deals.logistics_manager import compute_hub_recommendation, get_logistics_info
from deals.logistics_v2_service import find_optimal_hub_v2, get_recommendation_method
from hubs.models import HubPartner
from users.models import CustomUser
from products.models import CropProfile
import random


class Command(BaseCommand):
    help = 'Test the logistics system with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-v1',
            action='store_true',
            help='Test V1 logistics (centroid + nearest hub)',
        )
        parser.add_argument(
            '--test-v2',
            action='store_true',
            help='Test V2 logistics (road network optimization)',
        )
        parser.add_argument(
            '--create-sample-group',
            action='store_true',
            help='Create a sample deal group for testing',
        )

    def handle(self, *args, **options):
        if options['create_sample_group']:
            self.create_sample_group()
        
        if options['test_v1']:
            self.test_v1_logistics()
        
        if options['test_v2']:
            self.test_v2_logistics()
        
        if not any([options['test_v1'], options['test_v2'], options['create_sample_group']]):
            self.stdout.write(
                self.style.WARNING('No test specified. Use --help to see available options.')
            )

    def create_sample_group(self):
        """Create a sample deal group for testing."""
        try:
            with transaction.atomic():
                # Get or create a crop
                crop, created = CropProfile.objects.get_or_create(
                    name='Tomato',
                    defaults={'description': 'Fresh tomatoes'}
                )
                
                # Get or create farmers with coordinates
                farmers = []
                for i in range(3):
                    farmer, created = CustomUser.objects.get_or_create(
                        username=f'test_farmer_{i}',
                        defaults={
                            'role': 'FARMER',
                            'latitude': 14.4753 + random.uniform(-0.1, 0.1),  # Around Kadapa
                            'longitude': 78.8355 + random.uniform(-0.1, 0.1),
                            'pincode': f'51600{i}',
                            'region': 'Kadapa'
                        }
                    )
                    farmers.append(farmer)
                
                # Create product listings
                listings = []
                for farmer in farmers:
                    listing = ProductListing.objects.create(
                        farmer=farmer,
                        crop=crop,
                        quantity_kg=100,
                        grade='A',
                        status='AVAILABLE'
                    )
                    listings.append(listing)
                
                # Create deal group
                deal_group = DealGroup.objects.create(
                    group_id=f'TEST-TOMATO-A-{random.randint(1000, 9999)}',
                    total_quantity_kg=300,
                    status='FORMED'
                )
                deal_group.products.set(listings)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created sample deal group: {deal_group.group_id} with {len(farmers)} farmers'
                    )
                )
                
                # Test V1 logistics
                self.test_v1_logistics_for_group(deal_group)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating sample group: {e}')
            )

    def test_v1_logistics_for_group(self, deal_group):
        """Test V1 logistics for a specific group."""
        try:
            self.stdout.write(f'\nTesting V1 logistics for group: {deal_group.group_id}')
            
            # Compute hub recommendation
            hub = compute_hub_recommendation(deal_group)
            
            if hub:
                self.stdout.write(
                    self.style.SUCCESS(f'V1 Hub selected: {hub.name}')
                )
                
                # Get logistics info
                logistics_info = get_logistics_info(deal_group)
                if logistics_info:
                    self.stdout.write(
                        f'Distance: ~{logistics_info["distances"]["median_km"]} km\n'
                        f'Farmers: {logistics_info["distances"]["farmer_count"]}'
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('V1 logistics failed - no hub selected')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error testing V1 logistics: {e}')
            )

    def test_v1_logistics(self):
        """Test V1 logistics system."""
        self.stdout.write('\n=== Testing V1 Logistics ===')
        
        # Check if we have hubs
        hub_count = HubPartner.objects.count()
        if hub_count == 0:
            self.stdout.write(
                self.style.WARNING('No hubs found. Run seed_hubs command first.')
            )
            return
        
        self.stdout.write(f'Found {hub_count} hubs')
        
        # Check if we have deal groups
        deal_groups = DealGroup.objects.filter(status__in=['FORMED', 'NEGOTIATING'])
        if not deal_groups.exists():
            self.stdout.write(
                self.style.WARNING('No active deal groups found for testing.')
            )
            return
        
        self.stdout.write(f'Found {deal_groups.count()} active deal groups')
        
        # Test each group
        for group in deal_groups[:3]:  # Test first 3 groups
            self.test_v1_logistics_for_group(group)

    def test_v2_logistics(self):
        """Test V2 logistics system."""
        self.stdout.write('\n=== Testing V2 Logistics ===')
        
        # Check if we have deal groups with V1 recommendations
        deal_groups = DealGroup.objects.filter(
            status__in=['FORMED', 'NEGOTIATING'],
            recommended_collection_point__isnull=False
        )
        
        if not deal_groups.exists():
            self.stdout.write(
                self.style.WARNING('No deal groups with V1 recommendations found.')
            )
            return
        
        self.stdout.write(f'Found {deal_groups.count()} groups with V1 recommendations')
        
        # Test V2 for each group
        for group in deal_groups[:2]:  # Test first 2 groups
            try:
                self.stdout.write(f'\nTesting V2 for group: {group.group_id}')
                
                # Get current method
                current_method = get_recommendation_method(group)
                self.stdout.write(f'Current method: {current_method}')
                
                # Try V2 optimization
                new_hub = find_optimal_hub_v2(group)
                
                if new_hub:
                    new_method = get_recommendation_method(group)
                    self.stdout.write(
                        self.style.SUCCESS(f'V2 completed. Method: {new_method}, Hub: {new_hub.name}')
                    )
                    
                    if new_method == 'V2' and new_hub != group.recommended_collection_point:
                        self.stdout.write(
                            self.style.SUCCESS('V2 found a different hub!')
                        )
                    else:
                        self.stdout.write('V2 kept the same hub or fell back to V1')
                else:
                    self.stdout.write(
                        self.style.WARNING('V2 failed, keeping V1 recommendation')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error testing V2 for group {group.id}: {e}')
                )

    def show_system_status(self):
        """Show current logistics system status."""
        self.stdout.write('\n=== Logistics System Status ===')
        
        # Hub count
        hub_count = HubPartner.objects.count()
        self.stdout.write(f'Hubs: {hub_count}')
        
        # Deal groups
        total_groups = DealGroup.objects.count()
        active_groups = DealGroup.objects.filter(status__in=['FORMED', 'NEGOTIATING']).count()
        groups_with_hubs = DealGroup.objects.filter(recommended_collection_point__isnull=False).count()
        
        self.stdout.write(f'Total deal groups: {total_groups}')
        self.stdout.write(f'Active groups: {active_groups}')
        self.stdout.write(f'Groups with hub recommendations: {groups_with_hubs}')
        
        # Method distribution
        v1_count = 0
        v2_count = 0
        
        for group in DealGroup.objects.filter(recommended_collection_point__isnull=False):
            method = get_recommendation_method(group)
            if method == 'V1':
                v1_count += 1
            elif method == 'V2':
                v2_count += 1
        
        self.stdout.write(f'V1 recommendations: {v1_count}')
        self.stdout.write(f'V2 recommendations: {v2_count}')
