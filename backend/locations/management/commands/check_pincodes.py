# backend/locations/management/commands/check_pincodes.py

from django.core.management.base import BaseCommand
from locations.models import PinCode


class Command(BaseCommand):
    help = "Check the current state of pincodes in the database."

    def handle(self, *args, **options):
        total_pincodes = PinCode.objects.count()
        self.stdout.write(f"Total pincodes in database: {total_pincodes}")
        
        if total_pincodes == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No pincodes found! You need to seed the database first.\n"
                    "Run: python manage.py seed_pincodes --file path/to/your/pincode_csv.csv"
                )
            )
            return
        
        # Show some sample pincodes
        self.stdout.write("\nSample pincodes:")
        sample_pincodes = PinCode.objects.all()[:10]
        for pincode in sample_pincodes:
            self.stdout.write(
                f"  {pincode.code} -> {pincode.district}, {pincode.state} "
                f"({pincode.latitude}, {pincode.longitude})"
            )
        
        # Check for specific test pincodes
        test_pincodes = ['516001', '515631', '500001', '560001']
        self.stdout.write("\nChecking test pincodes:")
        for test_code in test_pincodes:
            try:
                pincode = PinCode.objects.get(code=test_code)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {test_code} -> {pincode.district}, {pincode.state}"
                    )
                )
            except PinCode.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {test_code} -> NOT FOUND")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDatabase is ready with {total_pincodes} pincodes!"
            )
        )
