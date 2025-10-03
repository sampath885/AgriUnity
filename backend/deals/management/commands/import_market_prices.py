# backend/deals/management/commands/import_market_prices.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from deals.models import MarketPrice
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import market price data from CSV files for efficient bargaining"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file with market prices')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing (default: 1000)')
        parser.add_argument('--clear-existing', action='store_true', help='Clear existing market price data before import')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        clear_existing = options['clear_existing']

        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_file}")
            )
            return

        if clear_existing:
            self.stdout.write("Clearing existing market price data...")
            MarketPrice.objects.all().delete()
            cache.clear()
            self.stdout.write("Existing data cleared.")

        self.stdout.write(f"Starting import from: {csv_file}")
        self.stdout.write(f"Batch size: {batch_size}")

        try:
            total_imported = self._import_csv_data(csv_file, batch_size)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {total_imported} market price records!"
                )
            )
            
            # Clear cache after import
            cache.clear()
            self.stdout.write("Cache cleared after import.")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Import failed: {str(e)}")
            )
            logger.error(f"Market price import failed: {e}")

    def _import_csv_data(self, csv_file: str, batch_size: int) -> int:
        """Import CSV data in batches for memory efficiency"""
        total_imported = 0
        total_skipped = 0
        batch_data = []
        
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
            
            self.stdout.write(f"Detected delimiter: '{detected_delimiter}'")
            
            reader = csv.DictReader(file, delimiter=detected_delimiter)
            
            # Map common CSV column names to our model fields
            field_mapping = self._get_field_mapping(reader.fieldnames)
            
            self.stdout.write(f"Available columns: {list(reader.fieldnames)}")
            self.stdout.write(f"Field mapping: {field_mapping}")
            
            if not field_mapping:
                self.stdout.write(
                    self.style.ERROR("Could not map CSV columns to model fields")
                )
                return 0
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Parse and validate row data
                    market_price = self._parse_row(row, field_mapping, row_num, total_skipped)
                    if market_price:
                        batch_data.append(market_price)
                    else:
                        total_skipped += 1
                    
                    # Process batch when it reaches batch_size
                    if len(batch_data) >= batch_size:
                        imported_in_batch = self._process_batch(batch_data)
                        total_imported += imported_in_batch
                        batch_data = []
                        
                        # Progress report every 10 batches
                        if row_num % (batch_size * 10) == 0:
                            self.stdout.write(
                                f"📊 Progress: Row {row_num:,} | Imported: {total_imported:,} | Skipped: {total_skipped:,}"
                            )
                
                except Exception as e:
                    total_skipped += 1
                    if total_skipped % 1000 == 0:  # Only show every 1000 errors
                        self.stdout.write(
                            self.style.WARNING(f"⚠️ Skipped {total_skipped} rows with errors so far...")
                        )
                    continue
            
            # Process remaining batch
            if batch_data:
                imported_in_batch = self._process_batch(batch_data)
                total_imported += imported_in_batch
        
        # Final statistics
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Import Complete!\n"
                f"   Total Rows Processed: {total_imported + total_skipped:,}\n"
                f"   Successfully Imported: {total_imported:,}\n"
                f"   Skipped (Invalid Data): {total_skipped:,}\n"
                f"   Success Rate: {(total_imported / (total_imported + total_skipped) * 100):.1f}%"
            )
        )
        
        return total_imported

    def _get_field_mapping(self, fieldnames) -> dict:
        """Map CSV column names to model fields intelligently"""
        if not fieldnames:
            return {}
        
        # Map the user's actual CSV columns to our model fields
        field_variations = {
            'crop_name': ['commodity', 'commodit', 'crop', 'crop_name', 'product', 'item'],
            'region': ['state', 'district_name', 'district', 'market_name', 'market', 'region', 'location', 'mandi'],
            'price': ['modal_price', 'modal_pri', 'price', 'rate', 'cost', 'value', 'amount'],
            'date': ['price_date', 'price date', 'date', 'date_price', 'timestamp'],
            'quality_grade': ['grade', 'quality', 'quality_grade', 'class', 'variety'],
            'volume_kg': ['volume', 'quantity', 'kg', 'weight', 'volume_kg']
        }
        
        mapping = {}
        for model_field, variations in field_variations.items():
            for variation in variations:
                if variation.upper() in [col.upper() for col in fieldnames]:
                    # Find the exact column name (case-insensitive)
                    for col in fieldnames:
                        if col.upper() == variation.upper():
                            mapping[model_field] = col
                            break
                    break
        
        # Special handling for the user's CSV structure
        if 'STATE' in fieldnames and 'District Name' in fieldnames:
            mapping['state'] = 'STATE'
            mapping['district_name'] = 'District Name'
        
        if 'Min_Price' in fieldnames and 'Max_Price' in fieldnames:
            mapping['min_price'] = 'Min_Price'
            mapping['max_price'] = 'Max_Price'
        
        if 'Variety' in fieldnames:
            mapping['variety'] = 'Variety'
        
        if 'Market Name' in fieldnames:
            mapping['market_name'] = 'Market Name'
        
        # Explicit mapping for the exact column names we know exist
        if 'Commodity' in fieldnames:
            mapping['crop_name'] = 'Commodity'
        
        if 'Modal_Price' in fieldnames:
            mapping['price'] = 'Modal_Price'
        
        if 'Price Date' in fieldnames:
            mapping['date'] = 'Price Date'
        
        if 'Grade' in fieldnames:
            mapping['quality_grade'] = 'Grade'
        
        return mapping

    def _parse_row(self, row: dict, field_mapping: dict, row_num: int, total_skipped: int) -> MarketPrice:
        """Parse a single CSV row into a MarketPrice object"""
        try:
            # Extract crop name (Commodity column)
            crop_name = row.get(field_mapping.get('crop_name', ''), '').strip()
            if not crop_name:
                return None
            
            # Extract and combine region (STATE + District Name)
            region = 'Unknown'
            if 'state' in field_mapping and 'district_name' in field_mapping:
                state = row.get(field_mapping['state'], '').strip()
                district = row.get(field_mapping['district_name'], '').strip()
                if state and district:
                    region = f"{district}, {state}"
                elif state:
                    region = state
                elif district:
                    region = district
            else:
                region = row.get(field_mapping.get('region', ''), '').strip() or 'Unknown'
            
            # Extract and parse main price (Modal_Price column)
            price_str = row.get(field_mapping.get('price', ''), '0').strip()
            try:
                price = float(price_str.replace(',', '').replace('₹', '').replace('Rs', ''))
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f"Invalid price '{price_str}' in row {row_num}")
                )
                return None
            
            # Extract and parse date (Price Date column)
            date_str = row.get(field_mapping.get('date', ''), '').strip()
            
            # Skip rows with empty dates instead of failing
            if not date_str:
                # Only show warning every 1000 skipped rows to avoid console spam
                if total_skipped % 1000 == 0:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Skipped {total_skipped} rows with empty dates so far...")
                    )
                return None
            
            try:
                # Try multiple date formats - user's CSV uses DD-MM-YYYY format
                date_formats = ['%d-%m-%Y', '%d-%m-%y', '%d/%m/%Y', '%d/%m/%y', '%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%Y/%m/%d']
                parsed_date = None
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Row {row_num}: Could not parse date '{date_str}' - skipping row")
                    )
                    return None
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Row {row_num}: Date parsing error '{date_str}' - {str(e)} - skipping row")
                )
                return None
            
            # Extract quality grade (combine Grade and Variety if available)
            quality_grade = None
            if 'grade' in field_mapping and row.get(field_mapping['grade']):
                grade = row.get(field_mapping['grade'], '').strip()
                variety = row.get(field_mapping.get('variety', ''), '').strip()
                if grade and variety:
                    quality_grade = f"{grade} - {variety}"
                elif grade:
                    quality_grade = grade
                elif variety:
                    quality_grade = variety
            
            # Extract volume (optional)
            volume_kg = None
            volume_str = row.get(field_mapping.get('volume_kg', ''), '').strip()
            if volume_str:
                try:
                    volume_kg = float(volume_str.replace(',', ''))
                except ValueError:
                    pass
            
            return MarketPrice(
                crop_name=crop_name,
                region=region,
                price=price,
                date=parsed_date,
                quality_grade=quality_grade,
                volume_kg=volume_kg,
                source='CSV_Import'
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Error parsing row {row_num}: {str(e)}")
            )
            return None

    def _process_batch(self, batch_data: list) -> int:
        """Process a batch of MarketPrice objects"""
        try:
            with transaction.atomic():
                MarketPrice.objects.bulk_create(
                    batch_data,
                    ignore_conflicts=True,  # Skip duplicates
                    batch_size=1000
                )
            return len(batch_data)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Batch processing failed: {str(e)}")
            )
            return 0
