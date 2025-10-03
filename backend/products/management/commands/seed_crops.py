from django.core.management.base import BaseCommand

from products.models import CropProfile


DEFAULT_CROPS = [
    # name, perishability_score (1-10), is_storable, has_msp, min_group_kg
    # Only crops that exist in BIG_DATA.csv
    ("Tomato", 9, False, False, 20000),
    ("Onion", 6, True, False, 15000),
    ("Potato", 4, True, False, 15000),
    ("Rice", 3, True, True, 10000),
    ("Wheat", 3, True, True, 10000),
    # Removed "Chili" - not in BIG_DATA.csv, causes ML analysis to fail
]


class Command(BaseCommand):
    help = "Seeds common crops (idempotent). Only crops with BIG_DATA.csv support."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        
        for name, perishability, storable, has_msp, min_group in DEFAULT_CROPS:
            obj, was_created = CropProfile.objects.get_or_create(
                name=name,
                defaults={
                    "perishability_score": perishability,
                    "is_storable": storable,
                    "has_msp": has_msp,
                    "min_group_kg": min_group,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"✅ Created crop: {name}")
            else:
                # Update existing crop
                obj.perishability_score = perishability
                obj.is_storable = storable
                obj.has_msp = has_msp
                obj.min_group_kg = min_group
                obj.save()
                updated += 1
                self.stdout.write(f"🔄 Updated crop: {name}")
        
        # Show summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Crops updated. New: {created}, Updated: {updated}, "
                f"Total now: {CropProfile.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f"✅ Supported crops (exist in BIG_DATA.csv): {[crop[0] for crop in DEFAULT_CROPS]}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f"⚠️ Only these 5 crops are supported by the ML system"
            )
        )


