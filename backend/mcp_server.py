"""
AgriUnity MCP Performance Server
High-performance caching layer for ML models and data processing
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add Django to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

# Now import Django models and services
from deals.ml_models.pricing_engine import MLPricingEngine
from deals.ml_models.market_analyzer import MarketAnalyzer
from deals.logistics.logistics_v2_service import LogisticsV2Service
from deals.logistics.hub_optimizer import HubOptimizer
from deals.models import DealGroup
from users.models import CustomUser

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgriUnityMCPServer:
    """
    High-performance MCP server that keeps ML models and data loaded in memory
    for instant access, dramatically improving response times.
    """
    
    def __init__(self):
        self.pricing_engine = None
        self.market_analyzer = None
        self.logistics_v2_service = None
        self.hub_optimizer = None
        
        # Caching layers
        self.price_cache = {}
        self.market_data_cache = {}
        self.hub_cache = {}
        
        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0
        
        logger.info("🚀 Initializing AgriUnity MCP Server...")
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services with pre-loaded data"""
        try:
            logger.info("📊 Loading ML Pricing Engine...")
            self.pricing_engine = MLPricingEngine()
            
            logger.info("📈 Loading Market Analyzer...")
            self.market_analyzer = MarketAnalyzer()
            
            logger.info("🚚 Loading Logistics V2 Service...")
            self.logistics_v2_service = LogisticsV2Service()
            
            logger.info("🏢 Loading Hub Optimizer...")
            self.hub_optimizer = HubOptimizer()
            
            logger.info("✅ All services initialized successfully!")
            logger.info(f"💾 Memory usage: {self._get_memory_usage():.2f} MB")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters"""
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            if isinstance(v, datetime):
                key_parts.append(f"{k}:{v.isoformat()}")
            else:
                key_parts.append(f"{k}:{str(v).lower()}")
        return "|".join(key_parts)
    
    # ==================== PRICING TOOLS ====================
    
    async def predict_price_fast(self, crop_name: str, district: str, 
                                date: datetime = None, user_context: dict = None) -> Dict[str, Any]:
        """
        Fast price prediction using pre-loaded ML models and caching
        """
        self.total_requests += 1
        
        if date is None:
            date = datetime.now()
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            "price", 
            crop=crop_name, 
            district=district, 
            date=date.date(),
            user_id=user_context.get('user_id') if user_context else None
        )
        
        # Check cache first
        if cache_key in self.price_cache:
            self.cache_hits += 1
            logger.info(f"💨 Cache hit for price prediction: {crop_name} in {district}")
            return self.price_cache[cache_key]
        
        # Cache miss - compute prediction
        self.cache_misses += 1
        start_time = datetime.now()
        
        try:
            # Use pre-loaded pricing engine (no loading time)
            result = self.pricing_engine.predict_price_with_analysis(
                crop_name, district, date, user_context
            )
            
            # Add performance metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            result['performance'] = {
                'processing_time_seconds': processing_time,
                'cache_status': 'miss',
                'memory_usage_mb': self._get_memory_usage()
            }
            
            # Cache the result (keep last 1000 predictions)
            if len(self.price_cache) >= 1000:
                # Remove oldest 100 entries
                oldest_keys = list(self.price_cache.keys())[:100]
                for key in oldest_keys:
                    del self.price_cache[key]
            
            self.price_cache[cache_key] = result
            
            logger.info(f"⚡ Price prediction completed in {processing_time:.3f}s: {crop_name} = ₹{result['predicted_price']}/kg")
            return result
            
        except Exception as e:
            logger.error(f"❌ Price prediction failed: {e}")
            return {
                'error': str(e),
                'predicted_price': 0,
                'confidence_level': 'Error',
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
    
    async def get_market_data_fast(self, crop_name: str, district: str, 
                                  date: datetime = None, grade: str = None) -> Dict[str, Any]:
        """
        Fast market data retrieval using pre-loaded data and caching
        """
        self.total_requests += 1
        
        if date is None:
            date = datetime.now()
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            "market", 
            crop=crop_name, 
            district=district, 
            date=date.date(),
            grade=grade or "any"
        )
        
        # Check cache first
        if cache_key in self.market_data_cache:
            self.cache_hits += 1
            logger.info(f"💨 Cache hit for market data: {crop_name} in {district}")
            return self.market_data_cache[cache_key]
        
        # Cache miss - compute market data
        self.cache_misses += 1
        start_time = datetime.now()
        
        try:
            # Use pre-loaded market analyzer (no loading time)
            result = self.market_analyzer.get_market_data(crop_name, district, date, grade)
            
            # Add performance metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            result['performance'] = {
                'processing_time_seconds': processing_time,
                'cache_status': 'miss',
                'memory_usage_mb': self._get_memory_usage()
            }
            
            # Cache the result (keep last 500 market data requests)
            if len(self.market_data_cache) >= 500:
                # Remove oldest 50 entries
                oldest_keys = list(self.market_data_cache.keys())[:50]
                for key in oldest_keys:
                    del self.market_data_cache[key]
            
            self.market_data_cache[cache_key] = result
            
            logger.info(f"⚡ Market data retrieved in {processing_time:.3f}s: {crop_name} in {district}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Market data retrieval failed: {e}")
            return {
                'error': str(e),
                'crop_name': crop_name,
                'district': district,
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
    
    # ==================== LOGISTICS TOOLS ====================
    
    async def compute_hub_v2_fast(self, deal_group_id: int) -> Dict[str, Any]:
        """
        Fast hub computation using pre-loaded logistics service
        """
        self.total_requests += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key("hub_v2", group_id=deal_group_id)
        
        # Check cache first
        if cache_key in self.hub_cache:
            self.cache_hits += 1
            logger.info(f"💨 Cache hit for hub computation: Group {deal_group_id}")
            return self.hub_cache[cache_key]
        
        # Cache miss - compute hub
        self.cache_misses += 1
        start_time = datetime.now()
        
        try:
            # Get deal group
            deal_group = DealGroup.objects.get(id=deal_group_id)
            
            # Use pre-loaded logistics service (no loading time)
            optimal_hub = self.logistics_v2_service.find_optimal_hub_v2(deal_group)
            
            result = {
                'deal_group_id': deal_group_id,
                'optimal_hub': optimal_hub.__dict__ if optimal_hub else None,
                'method': 'V2',
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'miss',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
            
            # Cache the result (keep last 200 hub computations)
            if len(self.hub_cache) >= 200:
                # Remove oldest 20 entries
                oldest_keys = list(self.hub_cache.keys())[:20]
                for key in oldest_keys:
                    del self.hub_cache[key]
            
            self.hub_cache[cache_key] = result
            
            logger.info(f"⚡ Hub computation completed in {result['performance']['processing_time_seconds']:.3f}s: Group {deal_group_id}")
            return result
            
        except DealGroup.DoesNotExist:
            return {
                'error': f'Deal group {deal_group_id} not found',
                'deal_group_id': deal_group_id,
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
        except Exception as e:
            logger.error(f"❌ Hub computation failed: {e}")
            return {
                'error': str(e),
                'deal_group_id': deal_group_id,
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
    
    async def compute_hub_v1_fast(self, deal_group_id: int) -> Dict[str, Any]:
        """
        Fast hub computation using pre-loaded hub optimizer (V1)
        """
        self.total_requests += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key("hub_v1", group_id=deal_group_id)
        
        # Check cache first
        if cache_key in self.hub_cache:
            self.cache_hits += 1
            logger.info(f"💨 Cache hit for hub V1 computation: Group {deal_group_id}")
            return self.hub_cache[cache_key]
        
        # Cache miss - compute hub
        self.cache_misses += 1
        start_time = datetime.now()
        
        try:
            # Get deal group
            deal_group = DealGroup.objects.get(id=deal_group_id)
            
            # Use pre-loaded hub optimizer (no loading time)
            optimal_hub = self.hub_optimizer.compute_and_recommend_hub(deal_group)
            
            result = {
                'deal_group_id': deal_group_id,
                'optimal_hub': optimal_hub,
                'method': 'V1',
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'miss',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
            
            # Cache the result
            if len(self.hub_cache) >= 200:
                oldest_keys = list(self.hub_cache.keys())[:20]
                for key in oldest_keys:
                    del self.hub_cache[key]
            
            self.hub_cache[cache_key] = result
            
            logger.info(f"⚡ Hub V1 computation completed in {result['performance']['processing_time_seconds']:.3f}s: Group {deal_group_id}")
            return result
            
        except DealGroup.DoesNotExist:
            return {
                'error': f'Deal group {deal_group_id} not found',
                'deal_group_id': deal_group_id,
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
        except Exception as e:
            logger.error(f"❌ Hub V1 computation failed: {e}")
            return {
                'error': str(e),
                'deal_group_id': deal_group_id,
                'performance': {
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'cache_status': 'error',
                    'memory_usage_mb': self._get_memory_usage()
                }
            }
    
    # ==================== UTILITY TOOLS ====================
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get server performance statistics"""
        cache_hit_rate = (self.cache_hits / max(self.total_requests, 1)) * 100
        
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'memory_usage_mb': round(self._get_memory_usage(), 2),
            'price_cache_size': len(self.price_cache),
            'market_cache_size': len(self.market_data_cache),
            'hub_cache_size': len(self.hub_cache),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }
    
    async def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """Clear specified cache"""
        cleared = {}
        
        if cache_type in ["all", "price"]:
            cleared['price_cache'] = len(self.price_cache)
            self.price_cache.clear()
        
        if cache_type in ["all", "market"]:
            cleared['market_cache'] = len(self.market_data_cache)
            self.market_data_cache.clear()
        
        if cache_type in ["all", "hub"]:
            cleared['hub_cache'] = len(self.hub_cache)
            self.hub_cache.clear()
        
        logger.info(f"🧹 Cache cleared: {cleared}")
        return {
            'cleared_entries': cleared,
            'memory_usage_mb': round(self._get_memory_usage(), 2)
        }
    
    def start(self):
        """Start the MCP server"""
        self.start_time = datetime.now()
        logger.info("🚀 AgriUnity MCP Server started successfully!")
        logger.info(f"💾 Initial memory usage: {self._get_memory_usage():.2f} MB")
        logger.info("📊 Available tools:")
        logger.info("  - predict_price_fast(crop, district, date, user_context)")
        logger.info("  - get_market_data_fast(crop, district, date, grade)")
        logger.info("  - compute_hub_v2_fast(deal_group_id)")
        logger.info("  - compute_hub_v1_fast(deal_group_id)")
        logger.info("  - get_performance_stats()")
        logger.info("  - clear_cache(cache_type)")

# Global MCP server instance
mcp_server = None

def get_mcp_server() -> AgriUnityMCPServer:
    """Get or create the global MCP server instance"""
    global mcp_server
    if mcp_server is None:
        mcp_server = AgriUnityMCPServer()
        mcp_server.start()
    return mcp_server

# Example usage and testing
async def test_mcp_server():
    """Test the MCP server functionality"""
    server = get_mcp_server()
    
    # Test price prediction
    print("\n🧪 Testing price prediction...")
    price_result = await server.predict_price_fast(
        crop_name="rice",
        district="krishna",
        date=datetime.now(),
        user_context={"user_id": 1}
    )
    print(f"Price result: {json.dumps(price_result, indent=2, default=str)}")
    
    # Test market data
    print("\n🧪 Testing market data...")
    market_result = await server.get_market_data_fast(
        crop_name="rice",
        district="krishna",
        date=datetime.now()
    )
    print(f"Market result: {json.dumps(market_result, indent=2, default=str)}")
    
    # Test performance stats
    print("\n🧪 Testing performance stats...")
    stats = await server.get_performance_stats()
    print(f"Performance stats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_mcp_server())

