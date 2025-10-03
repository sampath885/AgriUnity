"""
Types and data structures for the deals app
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AgentDecision:
    """Clean decision structure with no fallbacks"""
    action: str  # ACCEPT, COUNTER_OFFER, REJECT
    new_price: float  # Must be valid price > 0
    justification_for_farmers: str
    message_to_buyer: str
    market_analysis: Dict[str, Any]
    confidence_level: str
    ml_prediction: float
    data_source: str
    farmer_simple_explanation: str = ""  # Simple 4-point explanation for farmers
