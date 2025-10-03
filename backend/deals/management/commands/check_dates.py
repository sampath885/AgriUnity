# backend/deals/management/commands/check_dates.py

import csv
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Check the actual date values in the CSV to see the format"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file to check')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_file}")
            )
            return
        
        self.stdout.write(f"🔍 Checking date values in: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Check first 10 rows for date values
                self.stdout.write(f"\n📅 Date Values in First 10 Rows:")
                for row_num, row in enumerate(reader, 1):
                    if row_num > 10:
                        break
                    
                    date_value = row.get('Price Date', '').strip()
                    self.stdout.write(f"   Row {row_num}: '{date_value}' (length: {len(date_value)})")
                
                # Check around the problematic row (97,518)
                self.stdout.write(f"\n🔍 Checking around problematic row 97,518:")
                file.seek(0)
                next(file)  # Skip header
                
                for row_num, line in enumerate(file, 1):
                    if 97510 <= row_num <= 97525:  # Check around the problem area
                        row = next(csv.reader([line]))
                        if len(row) >= 10:  # Ensure we have enough columns
                            date_value = row[9].strip()  # Price Date is 10th column (index 9)
                            self.stdout.write(f"   Row {row_num}: '{date_value}' (length: {len(date_value)})")
                    
                    if row_num > 97525:
                        break
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking dates: {str(e)}")
            )
