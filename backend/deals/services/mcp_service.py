"""
MCP Service Integration Layer
Provides high-performance access to MCP server for Django views
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class MCPService:
    """
    Service layer that provides synchronous access to MCP server
    for use in Django views and other synchronous code
    """
    
    _instance = None
    _mcp_server = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPService, cls).__new__(cls)
        return cls._instance
    
    def _get_mcp_server(self):
        """Get or initialize MCP server"""
        if self._mcp_server is None:
            try:
                from mcp_server import get_mcp_server
                self._mcp_server = get_mcp_server()
                logger.info("✅ MCP server initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize MCP server: {e}")
                raise
        return self._mcp_server
    
    def _run_async(self, coro):
        """Run async function in sync context"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    # ==================== PRICING METHODS ====================
    
    def predict_price_fast(self, crop_name: str, district: str, 
                          date: datetime = None, user_context: dict = None) -> Dict[str, Any]:
        """
        Fast price prediction using MCP server
        Returns the same format as the original MLPricingEngine
        """
        try:
            if date is None:
                date = datetime.now()
            
            mcp_server = self._get_mcp_server()
            result = self._run_async(
                mcp_server.predict_price_fast(crop_name, district, date, user_context)
            )
            
            logger.info(f"⚡ MCP price prediction: {crop_name} in {district} = ₹{result.get('predicted_price', 'N/A')}/kg")
            return result
            
        except Exception as e:
            logger.error(f"❌ MCP price prediction failed: {e}")
            # Fallback to original pricing engine
            return self._fallback_price_prediction(crop_name, district, date, user_context)
    
    def get_market_data_fast(self, crop_name: str, district: str, 
                            date: datetime = None, grade: str = None) -> Dict[str, Any]:
        """
        Fast market data retrieval using MCP server
        """
        try:
            if date is None:
                date = datetime.now()
            
            mcp_server = self._get_mcp_server()
            result = self._run_async(
                mcp_server.get_market_data_fast(crop_name, district, date, grade)
            )
            
            logger.info(f"⚡ MCP market data: {crop_name} in {district} = {result.get('data_points', 'N/A')} points")
            return result
            
        except Exception as e:
            logger.error(f"❌ MCP market data failed: {e}")
            # Fallback to original market analyzer
            return self._fallback_market_data(crop_name, district, date, grade)
    
    # ==================== LOGISTICS METHODS ====================
    
    def compute_hub_v2_fast(self, deal_group_id: int) -> Dict[str, Any]:
        """
        Fast hub computation using MCP server V2
        """
        try:
            mcp_server = self._get_mcp_server()
            result = self._run_async(
                mcp_server.compute_hub_v2_fast(deal_group_id)
            )
            
            logger.info(f"⚡ MCP hub V2: Group {deal_group_id} = {result.get('optimal_hub', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ MCP hub V2 failed: {e}")
            # Fallback to original logistics service
            return self._fallback_hub_v2(deal_group_id)
    
    def compute_hub_v1_fast(self, deal_group_id: int) -> Dict[str, Any]:
        """
        Fast hub computation using MCP server V1
        """
        try:
            mcp_server = self._get_mcp_server()
            result = self._run_async(
                mcp_server.compute_hub_v1_fast(deal_group_id)
            )
            
            logger.info(f"⚡ MCP hub V1: Group {deal_group_id} = {result.get('optimal_hub', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ MCP hub V1 failed: {e}")
            # Fallback to original hub optimizer
            return self._fallback_hub_v1(deal_group_id)
    
    # ==================== UTILITY METHODS ====================
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get MCP server performance statistics"""
        try:
            mcp_server = self._get_mcp_server()
            return self._run_async(mcp_server.get_performance_stats())
        except Exception as e:
            logger.error(f"❌ Failed to get performance stats: {e}")
            return {"error": str(e)}
    
    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """Clear MCP server cache"""
        try:
            mcp_server = self._get_mcp_server()
            return self._run_async(mcp_server.clear_cache(cache_type))
        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {e}")
            return {"error": str(e)}
    
    # ==================== FALLBACK METHODS ====================
    
    def _fallback_price_prediction(self, crop_name: str, district: str, 
                                  date: datetime, user_context: dict) -> Dict[str, Any]:
        """Fallback to original pricing engine when MCP fails"""
        try:
            from deals.ml_models.pricing_engine import MLPricingEngine
            engine = MLPricingEngine()
            result = engine.predict_price_with_analysis(crop_name, district, date, user_context)
            result['performance'] = {
                'processing_time_seconds': 0.0,
                'cache_status': 'fallback',
                'memory_usage_mb': 0.0
            }
            logger.info(f"🔄 Fallback price prediction: {crop_name} in {district}")
            return result
        except Exception as e:
            logger.error(f"❌ Fallback price prediction failed: {e}")
            return {
                'predicted_price': 25.0,
                'confidence_level': 'Error - Fallback failed',
                'error': str(e),
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'error',
                    'memory_usage_mb': 0.0
                }
            }
    
    def _fallback_market_data(self, crop_name: str, district: str, 
                             date: datetime, grade: str) -> Dict[str, Any]:
        """Fallback to original market analyzer when MCP fails"""
        try:
            from deals.ml_models.market_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer()
            result = analyzer.get_market_data(crop_name, district, date, grade)
            result['performance'] = {
                'processing_time_seconds': 0.0,
                'cache_status': 'fallback',
                'memory_usage_mb': 0.0
            }
            logger.info(f"🔄 Fallback market data: {crop_name} in {district}")
            return result
        except Exception as e:
            logger.error(f"❌ Fallback market data failed: {e}")
            return {
                'crop_name': crop_name,
                'district': district,
                'error': str(e),
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'error',
                    'memory_usage_mb': 0.0
                }
            }
    
    def _fallback_hub_v2(self, deal_group_id: int) -> Dict[str, Any]:
        """Fallback to original logistics service when MCP fails"""
        try:
            from deals.logistics.logistics_v2_service import LogisticsV2Service
            from deals.models import DealGroup
            
            deal_group = DealGroup.objects.get(id=deal_group_id)
            service = LogisticsV2Service()
            optimal_hub = service.find_optimal_hub_v2(deal_group)
            
            return {
                'deal_group_id': deal_group_id,
                'optimal_hub': optimal_hub.__dict__ if optimal_hub else None,
                'method': 'V2_Fallback',
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'fallback',
                    'memory_usage_mb': 0.0
                }
            }
        except Exception as e:
            logger.error(f"❌ Fallback hub V2 failed: {e}")
            return {
                'deal_group_id': deal_group_id,
                'error': str(e),
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'error',
                    'memory_usage_mb': 0.0
                }
            }
    
    def _fallback_hub_v1(self, deal_group_id: int) -> Dict[str, Any]:
        """Fallback to original hub optimizer when MCP fails"""
        try:
            from deals.logistics.hub_optimizer import HubOptimizer
            from deals.models import DealGroup
            
            deal_group = DealGroup.objects.get(id=deal_group_id)
            optimizer = HubOptimizer()
            optimal_hub = optimizer.compute_and_recommend_hub(deal_group)
            
            return {
                'deal_group_id': deal_group_id,
                'optimal_hub': optimal_hub,
                'method': 'V1_Fallback',
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'fallback',
                    'memory_usage_mb': 0.0
                }
            }
        except Exception as e:
            logger.error(f"❌ Fallback hub V1 failed: {e}")
            return {
                'deal_group_id': deal_group_id,
                'error': str(e),
                'performance': {
                    'processing_time_seconds': 0.0,
                    'cache_status': 'error',
                    'memory_usage_mb': 0.0
                }
            }

# Global service instance
mcp_service = MCPService()

def get_mcp_service() -> MCPService:
    """Get the global MCP service instance"""
    return mcp_service

