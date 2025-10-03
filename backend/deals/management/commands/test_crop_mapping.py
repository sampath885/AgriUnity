from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Test crop mapping to fix the ML analysis issue"

    def handle(self, *args, **options):
        """Test the crop mapping functionality"""
        self.stdout.write("🧪 Testing Crop Mapping")
        self.stdout.write("=" * 40)
        
        try:
            from deals.agent_logic import DataIntegrationManager
            
            # Create data integrator
            self.stdout.write("🚀 Creating DataIntegrationManager...")
            data_integrator = DataIntegrationManager()
            
            # Test available crops
            self.stdout.write("\n🌾 Testing Available Crops:")
            available_crops = data_integrator.get_available_crops()
            self.stdout.write(f"  Available crops: {available_crops}")
            
            # Test crop standardization
            self.stdout.write("\n🔄 Testing Crop Standardization:")
            test_crops = ['WHEAT', 'wheat', 'Wheat', 'TOMATO', 'tomato', 'Tomato']
            
            for crop in test_crops:
                std_crop = data_integrator.get_standardized_crop_name(crop)
                self.stdout.write(f"  '{crop}' -> '{std_crop}'")
            
            # Test district standardization
            self.stdout.write("\n📍 Testing District Standardization:")
            test_districts = ['500001', 'Hyderabad', 'hyderabad', 'HYDERABAD']
            
            for district in test_districts:
                std_district = data_integrator.get_standardized_district_name(district)
                self.stdout.write(f"  '{district}' -> '{std_district}'")
            
            # Test market data retrieval
            self.stdout.write("\n📊 Testing Market Data Retrieval:")
            test_crop = 'Wheat'
            test_district = 'Hyderabad'
            
            market_data = data_integrator.get_market_data_for_crop_district(
                test_crop, test_district
            )
            
            if market_data:
                self.stdout.write(f"  ✅ Market data found for {test_crop} in {test_district}")
                self.stdout.write(f"    Data points: {market_data.get('data_points', 0)}")
                if 'price_analysis' in market_data:
                    price_analysis = market_data['price_analysis']
                    self.stdout.write(f"    Current price: ₹{price_analysis.get('current_price_per_kg', 0)}/kg")
                    self.stdout.write(f"    Average price: ₹{price_analysis.get('average_price_per_kg', 0)}/kg")
            else:
                self.stdout.write(f"  ❌ No market data found for {test_crop} in {test_district}")
            
            # Show crop mappings
            self.stdout.write("\n🔍 Crop Mappings:")
            for i, (key, value) in enumerate(data_integrator.crop_mappings.items()):
                if i < 20:  # Show first 20 mappings
                    self.stdout.write(f"  '{key}' -> '{value}'")
                else:
                    self.stdout.write(f"  ... and {len(data_integrator.crop_mappings) - 20} more")
                    break
            
            # Test the specific issue from the logs
            self.stdout.write("\n🔍 Testing WHEAT Analysis:")
            wheat_data = data_integrator.get_market_data_for_crop_district('WHEAT', '500001')
            if wheat_data:
                self.stdout.write(f"  ✅ WHEAT data found: {wheat_data.get('data_points', 0)} records")
                if 'price_analysis' in wheat_data:
                    price_analysis = wheat_data['price_analysis']
                    current_price = price_analysis.get('current_price_per_kg', 0)
                    self.stdout.write(f"  ✅ Current price: ₹{current_price}/kg")
                    if current_price > 0:
                        self.stdout.write("  🎉 WHEAT analysis is working!")
                    else:
                        self.stdout.write("  ⚠️ WHEAT price is still ₹0.00/kg")
            else:
                self.stdout.write("  ❌ No WHEAT data found")
            
            self.stdout.write("\n✅ Crop mapping test completed!")
            
        except Exception as e:
            self.stdout.write(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
