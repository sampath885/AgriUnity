# backend/deals/management/commands/inspect_csv.py

import csv
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Inspect CSV file structure to see column names and sample data"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file to inspect')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_file}")
            )
            return
        
        self.stdout.write(f"🔍 Inspecting CSV file: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                
                # Common delimiters to try
                delimiters = [',', ';', '\t', '|']
                detected_delimiter = ','
                
                for delimiter in delimiters:
                    if delimiter in sample:
                        detected_delimiter = delimiter
                        break
                
                self.stdout.write(f"📊 Detected delimiter: '{detected_delimiter}'")
                
                reader = csv.DictReader(file, delimiter=detected_delimiter)
                
                # Show column names
                self.stdout.write(f"\n📋 CSV Column Names:")
                for i, col in enumerate(reader.fieldnames):
                    self.stdout.write(f"   {i+1:2d}. '{col}'")
                
                # Show first few rows as sample
                self.stdout.write(f"\n📄 Sample Data (first 3 rows):")
                for row_num, row in enumerate(reader, 1):
                    if row_num > 3:
                        break
                    
                    self.stdout.write(f"\n   Row {row_num}:")
                    for col in reader.fieldnames[:5]:  # Show first 5 columns
                        value = row.get(col, '')
                        if len(value) > 50:
                            value = value[:50] + "..."
                        self.stdout.write(f"     {col}: {value}")
                    
                    if len(reader.fieldnames) > 5:
                        self.stdout.write(f"     ... and {len(reader.fieldnames) - 5} more columns")
                
                # Count total rows
                file.seek(0)
                next(file)  # Skip header
                total_rows = sum(1 for line in file)
                
                self.stdout.write(f"\n📊 Total Rows: {total_rows:,}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error inspecting CSV: {str(e)}")
            )
