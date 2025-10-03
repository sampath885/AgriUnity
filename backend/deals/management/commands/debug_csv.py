# backend/deals/management/commands/debug_csv.py

import csv
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Debug CSV file to see exactly what's in the data"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file to debug')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_file}")
            )
            return
        
        self.stdout.write(f"🔍 Debugging CSV file: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                # Read first few lines as raw text
                self.stdout.write(f"\n📄 Raw File Content (first 3 lines):")
                file.seek(0)
                for i, line in enumerate(file, 1):
                    if i > 3:
                        break
                    self.stdout.write(f"   Line {i}: {repr(line.strip())}")
                
                # Now try CSV parsing
                file.seek(0)
                reader = csv.DictReader(file)
                
                self.stdout.write(f"\n📋 CSV Column Names:")
                for i, col in enumerate(reader.fieldnames):
                    self.stdout.write(f"   {i+1:2d}. '{col}' (length: {len(col)})")
                
                # Check first few rows
                self.stdout.write(f"\n📊 First 3 Rows Data:")
                for row_num, row in enumerate(reader, 1):
                    if row_num > 3:
                        break
                    
                    self.stdout.write(f"\n   Row {row_num}:")
                    for col in reader.fieldnames:
                        value = row.get(col, '')
                        self.stdout.write(f"     {col}: '{value}' (length: {len(value)}, type: {type(value)})")
                
                # Check around problematic area
                self.stdout.write(f"\n🔍 Checking around row 67,827 (where empty dates started):")
                file.seek(0)
                next(file)  # Skip header
                
                for row_num, line in enumerate(file, 1):
                    if 67820 <= row_num <= 67835:  # Check around the problem area
                        row = next(csv.reader([line]))
                        if len(row) >= 10:  # Ensure we have enough columns
                            date_value = row[9].strip()  # Price Date is 10th column (index 9)
                            self.stdout.write(f"   Row {row_num}: Date field = '{date_value}' (length: {len(date_value)})")
                    
                    if row_num > 67835:
                        break
                
                # Check file encoding and BOM
                file.seek(0)
                first_bytes = file.read(10)
                self.stdout.write(f"\n🔍 File Analysis:")
                self.stdout.write(f"   First 10 bytes: {repr(first_bytes)}")
                bom_check = first_bytes.startswith(b'\xef\xbb\xbf')
                self.stdout.write(f"   Has BOM: {bom_check}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error debugging CSV: {str(e)}")
            )
