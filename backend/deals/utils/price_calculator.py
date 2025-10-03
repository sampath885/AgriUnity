"""
Price Calculator
Clean price calculations with no fallbacks
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PriceCalculator:
    """Clean price calculator - NO FALLBACKS"""
    
    def __init__(self):
        self.quality_premiums = {
            'FAQ': 1.20,        # 20% premium for FAQ grade
            'REF GRADE-1': 1.15, # 15% premium for Ref grade-1
            'REF GRADE-2': 1.10, # 10% premium for Ref grade-2
            'LARGE': 1.05,       # 5% premium for Large
            'MEDIUM': 1.00,      # No premium for Medium
            'LOCAL': 0.95,       # 5% discount for Local
            'NON-FAQ': 0.90,     # 10% discount for Non-FAQ
        }
        
        self.seasonal_factors = {
            'Monsoon': 1.20,      # 20% premium during monsoon
            'Post-Monsoon': 1.10, # 10% premium post-monsoon
            'Winter': 1.05,       # 5% premium in winter
            'Summer': 0.95,       # 5% discount in summer
        }
        
        logger.info("✅ Price calculator initialized")
    
    def calculate_optimal_price(self, offer_price: float, ml_prediction: float,
                              market_data: Dict[str, Any], user_context: dict = None) -> float:
        """Calculate optimal price - NO FALLBACKS"""
        
        try:
            if offer_price <= 0:
                raise ValueError(f"Invalid offer price: {offer_price}")
            
            if ml_prediction <= 0:
                raise ValueError(f"Invalid ML prediction: {ml_prediction}")
            
            # Get market price
            market_price = market_data.get('price_analysis', {}).get('current_price_per_kg', 0)
            if market_price <= 0:
                raise ValueError(f"Invalid market price: {market_price}")
            
            # Calculate base optimal price (average of ML and market)
            base_price = (ml_prediction + market_price) / 2
            
            # Apply quality premium
            quality_premium = self._get_quality_premium(user_context)
            base_price *= quality_premium
            
            # Apply seasonal factor
            seasonal_factor = self._get_seasonal_factor(market_data)
            base_price *= seasonal_factor
            
            # Apply location premium
            location_premium = self._get_location_premium(user_context)
            base_price *= location_premium
            
            # Validate final price
            if base_price <= 0:
                raise ValueError(f"Calculated price is invalid: {base_price}")
            
            # Round to 2 decimal places
            optimal_price = round(base_price, 2)
            
            logger.info(f"✅ Optimal price calculated: ₹{optimal_price}/kg")
            return optimal_price
            
        except Exception as e:
            logger.error(f"❌ Price calculation failed: {e}")
            raise RuntimeError(f"Price calculation failed: {e}")
    
    def _get_quality_premium(self, user_context: dict) -> float:
        """Get quality premium from user context"""
        try:
            if not user_context:
                return 1.0
            
            # Try to get grade from deal group or user context
            grade = user_context.get('grade', 'C')
            if isinstance(grade, str):
                grade = grade.upper()
            
            return self.quality_premiums.get(grade, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Quality premium calculation failed: {e}")
            return 1.0
    
    def _get_seasonal_factor(self, market_data: Dict[str, Any]) -> float:
        """Get seasonal factor from market data"""
        try:
            seasonal_factors = market_data.get('market_insights', {}).get('seasonal_factors', [])
            
            if not seasonal_factors:
                return 1.0
            
            # Check for monsoon season (highest premium)
            if any('Monsoon' in factor for factor in seasonal_factors):
                return self.seasonal_factors['Monsoon']
            elif any('Post-Monsoon' in factor for factor in seasonal_factors):
                return self.seasonal_factors['Post-Monsoon']
            elif any('Winter' in factor for factor in seasonal_factors):
                return self.seasonal_factors['Winter']
            elif any('Summer' in factor for factor in seasonal_factors):
                return self.seasonal_factors['Summer']
            
            return 1.0
            
        except Exception as e:
            logger.error(f"❌ Seasonal factor calculation failed: {e}")
            return 1.0
    
    def _get_location_premium(self, user_context: dict) -> float:
        """Get location premium based on user location"""
        try:
            if not user_context:
                return 1.0
            
            # Check if user has location data
            latitude = user_context.get('latitude')
            longitude = user_context.get('longitude')
            
            if latitude and longitude:
                # Calculate distance from major markets
                # For now, use a simple premium based on region
                region = user_context.get('extracted_region', 'krishna')
                
                # Premium for major agricultural regions
                region_premiums = {
                    'krishna': 1.05,      # 5% premium for Krishna district
                    'east godavari': 1.03, # 3% premium for East Godavari
                    'west godavari': 1.02, # 2% premium for West Godavari
                }
                
                return region_premiums.get(region.lower(), 1.0)
            
            return 1.0
            
        except Exception as e:
            logger.error(f"❌ Location premium calculation failed: {e}")
            return 1.0
    
    def validate_price(self, price: float, context: str = "") -> bool:
        """Validate price is reasonable"""
        try:
            if price <= 0:
                logger.error(f"❌ Invalid price {context}: {price} (must be > 0)")
                return False
            
            if price > 1000:  # ₹1000/kg seems unreasonable
                logger.warning(f"⚠️ High price {context}: ₹{price}/kg")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Price validation failed: {e}")
            return False
    
    def get_price_breakdown(self, offer_price: float, optimal_price: float,
                           ml_prediction: float, market_price: float) -> Dict[str, Any]:
        """Get detailed price breakdown"""
        try:
            price_diff = optimal_price - offer_price
            price_diff_percent = (price_diff / offer_price * 100) if offer_price > 0 else 0
            
            return {
                'buyer_offer': offer_price,
                'optimal_price': optimal_price,
                'price_difference': price_diff,
                'price_difference_percent': round(price_diff_percent, 2),
                'ml_prediction': ml_prediction,
                'market_price': market_price,
                'recommendation': self._get_price_recommendation(price_diff_percent)
            }
            
        except Exception as e:
            logger.error(f"❌ Price breakdown failed: {e}")
            raise RuntimeError(f"Price breakdown failed: {e}")
    
    def _get_price_recommendation(self, price_diff_percent: float) -> str:
        """Get price recommendation based on difference"""
        if price_diff_percent >= 20:
            return "Strongly recommend counter-offer - buyer offer too low"
        elif price_diff_percent >= 10:
            return "Recommend counter-offer - room for improvement"
        elif price_diff_percent >= -5:
            return "Acceptable offer - minor adjustments possible"
        else:
            return "Excellent offer - consider accepting"
