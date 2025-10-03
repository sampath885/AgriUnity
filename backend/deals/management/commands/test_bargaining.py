# Update deals/management/commands/test_bargaining.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from deals.models import DealGroup, MarketPrice
from deals.agent_logic import get_negotiation_agent, MarketDataCache
from datetime import datetime, timedelta
import time

class Command(BaseCommand):
    help = 'Test the enhanced ML bargaining system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deal-group-id',
            type=int,
            help='Test bargaining for a specific deal group'
        )
        parser.add_argument(
            '--performance-test',
            action='store_true',
            help='Run performance benchmarks'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear cache before testing'
        )

    def handle(self, *args, **options):
        if options['clear_cache']:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write("✅ Cache cleared")

        if options['performance_test']:
            self._run_performance_test()
        elif options['deal_group_id']:
            self._test_specific_group(options['deal_group_id'])
        else:
            self._run_basic_test()

    def _run_performance_test(self):
        """Run comprehensive performance benchmarks"""
        self.stdout.write("🚀 Running Performance Benchmark...")
        
        # Test ML pricing engine
        self._test_ml_pricing_engine()
        
        # Test market data cache
        self._test_cache_performance()
        
        # Test bargaining speed
        self._test_bargaining_speed()

    def _test_ml_pricing_engine(self):
        """Test the ML pricing engine performance"""
        self.stdout.write("\n�� Testing ML Pricing Engine...")
        
        try:
            from deals.agent_logic import MLPricingEngine
            
            ml_engine = MLPricingEngine()
            
            # Test scenarios
            test_scenarios = [
                ('Potato', 'hyderabad', '2025-06-15'),
                ('Onion', 'warangal', '2025-12-10'),
                ('Tomato', 'nalgonda', '2025-07-20')
            ]
            
            for crop, district, date_str in test_scenarios:
                start_time = time.time()
                
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    analysis = ml_engine.predict_price_with_analysis(crop, district, date_obj)
                    
                    processing_time = time.time() - start_time
                    
                    self.stdout.write(f"\n✅ {crop} in {district} ({date_str}):")
                    predicted_price = analysis.get('predicted_price', 'N/A')
                    predicted_price_quintal = analysis.get('predicted_price_quintal', 'N/A')
                    
                    if predicted_price != 'N/A':
                        self.stdout.write(f"   Predicted Price: ₹{predicted_price}/kg (₹{predicted_price_quintal}/quintal)")
                    else:
                        self.stdout.write(f"   Predicted Price: {predicted_price}")
                    
                    self.stdout.write(f"   Confidence: {analysis.get('confidence_level', 'N/A')}")
                    self.stdout.write(f"   Processing Time: {processing_time:.3f}s")
                    
                    # Show unit info
                    unit_info = analysis.get('unit_info', {})
                    if unit_info:
                        self.stdout.write(f"   Units: {unit_info.get('display_unit', 'N/A')} (from {unit_info.get('source_unit', 'N/A')})")
                        self.stdout.write(f"   Buyer Quantity: {unit_info.get('buyer_quantity', 'N/A')}")
                    
                    # Show market analysis
                    market_analysis = analysis.get('market_analysis', {})
                    if market_analysis:
                        self.stdout.write(f"   Market Trend: {market_analysis.get('current_month_trend', 'N/A')}")
                        self.stdout.write(f"   Risk Level: {market_analysis.get('crop_volatility', {}).get('risk_level', 'N/A')}")
                    
                except Exception as e:
                    self.stdout.write(f"❌ Error testing {crop}: {str(e)}")
            
        except Exception as e:
            self.stdout.write(f"❌ ML Pricing Engine test failed: {str(e)}")

    def _test_cache_performance(self):
        """Test market data cache performance"""
        self.stdout.write("\n📊 Testing Market Data Cache Performance...")
        
        try:
            # Test with real data
            crop = 'Potato'
            region = 'Andhra Pradesh'
            date = datetime.now()
            
            # First call (cache miss)
            start_time = time.time()
            data1 = MarketDataCache().get_market_data(crop, region, date)
            first_call_time = time.time() - start_time
            
            # Second call (cache hit)
            start_time = time.time()
            data2 = MarketDataCache().get_market_data(crop, region, date)
            second_call_time = time.time() - start_time
            
            self.stdout.write(f"✅ {crop} in {region}:")
            self.stdout.write(f"   First call: {first_call_time:.3f}s")
            self.stdout.write(f"   Second call: {second_call_time:.3f}s")
            
            if second_call_time > 0:
                speedup = first_call_time / second_call_time
                self.stdout.write(f"   Speedup: {speedup:.1f}x")
            
            # Show data quality
            if data1 and isinstance(data1, dict):
                self.stdout.write(f"   Data Points: {data1.get('historical_context', {}).get('data_points_analyzed', 'N/A')}")
                self.stdout.write(f"   Confidence: {data1.get('confidence_level', 'N/A')}")
            
        except Exception as e:
            self.stdout.write(f"❌ Cache performance test failed: {str(e)}")

    def _test_bargaining_speed(self):
        """Test bargaining agent speed"""
        self.stdout.write("\n⚡ Testing Bargaining Agent Speed...")
        
        try:
            agent = get_negotiation_agent()
            
            # Create a mock deal group for testing
            mock_deal_group = self._create_mock_deal_group()
            
            # Test multiple offers
            test_offers = [40, 50, 60, 70, 80]
            
            total_time = 0
            successful_offers = 0
            
            for offer in test_offers:
                start_time = time.time()
                
                try:
                    decision = agent.analyze_offer(mock_deal_group, offer, "test_buyer")
                    processing_time = time.time() - start_time
                    
                    self.stdout.write(f"Offer ₹{offer}/kg: {processing_time:.3f}s - {decision.action}")
                    total_time += processing_time
                    successful_offers += 1
                    
                except Exception as e:
                    self.stdout.write(f"Offer ₹{offer}/kg: Failed - {str(e)}")
            
            if successful_offers > 0:
                avg_time = total_time / successful_offers
                self.stdout.write(f"\n📊 Performance Summary:")
                self.stdout.write(f"   Average processing time: {avg_time:.3f}s")
                self.stdout.write(f"   Total time for {successful_offers} offers: {total_time:.3f}s")
                
                if avg_time < 1.0:
                    self.stdout.write("   ✅ Excellent performance! Bargaining is fast and efficient.")
                elif avg_time < 3.0:
                    self.stdout.write("   ⚠️ Good performance, but could be optimized further.")
                else:
                    self.stdout.write("   ❌ Performance needs improvement.")
            
        except Exception as e:
            self.stdout.write(f"❌ Bargaining speed test failed: {str(e)}")

    def _create_mock_deal_group(self):
        """Create a mock deal group for testing"""
        try:
            # Try to get an existing deal group
            existing_group = DealGroup.objects.first()
            if existing_group:
                return existing_group
            
            # Create a mock one if none exists
            mock_group = DealGroup(
                group_id="TEST-GROUP-001",
                total_quantity_kg=1000,
                status="FORMED"
            )
            mock_group.save()
            return mock_group
            
        except Exception as e:
            self.stdout.write(f"⚠️ Could not create mock deal group: {str(e)}")
            return None

    def _test_specific_group(self, group_id):
        """Test bargaining for a specific deal group"""
        try:
            deal_group = DealGroup.objects.get(id=group_id)
            self.stdout.write(f"�� Testing bargaining for group: {deal_group.group_id}")
            
            agent = get_negotiation_agent()
            
            # Test with different offer prices
            test_offers = [45, 55, 65]
            
            for offer in test_offers:
                self.stdout.write(f"\n--- Testing Offer: ₹{offer}/kg ---")
                
                try:
                    decision = agent.analyze_offer(deal_group, offer, "test_buyer")
                    
                    self.stdout.write(f"✅ Action: {decision.action}")
                    if decision.new_price:
                        self.stdout.write(f"💰 New Price: ₹{decision.new_price}/kg")
                    self.stdout.write(f"📝 Justification: {decision.justification_for_farmers}")
                    
                    # Show market analysis if available
                    if hasattr(decision, 'market_analysis') and decision.market_analysis:
                        self.stdout.write(f"📊 Market Analysis Available")
                        self.stdout.write(f"   Confidence: {decision.confidence_level}")
                        self.stdout.write(f"   Risk Assessment: {decision.risk_assessment}")
                    
                except Exception as e:
                    self.stdout.write(f"❌ Error processing offer ₹{offer}/kg: {str(e)}")
            
        except DealGroup.DoesNotExist:
            self.stdout.write(f"❌ Deal group {group_id} not found")
        except Exception as e:
            self.stdout.write(f"❌ Error testing group {group_id}: {str(e)}")

    def _run_basic_test(self):
        """Run basic functionality test"""
        self.stdout.write("🧪 Running Basic Functionality Test...")
        
        try:
            # Test market data availability
            crop_count = MarketPrice.objects.values('crop_name').distinct().count()
            region_count = MarketPrice.objects.values('region').distinct().count()
            total_records = MarketPrice.objects.count()
            
            self.stdout.write(f"✅ Market Data Available:")
            self.stdout.write(f"   Crops: {crop_count}")
            self.stdout.write(f"   Regions: {region_count}")
            self.stdout.write(f"   Total Records: {total_records}")
            
            # Test ML pricing engine
            self._test_ml_pricing_engine()
            
        except Exception as e:
            self.stdout.write(f"❌ Basic test failed: {str(e)}")