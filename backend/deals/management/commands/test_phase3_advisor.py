# backend/deals/management/commands/test_phase3_advisor.py
"""
Test command for Phase 3 of the AI Agricultural Advisor
Tests advanced AI capabilities, comprehensive advisory services, and automation
"""

from django.core.management.base import BaseCommand
from deals.ai_advisor import agri_genie
from django.utils import timezone

class Command(BaseCommand):
    help = 'Test Phase 3 of the AI Agricultural Advisor - Advanced AI & Integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['nlu', 'learning', 'crop_planning', 'market_strategy', 'notifications', 'automation', 'all'],
            default='all',
            help='Type of Phase 3 test to run'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        
        self.stdout.write("🚀 Testing Phase 3 AI Agricultural Advisor...")
        self.stdout.write("=" * 70)
        self.stdout.write("🎯 Phase 3 Features:")
        self.stdout.write("  • Advanced Natural Language Understanding")
        self.stdout.write("  • Learning & Adaptation System")
        self.stdout.write("  • Comprehensive Crop Planning Advisor")
        self.stdout.write("  • Advanced Market Strategy Advisor")
        self.stdout.write("  • Smart Notification System")
        self.stdout.write("  • Automated Action System")
        self.stdout.write("=" * 70)
        
        if test_type == 'nlu' or test_type == 'all':
            self._test_natural_language_understanding()
        
        if test_type == 'learning' or test_type == 'all':
            self._test_learning_adaptation()
        
        if test_type == 'crop_planning' or test_type == 'all':
            self._test_crop_planning_advisor()
        
        if test_type == 'market_strategy' or test_type == 'all':
            self._test_market_strategy_advisor()
        
        if test_type == 'notifications' or test_type == 'all':
            self._test_smart_notifications()
        
        if test_type == 'automation' or test_type == 'all':
            self._test_automated_actions()
        
        if test_type == 'all':
            self._test_comprehensive_phase3()
        
        self.stdout.write("=" * 70)
        self.stdout.write("✅ Phase 3 AI Advisor testing completed!")

    def _test_natural_language_understanding(self):
        """Test advanced natural language understanding"""
        self.stdout.write("\n🧠 Testing Advanced Natural Language Understanding...")
        
        test_queries = [
            "What should I plant next season in Maharashtra?",
            "When is the best time to sell potatoes for maximum profit?",
            "How can I reduce risks when growing tomatoes?",
            "What's the optimal strategy for group bargaining?",
            "Can you help me plan my crop budget for next year?"
        ]
        
        for query in test_queries:
            try:
                self.stdout.write(f"\n🔍 Testing Query: '{query}'")
                
                # Test NLU understanding
                response = agri_genie.get_comprehensive_agricultural_advice(query)
                
                if response['status'] == 'success':
                    nlu_data = response.get('nlu_understanding', {})
                    intent = nlu_data.get('intent', {})
                    entities = nlu_data.get('entities', {})
                    
                    self.stdout.write(f"  ✅ Intent: {intent.get('primary', 'Unknown')}")
                    self.stdout.write(f"  ✅ Confidence: {nlu_data.get('confidence', 'Unknown')}")
                    
                    if entities:
                        for entity_type, values in entities.items():
                            self.stdout.write(f"  ✅ {entity_type.title()}: {', '.join(values)}")
                    
                    self.stdout.write(f"  ✅ Response Type: {response.get('response_type', 'Unknown')}")
                    self.stdout.write(f"  ✅ Phase: {response.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {response.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_learning_adaptation(self):
        """Test learning and adaptation system"""
        self.stdout.write("\n🎓 Testing Learning & Adaptation System...")
        
        try:
            # Test learning insights
            insights = agri_genie.get_learning_insights()
            
            if insights['status'] == 'success':
                self.stdout.write(f"  ✅ Learning Data Points: {insights.get('learning_data_points', 0)}")
                self.stdout.write(f"  ✅ Prediction Types: {insights.get('total_prediction_types', 0)}")
                self.stdout.write(f"  ✅ Phase: {insights.get('phase', 'Unknown')}")
                
                # Test specific prediction type insights
                price_insights = agri_genie.get_learning_insights('price_prediction')
                if price_insights['status'] == 'success':
                    self.stdout.write(f"  ✅ Price Prediction Success Rate: {price_insights.get('success_rate', 0):.1f}%")
                    self.stdout.write(f"  ✅ Average Success Score: {price_insights.get('average_success_score', 0):.2f}")
                    self.stdout.write(f"  ✅ Recent Trend: {price_insights.get('recent_trend', 'Unknown')}")
            else:
                self.stdout.write(f"  ❌ Error: {insights.get('error', 'Unknown error')}")
            
            # Test learning from outcome
            test_outcome = {
                'price_accuracy': 0.85,
                'timing_accuracy': 0.78
            }
            
            test_feedback = {
                'satisfaction': 0.8,
                'usefulness': 0.9
            }
            
            learning_result = agri_genie.learn_from_outcome(
                'test_prediction_001', 
                test_outcome, 
                test_feedback
            )
            
            if learning_result['status'] == 'success':
                self.stdout.write(f"  ✅ Learning Applied: {learning_result.get('learning_applied', False)}")
                self.stdout.write(f"  ✅ Success Score: {learning_result.get('success_score', 0):.2f}")
                self.stdout.write(f"  ✅ Adaptation Needed: {learning_result.get('adaptation_needed', {}).get('needed', False)}")
            else:
                self.stdout.write(f"  ❌ Learning Error: {learning_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_crop_planning_advisor(self):
        """Test comprehensive crop planning advisor"""
        self.stdout.write("\n🌾 Testing Comprehensive Crop Planning Advisor...")
        
        test_cases = [
            ('Andhra Pradesh', 'kharif', 'medium'),
            ('Maharashtra', None, 'low'),
            ('Punjab', 'rabi', 'high')
        ]
        
        for region, season, risk_tolerance in test_cases:
            try:
                self.stdout.write(f"\n🔍 Testing {region} - Season: {season or 'Auto'}, Risk: {risk_tolerance}")
                
                advice = agri_genie.get_crop_planning_advice(region, season, None, risk_tolerance)
                
                if advice['status'] == 'success':
                    self.stdout.write(f"  ✅ Recommended Season: {advice.get('recommended_season', 'Unknown')}")
                    
                    top_recommendations = advice.get('top_recommendations', [])
                    if top_recommendations:
                        top_crop = top_recommendations[0]
                        self.stdout.write(f"  ✅ Top Crop: {top_crop.get('crop', 'Unknown')}")
                        self.stdout.write(f"  ✅ Expected ROI: {top_crop.get('roi', 0):.1f}%")
                        self.stdout.write(f"  ✅ Risk Level: {top_crop.get('risk_level', {}).get('level', 'Unknown')}")
                    
                    financial_plan = advice.get('financial_plan', {})
                    if financial_plan:
                        self.stdout.write(f"  ✅ Total Investment: ₹{financial_plan.get('total_investment', 0):,.0f}/acre")
                        self.stdout.write(f"  ✅ Expected Profit: ₹{financial_plan.get('expected_profit', 0):,.0f}/acre")
                        self.stdout.write(f"  ✅ Break-even Yield: {financial_plan.get('break_even_yield', 0):.1f} quintals/acre")
                    
                    self.stdout.write(f"  ✅ Next Actions: {len(advice.get('next_actions', []))} suggested")
                    self.stdout.write(f"  ✅ Phase: {advice.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {advice.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_market_strategy_advisor(self):
        """Test advanced market strategy advisor"""
        self.stdout.write("\n📊 Testing Advanced Market Strategy Advisor...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh', '1000'),
            ('Onion', 'Maharashtra', '2000'),
            ('Tomato', 'Karnataka', '1500')
        ]
        
        for crop, region, quantity in test_cases:
            try:
                self.stdout.write(f"\n🔍 Testing {crop} in {region} - Quantity: {quantity} kg")
                
                strategy = agri_genie.get_market_strategy_advice(crop, region, quantity)
                
                if strategy['status'] == 'success':
                    self.stdout.write(f"  ✅ Market Type: {strategy.get('market_type', 'Unknown')}")
                    
                    timing = strategy.get('timing_strategy', {})
                    if timing:
                        self.stdout.write(f"  ✅ Timing Recommendation: {timing.get('recommendation', 'Unknown')}")
                        self.stdout.write(f"  ✅ Urgency: {timing.get('urgency', 'Unknown')}")
                        self.stdout.write(f"  ✅ Optimal Window: {timing.get('optimal_window', 'Unknown')}")
                    
                    pricing = strategy.get('pricing_strategy', {})
                    if pricing:
                        self.stdout.write(f"  ✅ Current Market Price: ₹{pricing.get('current_market_price', 0):.2f}/quintal")
                        self.stdout.write(f"  ✅ Target Price: ₹{pricing.get('target_price', 0):.2f}/quintal")
                        self.stdout.write(f"  ✅ Price Range: ₹{pricing.get('price_range', {}).get('minimum', 0):.2f} - ₹{pricing.get('price_range', {}).get('maximum', 0):.2f}/quintal")
                    
                    negotiation = strategy.get('negotiation_guidance', {})
                    if negotiation:
                        self.stdout.write(f"  ✅ Strategy: {negotiation.get('strategy', 'Unknown')}")
                        self.stdout.write(f"  ✅ Negotiation Style: {negotiation.get('negotiation_style', 'Unknown')}")
                    
                    self.stdout.write(f"  ✅ Action Plan: {len(strategy.get('action_plan', []))} actions")
                    self.stdout.write(f"  ✅ Phase: {strategy.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {strategy.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_smart_notifications(self):
        """Test smart notification system"""
        self.stdout.write("\n🔔 Testing Smart Notification System...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n🔍 Testing {crop} in {region}:")
                
                notifications = agri_genie.get_smart_notifications(crop, region)
                
                if notifications['status'] == 'success':
                    notification_list = notifications.get('notifications', [])
                    self.stdout.write(f"  ✅ Notifications Generated: {len(notification_list)}")
                    
                    for i, notification in enumerate(notification_list[:3], 1):  # Show first 3
                        self.stdout.write(f"    {i}. {notification.get('title', 'Unknown')}")
                        self.stdout.write(f"       Type: {notification.get('type', 'Unknown')}")
                        self.stdout.write(f"       Priority: {notification.get('priority', 'Unknown')}")
                        self.stdout.write(f"       Actions: {len(notification.get('actions', []))} suggested")
                    
                    self.stdout.write(f"  ✅ Phase: {notifications.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {notifications.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_automated_actions(self):
        """Test automated action system"""
        self.stdout.write("\n🤖 Testing Automated Action System...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n🔍 Testing {crop} in {region}:")
                
                automation = agri_genie.get_automation_suggestions(crop, region)
                
                if automation['status'] == 'success':
                    actions = automation.get('automation_actions', [])
                    self.stdout.write(f"  ✅ Automation Actions: {len(actions)} triggered")
                    
                    for i, action in enumerate(actions[:3], 1):  # Show first 3
                        self.stdout.write(f"    {i}. {action.get('automation_type', 'Unknown')}")
                        self.stdout.write(f"       Priority: {action.get('priority', 'Unknown')}")
                        self.stdout.write(f"       Reason: {action.get('reason', 'Unknown')}")
                        self.stdout.write(f"       Actions: {len(action.get('suggested_actions', []))} suggested")
                        self.stdout.write(f"       Impact: {action.get('estimated_impact', 'Unknown')}")
                    
                    self.stdout.write(f"  ✅ Phase: {automation.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {automation.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_comprehensive_phase3(self):
        """Test comprehensive Phase 3 integration"""
        self.stdout.write("\n🌟 Testing Comprehensive Phase 3 Integration...")
        
        try:
            # Test capabilities summary
            capabilities = agri_genie.get_phase3_capabilities_summary()
            
            if capabilities['status'] == 'success':
                self.stdout.write(f"  ✅ Phase: {capabilities.get('phase', 'Unknown')}")
                self.stdout.write(f"  ✅ Data Integration: {capabilities.get('data_integration', 'Unknown')}")
                self.stdout.write(f"  ✅ ML Models: {capabilities.get('ml_models', 'Unknown')}")
                self.stdout.write(f"  ✅ User Experience: {capabilities.get('user_experience', 'Unknown')}")
                
                # Test advanced query processing
                advanced_query = "I want to grow potatoes in Maharashtra next season. What's the best strategy considering market conditions and my budget of ₹50,000 per acre?"
                
                self.stdout.write(f"\n🔍 Testing Advanced Query: '{advanced_query}'")
                
                response = agri_genie.get_comprehensive_agricultural_advice(advanced_query)
                
                if response['status'] == 'success':
                    self.stdout.write(f"  ✅ Intent Recognized: {response.get('intent', 'Unknown')}")
                    self.stdout.write(f"  ✅ Response Type: {response.get('response_type', 'Unknown')}")
                    self.stdout.write(f"  ✅ Confidence: {response.get('confidence', 'Unknown')}")
                    self.stdout.write(f"  ✅ Key Recommendations: {len(response.get('key_recommendations', []))} provided")
                    self.stdout.write(f"  ✅ Next Actions: {len(response.get('next_actions', []))} suggested")
                    
                    # Check for smart features
                    if 'smart_notifications' in response:
                        self.stdout.write(f"  ✅ Smart Notifications: {len(response['smart_notifications'])} generated")
                    
                    if 'automation_suggestions' in response:
                        self.stdout.write(f"  ✅ Automation Suggestions: {len(response['automation_suggestions'])} provided")
                    
                    self.stdout.write(f"  ✅ Phase: {response.get('phase', 'Unknown')}")
                else:
                    self.stdout.write(f"  ❌ Error: {response.get('error', 'Unknown error')}")
                
            else:
                self.stdout.write(f"  ❌ Capabilities Error: {capabilities.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _display_phase3_features(self):
        """Display Phase 3 feature summary"""
        self.stdout.write("\n🚀 Phase 3 Features Implemented:")
        self.stdout.write("  🧠 Advanced AI Capabilities")
        self.stdout.write("    • Natural Language Understanding with intent recognition")
        self.stdout.write("    • Entity extraction (crops, regions, quantities, time)")
        self.stdout.write("    • Context-aware multi-turn conversations")
        self.stdout.write("    • Learning & adaptation from outcomes and feedback")
        
        self.stdout.write("\n  🌾 Comprehensive Advisory Services")
        self.stdout.write("    • Crop planning with financial analysis and risk assessment")
        self.stdout.write("    • Market strategy with timing and negotiation support")
        self.stdout.write("    • Portfolio optimization and diversification")
        self.stdout.write("    • Financing recommendations and cost analysis")
        
        self.stdout.write("\n  🔔 Integration & Automation")
        self.stdout.write("    • Smart notifications for market opportunities and risks")
        self.stdout.write("    • Automated actions for optimal market responses")
        self.stdout.write("    • Performance tracking and continuous optimization")
        self.stdout.write("    • Proactive intelligence and recommendations")
        
        self.stdout.write("\n  🔮 Production-Ready Features")
        self.stdout.write("    • Advanced ML models with 7 lakh rows integration")
        self.stdout.write("    • Real-time market analysis and predictions")
        self.stdout.write("    • Comprehensive risk assessment and mitigation")
        self.stdout.write("    • Group intelligence and collective decision making")
