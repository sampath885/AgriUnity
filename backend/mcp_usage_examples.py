"""
AgriUnity MCP Server Usage Examples
Demonstrates how to use the MCP server for high-performance operations
"""

import asyncio
import json
from datetime import datetime
from mcp_server import get_mcp_server

async def example_price_prediction():
    """Example: Fast price prediction using MCP server"""
    print("🌾 Example: Price Prediction")
    print("=" * 50)
    
    server = get_mcp_server()
    
    # Predict rice price in Krishna district
    result = await server.predict_price_fast(
        crop_name="rice",
        district="krishna",
        date=datetime.now(),
        user_context={"user_id": 1, "latitude": 16.4, "longitude": 80.6}
    )
    
    print(f"💰 Predicted Price: ₹{result['predicted_price']}/kg")
    print(f"🎯 Confidence: {result['confidence_level']}")
    print(f"⚡ Processing Time: {result['performance']['processing_time_seconds']:.3f}s")
    print(f"💾 Memory Usage: {result['performance']['memory_usage_mb']:.2f} MB")
    print()

async def example_market_data():
    """Example: Fast market data retrieval using MCP server"""
    print("📊 Example: Market Data Analysis")
    print("=" * 50)
    
    server = get_mcp_server()
    
    # Get market data for wheat in Pune
    result = await server.get_market_data_fast(
        crop_name="wheat",
        district="pune",
        date=datetime.now(),
        grade="FAQ"
    )
    
    print(f"🌾 Crop: {result['crop_name']}")
    print(f"📍 District: {result['district']}")
    print(f"📈 Data Points: {result['data_points']}")
    print(f"💰 Current Price: ₹{result['price_analysis']['current_price_per_kg']:.2f}/kg")
    print(f"📊 Average Price: ₹{result['price_analysis']['average_price_per_kg']:.2f}/kg")
    print(f"📈 Price Trend: {result['price_analysis']['price_trend']}")
    print(f"⚡ Processing Time: {result['performance']['processing_time_seconds']:.3f}s")
    print()

async def example_hub_optimization():
    """Example: Fast hub optimization using MCP server"""
    print("🚚 Example: Hub Optimization")
    print("=" * 50)
    
    server = get_mcp_server()
    
    # Compute optimal hub for deal group (assuming group ID 1 exists)
    result = await server.compute_hub_v2_fast(deal_group_id=1)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        print("💡 Note: Make sure deal group ID 1 exists in your database")
    else:
        print(f"🏢 Optimal Hub: {result['optimal_hub']}")
        print(f"🔧 Method: {result['method']}")
        print(f"⚡ Processing Time: {result['performance']['processing_time_seconds']:.3f}s")
    print()

async def example_performance_comparison():
    """Example: Performance comparison between MCP and direct calls"""
    print("⚡ Example: Performance Comparison")
    print("=" * 50)
    
    server = get_mcp_server()
    
    # Test multiple requests to show caching benefits
    crops = ["rice", "wheat", "maize", "tomato", "potato"]
    districts = ["krishna", "pune", "delhi", "mumbai", "bangalore"]
    
    print("🔄 Making 10 price prediction requests...")
    start_time = datetime.now()
    
    for i in range(10):
        crop = crops[i % len(crops)]
        district = districts[i % len(districts)]
        
        result = await server.predict_price_fast(
            crop_name=crop,
            district=district,
            date=datetime.now()
        )
        
        print(f"  {i+1:2d}. {crop:8s} in {district:10s}: ₹{result['predicted_price']:6.2f}/kg ({result['performance']['cache_status']})")
    
    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total Time: {total_time:.3f}s")
    print(f"📊 Average per request: {total_time/10:.3f}s")
    
    # Show performance stats
    stats = await server.get_performance_stats()
    print(f"🎯 Cache Hit Rate: {stats['cache_hit_rate_percent']}%")
    print(f"💾 Memory Usage: {stats['memory_usage_mb']:.2f} MB")
    print()

async def example_cache_management():
    """Example: Cache management and statistics"""
    print("🧹 Example: Cache Management")
    print("=" * 50)
    
    server = get_mcp_server()
    
    # Get initial stats
    stats = await server.get_performance_stats()
    print("📊 Initial Cache Status:")
    print(f"  Price Cache: {stats['price_cache_size']} entries")
    print(f"  Market Cache: {stats['market_cache_size']} entries")
    print(f"  Hub Cache: {stats['hub_cache_size']} entries")
    print(f"  Memory Usage: {stats['memory_usage_mb']:.2f} MB")
    print()
    
    # Clear price cache
    print("🧹 Clearing price cache...")
    clear_result = await server.clear_cache("price")
    print(f"  Cleared: {clear_result['cleared_entries']}")
    print(f"  Memory after clear: {clear_result['memory_usage_mb']:.2f} MB")
    print()
    
    # Get updated stats
    stats = await server.get_performance_stats()
    print("📊 Updated Cache Status:")
    print(f"  Price Cache: {stats['price_cache_size']} entries")
    print(f"  Market Cache: {stats['market_cache_size']} entries")
    print(f"  Hub Cache: {stats['hub_cache_size']} entries")
    print(f"  Memory Usage: {stats['memory_usage_mb']:.2f} MB")
    print()

async def main():
    """Run all examples"""
    print("🚀 AgriUnity MCP Server Examples")
    print("=" * 60)
    print()
    
    try:
        await example_price_prediction()
        await example_market_data()
        await example_hub_optimization()
        await example_performance_comparison()
        await example_cache_management()
        
        print("✅ All examples completed successfully!")
        print("\n💡 Key Benefits of MCP Server:")
        print("  - Pre-loaded ML models (no loading time)")
        print("  - Intelligent caching (faster repeated requests)")
        print("  - Memory optimization (shared resources)")
        print("  - Performance monitoring (real-time stats)")
        print("  - Error handling (graceful fallbacks)")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

