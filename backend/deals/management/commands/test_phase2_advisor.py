# backend/deals/management/commands/test_phase2_advisor.py
"""
Test command for Phase 2 of the AI Agricultural Advisor
Tests enhanced market intelligence, decision support, and comprehensive analysis
"""

from django.core.management.base import BaseCommand
from deals.ai_advisor import agri_genie
from django.utils import timezone

class Command(BaseCommand):
    help = 'Test Phase 2 of the AI Agricultural Advisor - Enhanced Market Intelligence & Decision Support'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['market_analysis', 'decision_support', 'comprehensive', 'all'],
            default='all',
            help='Type of Phase 2 test to run'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        
        self.stdout.write("🚀 Testing Phase 2 AI Agricultural Advisor...")
        self.stdout.write("=" * 60)
        self.stdout.write("🎯 Phase 2 Features:")
        self.stdout.write("  • Enhanced Market Intelligence Engine")
        self.stdout.write("  • Intelligent Decision Support System")
        self.stdout.write("  • Comprehensive Market Analysis")
        self.stdout.write("  • Risk Assessment & Mitigation")
        self.stdout.write("=" * 60)
        
        if test_type == 'market_analysis' or test_type == 'all':
            self._test_enhanced_market_analysis()
        
        if test_type == 'decision_support' or test_type == 'all':
            self._test_decision_support_system()
        
        if test_type == 'comprehensive' or test_type == 'all':
            self._test_comprehensive_intelligence()
        
        self.stdout.write("=" * 60)
        self.stdout.write("✅ Phase 2 AI Advisor testing completed!")

    def _test_enhanced_market_analysis(self):
        """Test enhanced market analysis engine"""
        self.stdout.write("\n📊 Testing Enhanced Market Analysis Engine...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra'),
            ('Tomato', 'Karnataka')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n🔍 Testing {crop} in {region}:")
                
                # Get enhanced market analysis
                analysis = agri_genie.get_enhanced_market_analysis(crop, region, timeframe_days=90)
                
                if analysis['status'] == 'success':
                    data = analysis['analysis']
                    
                    # Display results
                    self.stdout.write(f"  ✅ Analysis Period: {data.get('analysis_period', 'Unknown')}")
                    self.stdout.write(f"  ✅ Data Points: {data.get('data_points', 0)}")
                    
                    # Price trends
                    price_trend = data.get('price_trend', {})
                    if price_trend:
                        self.stdout.write(f"  📈 Price Trend: {price_trend.get('direction', 'Unknown')}")
                        self.stdout.write(f"  📈 Trend Strength: {price_trend.get('strength', 'Unknown')}")
                        self.stdout.write(f"  📈 Change: {price_trend.get('change_percent', 0)}%")
                    
                    # Volatility
                    volatility = data.get('volatility', {})
                    if volatility:
                        self.stdout.write(f"  📊 Volatility: {volatility.get('level', 'Unknown')} ({volatility.get('percentage', 0)}%)")
                    
                    # Market sentiment
                    sentiment = data.get('market_sentiment', {})
                    if sentiment:
                        self.stdout.write(f"  🎭 Market Sentiment: {sentiment.get('sentiment', 'Unknown')}")
                        self.stdout.write(f"  🎭 Confidence: {sentiment.get('confidence', 'Unknown')}")
                    
                    # Seasonal patterns
                    seasonal = data.get('seasonal_pattern', {})
                    if seasonal and 'pattern' in seasonal:
                        self.stdout.write(f"  🌾 Seasonal Pattern: {seasonal.get('pattern', 'Unknown')}")
                        if 'peak_month' in seasonal:
                            self.stdout.write(f"  🌾 Peak Month: {seasonal.get('peak_month', 'Unknown')}")
                            self.stdout.write(f"  🌾 Peak Price: ₹{seasonal.get('peak_price', 0):.2f}/quintal")
                
                else:
                    self.stdout.write(f"  ❌ Error: {analysis.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_decision_support_system(self):
        """Test intelligent decision support system"""
        self.stdout.write("\n🧠 Testing Intelligent Decision Support System...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra'),
            ('Tomato', 'Karnataka')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n🎯 Testing {crop} in {region}:")
                
                # Get intelligent selling recommendation
                recommendation = agri_genie.get_intelligent_selling_recommendation(crop, region)
                
                if recommendation['status'] == 'success':
                    data = recommendation['recommendation']
                    
                    # Display recommendation
                    rec = data.get('recommendation', {})
                    if rec:
                        self.stdout.write(f"  🎯 Action: {rec.get('action', 'Unknown')}")
                        self.stdout.write(f"  🎯 Price Context: {rec.get('price_context', 'Unknown')}")
                        self.stdout.write(f"  🎯 Market Context: {rec.get('market_context', 'Unknown')}")
                        self.stdout.write(f"  🎯 Risk Level: {rec.get('risk_level', 'Unknown')}")
                        self.stdout.write(f"  🎯 Confidence: {rec.get('confidence', 'Unknown')}")
                    
                    # Timing analysis
                    timing = data.get('timing_analysis', {})
                    if timing:
                        overall = timing.get('overall_timing', {})
                        if overall:
                            self.stdout.write(f"  ⏰ Overall Timing: {overall.get('recommendation', 'Unknown')}")
                            self.stdout.write(f"  ⏰ Urgency: {overall.get('urgency', 'Unknown')}")
                            self.stdout.write(f"  ⏰ Reasoning: {overall.get('reasoning', 'Unknown')}")
                    
                    # Market conditions
                    conditions = data.get('market_conditions', {})
                    if conditions:
                        self.stdout.write(f"  🏥 Market Health: {conditions.get('market_health', 'Unknown')}")
                        self.stdout.write(f"  🏥 Opportunity Level: {conditions.get('opportunity_level', 'Unknown')}")
                    
                    # Risk assessment
                    risk = data.get('risk_assessment', {})
                    if risk:
                        self.stdout.write(f"  ⚠️ Risk Level: {risk.get('risk_level', 'Unknown')}")
                        if risk.get('risk_factors'):
                            self.stdout.write(f"  ⚠️ Risk Factors: {', '.join(risk.get('risk_factors', []))}")
                    
                    # Next actions
                    actions = data.get('next_actions', [])
                    if actions:
                        self.stdout.write(f"  📋 Next Actions: {len(actions)} suggested")
                        for i, action in enumerate(actions[:3], 1):  # Show first 3
                            self.stdout.write(f"    {i}. {action}")
                
                else:
                    self.stdout.write(f"  ❌ Error: {recommendation.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _test_comprehensive_intelligence(self):
        """Test comprehensive market intelligence summary"""
        self.stdout.write("\n🌟 Testing Comprehensive Market Intelligence...")
        
        test_cases = [
            ('Potato', 'Andhra Pradesh'),
            ('Onion', 'Maharashtra')
        ]
        
        for crop, region in test_cases:
            try:
                self.stdout.write(f"\n🔮 Testing {crop} in {region}:")
                
                # Get comprehensive intelligence summary
                summary = agri_genie.get_market_intelligence_summary(crop, region)
                
                if summary['status'] == 'success':
                    data = summary['summary']
                    
                    self.stdout.write(f"  ✅ Phase: {summary.get('phase', 'Unknown')}")
                    self.stdout.write(f"  ✅ Generated: {summary.get('generated_at', 'Unknown')}")
                    
                    # Check components
                    components = ['basic_advice', 'market_trends', 'selling_recommendation']
                    for component in components:
                        if component in data and data[component]:
                            if 'error' not in data[component]:
                                self.stdout.write(f"  ✅ {component.replace('_', ' ').title()}: Available")
                            else:
                                self.stdout.write(f"  ⚠️ {component.replace('_', ' ').title()}: {data[component].get('error', 'Unknown error')}")
                        else:
                            self.stdout.write(f"  ❌ {component.replace('_', ' ').title()}: Not available")
                    
                    # Show key insights
                    if 'selling_recommendation' in data and data['selling_recommendation']:
                        rec = data['selling_recommendation'].get('recommendation', {})
                        if rec and 'action' in rec:
                            self.stdout.write(f"  🎯 Key Recommendation: {rec['action']}")
                
                else:
                    self.stdout.write(f"  ❌ Error: {summary.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.stdout.write(f"  ❌ Exception: {str(e)}")

    def _display_phase2_features(self):
        """Display Phase 2 feature summary"""
        self.stdout.write("\n🚀 Phase 2 Features Implemented:")
        self.stdout.write("  📊 Enhanced Market Intelligence Engine")
        self.stdout.write("    • Advanced trend analysis with linear regression")
        self.stdout.write("    • Volume trend analysis")
        self.stdout.write("    • Volatility calculation and assessment")
        self.stdout.write("    • Seasonal pattern detection")
        self.stdout.write("    • Market sentiment analysis")
        
        self.stdout.write("\n  🧠 Intelligent Decision Support System")
        self.stdout.write("    • Multi-factor timing analysis")
        self.stdout.write("    • Risk assessment and mitigation")
        self.stdout.write("    • Market health evaluation")
        self.stdout.write("    • Opportunity level assessment")
        self.stdout.write("    • Actionable next steps")
        
        self.stdout.write("\n  🔮 Comprehensive Intelligence Integration")
        self.stdout.write("    • Unified market intelligence summary")
        self.stdout.write("    • Cross-component data correlation")
        self.stdout.write("    • Confidence scoring")
        self.stdout.write("    • Phase identification")
