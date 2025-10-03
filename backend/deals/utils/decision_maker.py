"""
Decision Maker
Clean decision logic with no fallbacks
"""

import logging
from typing import Dict, Any
from .types import AgentDecision

logger = logging.getLogger(__name__)

class DecisionMaker:
    """Clean decision maker - NO FALLBACKS"""
    
    def __init__(self):
        self.decision_thresholds = {
            'accept_threshold': 0.95,      # Accept if offer is 95% of optimal
            'counter_threshold': 0.85,     # Counter if offer is 85% of optimal
            'reject_threshold': 0.70,      # Reject if offer is below 70% of optimal
        }
        
        logger.info("✅ Decision maker initialized")
    
    def make_decision(self, offer_price: float, optimal_price: float,
                     ml_prediction: float, market_data: Dict[str, Any]) -> AgentDecision:
        """Make negotiation decision - NO FALLBACKS"""
        
        try:
            if offer_price <= 0:
                raise ValueError(f"Invalid offer price: {offer_price}")
            
            if optimal_price <= 0:
                raise ValueError(f"Invalid optimal price: {optimal_price}")
            
            if ml_prediction <= 0:
                raise ValueError(f"Invalid ML prediction: {ml_prediction}")
            
            # Calculate offer ratio
            offer_ratio = offer_price / optimal_price
            
            # Make decision based on thresholds
            if offer_ratio >= self.decision_thresholds['accept_threshold']:
                decision = self._create_accept_decision(offer_price, optimal_price, ml_prediction, market_data)
            elif offer_ratio >= self.decision_thresholds['counter_threshold']:
                decision = self._create_counter_decision(offer_price, optimal_price, ml_prediction, market_data)
            else:
                decision = self._create_reject_decision(offer_price, optimal_price, ml_prediction, market_data)
            
            # Validate decision
            if decision.new_price <= 0:
                raise ValueError(f"Invalid decision price: {decision.new_price}")
            
            logger.info(f"✅ Decision made: {decision.action} at ₹{decision.new_price}/kg")
            return decision
            
        except Exception as e:
            logger.error(f"❌ Decision making failed: {e}")
            raise RuntimeError(f"Decision making failed: {e}")
    
    def _create_accept_decision(self, offer_price: float, optimal_price: float,
                               ml_prediction: float, market_data: Dict[str, Any]) -> AgentDecision:
        """Create accept decision"""
        
        justification = (
            f"Excellent offer! ₹{offer_price}/kg is very close to our optimal price "
            f"of ₹{optimal_price}/kg. This represents fair value for both parties "
            f"based on ML analysis (₹{ml_prediction}/kg) and current market conditions."
        )
        
        message_to_buyer = (
            f"Thank you for your competitive offer of ₹{offer_price}/kg! "
            f"This price aligns well with our market analysis and ML predictions. "
            f"We accept your offer and look forward to completing this transaction."
        )
        
        return AgentDecision(
            action="ACCEPT",
            new_price=offer_price,
            justification_for_farmers=justification,
            message_to_buyer=message_to_buyer,
            market_analysis=market_data,
            confidence_level="High - ML and market data aligned",
            ml_prediction=ml_prediction,
            data_source="ML Engine + BIG_DATA.csv"
        )
    
    def _create_counter_decision(self, offer_price: float, optimal_price: float,
                                ml_prediction: float, market_data: Dict[str, Any]) -> AgentDecision:
        """Create counter-offer decision"""
        
        # Calculate counter price (slightly below optimal)
        counter_price = round(optimal_price * 0.98, 2)
        
        justification = (
            f"Your offer of ₹{offer_price}/kg is reasonable but below our optimal "
            f"price of ₹{optimal_price}/kg. Based on ML analysis (₹{ml_prediction}/kg) "
            f"and current market conditions, we suggest ₹{counter_price}/kg to ensure "
            f"fair value for our farmers while maintaining competitive pricing."
        )
        
        message_to_buyer = (
            f"Thank you for your offer of ₹{offer_price}/kg. After comprehensive "
            f"analysis using ML predictions and market data, we recommend ₹{counter_price}/kg. "
            f"This ensures fair compensation for our farmers while providing you "
            f"with quality produce at competitive rates."
        )
        
        return AgentDecision(
            action="COUNTER_OFFER",
            new_price=counter_price,
            justification_for_farmers=justification,
            message_to_buyer=message_to_buyer,
            market_analysis=market_data,
            confidence_level="High - ML and market data support counter",
            ml_prediction=ml_prediction,
            data_source="ML Engine + BIG_DATA.csv"
        )
    
    def _create_reject_decision(self, offer_price: float, optimal_price: float,
                               ml_prediction: float, market_data: Dict[str, Any]) -> AgentDecision:
        """Create reject decision"""
        
        # Calculate minimum acceptable price
        min_price = round(optimal_price * 0.90, 2)
        
        justification = (
            f"Your offer of ₹{offer_price}/kg is significantly below our optimal "
            f"price of ₹{optimal_price}/kg. Based on ML analysis (₹{ml_prediction}/kg) "
            f"and current market conditions, we cannot accept below ₹{min_price}/kg. "
            f"This ensures our farmers receive fair compensation for their quality produce."
        )
        
        message_to_buyer = (
            f"Thank you for your offer of ₹{offer_price}/kg. However, this price "
            f"is significantly below current market rates and our ML-optimized "
            f"pricing. We recommend ₹{min_price}/kg as the minimum acceptable price "
            f"to ensure fair value for our farmers."
        )
        
        return AgentDecision(
            action="REJECT",
            new_price=min_price,
            justification_for_farmers=justification,
            message_to_buyer=message_to_buyer,
            market_analysis=market_data,
            confidence_level="High - Strong ML and market data support",
            ml_prediction=ml_prediction,
            data_source="ML Engine + BIG_DATA.csv"
        )
    
    def get_decision_summary(self, decision: AgentDecision) -> Dict[str, Any]:
        """Get decision summary for logging"""
        
        try:
            return {
                'action': decision.action,
                'new_price': decision.new_price,
                'confidence_level': decision.confidence_level,
                'ml_prediction': decision.ml_prediction,
                'data_source': decision.data_source,
                'justification_length': len(decision.justification_for_farmers),
                'message_length': len(decision.message_to_buyer)
            }
            
        except Exception as e:
            logger.error(f"❌ Decision summary failed: {e}")
            return {"error": str(e)}
    
    def validate_decision(self, decision: AgentDecision) -> bool:
        """Validate decision is complete and valid"""
        
        try:
            # Check required fields
            required_fields = ['action', 'new_price', 'justification_for_farmers', 
                             'message_to_buyer', 'market_analysis', 'confidence_level',
                             'ml_prediction', 'data_source']
            
            for field in required_fields:
                if not hasattr(decision, field) or getattr(decision, field) is None:
                    logger.error(f"❌ Missing required field: {field}")
                    return False
            
            # Validate action
            valid_actions = ['ACCEPT', 'COUNTER_OFFER', 'REJECT']
            if decision.action not in valid_actions:
                logger.error(f"❌ Invalid action: {decision.action}")
                return False
            
            # Validate price
            if decision.new_price <= 0:
                logger.error(f"❌ Invalid price: {decision.new_price}")
                return False
            
            # Validate ML prediction
            if decision.ml_prediction <= 0:
                logger.error(f"❌ Invalid ML prediction: {decision.ml_prediction}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Decision validation failed: {e}")
            return False
