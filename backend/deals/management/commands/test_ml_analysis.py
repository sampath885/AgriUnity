from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Test the complete ML analysis function to verify it's working"

    def handle(self, *args, **options):
        """Test the complete ML analysis function"""
        self.stdout.write("🤖 Testing Complete ML Analysis")
        self.stdout.write("=" * 50)
        
        try:
            from deals.agent_logic import analyze_and_respond_to_offer
            
            # Test the exact scenario from the logs
            self.stdout.write("\n🧪 Testing WHEAT Analysis (Same as website):")
            self.stdout.write("  Crop: WHEAT")
            self.stdout.write("  District: 500001 (pincode)")
            self.stdout.write("  Offer Price: ₹5.00/kg")
            
            # Call the main function
            result = analyze_and_respond_to_offer(
                crop_name='WHEAT',
                district='500001',
                offer_price=5.0,
                user_context={'role': 'BUYER', 'location': 'Hyderabad'}
            )
            
            if result:
                self.stdout.write("\n✅ ML Analysis Result:")
                self.stdout.write(f"  Action: {result.action}")
                self.stdout.write(f"  New Price: {result.new_price}")
                self.stdout.write(f"  Confidence: {result.confidence_level}")
                
                # Check if ML returned real data
                if hasattr(result, 'market_analysis') and result.market_analysis:
                    ml_data = result.market_analysis
                    if isinstance(ml_data, dict):
                        predicted_price = ml_data.get('predicted_price', 0)
                        data_points = ml_data.get('historical_context', {}).get('data_points_analyzed', 0)
                        
                        self.stdout.write(f"\n📊 Market Analysis:")
                        self.stdout.write(f"  Predicted Price: ₹{predicted_price}/kg")
                        self.stdout.write(f"  Data Points: {data_points}")
                        
                        if predicted_price > 0 and data_points > 0:
                            self.stdout.write("  🎉 ML analysis working with real data!")
                            
                            # Show more details
                            if 'price_breakdown' in ml_data:
                                breakdown = ml_data['price_breakdown']
                                self.stdout.write(f"  Base Market Price: ₹{breakdown.get('base_market_price', 0)}/kg")
                                self.stdout.write(f"  Logistics Cost: ₹{breakdown.get('logistics_cost', 0)}/kg")
                            
                            if 'crop_volatility' in ml_data.get('market_analysis', {}):
                                volatility = ml_data['market_analysis']['crop_volatility']
                                self.stdout.write(f"  Risk Level: {volatility.get('risk_level', 'Unknown')}")
                                self.stdout.write(f"  Price Volatility: {volatility.get('standard_deviation', 0):.2f}")
                        else:
                            self.stdout.write("  ⚠️ ML analysis still returning no data")
                    else:
                        self.stdout.write("  ⚠️ Market analysis format unexpected")
                else:
                    self.stdout.write("  ⚠️ No market analysis in result")
                
                # Show the AI agent message
                if hasattr(result, 'message_to_buyer'):
                    self.stdout.write(f"\n🤖 AI Agent Message:")
                    self.stdout.write(f"  {result.message_to_buyer[:200]}...")
                
            else:
                self.stdout.write("  ❌ ML analysis failed - no result returned")
            
            # Test with other crops
            self.stdout.write("\n🧪 Testing Other Crops:")
            test_crops = ['TOMATO', 'ONION', 'POTATO']
            
            for crop in test_crops:
                self.stdout.write(f"\n  Testing {crop}:")
                try:
                    crop_result = analyze_and_respond_to_offer(
                        crop_name=crop,
                        district='500001',
                        offer_price=4.0,
                        user_context={'role': 'BUYER', 'location': 'Hyderabad'}
                    )
                    
                    if crop_result and hasattr(crop_result, 'market_analysis'):
                        ml_data = crop_result.market_analysis
                        predicted_price = ml_data.get('predicted_price', 0)
                        data_points = ml_data.get('historical_context', {}).get('data_points_analyzed', 0)
                        
                        if predicted_price > 0 and data_points > 0:
                            self.stdout.write(f"    ✅ {crop}: ₹{predicted_price}/kg ({data_points} data points)")
                        else:
                            self.stdout.write(f"    ⚠️ {crop}: No data (₹{predicted_price}/kg, {data_points} points)")
                    else:
                        self.stdout.write(f"    ❌ {crop}: Analysis failed")
                        
                except Exception as e:
                    self.stdout.write(f"    ❌ {crop}: Error - {e}")
            
            self.stdout.write("\n✅ ML Analysis Test Completed!")
            
        except Exception as e:
            self.stdout.write(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
