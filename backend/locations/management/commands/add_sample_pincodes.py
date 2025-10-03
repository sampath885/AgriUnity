# backend/locations/management/commands/add_sample_pincodes.py

from django.core.management.base import BaseCommand
from locations.models import PinCode

class Command(BaseCommand):
    help = "Add sample pincodes for testing"

    def handle(self, *args, **options):
        sample_pincodes = [
            {
                'code': '533289',
                'district': 'East Godavari',
                'state': 'Andhra Pradesh',
                'latitude': 16.5062,
                'longitude': 81.7272
            },
            {
                'code': '516001',
                'district': 'Kadapa',
                'state': 'Andhra Pradesh',
                'latitude': 14.4753,
                'longitude': 78.8354
            },
            {
                'code': '500001',
                'district': 'Hyderabad',
                'state': 'Telangana',
                'latitude': 17.3850,
                'longitude': 78.4867
            },
            {
                'code': '560001',
                'district': 'Bangalore',
                'state': 'Karnataka',
                'latitude': 12.9716,
                'longitude': 77.5946
            },
            {
                'code': '515631',
                'district': 'Anantapur',
                'state': 'Andhra Pradesh',
                'latitude': 14.6819,
                'longitude': 77.6006
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for pincode_data in sample_pincodes:
            pincode, created = PinCode.objects.update_or_create(
                code=pincode_data['code'],
                defaults={
                    'district': pincode_data['district'],
                    'state': pincode_data['state'],
                    'latitude': pincode_data['latitude'],
                    'longitude': pincode_data['longitude']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created pincode {pincode.code}: {pincode.district}, {pincode.state}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"↻ Updated pincode {pincode.code}: {pincode.district}, {pincode.state}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Sample pincodes added successfully!\n"
                f"   Created: {created_count}\n"
                f"   Updated: {updated_count}\n"
                f"   Total: {PinCode.objects.count()}"
            )
        )
