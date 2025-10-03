# backend/locations/management/commands/seed_pincodes.py

import csv
from django.core.management.base import BaseCommand
from locations.models import PinCode  # Make sure this import path is correct for your project

class Command(BaseCommand):
    help = "Seeds the PinCode table from a CSV, automatically cleaning common data errors."

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to the CSV file containing pincode data.')

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Start with a clean slate by deleting old records.
        self.stdout.write(self.style.WARNING("Deleting old PinCode data..."))
        count, _ = PinCode.objects.all().delete()
        self.stdout.write(f"Deleted {count} old records.")
        
        self.stdout.write(f"Starting to seed PinCodes from: {file_path}")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        try:
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Define the exact headers we expect to find in the CSV file.
                expected_headers = ['Pincode', 'Latitude', 'Longitude', 'District', 'StateName']
                
                # Validate that all required headers are present.
                if not all(header in reader.fieldnames for header in expected_headers):
                    self.stdout.write(self.style.ERROR(f"CSV file is missing one of the required headers: {expected_headers}"))
                    self.stdout.write(self.style.WARNING(f"Found headers: {reader.fieldnames}"))
                    return

                total_rows = sum(1 for row in reader) # Get total rows for progress
                f.seek(0) # Reset reader to the start
                reader = csv.DictReader(f) # Re-initialize reader
                
                self.stdout.write(f"Found {total_rows} rows to process...")

                for i, row in enumerate(reader):
                    try:
                        # --- SELF-CLEANING AND VALIDATION BLOCK ---
                        # 1. Extract the raw string data safely using .get()
                        pincode_val = row.get('Pincode', '').strip()
                        latitude_str = row.get('Latitude', '').strip()
                        longitude_str = row.get('Longitude', '').strip()
                        district_val = row.get('District', '').strip()
                        state_val = row.get('StateName', '').strip()

                        # 2. Basic validation: skip rows with empty essential string values.
                        if not all([pincode_val, district_val, state_val]):
                            skipped_count += 1
                            continue
                        
                        # 3. Skip rows where latitude or longitude is 'NA' or empty.
                        if latitude_str.upper() == 'NA' or longitude_str.upper() == 'NA' or not latitude_str or not longitude_str:
                            skipped_count += 1
                            continue
                        
                        # 4. Clean the specific formatting errors (remove 'N', 'S', 'E', 'W', and '-')
                        latitude_str = latitude_str.upper().replace('N', '').replace('S', '').replace('-', '').strip()
                        longitude_str = longitude_str.upper().replace('E', '').replace('W', '').replace('-', '').strip()
                        
                        # 5. Now it should be safe to convert to float.
                        latitude_val = float(latitude_str)
                        longitude_val = float(longitude_str)
                        
                        # Use update_or_create to insert or update the data.
                        obj, created = PinCode.objects.update_or_create(
                            code=pincode_val,
                            defaults={
                                'latitude': latitude_val,
                                'longitude': longitude_val,
                                'district': district_val,
                                'state': state_val,
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                        # Provide progress feedback for large files.
                        if (i + 1) % 5000 == 0:
                            self.stdout.write(f"  ... {i + 1} / {total_rows} rows processed...")

                    except (ValueError, TypeError) as e:
                        # This will now only catch truly unfixable errors (e.g., text that can't be cleaned)
                        self.stdout.write(self.style.WARNING(f"Skipping row with unfixable data: {row}. Error: {e}"))
                        skipped_count += 1
                        continue

            self.stdout.write(self.style.SUCCESS(f"\nPinCode seeding complete."))
            self.stdout.write(f"Successfully created: {created_count} records.")
            self.stdout.write(f"Successfully updated: {updated_count} records.")
            self.stdout.write(f"Skipped due to missing or unfixable data: {skipped_count} records.")
            self.stdout.write(f"Total PinCodes in database: {PinCode.objects.count()}")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: The file was not found at '{file_path}'"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))