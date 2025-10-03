"""
Management command to seed hub partners for testing logistics.
"""

from django.core.management.base import BaseCommand
from hubs.models import HubPartner


class Command(BaseCommand):
    help = 'Seed hub partners with coordinates for testing logistics'

    def handle(self, *args, **options):
        # Sample hub data for testing
        hubs_data = [
            {
                'name': 'Kadapa, Andhra Pradesh',
                'address': 'Kadapa, Andhra Pradesh 516001',
                'latitude': 14.4753,
                'longitude': 78.8355
            },
            {
                'name': 'Anantapur, Andhra Pradesh',
                'address': 'Anantapur, Andhra Pradesh 515001',
                'latitude': 14.6819,
                'longitude': 77.6006
            },
            {
                'name': 'Kurnool, Andhra Pradesh',
                'address': 'Kurnool, Andhra Pradesh 518001',
                'latitude': 15.8281,
                'longitude': 78.0373
            },
            {
                'name': 'Chittoor, Andhra Pradesh',
                'address': 'Chittoor, Andhra Pradesh 517001',
                'latitude': 13.2156,
                'longitude': 79.1004
            },
            {
                'name': 'Nellore, Andhra Pradesh',
                'address': 'Nellore, Andhra Pradesh 524001',
                'latitude': 14.4426,
                'longitude': 79.9865
            },
            {
                'name': 'Guntur, Andhra Pradesh',
                'address': 'Guntur, Andhra Pradesh 522001',
                'latitude': 16.2992,
                'longitude': 80.4575
            },
            {
                'name': 'Vijayawada, Andhra Pradesh',
                'address': 'Vijayawada, Andhra Pradesh 520001',
                'latitude': 16.5062,
                'longitude': 80.6480
            },
            {
                'name': 'Rajahmundry, Andhra Pradesh',
                'address': 'Rajahmundry, Andhra Pradesh 533101',
                'latitude': 17.0005,
                'longitude': 81.8040
            }
        ]

        created_count = 0
        updated_count = 0

        for hub_data in hubs_data:
            hub, created = HubPartner.objects.get_or_create(
                name=hub_data['name'],
                defaults={
                    'address': hub_data['address'],
                    'latitude': hub_data['latitude'],
                    'longitude': hub_data['longitude']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created hub: {hub.name}')
                )
            else:
                # Update existing hub with new coordinates if they changed
                if (hub.latitude != hub_data['latitude'] or 
                    hub.longitude != hub_data['longitude'] or
                    hub.address != hub_data['address']):
                    hub.latitude = hub_data['latitude']
                    hub.longitude = hub_data['longitude']
                    hub.address = hub_data['address']
                    hub.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated hub: {hub.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed hubs. Created: {created_count}, Updated: {updated_count}'
            )
        )
