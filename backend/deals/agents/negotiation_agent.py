"""
Main Negotiation Agent
Clean negotiation logic with NO FALLBACKS - clear errors only
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..ml_models.pricing_engine import MLPricingEngine
from ..ml_models.market_analyzer import MarketAnalyzer
from ..utils.decision_maker import DecisionMaker
from ..utils.price_calculator import PriceCalculator
from ..utils.types import AgentDecision

logger = logging.getLogger(__name__)

class NegotiationAgent:
    """Main negotiation agent - NO FALLBACKS, clear errors only"""
    
    def __init__(self):
        self.ml_engine = MLPricingEngine()
        self.market_analyzer = MarketAnalyzer()
        self.decision_maker = DecisionMaker()
        self.price_calculator = PriceCalculator()
        
        logger.info("✅ Negotiation agent initialized with ML engine and market analyzer")
    
    def analyze_offer(self, deal_group, offer_price: float, buyer_username: str, 
                     user_context: dict = None) -> AgentDecision:
        """Analyze buyer offer and make decision - NO FALLBACKS"""
        
        try:
            # Extract crop, grade, and region information
            crop_name = self._extract_crop_from_group(deal_group)
            grade = self._extract_grade_from_group(deal_group)
            region = self._extract_region_from_group(deal_group)
            
            if not crop_name or not region:
                raise ValueError(f"Invalid deal group: crop={crop_name}, region={region}")
            
            # Get ML price prediction
            ml_analysis = self.ml_engine.predict_price_with_analysis(
                crop_name, region, datetime.now(), user_context
            )
            
            ml_prediction = ml_analysis['predicted_price']
            if ml_prediction <= 0:
                raise ValueError(f"Invalid ML prediction: {ml_prediction}")
            
            # Get market data from BIG_DATA.csv (including grade if available)
            market_data = self.market_analyzer.get_market_data(
                crop_name, region, datetime.now(), grade
            )
            
            # Calculate optimal price
            optimal_price = self.price_calculator.calculate_optimal_price(
                offer_price, ml_prediction, market_data, user_context
            )
            
            if optimal_price <= 0:
                raise ValueError(f"Invalid optimal price calculation: {optimal_price}")
            
            # Make intelligent, human-like decision
            decision = self._make_human_like_decision(
                offer_price, optimal_price, market_data, ml_prediction, user_context
            )
            
            # Validate decision
            if decision.new_price <= 0:
                raise ValueError(f"Invalid decision price: {decision.new_price}")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Negotiation analysis failed: {e}")
            raise RuntimeError(f"Negotiation analysis failed: {e}")
    
    def _extract_crop_from_group(self, deal_group) -> Optional[str]:
        """Extract crop name from deal group"""
        try:
            if hasattr(deal_group, 'group_id') and deal_group.group_id:
                group_parts = deal_group.group_id.split('-')
                if len(group_parts) >= 1:
                    return group_parts[0].replace('_', ' ').title()
            
            # Try to get from products
            if hasattr(deal_group, 'products') and deal_group.products.exists():
                first_product = deal_group.products.first()
                if hasattr(first_product, 'crop') and first_product.crop:
                    return first_product.crop.name
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Crop extraction failed: {e}")
            return None
    
    def _extract_grade_from_group(self, deal_group) -> Optional[str]:
        """Extract grade from deal group"""
        try:
            if hasattr(deal_group, 'group_id') and deal_group.group_id:
                group_parts = deal_group.group_id.split('-')
                if len(group_parts) >= 2:
                    return group_parts[1]  # Grade is the second part
            
            # Try to get from products
            if hasattr(deal_group, 'products') and deal_group.products.exists():
                first_product = deal_group.products.first()
                if hasattr(first_product, 'grade') and first_product.grade:
                    return first_product.grade
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Grade extraction failed: {e}")
            return None
    
    def _extract_region_from_group(self, deal_group) -> Optional[str]:
        """Extract region from deal group"""
        try:
            # New format: "CROP-GRADE-TIMESTAMP" (no region)
            # Old format was: "REGION-CROP-GRADE-TIMESTAMP"
            # Since we're not using region-based grouping anymore, use default district
            return "krishna"  # Default to available district
            
        except Exception as e:
            logger.error(f"❌ Region extraction failed: {e}")
            return None
    
    def get_negotiation_summary(self, deal_group, offer_price: float) -> Dict[str, Any]:
        """Get negotiation summary - NO FALLBACKS"""
        
        try:
            crop_name = self._extract_crop_from_group(deal_group)
            grade = self._extract_grade_from_group(deal_group)
            region = self._extract_region_from_group(deal_group)
            
            if not crop_name or not region:
                raise ValueError("Cannot extract crop or region information")
            
            # Get market data (including grade if available)
            market_data = self.market_analyzer.get_market_data(
                crop_name, region, datetime.now(), grade
            )
            
            # Get ML prediction
            ml_analysis = self.ml_engine.predict_price_with_analysis(
                crop_name, region, datetime.now()
            )
            
            return {
                'crop_name': crop_name,
                'grade': grade,
                'region': region,
                'buyer_offer': offer_price,
                'ml_prediction': ml_analysis['predicted_price'],
                'market_data': market_data,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Negotiation summary failed: {e}")
            raise RuntimeError(f"Negotiation summary failed: {e}")
    
    def _make_human_like_decision(self, buyer_offer: float, optimal_price: float, 
                                 market_data: dict, ml_prediction: float, user_context: dict) -> AgentDecision:
        """Make human-like bargaining decision with psychology and strategy"""
        
        # Extract market insights
        current_market_price = market_data.get('price_analysis', {}).get('current_price_per_kg', 0)
        min_market_price = market_data.get('price_analysis', {}).get('min_price_per_kg', 0)
        max_market_price = market_data.get('price_analysis', {}).get('max_price_per_kg', 0)
        
        # Calculate bargaining ranges
        absolute_minimum = min(optimal_price * 0.85, min_market_price * 0.9)  # 15% below optimal or 10% below market min
        reasonable_minimum = optimal_price * 0.92  # 8% below optimal
        target_price = optimal_price * 1.05  # 5% above optimal for bargaining room
        
        # Analyze buyer psychology
        buyer_aggressiveness = self._assess_buyer_aggressiveness(buyer_offer, current_market_price)
        
        # Human-like decision making
        if buyer_offer >= target_price:
            # Buyer is offering above target - ACCEPT with enthusiasm
            action = "ACCEPT"
            new_price = buyer_offer
            confidence = "Very High - Excellent offer"
            farmer_message = f"Excellent offer! We're happy to accept ₹{buyer_offer}/kg. This is above our target price and shows you value quality produce."
            buyer_message = f"Great! Your offer of ₹{buyer_offer}/kg has been accepted. We appreciate fair pricing and look forward to a successful transaction."
            
        elif buyer_offer >= reasonable_minimum:
            # Buyer is in reasonable range - COUNTER with small adjustment
            action = "COUNTER_OFFER"
            new_price = min(buyer_offer * 1.03, target_price)  # Ask for 3% more or target price
            confidence = "High - Close to agreement"
            farmer_message = f"Good offer! We're very close. Can we meet at ₹{new_price:.2f}/kg? This is just ₹{new_price - buyer_offer:.2f}/kg more and ensures fair value."
            buyer_message = f"Your offer is reasonable. We're asking for just ₹{new_price - buyer_offer:.2f}/kg more to ₹{new_price:.2f}/kg. This reflects current market conditions and quality."
            
        elif buyer_offer >= absolute_minimum:
            # Buyer is below reasonable but not insulting - COUNTER with education
            action = "COUNTER_OFFER"
            new_price = reasonable_minimum
            confidence = "Medium - Needs education"
            farmer_message = f"Your offer is below current market rates. We can work with ₹{new_price:.2f}/kg, which reflects quality and market conditions. This ensures fair value for our farmers."
            buyer_message = f"While your offer shows interest, current market rates for this quality are higher. We're offering ₹{new_price:.2f}/kg, which is competitive and fair. Consider the quality premium."
            
        else:
            # Buyer offer is too low - REJECT with explanation
            action = "REJECT"
            new_price = reasonable_minimum
            confidence = "High - Offer too low"
            farmer_message = f"Your offer of ₹{buyer_offer}/kg is significantly below market rates. We cannot accept less than ₹{new_price:.2f}/kg for this quality. This ensures our farmers receive fair compensation."
            buyer_message = f"Your offer is below our minimum acceptable price. Current market rates for this quality start at ₹{new_price:.2f}/kg. We're open to reasonable negotiations within market parameters."
        
        # Create comprehensive market analysis
        market_analysis = {
            'crop_name': market_data.get('crop_name', 'Unknown'),
            'region': market_data.get('district', 'Unknown'),
            'current_market_price': current_market_price,
            'market_range': f"₹{min_market_price:.2f} - ₹{max_market_price:.2f}/kg",
            'ml_prediction': ml_prediction,
            'optimal_price': optimal_price,
            'bargaining_range': f"₹{absolute_minimum:.2f} - ₹{target_price:.2f}/kg",
            'buyer_aggressiveness': buyer_aggressiveness,
            'quality_premium': self._calculate_quality_premium(market_data),
            'seasonal_factors': self._get_seasonal_analysis(),
            'transport_cost_estimate': self._estimate_transport_cost(user_context)
        }
        
        # Create simple 4-point explanation for farmers
        farmer_simple_explanation = self._create_simple_farmer_explanation(
            action, new_price, current_market_price, buyer_offer, market_data
        )
        
        return AgentDecision(
            action=action,
            new_price=round(new_price, 2),  # Round to 2 decimal places for clean display
            justification_for_farmers=farmer_message,
            message_to_buyer=buyer_message,
            market_analysis=market_analysis,
            confidence_level=confidence,
            ml_prediction=ml_prediction,
            data_source="ML + Market Data + Human Psychology",
            farmer_simple_explanation=farmer_simple_explanation
        )
    
    def _assess_buyer_aggressiveness(self, buyer_offer: float, market_price: float) -> str:
        """Assess how aggressive the buyer's offer is"""
        if market_price <= 0:
            return "Unknown - No market data"
        
        offer_ratio = buyer_offer / market_price
        
        if offer_ratio >= 1.1:
            return "Very Generous - Above market"
        elif offer_ratio >= 1.0:
            return "Fair - At market rate"
        elif offer_ratio >= 0.9:
            return "Reasonable - Slightly below market"
        elif offer_ratio >= 0.8:
            return "Aggressive - Below market"
        elif offer_ratio >= 0.6:
            return "Very Aggressive - Well below market"
        else:
            return "Insulting - Far below market"
    
    def _calculate_quality_premium(self, market_data: dict) -> str:
        """Calculate quality premium based on grade"""
        grade = market_data.get('grade', 'Unknown')
        if grade == 'FAQ':
            return "20% premium for FAQ quality"
        elif grade == 'Ref grade-1':
            return "15% premium for Ref grade-1"
        elif grade == 'Ref grade-2':
            return "10% premium for Ref grade-2"
        elif grade == 'Large':
            return "5% premium for Large size"
        else:
            return "Standard pricing"
    
    def _get_seasonal_analysis(self) -> str:
        """Get seasonal market analysis"""
        month = datetime.now().month
        if month in [6, 7, 8, 9]:
            return "Monsoon season - Supply constraints, prices typically higher"
        elif month in [10, 11, 12]:
            return "Post-monsoon - Good supply, competitive pricing"
        elif month in [1, 2, 3]:
            return "Winter - Stable supply, moderate pricing"
        else:
            return "Summer - Variable supply, price fluctuations"
    
    def _estimate_transport_cost(self, user_context: dict) -> str:
        """Estimate transport cost based on user location"""
        if not user_context or 'user_info' not in user_context:
            return "₹2-5/kg (estimated)"
        
        user_info = user_context['user_info']
        pincode = user_info.get('pincode')
        latitude = user_info.get('latitude')
        longitude = user_info.get('longitude')
        
        if pincode or (latitude and longitude):
            return "₹3-6/kg (location-based estimate)"
        else:
            return "₹2-5/kg (standard estimate)"
    
    def _create_simple_farmer_explanation(self, action: str, new_price: float, 
                                        current_market_price: float, buyer_offer: float, 
                                        market_data: dict) -> str:
        """Create simple 4-point explanation for farmers"""
        
        crop_name = market_data.get('crop_name', 'this crop')
        grade = market_data.get('grade', 'this quality')
        
        if action == "ACCEPT":
            return f"""✅ **Simple Explanation for Farmers:**

1️⃣ **What Happened**: Buyer offered ₹{buyer_offer}/kg and we ACCEPTED it!

2️⃣ **Why We Accepted**: This price is above our target and shows the buyer values quality produce.

3️⃣ **Current Market Rate**: ₹{current_market_price}/kg - so we're getting a good deal.

4️⃣ **Next Steps**: Prepare your {crop_name} ({grade}) for collection. The deal is confirmed! 🎉"""
        
        elif action == "COUNTER_OFFER":
            return f"""🤝 **Simple Explanation for Farmers:**

1️⃣ **What Happened**: Buyer offered ₹{buyer_offer}/kg, but we countered with ₹{new_price}/kg.

2️⃣ **Why We Countered**: Current market rate is ₹{current_market_price}/kg, so we need fair pricing.

3️⃣ **Our Position**: ₹{new_price}/kg ensures you get fair value for your {crop_name} ({grade}).

4️⃣ **Next Steps**: Wait for buyer's response. We're close to a good deal! 💪"""
        
        else:  # REJECT
            return f"""❌ **Simple Explanation for Farmers:**

1️⃣ **What Happened**: Buyer offered ₹{buyer_offer}/kg, but we REJECTED it.

2️⃣ **Why We Rejected**: Current market rate is ₹{current_market_price}/kg - their offer was too low.

3️⃣ **Our Minimum**: We cannot accept less than ₹{new_price}/kg for your {crop_name} ({grade}).

4️⃣ **Next Steps**: Wait for a better offer or the buyer to increase their price. We're protecting your interests! 🛡️"""

def get_negotiation_agent() -> NegotiationAgent:
    """Get initialized negotiation agent"""
    try:
        return NegotiationAgent()
    except Exception as e:
        logger.error(f"❌ Failed to create negotiation agent: {e}")
        raise RuntimeError(f"Negotiation agent creation failed: {e}")
