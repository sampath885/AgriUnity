# backend/deals/management/commands/test_ai_advisor.py
"""
Test command for the AI Agricultural Advisor
"""

from django.core.management.base import BaseCommand
from deals.ai_advisor import agri_genie
from django.utils import timezone

class Command(BaseCommand):
    help = 'Test the AI Agricultural Advisor functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['crop_advice', 'market_analysis', 'group_analysis', 'selling_strategy', 'all'],
            default='all',
            help='Type of test to run'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        
        self.stdout.write("🧠 Testing AI Agricultural Advisor...")
        self.stdout.write("=" * 50)
        
        if test_type == 'crop_advice' or test_type == 'all':
            self._test_crop_advice()
        
        if test_type == 'market_analysis' or test_type == 'all':
            self._test_market_analysis()
        
        if test_type == 'selling_strategy' or test_type == 'all':
            self._test_selling_strategy()
        
        if test_type == 'group_analysis' or test_type == 'all':
            self._test_group_analysis()
        
        self.stdout.write("=" * 50)
        self.stdout.write("✅ AI Advisor testing completed!")

    def _test_crop_advice(self):
        """Test crop advice functionality"""
        self.stdout.write("\n🌾 Testing Crop Advice...")
        
        # Test different crops and regions
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra'),
            ('Tomato', 'Karnataka'),
            ('Rice', 'Tamil Nadu'),
            ('Wheat', 'Punjab')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n📊 Testing {crop} in {region}:")
                
                # Get comprehensive crop advice
                advice = agri_genie.crop_advisor.get_crop_advice(crop, region)
                
                if 'error' not in advice:
                    self.stdout.write(f"  ✅ Crop: {advice['crop_name']}")
                    self.stdout.write(f"  ✅ Region: {advice['region']}")
                    
                    # Market analysis
                    market = advice.get('market_analysis', {})
                    if 'ml_prediction' in market:
                        ml_pred = market['ml_prediction']
                        self.stdout.write(f"  🎯 ML Prediction: ₹{ml_pred.get('predicted_price_kg', 0):.2f}/kg")
                        self.stdout.write(f"  🎯 Confidence: {ml_pred.get('confidence', 'Unknown')}")
                    
                    # Seasonal advice
                    seasonal = advice.get('seasonal_advice', {})
                    if 'timing_advice' in seasonal:
                        self.stdout.write(f"  📅 {seasonal['timing_advice']}")
                    
                    # Regional insights
                    regional = advice.get('regional_insights', {})
                    if 'avg_price_kg' in regional:
                        self.stdout.write(f"  🏘️ Regional Avg: ₹{regional['avg_price_kg']:.2f}/kg")
                        self.stdout.write(f"  🏘️ Market Stability: {regional.get('market_stability', 'Unknown')}")
                    
                    # Selling recommendations
                    selling = advice.get('selling_recommendations', {})
                    if 'recommendation' in selling:
                        self.stdout.write(f"  💰 {selling['recommendation']}")
                        self.stdout.write(f"  💰 Strategy: {selling.get('strategy', 'Unknown')}")
                        self.stdout.write(f"  💰 Urgency: {selling.get('urgency', 'Unknown')}")
                
                else:
                    self.stdout.write(f"  ❌ Error: {advice['error']}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_market_analysis(self):
        """Test market analysis functionality"""
        self.stdout.write("\n📈 Testing Market Analysis...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n📊 Market Analysis for {crop} in {region}:")
                
                # Get market analysis
                analysis = agri_genie.crop_advisor._analyze_current_market(
                    crop, region, timezone.now().date()
                )
                
                if 'ml_prediction' in analysis:
                    ml_pred = analysis['ml_prediction']
                    self.stdout.write(f"  🎯 ML Prediction: ₹{ml_pred.get('predicted_price_kg', 0):.2f}/kg")
                    self.stdout.write(f"  🎯 Model Type: {ml_pred.get('model_type', 'Unknown')}")
                
                if 'price_trends' in analysis:
                    trends = analysis['price_trends']
                    if 'trend' in trends:
                        self.stdout.write(f"  📈 Price Trend: {trends['trend']}")
                        self.stdout.write(f"  📈 Description: {trends.get('trend_description', 'Unknown')}")
                        self.stdout.write(f"  📈 Strength: {trends.get('trend_strength', 0)}%")
                
                if 'market_sentiment' in analysis:
                    sentiment = analysis['market_sentiment']
                    if 'volume_sentiment' in sentiment:
                        self.stdout.write(f"  😊 Volume Sentiment: {sentiment['volume_sentiment']}")
                    if 'stability_sentiment' in sentiment:
                        self.stdout.write(f"  🎯 Stability: {sentiment['stability_sentiment']}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_selling_strategy(self):
        """Test selling strategy functionality"""
        self.stdout.write("\n💰 Testing Selling Strategy...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n💡 Selling Strategy for {crop} in {region}:")
                
                # Get selling recommendations
                strategy = agri_genie.crop_advisor._get_selling_recommendations(
                    crop, region, timezone.now().date()
                )
                
                if 'error' not in strategy:
                    self.stdout.write(f"  💰 Current Price: ₹{strategy.get('current_price_quintal', 0):.2f}/quintal")
                    self.stdout.write(f"  💰 Historical Avg: ₹{strategy.get('historical_average_quintal', 0):.2f}/quintal")
                    self.stdout.write(f"  💰 Price Difference: ₹{strategy.get('price_difference', 0):.2f}")
                    self.stdout.write(f"  💰 Price % Change: {strategy.get('price_percentage', 0)}%")
                    self.stdout.write(f"  💰 Recommendation: {strategy.get('recommendation', 'Unknown')}")
                    self.stdout.write(f"  💰 Strategy: {strategy.get('strategy', 'Unknown')}")
                    self.stdout.write(f"  💰 Urgency: {strategy.get('urgency', 'Unknown')}")
                    self.stdout.write(f"  💰 Confidence: {strategy.get('confidence', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {strategy['error']}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_group_analysis(self):
        """Test group analysis functionality"""
        self.stdout.write("\n👥 Testing Group Analysis...")
        
        try:
            # Get a sample deal group (if exists)
            from deals.models import DealGroup
            sample_group = DealGroup.objects.first()
            
            if sample_group:
                self.stdout.write(f"\n📊 Group Analysis for Deal Group {sample_group.id}:")
                
                # Analyze group performance
                analysis = agri_genie.group_intelligence.analyze_group_performance(sample_group.id)
                
                if 'error' not in analysis:
                    self.stdout.write(f"  👥 Group Status: {analysis.get('group_status', 'Unknown')}")
                    self.stdout.write(f"  👥 Total Quantity: {analysis.get('total_quantity_kg', 0)} kg")
                    
                    # Sentiment analysis
                    sentiment = analysis.get('sentiment_analysis', {})
                    if 'overall_sentiment' in sentiment:
                        self.stdout.write(f"  😊 Overall Sentiment: {sentiment['overall_sentiment']}")
                        self.stdout.write(f"  😊 Description: {sentiment.get('sentiment_description', 'Unknown')}")
                        self.stdout.write(f"  😊 Positive: {sentiment.get('positive_percent', 0)}%")
                        self.stdout.write(f"  😊 Negative: {sentiment.get('negative_percent', 0)}%")
                    
                    # Negotiation analysis
                    negotiation = analysis.get('negotiation_analysis', {})
                    if 'negotiation_intensity' in negotiation:
                        self.stdout.write(f"  💬 Negotiation Intensity: {negotiation['negotiation_intensity']}")
                        self.stdout.write(f"  💬 Total Messages: {negotiation.get('total_negotiation_messages', 0)}")
                        self.stdout.write(f"  💬 Duration: {negotiation.get('negotiation_duration_hours', 0)} hours")
                    
                    # Market context
                    market = analysis.get('market_context', {})
                    if 'crop_name' in market:
                        self.stdout.write(f"  🏘️ Crop: {market['crop_name']}")
                        self.stdout.write(f"  🏘️ Region: {market['region']}")
                        self.stdout.write(f"  🏘️ Price Trend: {market.get('price_trend', 'Unknown')}")
                    
                    # Recommendations
                    recommendations = analysis.get('group_recommendations', [])
                    if recommendations:
                        self.stdout.write(f"  💡 Group Recommendations ({len(recommendations)}):")
                        for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
                            self.stdout.write(f"    {i}. [{rec.get('type', 'Unknown')}] {rec.get('message', 'No message')}")
                            self.stdout.write(f"       Action: {rec.get('action', 'No action')}")
                    else:
                        self.stdout.write("  💡 No group recommendations available")
                
                else:
                    self.stdout.write(f"  ❌ Error: {analysis['error']}")
            
            else:
                self.stdout.write("  ⚠️ No deal groups found in database")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_comprehensive_advice(self):
        """Test comprehensive advice functionality"""
        self.stdout.write("\n🧠 Testing Comprehensive Advice...")
        
        test_queries = [
            "What should I plant next season?",
            "When is the best time to sell potatoes?",
            "How are current market trends for onions?",
            "What's the selling strategy for tomatoes?",
            "How is my group performing?"
        ]
        
        for query in test_queries:
            try:
                self.stdout.write(f"\n❓ Query: {query}")
                
                # Get comprehensive advice
                advice = agri_genie.get_comprehensive_advice(query, user_role='farmer')
                
                if 'error' not in advice:
                    self.stdout.write(f"  ✅ Response Type: {advice.get('response_type', 'Unknown')}")
                    self.stdout.write(f"  ✅ Summary: {advice.get('summary', 'No summary')}")
                    
                    if 'key_insights' in advice:
                        self.stdout.write(f"  💡 Key Insights:")
                        for insight in advice['key_insights'][:3]:  # Show first 3
                            self.stdout.write(f"    • {insight}")
                    
                    if 'next_actions' in advice:
                        self.stdout.write(f"  🚀 Next Actions:")
                        for action in advice['next_actions'][:3]:  # Show first 3
                            self.stdout.write(f"    • {action}")
                    
                    if 'capabilities' in advice:
                        self.stdout.write(f"  🎯 Capabilities:")
                        for capability in advice['capabilities'][:3]:  # Show first 3
                            self.stdout.write(f"    • {capability}")
                
                else:
                    self.stdout.write(f"  ❌ Error: {advice['error']}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")
